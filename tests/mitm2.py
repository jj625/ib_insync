"""
single-session, single-client server
"""
import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio.log import logger
from collections.abc import Awaitable, Callable
import datetime
import zoneinfo
TZ_NewYork=zoneinfo.ZoneInfo('America/New_York')
import logging, argparse
from xml.sax import handler
# from rich.logging import RichHandler
import colorama
import struct
import time
from typing import Dict, Type, cast
from enum import Enum, auto, IntEnum, EnumMeta

import google.protobuf.message as gpm
def proto_to_nested(msg: gpm.Message) -> list:
    result = []
    for descriptor, value in msg.ListFields():
        if hasattr(value, 'ListFields'):  # nested Message
            result.append((descriptor.name, proto_to_nested(value)))
        else:
            result.append((descriptor.name, value))
    return result

def format_protobuf_message(msg):
    _s = msg.__str__()
    # replace '\n' with ' ,'
    _s = _s.rstrip('\n').replace('\n', ', ')
    return _s

def enum_from_class(cls, enum_name=''):
    enum_name = enum_name or cls.__name__ + "Enum"

    members: Dict[str, int] = {
        name: value
        for name, value in cls.__dict__.items()
        if name.isupper() and isinstance(value, int)
    }
    return IntEnum(enum_name, members)

def make_enum(cls: type) -> type:
    attrs = {k: v for k, v in vars(cls).items()
             if not k.startswith('_') and isinstance(v, int)}
    return cast(type, IntEnum(cls.__name__, attrs))

from ibapi.message import IN, OUT
from ib_insync.objects import TickTypeEnum
IBMsgInEnum = make_enum(IN)
IBMsgOutEnum = make_enum(OUT)

from ib_insync.client import MIN_SERVER_VER_PROTOBUF, PROTOBUF_MSG_ID

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 4002          # your client connects here
TWS_HOST    = "127.0.0.1"
TWS_PORT    = 7497          # real TWS/Gateway port

class GWState(Enum):
    INITIAL = auto()
    HANDSHAKE = auto()
    READY = auto() # once in this state, we expect StartApi
    # READY_seen_StartApi = auto()
    READY_waitNextValidId = auto() # after seeing StartApi, we expect nextValidId
    REQUESTS = auto()
    CLOSED = auto()

# # -------------------------------
# # IBKR message framing utilities
# # -------------------------------

# async def read_ib_message_from_buffer(buffer: bytes):
#     """Try to parse one IBKR-framed message from a buffer: [4-byte len][null-delimited text]."""
#     if len(buffer) < 4:
#         return None, buffer
#     msg_len = struct.unpack(">I", buffer[:4])[0]
#     if len(buffer) < 4 + msg_len:
#         return None, buffer
#     payload = buffer[4:4 + msg_len]
#     remaining = buffer[4 + msg_len:]
#     return payload.decode("utf-8", errors="backslashreplace").split("\0"), remaining

# def encode_ib_message(fields):
#     """Encode fields into IBKR framing."""
#     payload = ("\0".join(fields) + "\0").encode("utf-8")
#     return struct.pack(">I", len(payload)) + payload

# # -------------------------------
# # Minimal IBKR message IDs
# # -------------------------------

# REQ_MKT_DATA          = 1
# CANCEL_MKT_DATA       = 2
# REQ_CONTRACT_DETAILS  = 9
# START_API             = 71

# TICK_PRICE            = 1
# CONTRACT_DETAILS      = 10
# CONTRACT_DETAILS_END  = 11

class FakeIBGW:
    def __init__(self, host, port, fakegw_port, clientid, enable_sim=False):
        self.logger = logging.getLogger(__name__)
        self.state = GWState.INITIAL
        self.real_tws_host = host
        self.proxy_host = LISTEN_HOST
        self.real_tws_port = port
        self.proxy_port = fakegw_port
        self.real_tws_clientid = clientid
        self._data = b''
        self.static_db = None
        self.synthetic_engine = None
        self.enable_sim = enable_sim

    async def start(self):
        """Start listening like a real IB Gateway."""
        # single-session server pattern
        self._stop = asyncio.Future()
        self.server = await asyncio.start_server(self._on_client, self.proxy_host, self.proxy_port)
        self.logger.info(f"MITM proxy listening on {self.proxy_host}:{self.proxy_port}")
        async with self.server:
            # await server.serve_forever()
            await self._stop

    async def stop(self):
        """Stop the MITM proxy."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

    # ---------------------------
    # Client session handler
    # ---------------------------

    async def _on_client(self, reader: StreamReader, writer: StreamWriter):
        """
        Handle a single IBAPI client session.
        """
        session = FakeIBGWSession(reader, writer, 
            self.real_tws_host, self.real_tws_port, 
            self.static_db, self.synthetic_engine, 
            enable_sim=self.enable_sim)
        await session.run()
        self.logger.info(f"Client session finished")
        self._stop.set_result(None)

    def _onSocketHasData(self, data: bytes):
        """
        Borrowed from ib_insync.Client
        """
        while True:
            if len(self._data) <= 4:
                break
            # 4 byte prefix tells the message length
            msgEnd = 4 + struct.unpack('>I', self._data[:4])[0]
            if len(self._data) < msgEnd:
                # insufficient data for now
                break
            rawMsg = self._data[4:msgEnd]
            self._data = self._data[msgEnd:]

            # Legacy framing: all text, null-delimited
            msg = rawMsg.decode(errors='backslashreplace')
            fields = msg.split('\0')

# -------------------------------
# Per-connection session object
# -------------------------------
def ts():
    return datetime.datetime.now(TZ_NewYork).isoformat(timespec="microseconds")

class FakeIBGWSession:
    """
    Handles one client connection, including:
    - handshake
    - StartAPI
    - static requests
    - streaming requests
    """

    def __init__(self, client_reader: StreamReader, client_writer: StreamWriter,
            tws_host, tws_port,
            static_db, synthetic_engine,
            enable_sim):
        self.client_reader = client_reader
        self.client_writer = client_writer
        self.tws_host = tws_host
        self.tws_port = tws_port
        self.static_db = static_db
        self.synthetic_engine = synthetic_engine
        self.state = GWState.INITIAL
        self.active_streams = {}  # reqId -> task
        self.enable_sim = enable_sim
        self.client_buffer = bytearray()
        self.server_buffer = bytearray()
        self.server_supports_protobuf = False
        self.server_version = ''
        self.parser: Callable[[bytearray], Awaitable[tuple[int, list[str], bytearray]]] = self._try_parse
        self.logger = logging.getLogger(__name__)

    async def run(self):
        server_reader, server_writer = await asyncio.open_connection(self.tws_host, self.tws_port)
        cancel_event = asyncio.Event()

        async def client_to_server():
            try:
                while not cancel_event.is_set():
                    data = await self.client_reader.read(4096*10)
                    if not data:
                        # eof from one side → trigger shutdown
                        cancel_event.set()
                        break

                    # raw logging (binary-safe)
                    self.logger.info(f"{ts()} C→S {len(data)} bytes")

                    # Always relay
                    server_writer.write(data)
                    await server_writer.drain()

                    # Optionally intercept client messages
                    if self.enable_sim:
                        self.client_buffer.extend(data)
                        await self._process_client_messages(server_writer)
            except asyncio.CancelledError:
                pass
            finally:
                self.logger.info(f"Client to server task finished")
                server_writer.close()
                await server_writer.wait_closed()

        async def server_to_client():
            try:
                while not cancel_event.is_set():
                    data = await server_reader.read(4096*10)
                    if not data:
                        cancel_event.set()
                        break

                    # raw logging (binary-safe)
                    self.logger.info(f"{ts()} S→C {len(data)} bytes")

                    # Always relay
                    self.client_writer.write(data)
                    await self.client_writer.drain()

                    # Optionally intercept server messages
                    if self.enable_sim:
                        self.server_buffer.extend(data)
                        await self._process_server_messages()
            except asyncio.CancelledError:
                pass
            finally:
                self.logger.info(f"Server to client task finished")
                self.client_writer.close()
                await self.client_writer.wait_closed()

        # Connect to real TWS/Gateway
        server_reader, server_writer = await asyncio.open_connection(self.tws_host, self.tws_port)
        cancel_event = asyncio.Event()
        tasks = [
            asyncio.create_task(cancel_event.wait(), name='cancel_event'), # awaitable
            asyncio.create_task(client_to_server(), name='C→S'),
            asyncio.create_task(server_to_client(), name='S→C'),
        ]

        # Wait until either pipe finishes
        self.logger.info(f"Connection established. Waiting for return...")
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        self.logger.info(f"Connection finished. Shutting down...")
        self.logger.info(f"done: {done}, pending: {pending}")

        # trigger shutdown
        cancel_event.set()

        # 🔥 CRITICAL FIX: close transports so read() wakes up
        self.client_writer.transport.close()
        server_writer.transport.close()

        # Cancel the other direction
        for t in pending:
            self.logger.info(f"Cancelling task: {t}")
            t.cancel()

        await asyncio.gather(*pending, return_exceptions=True)

        # server_writer.close()
        # client_writer.close()
        # await server_writer.wait_closed()
        # await client_writer.wait_closed()

        self.logger.info(f"Connection closed")

    # ---------------------------
    # Main session loop
    # ---------------------------

    # async def run2(self):


    #     try:
    #         await self._send_handshake()

    #         buffer = b''
    #         while True:
    #             fields = await read_ib_message(self.reader)
    #             if not fields:
    #                 break
    #             await self._dispatch(fields)

    #     except (asyncio.IncompleteReadError, ConnectionResetError):
    #         pass
    #     finally:
    #         await self._shutdown()

    # # ---------------------------
    # # Handshake
    # # ---------------------------

    # async def _send_handshake(self):
    #     """
    #     Send serverVersion + connectionTime.
    #     """
    #     server_version = "151"
    #     connection_time = "20260101 12:00:00"
    #     self.writer.write(encode_ib_message([server_version, connection_time]))
    #     await self.writer.drain()
    #     self.state = GWState.READY

    # ---------------------------
    # Message dispatcher
    # ---------------------------

    # async def _dispatch(self, fields: list[str]):
    #     msg_id = int(fields[0])

    #     if self.state == GWState.READY:
    #         if msg_id == START_API:
    #             self.state = GWState.REQUESTS
    #             return

    #     if self.state == GWState.REQUESTS:
    #         if msg_id == REQ_MKT_DATA:
    #             await self._handle_req_mkt_data(fields)
    #         elif msg_id == CANCEL_MKT_DATA:
    #             await self._handle_cancel_mkt_data(fields)
    #         elif msg_id == REQ_CONTRACT_DETAILS:
    #             await self._handle_req_contract_details(fields)

    # # ---------------------------
    # # Static request handler
    # # ---------------------------

    # async def _handle_req_contract_details(self, fields: list[str]):
    #     key = tuple(fields[1:])
    #     responses = self.static_db.lookup_contract_details(key)

    #     for resp_fields in responses:
    #         self.writer.write(encode_ib_message(resp_fields))
    #         await self.writer.drain()

    #     # End marker
    #     self.writer.write(encode_ib_message([str(CONTRACT_DETAILS_END)]))
    #     await self.writer.drain()

    # ---------------------------
    # Streaming request handlers
    # ---------------------------

    async def _handle_req_mkt_data(self, fields: list[str]):
        req_id = int(fields[1])
        contract_key = tuple(fields[2:])

        async def stream_task():
            async for tick in self.synthetic_engine.stream_ticks(contract_key, req_id):
                pass
                # self.writer.write(tick)
                # await self.writer.drain()

        task = asyncio.create_task(stream_task())
        self.active_streams[req_id] = task

    async def _handle_cancel_mkt_data(self, fields: list[str]):
        req_id = int(fields[1])
        task = self.active_streams.pop(req_id, None)
        if task:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    # ---------------------------
    # Shutdown
    # ---------------------------

    async def _shutdown(self):
        for task in self.active_streams.values():
            task.cancel()
        await asyncio.gather(*self.active_streams.values(), return_exceptions=True)

        # self.writer.close()
        # await self.writer.wait_closed()

    # ========================================================
    # Inline interception logic
    # ========================================================

    async def _process_client_messages(self, server_writer):
        """
        Decode client→TWS messages and optionally override behavior.
        """
        while True:
            if not self.server_supports_protobuf:
                self.logger.info(f'client_buffer {self.client_buffer[:40]}')

            if self.state == GWState.INITIAL:
                self.logger.info(colorama.Fore.GREEN + "INITIAL → HANDSHAKE state" + colorama.Style.RESET_ALL)
                self.state = GWState.HANDSHAKE
                # Need at least 4 bytes for "API\0"
                if len(self.client_buffer) < 4:
                    self.logger.info("Waiting for more client handshake data... (client_buffer < 4)")
                    return
                if self.client_buffer[:4] != b'API\0':
                    raise RuntimeError(f"Invalid IB handshake prefix: {self.client_buffer[:4]!r}")

                # Need length + payload
                if len(self.client_buffer) < 8:
                    self.logger.info("Waiting for more client handshake data... (client_buffer < 8)")
                    return
                msg_len = struct.unpack(">I", self.client_buffer[4:8])[0]
                if len(self.client_buffer) < 8 + msg_len:
                    self.logger.info("Waiting for more client handshake data... (client_buffer < 8 + msg_len)")
                    return

                ver_bytes = self.client_buffer[8:8+msg_len]
                self.client_version_range = ver_bytes.decode("ascii", errors="replace")
                # Drop handshake bytes from buffer (they've already been relayed)
                del self.client_buffer[:8+msg_len]

                # self.state = GWState.HANDSHAKE
                self.logger.info("Client handshake completed: client_version_range=%s", self.client_version_range)
                # fall through to next loop iteration
                continue

            # From here on, we’re in HANDSHAKE/READY/REQUESTS and can parse framed messages

            msg_id, fields, rawMsg = await self.parser(self.client_buffer)
            # self.logger.info(f'Parsed client message: msg_id={msg_id}, fields={fields}, rawMsg={rawMsg}')
            if not self.server_supports_protobuf:
                self.logger.info(f'Parsed client message: msg_id={msg_id}, fields={fields}')
            # if self.state == GWState.READY and 
            if not fields and msg_id < 0:
                return

            # self.logger.info(f"Received client message: {msg_id} {fields}")

            # State machine transitions
            _opts = PROTOBUF_MESSAGE_MAP_OUT_HANDLER_OPTS.get(msg_id, {})
            if self.state == GWState.READY:
                if msg_id == OUT.START_API:
                    if self.server_supports_protobuf:
                        proto = _decode_protobuf(PROTOBUF_MESSAGE_MAP_OUT, msg_id, rawMsg)
                        self.logger.info(f"Processing client proto msg: {msg_id}(START_API) {proto}")
                    else:
                        # legacy
                        self.logger.info(f"Processing client legacy msg: {msg_id}(START_API) {fields}")

                    self.logger.info(colorama.Fore.GREEN + "READY → READY_waitNextValidId state" + colorama.Style.RESET_ALL)
                    self.state = GWState.READY_waitNextValidId
                else:
                    self.logger.warning(f"Unexpected client message in READY state: {msg_id} {fields}")
                continue

            elif self.state == GWState.READY_waitNextValidId: # on server side
                pass

            #     self.state = GWState.READY_seen_nextValidId
            # elif self.state == GWState.READY_seen_nextValidId:
            #     pass
                self.state = GWState.REQUESTS
            elif self.state == GWState.REQUESTS:
                if self.server_supports_protobuf:
                    proto = _decode_protobuf(PROTOBUF_MESSAGE_MAP_OUT, msg_id, rawMsg)
                    match msg_id:
                      case OUT.REQ_HISTORICAL_TICKS:
                        o = cast(ibapi.protobuf.HistoricalTicksRequest_pb2.HistoricalTicksRequest, proto)
                        self.logger.info(f"Client: protobuf request: {IBMsgOutEnum(msg_id).name}({msg_id}) '{o.startDateTime}' '{o.endDateTime}'")
                      case _:
                        # default handler
                        self.logger.info(f"Client: protobuf request: {IBMsgOutEnum(msg_id).name}({msg_id}) {proto}")
                else:
                    self.logger.info(f"Client legacy request: {IBMsgOutEnum(msg_id).name}({msg_id}) {fields}")
                
                # if msg_id == REQ_CONTRACT_DETAILS:
                #     await self._handle_static_request(fields)
                # elif msg_id == REQ_MKT_DATA:
                #     await self._start_stream(fields)
                # elif msg_id == CANCEL_MKT_DATA:
                #     await self._cancel_stream(fields)

    async def _process_server_messages(self):
        """
        Decode server→client messages if needed.
        """
        while True:
            # if not self.server_supports_protobuf:
            #     self.logger.info(f'server_buffer {self.server_buffer[:40]}')
            # 1. attempt to parse what's in the buffer
            msgId, fields, rawMsg = await self.parser(self.server_buffer)

            # 2a. if we're during handshake ....
            if self.state == GWState.HANDSHAKE:
                if not fields or len(fields) != 2:
                    self.logger.warning(f"Failed to parse server handshake message: {fields}")
                    return
                # This is the serverVersion + connectionTime message
                _version, _connTime = fields
                self.server_version = _version # if _version else None
                if int(_version) >= MIN_SERVER_VER_PROTOBUF:
                    self.server_supports_protobuf = True
                    self.parser = self._parse_new_frame
                self.connection_time = _connTime # if _connTime else None

                self.logger.info("Server handshake completed: server_version=%s, connection_time=%s", self.server_version, self.connection_time)

                self.logger.info(colorama.Fore.GREEN + 'HANDSHAKE → READY state' + colorama.Style.RESET_ALL)
                self.state = GWState.READY

                continue

            # 2b. if we don't know what it is
            if fields == [] and msgId < 0:
                # log it and return
                _len = len(self.server_buffer)
                self.logger.info(f'server_buffer[{_len}] {self.server_buffer[:40]}'
                                 + ('...' if _len > 40 else ''))
                return

            if self.state == GWState.READY:
                raise RuntimeError

            if self.state == GWState.READY_waitNextValidId:
                # following START_API, if "Download open orders on connection" is checked in TWS
                # server will send 
                if self.server_supports_protobuf:
                    proto: gpm.Message = _decode_protobuf(PROTOBUF_MESSAGE_MAP_IN, msgId, rawMsg) # always decode
                    fields = proto_to_nested(proto)
                    print(fields)

                    _opts = PROTOBUF_MESSAGE_MAP_IN_HANDLER_OPTS.get(msgId, {})
                    # if _opts:
                    #     self.logger.info(_opts)
                    match msgId:
                        case 9: # NEXT_VALID_ID
                            v = cast(ibapi.protobuf.NextValidId_pb2.NextValidId, proto)
                            self.logger.info(f"Server: Protobuf message NEXT_VALID_ID(9) orderId={v.orderId}")
                            self.logger.info(colorama.Fore.GREEN + 'READY_waitNextValidId → REQUESTS state' + colorama.Style.RESET_ALL)
                            self.state = GWState.REQUESTS
                        case IN.OPEN_ORDER:
                            o = cast(ibapi.protobuf.OpenOrder_pb2.OpenOrder, proto)
                            self.logger.info(f"Server: Protobuf message OPEN_ORDER({msgId}) orderId={o.orderId}")
                        case IN.ORDER_STATUS:
                            s = cast(ibapi.protobuf.OrderStatus_pb2.OrderStatus, proto)
                            self.logger.info(f"Server: Protobuf message ORDER_STATUS({msgId}) orderId={s.orderId}")
                        case IN.OPEN_ORDER_END:
                            e = cast(ibapi.protobuf.OpenOrdersEnd_pb2.OpenOrdersEnd, proto)
                            self.logger.info(f"Server: Protobuf message OPEN_ORDER_END({msgId})")
                        case _:
                            self.logger.info(f'Unknown message {IBMsgInEnum(msgId).name}({msgId}) in READY_waitNextValidId state')
                
                continue

            if self.state == GWState.REQUESTS:
                if self.server_supports_protobuf:
                    proto: gpm.Message = _decode_protobuf(PROTOBUF_MESSAGE_MAP_IN, msgId, rawMsg) # always decode
                    # populated = proto.ListFields()
                    # fields = [(d.name, v) for d, v in populated]
                    fields = proto_to_nested(proto)
                    print(fields)
                    _opts = PROTOBUF_MESSAGE_MAP_IN_HANDLER_OPTS.get(msgId, {})
                    # if _opts:
                    #     self.logger.info(_opts)
                    match msgId:
                        case IN.TICK_SIZE:
                            t = cast(ibapi.protobuf.TickSize_pb2.TickSize, proto)
                            self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId}) reqId {t.reqId} size {t.size} tickType {TickTypeEnum(t.tickType).name}({t.tickType})")
                        case IN.TICK_STRING:
                            s = cast(ibapi.protobuf.TickString_pb2.TickString, proto)
                            if _opts.get('ignore_common_ticktypes') \
                              and s.tickType in {TickTypeEnum.BID_EXCH, TickTypeEnum.ASK_EXCH, TickTypeEnum.LAST_EXCH, TickTypeEnum.LAST_TIMESTAMP}:
                                self.logger.info(f"Server: Protobuf message TICK_STRING({msgId}) {TickTypeEnum(s.tickType).name}({s.tickType})")
                            else:
                                self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId})\n{proto}")
                        case IN.TICK_GENERIC:
                            g = cast(ibapi.protobuf.TickGeneric_pb2.TickGeneric, proto)
                            self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId}) reqId {g.reqId} value {g.value} tickType {TickTypeEnum(g.tickType).name}({g.tickType})")
                        case IN.ERR_MSG:
                            e = cast(ibapi.protobuf.ErrorMessage_pb2.ErrorMessage, proto)
                            if _opts.get('ignore_mktdata_errcodes') and e.errorCode in {2103, 2104, 2106, 2108, 2158}:
                                self.logger.info(f"Server: Protobuf message ERR_MSG({msgId}) errorCode={e.errorCode}")
                            else:
                                self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId})\n{proto}")
                        # case 9: # NEXT_VALID_ID
                        #     v = cast(ibapi.protobuf.NextValidId_pb2.NextValidId, proto)
                        #     self.logger.info(f"Server: NEXT_VALID_ID(9) orderId={v.orderId}")
                        case IN.MANAGED_ACCTS:
                            a = cast(ibapi.protobuf.ManagedAccounts_pb2.ManagedAccounts, proto)
                            self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId}) {a.accountsList}")
                        case IN.CURRENT_TIME:
                            t = cast(ibapi.protobuf.CurrentTime_pb2.CurrentTime, proto)
                            self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId}) {t.currentTime}({datetime.datetime.fromtimestamp(t.currentTime)}) ")
                        case IN.TICK_REQ_PARAMS:
                            p = cast(ibapi.protobuf.TickReqParams_pb2.TickReqParams, proto)
                            _s = format_protobuf_message(proto)
                            self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId}) {_s}")
                        case _:
                            # msg = _decode_protobuf(PROTOBUF_MESSAGE_MAP_IN, msgId, rawMsg)
                            # default handler just print
                            self.logger.info(f"Server: Protobuf message {IBMsgInEnum(msgId).name}({msgId})"
                                             + (f"\n{proto}" if not _opts.get('print_msgid_only') else f", buf size={len(rawMsg)}"))
                        # case _, _:
                        #     self.logger.info(colorama.Fore.RED + f'Server: Unknown message {msgId} {rawMsg}' + colorama.Style.RESET_ALL)
                else:
                    # legacy
                    _opts = LEGACY_MESSAGE_MAP_IN_HANDLER_OPTS.get(msgId, {})
                    match msgId:
                      case _:
                        self.logger.info(f"Server: {IBMsgInEnum(msgId).name}({msgId}) "
                                         + (f"{fields}" if not _opts.get('print_msgid_only') else f"field len={len(fields)}"))
    
    async def _try_parse(self, buffer: bytearray) -> tuple[int, list[str], bytearray]:
        """
        [4-byte length][payload]
        payload = null-delimited UTF-8 fields
        """
        _dummy = []
        if len(buffer) < 4:
            return -1, _dummy, buffer
        msg_len = struct.unpack(">I", buffer[:4])[0]
        if len(buffer) < 4 + msg_len:
            return -1, _dummy, buffer

        payload = buffer[4:4+msg_len]
        del buffer[:4+msg_len]

        text = payload.rstrip(b'\0').decode("utf-8", errors="backslashreplace")
        fields = text.split("\0")
        msgId = int(fields[0]) if fields else -1
       
        return msgId, fields, payload

    async def _parse_new_frame(self, buffer: bytearray) -> tuple[int, list[str], bytearray]:
        """[4-byte LENGTH][4-byte MSGID][PROTOBUF PAYLOAD]"""
        _dummy = []
        # need at least 4 bytes for length
        if len(buffer) < 4:
            return -1, _dummy, buffer

        msg_len = struct.unpack(">I", buffer[:4])[0]
        
        # need full message
        if len(buffer) < 4 + msg_len:
            return -2, _dummy, buffer

        # extract message block
        block = buffer[4:4+msg_len]
        del buffer[:4+msg_len]

        # first 4 bytes of block = msgId
        msgId = int.from_bytes(block[:4], "big")
        payload = block[4:]

        is_protobuf = msgId > PROTOBUF_MSG_ID
        assert is_protobuf
        realmsgId = msgId - PROTOBUF_MSG_ID

        return realmsgId, _dummy, payload

# Incoming message protobuf imports
import ibapi.protobuf.TickPrice_pb2
import ibapi.protobuf.TickSize_pb2
import ibapi.protobuf.OrderStatus_pb2
import ibapi.protobuf.ErrorMessage_pb2
import ibapi.protobuf.OpenOrder_pb2
import ibapi.protobuf.AccountValue_pb2
import ibapi.protobuf.PortfolioValue_pb2
import ibapi.protobuf.AccountUpdateTime_pb2
import ibapi.protobuf.NextValidId_pb2
import ibapi.protobuf.ContractData_pb2
import ibapi.protobuf.ExecutionDetails_pb2
import ibapi.protobuf.MarketDepth_pb2
import ibapi.protobuf.MarketDepthL2_pb2
import ibapi.protobuf.NewsBulletin_pb2
import ibapi.protobuf.ManagedAccounts_pb2
import ibapi.protobuf.ReceiveFA_pb2
import ibapi.protobuf.HistoricalData_pb2
import ibapi.protobuf.ScannerParameters_pb2
import ibapi.protobuf.ScannerData_pb2
import ibapi.protobuf.TickOptionComputation_pb2
import ibapi.protobuf.TickGeneric_pb2
import ibapi.protobuf.TickString_pb2
import ibapi.protobuf.CurrentTime_pb2
import ibapi.protobuf.RealTimeBarTick_pb2
import ibapi.protobuf.FundamentalsData_pb2
import ibapi.protobuf.ContractDataEnd_pb2
import ibapi.protobuf.OpenOrdersEnd_pb2
import ibapi.protobuf.AccountDataEnd_pb2
import ibapi.protobuf.ExecutionDetailsEnd_pb2
import ibapi.protobuf.TickSnapshotEnd_pb2
import ibapi.protobuf.MarketDataType_pb2
import ibapi.protobuf.CommissionAndFeesReport_pb2
import ibapi.protobuf.Position_pb2
import ibapi.protobuf.PositionEnd_pb2
import ibapi.protobuf.AccountSummary_pb2
import ibapi.protobuf.AccountSummaryEnd_pb2
import ibapi.protobuf.VerifyMessageApi_pb2
import ibapi.protobuf.VerifyCompleted_pb2
import ibapi.protobuf.DisplayGroupList_pb2
import ibapi.protobuf.DisplayGroupUpdated_pb2
import ibapi.protobuf.PositionMulti_pb2
import ibapi.protobuf.PositionMultiEnd_pb2
import ibapi.protobuf.AccountUpdateMulti_pb2
import ibapi.protobuf.AccountUpdateMultiEnd_pb2
import ibapi.protobuf.SecDefOptParameter_pb2
import ibapi.protobuf.SecDefOptParameterEnd_pb2
import ibapi.protobuf.SoftDollarTiers_pb2
import ibapi.protobuf.FamilyCodes_pb2
import ibapi.protobuf.SymbolSamples_pb2
import ibapi.protobuf.MarketDepthExchanges_pb2
import ibapi.protobuf.TickReqParams_pb2
import ibapi.protobuf.SmartComponents_pb2
import ibapi.protobuf.NewsArticle_pb2
import ibapi.protobuf.TickNews_pb2
import ibapi.protobuf.NewsProviders_pb2
import ibapi.protobuf.HistoricalNews_pb2
import ibapi.protobuf.HistoricalNewsEnd_pb2
import ibapi.protobuf.HeadTimestamp_pb2
import ibapi.protobuf.HistogramData_pb2
import ibapi.protobuf.HistoricalDataUpdate_pb2
import ibapi.protobuf.RerouteMarketDataRequest_pb2
import ibapi.protobuf.RerouteMarketDepthRequest_pb2
import ibapi.protobuf.MarketRule_pb2
import ibapi.protobuf.PnL_pb2
import ibapi.protobuf.PnLSingle_pb2
import ibapi.protobuf.HistoricalTicks_pb2
import ibapi.protobuf.HistoricalTicksBidAsk_pb2
import ibapi.protobuf.HistoricalTicksLast_pb2
import ibapi.protobuf.TickByTickData_pb2
import ibapi.protobuf.OrderBound_pb2
import ibapi.protobuf.CompletedOrder_pb2
import ibapi.protobuf.CompletedOrdersEnd_pb2
import ibapi.protobuf.ReplaceFAEnd_pb2
import ibapi.protobuf.WshMetaData_pb2
import ibapi.protobuf.WshEventData_pb2
import ibapi.protobuf.HistoricalSchedule_pb2
import ibapi.protobuf.UserInfo_pb2
import ibapi.protobuf.HistoricalDataEnd_pb2
import ibapi.protobuf.CurrentTimeInMillis_pb2
import ibapi.protobuf.ConfigResponse_pb2
import ibapi.protobuf.UpdateConfigResponse_pb2

PROTOBUF_MESSAGE_MAP_IN = {
    IN.TICK_PRICE: ibapi.protobuf.TickPrice_pb2.TickPrice,
    IN.TICK_SIZE: ibapi.protobuf.TickSize_pb2.TickSize,
    IN.ORDER_STATUS: ibapi.protobuf.OrderStatus_pb2.OrderStatus,
    IN.ERR_MSG: ibapi.protobuf.ErrorMessage_pb2.ErrorMessage,
    IN.OPEN_ORDER: ibapi.protobuf.OpenOrder_pb2.OpenOrder,
    IN.ACCT_VALUE: ibapi.protobuf.AccountValue_pb2.AccountValue,
    IN.PORTFOLIO_VALUE: ibapi.protobuf.PortfolioValue_pb2.PortfolioValue,
    IN.ACCT_UPDATE_TIME: ibapi.protobuf.AccountUpdateTime_pb2.AccountUpdateTime,
    IN.NEXT_VALID_ID: ibapi.protobuf.NextValidId_pb2.NextValidId,
    IN.CONTRACT_DATA: ibapi.protobuf.ContractData_pb2.ContractData,
    IN.EXECUTION_DATA: ibapi.protobuf.ExecutionDetails_pb2.ExecutionDetails,
    IN.MARKET_DEPTH: ibapi.protobuf.MarketDepth_pb2.MarketDepth,
    IN.MARKET_DEPTH_L2: ibapi.protobuf.MarketDepthL2_pb2.MarketDepthL2,
    IN.NEWS_BULLETINS: ibapi.protobuf.NewsBulletin_pb2.NewsBulletin,
    IN.MANAGED_ACCTS: ibapi.protobuf.ManagedAccounts_pb2.ManagedAccounts,
    IN.RECEIVE_FA: ibapi.protobuf.ReceiveFA_pb2.ReceiveFA,
    IN.HISTORICAL_DATA: ibapi.protobuf.HistoricalData_pb2.HistoricalData,
    IN.SCANNER_PARAMETERS: ibapi.protobuf.ScannerParameters_pb2.ScannerParameters,
    IN.SCANNER_DATA: ibapi.protobuf.ScannerData_pb2.ScannerData,
    IN.TICK_OPTION_COMPUTATION: ibapi.protobuf.TickOptionComputation_pb2.TickOptionComputation,
    IN.TICK_GENERIC: ibapi.protobuf.TickGeneric_pb2.TickGeneric,
    IN.TICK_STRING: ibapi.protobuf.TickString_pb2.TickString,
    IN.CURRENT_TIME: ibapi.protobuf.CurrentTime_pb2.CurrentTime,
    IN.REAL_TIME_BARS: ibapi.protobuf.RealTimeBarTick_pb2.RealTimeBarTick,
    IN.FUNDAMENTAL_DATA: ibapi.protobuf.FundamentalsData_pb2.FundamentalsData,
    IN.CONTRACT_DATA_END: ibapi.protobuf.ContractDataEnd_pb2.ContractDataEnd,
    IN.OPEN_ORDER_END: ibapi.protobuf.OpenOrdersEnd_pb2.OpenOrdersEnd,
    IN.ACCT_DOWNLOAD_END: ibapi.protobuf.AccountDataEnd_pb2.AccountDataEnd,
    IN.EXECUTION_DATA_END: ibapi.protobuf.ExecutionDetailsEnd_pb2.ExecutionDetailsEnd,
    IN.TICK_SNAPSHOT_END: ibapi.protobuf.TickSnapshotEnd_pb2.TickSnapshotEnd,
    IN.MARKET_DATA_TYPE: ibapi.protobuf.MarketDataType_pb2.MarketDataType,
    IN.COMMISSION_AND_FEES_REPORT: ibapi.protobuf.CommissionAndFeesReport_pb2.CommissionAndFeesReport,
    IN.POSITION_DATA: ibapi.protobuf.Position_pb2.Position,
    IN.POSITION_END: ibapi.protobuf.PositionEnd_pb2.PositionEnd,
    IN.ACCOUNT_SUMMARY: ibapi.protobuf.AccountSummary_pb2.AccountSummary,
    IN.ACCOUNT_SUMMARY_END: ibapi.protobuf.AccountSummaryEnd_pb2.AccountSummaryEnd,
    IN.VERIFY_MESSAGE_API: ibapi.protobuf.VerifyMessageApi_pb2.VerifyMessageApi,
    IN.VERIFY_COMPLETED: ibapi.protobuf.VerifyCompleted_pb2.VerifyCompleted,
    IN.DISPLAY_GROUP_LIST: ibapi.protobuf.DisplayGroupList_pb2.DisplayGroupList,
    IN.DISPLAY_GROUP_UPDATED: ibapi.protobuf.DisplayGroupUpdated_pb2.DisplayGroupUpdated,
    IN.POSITION_MULTI: ibapi.protobuf.PositionMulti_pb2.PositionMulti,
    IN.POSITION_MULTI_END: ibapi.protobuf.PositionMultiEnd_pb2.PositionMultiEnd,
    IN.ACCOUNT_UPDATE_MULTI: ibapi.protobuf.AccountUpdateMulti_pb2.AccountUpdateMulti,
    IN.ACCOUNT_UPDATE_MULTI_END: ibapi.protobuf.AccountUpdateMultiEnd_pb2.AccountUpdateMultiEnd,
    IN.SECURITY_DEFINITION_OPTION_PARAMETER: ibapi.protobuf.SecDefOptParameter_pb2.SecDefOptParameter,
    IN.SECURITY_DEFINITION_OPTION_PARAMETER_END: ibapi.protobuf.SecDefOptParameterEnd_pb2.SecDefOptParameterEnd,
    IN.SOFT_DOLLAR_TIERS: ibapi.protobuf.SoftDollarTiers_pb2.SoftDollarTiers,
    IN.FAMILY_CODES: ibapi.protobuf.FamilyCodes_pb2.FamilyCodes,
    IN.SYMBOL_SAMPLES: ibapi.protobuf.SymbolSamples_pb2.SymbolSamples,
    IN.MKT_DEPTH_EXCHANGES: ibapi.protobuf.MarketDepthExchanges_pb2.MarketDepthExchanges,
    IN.TICK_REQ_PARAMS: ibapi.protobuf.TickReqParams_pb2.TickReqParams,
    IN.SMART_COMPONENTS: ibapi.protobuf.SmartComponents_pb2.SmartComponents,
    IN.NEWS_ARTICLE: ibapi.protobuf.NewsArticle_pb2.NewsArticle,
    IN.TICK_NEWS: ibapi.protobuf.TickNews_pb2.TickNews,
    IN.NEWS_PROVIDERS: ibapi.protobuf.NewsProviders_pb2.NewsProviders,
    IN.HISTORICAL_NEWS: ibapi.protobuf.HistoricalNews_pb2.HistoricalNews,
    IN.HISTORICAL_NEWS_END: ibapi.protobuf.HistoricalNewsEnd_pb2.HistoricalNewsEnd,
    IN.HEAD_TIMESTAMP: ibapi.protobuf.HeadTimestamp_pb2.HeadTimestamp,
    IN.HISTOGRAM_DATA: ibapi.protobuf.HistogramData_pb2.HistogramData,
    IN.HISTORICAL_DATA_UPDATE: ibapi.protobuf.HistoricalDataUpdate_pb2.HistoricalDataUpdate,
    IN.REROUTE_MKT_DATA_REQ: ibapi.protobuf.RerouteMarketDataRequest_pb2.RerouteMarketDataRequest,
    IN.REROUTE_MKT_DEPTH_REQ: ibapi.protobuf.RerouteMarketDepthRequest_pb2.RerouteMarketDepthRequest,
    IN.MARKET_RULE: ibapi.protobuf.MarketRule_pb2.MarketRule,
    IN.PNL: ibapi.protobuf.PnL_pb2.PnL,
    IN.PNL_SINGLE: ibapi.protobuf.PnLSingle_pb2.PnLSingle,
    IN.HISTORICAL_TICKS: ibapi.protobuf.HistoricalTicks_pb2.HistoricalTicks,
    IN.HISTORICAL_TICKS_BID_ASK: ibapi.protobuf.HistoricalTicksBidAsk_pb2.HistoricalTicksBidAsk,
    IN.HISTORICAL_TICKS_LAST: ibapi.protobuf.HistoricalTicksLast_pb2.HistoricalTicksLast,
    IN.TICK_BY_TICK: ibapi.protobuf.TickByTickData_pb2.TickByTickData,
    IN.ORDER_BOUND: ibapi.protobuf.OrderBound_pb2.OrderBound,
    IN.COMPLETED_ORDER: ibapi.protobuf.CompletedOrder_pb2.CompletedOrder,
    IN.COMPLETED_ORDERS_END: ibapi.protobuf.CompletedOrdersEnd_pb2.CompletedOrdersEnd,
    IN.REPLACE_FA_END: ibapi.protobuf.ReplaceFAEnd_pb2.ReplaceFAEnd,
    IN.WSH_META_DATA: ibapi.protobuf.WshMetaData_pb2.WshMetaData,
    IN.WSH_EVENT_DATA: ibapi.protobuf.WshEventData_pb2.WshEventData,
    IN.HISTORICAL_SCHEDULE: ibapi.protobuf.HistoricalSchedule_pb2.HistoricalSchedule,
    IN.USER_INFO: ibapi.protobuf.UserInfo_pb2.UserInfo,
    IN.HISTORICAL_DATA_END: ibapi.protobuf.HistoricalDataEnd_pb2.HistoricalDataEnd,
    IN.CURRENT_TIME_IN_MILLIS: ibapi.protobuf.CurrentTimeInMillis_pb2.CurrentTimeInMillis,
    IN.CONFIG_RESPONSE: ibapi.protobuf.ConfigResponse_pb2.ConfigResponse,
    IN.UPDATE_CONFIG_RESPONSE: ibapi.protobuf.UpdateConfigResponse_pb2.UpdateConfigResponse,
}

PROTOBUF_MESSAGE_MAP_IN_HANDLER_OPTS = {
    IN.TICK_PRICE: { 'print_msgid_only': True },
    # IN.TICK_SIZE: { 'print_msgid_only': True },
    IN.TICK_STRING: { 'ignore_common_ticktypes': True },
    IN.ERR_MSG: { 'ignore_mktdata_errcodes': True },
    IN.ACCT_VALUE: { 'print_msgid_only': True },
    IN.PORTFOLIO_VALUE: { 'print_msgid_only': True },
    IN.ACCT_UPDATE_TIME: { 'print_msgid_only': True },
    # IN.CONTRACT_DATA: { 'print_msgid_only': True },
    IN.CONTRACT_DATA_END: { 'print_msgid_only': True },
    IN.HISTORICAL_TICKS_BID_ASK: { 'print_msgid_only': True },
    IN.HISTORICAL_TICKS_LAST: { 'print_msgid_only': True },
}

LEGACY_MESSAGE_MAP_IN_HANDLER_OPTS = {
    IN.TICK_PRICE: { 'print_msgid_only': True },
    # IN.TICK_SIZE: { 'print_msgid_only': True },
    IN.ERR_MSG: { 'ignore_mktdata_errcodes': True },
    IN.ACCT_VALUE: { 'print_msgid_only': True },
    IN.PORTFOLIO_VALUE: { 'print_msgid_only': True },
    IN.ACCT_UPDATE_TIME: { 'print_msgid_only': True },
    # IN.CONTRACT_DATA: { 'print_msgid_only': True },
    IN.CONTRACT_DATA_END: { 'print_msgid_only': True },
    IN.HISTORICAL_TICKS_LAST: { 'print_msgid_only': True },
    IN.HISTORICAL_TICKS_BID_ASK: { 'print_msgid_only': True },
}

# Outgoing message protobuf imports
import ibapi.protobuf.MarketDataRequest_pb2
import ibapi.protobuf.CancelMarketData_pb2
import ibapi.protobuf.PlaceOrderRequest_pb2
import ibapi.protobuf.CancelOrderRequest_pb2
import ibapi.protobuf.OpenOrdersRequest_pb2
import ibapi.protobuf.AccountDataRequest_pb2
import ibapi.protobuf.ExecutionRequest_pb2
import ibapi.protobuf.IdsRequest_pb2
import ibapi.protobuf.ContractDataRequest_pb2
import ibapi.protobuf.MarketDepthRequest_pb2
import ibapi.protobuf.CancelMarketDepth_pb2
import ibapi.protobuf.NewsBulletinsRequest_pb2
import ibapi.protobuf.CancelNewsBulletins_pb2
import ibapi.protobuf.SetServerLogLevelRequest_pb2
import ibapi.protobuf.AutoOpenOrdersRequest_pb2
import ibapi.protobuf.AllOpenOrdersRequest_pb2
import ibapi.protobuf.ManagedAccountsRequest_pb2
import ibapi.protobuf.FARequest_pb2
import ibapi.protobuf.FAReplace_pb2
import ibapi.protobuf.HistoricalDataRequest_pb2
import ibapi.protobuf.ExerciseOptionsRequest_pb2
import ibapi.protobuf.ScannerSubscriptionRequest_pb2
import ibapi.protobuf.CancelScannerSubscription_pb2
import ibapi.protobuf.ScannerParametersRequest_pb2
import ibapi.protobuf.CancelHistoricalData_pb2
import ibapi.protobuf.CurrentTimeRequest_pb2
import ibapi.protobuf.RealTimeBarsRequest_pb2
import ibapi.protobuf.CancelRealTimeBars_pb2
import ibapi.protobuf.FundamentalsDataRequest_pb2
import ibapi.protobuf.CancelFundamentalsData_pb2
import ibapi.protobuf.CalculateImpliedVolatilityRequest_pb2
import ibapi.protobuf.CalculateOptionPriceRequest_pb2
import ibapi.protobuf.CancelCalculateImpliedVolatility_pb2
import ibapi.protobuf.CancelCalculateOptionPrice_pb2
import ibapi.protobuf.GlobalCancelRequest_pb2
import ibapi.protobuf.MarketDataTypeRequest_pb2
import ibapi.protobuf.PositionsRequest_pb2
import ibapi.protobuf.AccountSummaryRequest_pb2
import ibapi.protobuf.CancelAccountSummary_pb2
import ibapi.protobuf.CancelPositions_pb2
import ibapi.protobuf.VerifyRequest_pb2
import ibapi.protobuf.VerifyMessageRequest_pb2
import ibapi.protobuf.QueryDisplayGroupsRequest_pb2
import ibapi.protobuf.SubscribeToGroupEventsRequest_pb2
import ibapi.protobuf.UpdateDisplayGroupRequest_pb2
import ibapi.protobuf.UnsubscribeFromGroupEventsRequest_pb2
import ibapi.protobuf.StartApiRequest_pb2
import ibapi.protobuf.VerifyRequest_pb2
import ibapi.protobuf.VerifyMessageRequest_pb2
import ibapi.protobuf.PositionsMultiRequest_pb2
import ibapi.protobuf.CancelPositionsMulti_pb2
import ibapi.protobuf.AccountUpdatesMultiRequest_pb2
import ibapi.protobuf.CancelAccountUpdatesMulti_pb2
import ibapi.protobuf.SecDefOptParamsRequest_pb2
import ibapi.protobuf.SoftDollarTiersRequest_pb2
import ibapi.protobuf.FamilyCodesRequest_pb2
import ibapi.protobuf.MatchingSymbolsRequest_pb2
import ibapi.protobuf.MarketDepthExchangesRequest_pb2
import ibapi.protobuf.SmartComponentsRequest_pb2
import ibapi.protobuf.NewsArticleRequest_pb2
import ibapi.protobuf.NewsProvidersRequest_pb2
import ibapi.protobuf.HistoricalNewsRequest_pb2
import ibapi.protobuf.HeadTimestampRequest_pb2
import ibapi.protobuf.HistogramDataRequest_pb2
import ibapi.protobuf.CancelHistogramData_pb2
import ibapi.protobuf.CancelHeadTimestamp_pb2
import ibapi.protobuf.MarketRuleRequest_pb2
import ibapi.protobuf.PnLRequest_pb2
import ibapi.protobuf.CancelPnL_pb2
import ibapi.protobuf.PnLSingleRequest_pb2
import ibapi.protobuf.CancelPnLSingle_pb2
import ibapi.protobuf.HistoricalTicksRequest_pb2
import ibapi.protobuf.TickByTickRequest_pb2
import ibapi.protobuf.CancelTickByTick_pb2
import ibapi.protobuf.CompletedOrdersRequest_pb2
import ibapi.protobuf.WshMetaDataRequest_pb2
import ibapi.protobuf.CancelWshMetaData_pb2
import ibapi.protobuf.WshEventDataRequest_pb2
import ibapi.protobuf.CancelWshEventData_pb2
import ibapi.protobuf.UserInfoRequest_pb2
import ibapi.protobuf.CurrentTimeInMillisRequest_pb2
import ibapi.protobuf.CancelContractData_pb2
import ibapi.protobuf.CancelHistoricalTicks_pb2
import ibapi.protobuf.ConfigRequest_pb2
import ibapi.protobuf.UpdateConfigRequest_pb2

PROTOBUF_MESSAGE_MAP_OUT = {
    OUT.REQ_MKT_DATA: ibapi.protobuf.MarketDataRequest_pb2.MarketDataRequest,
    OUT.CANCEL_MKT_DATA: ibapi.protobuf.CancelMarketData_pb2.CancelMarketData,
    OUT.PLACE_ORDER: ibapi.protobuf.PlaceOrderRequest_pb2.PlaceOrderRequest,
    OUT.CANCEL_ORDER: ibapi.protobuf.CancelOrderRequest_pb2.CancelOrderRequest,
    OUT.REQ_OPEN_ORDERS: ibapi.protobuf.OpenOrdersRequest_pb2.OpenOrdersRequest,
    OUT.REQ_ACCT_DATA: ibapi.protobuf.AccountDataRequest_pb2.AccountDataRequest,
    OUT.REQ_EXECUTIONS: ibapi.protobuf.ExecutionRequest_pb2.ExecutionRequest,
    OUT.REQ_IDS: ibapi.protobuf.IdsRequest_pb2.IdsRequest,
    OUT.REQ_CONTRACT_DATA: ibapi.protobuf.ContractDataRequest_pb2.ContractDataRequest,
    OUT.REQ_MKT_DEPTH: ibapi.protobuf.MarketDepthRequest_pb2.MarketDepthRequest,
    OUT.CANCEL_MKT_DEPTH: ibapi.protobuf.CancelMarketDepth_pb2.CancelMarketDepth,
    OUT.REQ_NEWS_BULLETINS: ibapi.protobuf.NewsBulletinsRequest_pb2.NewsBulletinsRequest,
    OUT.CANCEL_NEWS_BULLETINS: ibapi.protobuf.CancelNewsBulletins_pb2.CancelNewsBulletins,
    OUT.SET_SERVER_LOGLEVEL: ibapi.protobuf.SetServerLogLevelRequest_pb2.SetServerLogLevelRequest,
    OUT.REQ_AUTO_OPEN_ORDERS: ibapi.protobuf.AutoOpenOrdersRequest_pb2.AutoOpenOrdersRequest,
    OUT.REQ_ALL_OPEN_ORDERS: ibapi.protobuf.AllOpenOrdersRequest_pb2.AllOpenOrdersRequest,
    OUT.REQ_MANAGED_ACCTS: ibapi.protobuf.ManagedAccountsRequest_pb2.ManagedAccountsRequest,
    OUT.REQ_FA: ibapi.protobuf.FARequest_pb2.FARequest,
    OUT.REPLACE_FA: ibapi.protobuf.FAReplace_pb2.FAReplace,
    OUT.REQ_HISTORICAL_DATA: ibapi.protobuf.HistoricalDataRequest_pb2.HistoricalDataRequest,
    OUT.EXERCISE_OPTIONS: ibapi.protobuf.ExerciseOptionsRequest_pb2.ExerciseOptionsRequest,
    OUT.REQ_SCANNER_SUBSCRIPTION: ibapi.protobuf.ScannerSubscriptionRequest_pb2.ScannerSubscriptionRequest,
    OUT.CANCEL_SCANNER_SUBSCRIPTION: ibapi.protobuf.CancelScannerSubscription_pb2.CancelScannerSubscription,
    OUT.REQ_SCANNER_PARAMETERS: ibapi.protobuf.ScannerParametersRequest_pb2.ScannerParametersRequest,
    OUT.CANCEL_HISTORICAL_DATA: ibapi.protobuf.CancelHistoricalData_pb2.CancelHistoricalData,
    OUT.REQ_CURRENT_TIME: ibapi.protobuf.CurrentTimeRequest_pb2.CurrentTimeRequest,
    OUT.REQ_REAL_TIME_BARS: ibapi.protobuf.RealTimeBarsRequest_pb2.RealTimeBarsRequest,
    OUT.CANCEL_REAL_TIME_BARS: ibapi.protobuf.CancelRealTimeBars_pb2.CancelRealTimeBars,
    OUT.REQ_FUNDAMENTAL_DATA: ibapi.protobuf.FundamentalsDataRequest_pb2.FundamentalsDataRequest,
    OUT.CANCEL_FUNDAMENTAL_DATA: ibapi.protobuf.CancelFundamentalsData_pb2.CancelFundamentalsData,
    OUT.REQ_CALC_IMPLIED_VOLAT: ibapi.protobuf.CalculateImpliedVolatilityRequest_pb2.CalculateImpliedVolatilityRequest,
    OUT.REQ_CALC_OPTION_PRICE: ibapi.protobuf.CalculateOptionPriceRequest_pb2.CalculateOptionPriceRequest,
    OUT.CANCEL_CALC_IMPLIED_VOLAT: ibapi.protobuf.CancelCalculateImpliedVolatility_pb2.CancelCalculateImpliedVolatility,
    OUT.CANCEL_CALC_OPTION_PRICE: ibapi.protobuf.CancelCalculateOptionPrice_pb2.CancelCalculateOptionPrice,
    OUT.REQ_GLOBAL_CANCEL: ibapi.protobuf.GlobalCancelRequest_pb2.GlobalCancelRequest,
    OUT.REQ_MARKET_DATA_TYPE: ibapi.protobuf.MarketDataTypeRequest_pb2.MarketDataTypeRequest,
    OUT.REQ_POSITIONS: ibapi.protobuf.PositionsRequest_pb2.PositionsRequest,
    OUT.REQ_ACCOUNT_SUMMARY: ibapi.protobuf.AccountSummaryRequest_pb2.AccountSummaryRequest,
    OUT.CANCEL_ACCOUNT_SUMMARY: ibapi.protobuf.CancelAccountSummary_pb2.CancelAccountSummary,
    OUT.CANCEL_POSITIONS: ibapi.protobuf.CancelPositions_pb2.CancelPositions,
    OUT.VERIFY_REQUEST: ibapi.protobuf.VerifyRequest_pb2.VerifyRequest,
    OUT.VERIFY_MESSAGE: ibapi.protobuf.VerifyMessageRequest_pb2.VerifyMessageRequest,
    OUT.QUERY_DISPLAY_GROUPS: ibapi.protobuf.QueryDisplayGroupsRequest_pb2.QueryDisplayGroupsRequest,
    OUT.SUBSCRIBE_TO_GROUP_EVENTS: ibapi.protobuf.SubscribeToGroupEventsRequest_pb2.SubscribeToGroupEventsRequest,
    OUT.UPDATE_DISPLAY_GROUP: ibapi.protobuf.UpdateDisplayGroupRequest_pb2.UpdateDisplayGroupRequest,
    OUT.UNSUBSCRIBE_FROM_GROUP_EVENTS: ibapi.protobuf.UnsubscribeFromGroupEventsRequest_pb2.UnsubscribeFromGroupEventsRequest,
    OUT.START_API: ibapi.protobuf.StartApiRequest_pb2.StartApiRequest,
    OUT.VERIFY_AND_AUTH_REQUEST: ibapi.protobuf.VerifyRequest_pb2.VerifyRequest,
    OUT.VERIFY_AND_AUTH_MESSAGE: ibapi.protobuf.VerifyMessageRequest_pb2.VerifyMessageRequest,
    OUT.REQ_POSITIONS_MULTI: ibapi.protobuf.PositionsMultiRequest_pb2.PositionsMultiRequest,
    OUT.CANCEL_POSITIONS_MULTI: ibapi.protobuf.CancelPositionsMulti_pb2.CancelPositionsMulti,
    OUT.REQ_ACCOUNT_UPDATES_MULTI: ibapi.protobuf.AccountUpdatesMultiRequest_pb2.AccountUpdatesMultiRequest,
    OUT.CANCEL_ACCOUNT_UPDATES_MULTI: ibapi.protobuf.CancelAccountUpdatesMulti_pb2.CancelAccountUpdatesMulti,
    OUT.REQ_SEC_DEF_OPT_PARAMS: ibapi.protobuf.SecDefOptParamsRequest_pb2.SecDefOptParamsRequest,
    OUT.REQ_SOFT_DOLLAR_TIERS: ibapi.protobuf.SoftDollarTiersRequest_pb2.SoftDollarTiersRequest,
    OUT.REQ_FAMILY_CODES: ibapi.protobuf.FamilyCodesRequest_pb2.FamilyCodesRequest,
    OUT.REQ_MATCHING_SYMBOLS: ibapi.protobuf.MatchingSymbolsRequest_pb2.MatchingSymbolsRequest,
    OUT.REQ_MKT_DEPTH_EXCHANGES: ibapi.protobuf.MarketDepthExchangesRequest_pb2.MarketDepthExchangesRequest,
    OUT.REQ_SMART_COMPONENTS: ibapi.protobuf.SmartComponentsRequest_pb2.SmartComponentsRequest,
    OUT.REQ_NEWS_ARTICLE: ibapi.protobuf.NewsArticleRequest_pb2.NewsArticleRequest,
    OUT.REQ_NEWS_PROVIDERS: ibapi.protobuf.NewsProvidersRequest_pb2.NewsProvidersRequest,
    OUT.REQ_HISTORICAL_NEWS: ibapi.protobuf.HistoricalNewsRequest_pb2.HistoricalNewsRequest,
    OUT.REQ_HEAD_TIMESTAMP: ibapi.protobuf.HeadTimestampRequest_pb2.HeadTimestampRequest,
    OUT.REQ_HISTOGRAM_DATA: ibapi.protobuf.HistogramDataRequest_pb2.HistogramDataRequest,
    OUT.CANCEL_HISTOGRAM_DATA: ibapi.protobuf.CancelHistogramData_pb2.CancelHistogramData,
    OUT.CANCEL_HEAD_TIMESTAMP: ibapi.protobuf.CancelHeadTimestamp_pb2.CancelHeadTimestamp,
    OUT.REQ_MARKET_RULE: ibapi.protobuf.MarketRuleRequest_pb2.MarketRuleRequest,
    OUT.REQ_PNL: ibapi.protobuf.PnLRequest_pb2.PnLRequest,
    OUT.CANCEL_PNL: ibapi.protobuf.CancelPnL_pb2.CancelPnL,
    OUT.REQ_PNL_SINGLE: ibapi.protobuf.PnLSingleRequest_pb2.PnLSingleRequest,
    OUT.CANCEL_PNL_SINGLE: ibapi.protobuf.CancelPnLSingle_pb2.CancelPnLSingle,
    OUT.REQ_HISTORICAL_TICKS: ibapi.protobuf.HistoricalTicksRequest_pb2.HistoricalTicksRequest,
    OUT.REQ_TICK_BY_TICK_DATA: ibapi.protobuf.TickByTickRequest_pb2.TickByTickRequest,
    OUT.CANCEL_TICK_BY_TICK_DATA: ibapi.protobuf.CancelTickByTick_pb2.CancelTickByTick,
    OUT.REQ_COMPLETED_ORDERS: ibapi.protobuf.CompletedOrdersRequest_pb2.CompletedOrdersRequest,
    OUT.REQ_WSH_META_DATA: ibapi.protobuf.WshMetaDataRequest_pb2.WshMetaDataRequest,
    OUT.CANCEL_WSH_META_DATA: ibapi.protobuf.CancelWshMetaData_pb2.CancelWshMetaData,
    OUT.REQ_WSH_EVENT_DATA: ibapi.protobuf.WshEventDataRequest_pb2.WshEventDataRequest,
    OUT.CANCEL_WSH_EVENT_DATA: ibapi.protobuf.CancelWshEventData_pb2.CancelWshEventData,
    OUT.REQ_USER_INFO: ibapi.protobuf.UserInfoRequest_pb2.UserInfoRequest,
    OUT.REQ_CURRENT_TIME_IN_MILLIS: ibapi.protobuf.CurrentTimeInMillisRequest_pb2.CurrentTimeInMillisRequest,
    OUT.CANCEL_CONTRACT_DATA: ibapi.protobuf.CancelContractData_pb2.CancelContractData,
    OUT.CANCEL_HISTORICAL_TICKS: ibapi.protobuf.CancelHistoricalTicks_pb2.CancelHistoricalTicks,
    OUT.REQ_CONFIG: ibapi.protobuf.ConfigRequest_pb2.ConfigRequest,
    OUT.UPDATE_CONFIG: ibapi.protobuf.UpdateConfigRequest_pb2.UpdateConfigRequest,
}

PROTOBUF_MESSAGE_MAP_OUT_HANDLER_OPTS = {
    OUT.REQ_TICK_BY_TICK_DATA: { 'print_msgid_only': True },
    OUT.CANCEL_TICK_BY_TICK_DATA: { 'print_msgid_only': True },
}

def _decode_protobuf(map_, realMsgId: int, payload: bytearray) -> gpm.Message:
    msg_cls = map_.get(realMsgId)
    if msg_cls is None:
        raise ValueError(f"Unknown protobuf message ID: {realMsgId}")
        # return None  # unknown protobuf message

    proto = msg_cls()
    proto.ParseFromString(payload)
    return proto

async def main(args: argparse.Namespace):
    while True:
        gw = FakeIBGW(TWS_HOST, args.targetport, args.sourceport, 12345, enable_sim=args.sim)
        await gw.start()
        if args.once:
            break
        else:
            print('\n')

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
        # handlers=[RichHandler(show_level=False, show_path=False, show_time=False, markup=False)]
    )
    # cli args: -sourceport -targetport
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sourceport", type=int, default=LISTEN_PORT, help="Port for the MITM proxy to listen on")
    parser.add_argument("-t", "--targetport", type=int, default=TWS_PORT, help="Port of the real TWS/Gateway")
    parser.add_argument("-r", "--recording", action="store_true", help="Enable recording of traffic to a binary log file")
    parser.add_argument("-z", "--sim", action="store_true", help="Enable simulation mode")
    parser.add_argument("-o", "--once", action="store_true", help="Run the MITM proxy once and exit (otherwise it will run continuously)")
    args = parser.parse_args()
    asyncio.run(main(args))
