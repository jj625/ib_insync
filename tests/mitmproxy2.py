"""
single-session, single-client server
"""
import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio.log import logger
import datetime
import logging, argparse
import struct
import time
from enum import Enum, auto
from venv import logger

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 4002          # your client connects here
TWS_HOST    = "127.0.0.1"
TWS_PORT    = 7497          # real TWS/Gateway port

class GWState(Enum):
    INITIAL = auto()
    HANDSHAKE = auto()
    READY = auto()
    REQUESTS = auto()
    CLOSED = auto()

# -------------------------------
# IBKR message framing utilities
# -------------------------------

async def read_ib_message_from_buffer(buffer: bytes):
    """Try to parse one IBKR-framed message from a buffer: [4-byte len][null-delimited text]."""
    if len(buffer) < 4:
        return None, buffer
    msg_len = struct.unpack(">I", buffer[:4])[0]
    if len(buffer) < 4 + msg_len:
        return None, buffer
    payload = buffer[4:4 + msg_len]
    remaining = buffer[4 + msg_len:]
    return payload.decode("utf-8", errors="backslashreplace").split("\0"), remaining

def encode_ib_message(fields):
    """Encode fields into IBKR framing."""
    payload = ("\0".join(fields) + "\0").encode("utf-8")
    return struct.pack(">I", len(payload)) + payload

# -------------------------------
# Minimal IBKR message IDs
# -------------------------------

REQ_MKT_DATA          = 1
CANCEL_MKT_DATA       = 2
REQ_CONTRACT_DETAILS  = 9
START_API             = 71

TICK_PRICE            = 1
CONTRACT_DETAILS      = 10
CONTRACT_DETAILS_END  = 11

class FakeIBGW:
    def __init__(self, host, port, fakegw_port, clientid):
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
            enable_sim=False)
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
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="microseconds")

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
        self.logger = logging.getLogger(__name__)

    async def run(self):
        server_reader, server_writer = await asyncio.open_connection(self.tws_host, self.tws_port)
        cancel_event = asyncio.Event()

        async def client_to_server():
            try:
                while not cancel_event.is_set():
                    data = await self.client_reader.read(4096)
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
                    data = await server_reader.read(4096)
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

    async def run2(self):


        try:
            await self._send_handshake()

            buffer = b''
            while True:
                fields = await read_ib_message(self.reader)
                if not fields:
                    break
                await self._dispatch(fields)

        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            await self._shutdown()

    # ---------------------------
    # Handshake
    # ---------------------------

    async def _send_handshake(self):
        """
        Send serverVersion + connectionTime.
        """
        server_version = "151"
        connection_time = "20260101 12:00:00"
        self.writer.write(encode_ib_message([server_version, connection_time]))
        await self.writer.drain()
        self.state = GWState.READY

    # ---------------------------
    # Message dispatcher
    # ---------------------------

    async def _dispatch(self, fields: list[str]):
        msg_id = int(fields[0])

        if self.state == GWState.READY:
            if msg_id == START_API:
                self.state = GWState.REQUESTS
                return

        if self.state == GWState.REQUESTS:
            if msg_id == REQ_MKT_DATA:
                await self._handle_req_mkt_data(fields)
            elif msg_id == CANCEL_MKT_DATA:
                await self._handle_cancel_mkt_data(fields)
            elif msg_id == REQ_CONTRACT_DETAILS:
                await self._handle_req_contract_details(fields)

    # ---------------------------
    # Static request handler
    # ---------------------------

    async def _handle_req_contract_details(self, fields: list[str]):
        key = tuple(fields[1:])
        responses = self.static_db.lookup_contract_details(key)

        for resp_fields in responses:
            self.writer.write(encode_ib_message(resp_fields))
            await self.writer.drain()

        # End marker
        self.writer.write(encode_ib_message([str(CONTRACT_DETAILS_END)]))
        await self.writer.drain()

    # ---------------------------
    # Streaming request handlers
    # ---------------------------

    async def _handle_req_mkt_data(self, fields: list[str]):
        req_id = int(fields[1])
        contract_key = tuple(fields[2:])

        async def stream_task():
            async for tick in self.synthetic_engine.stream_ticks(contract_key, req_id):
                self.writer.write(tick)
                await self.writer.drain()

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

        self.writer.close()
        await self.writer.wait_closed()

async def main(args: argparse.Namespace):
    gw = FakeIBGW(TWS_HOST, args.targetport, args.sourceport, 12345)
    await gw.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # cli args: -sourceport -targetport
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--sourceport", type=int, default=LISTEN_PORT, help="Port for the MITM proxy to listen on")
    parser.add_argument("-t", "--targetport", type=int, default=TWS_PORT, help="Port of the real TWS/Gateway")
    parser.add_argument("-r", "--recording", action="store_true", help="Enable recording of traffic to a binary log file")
    args = parser.parse_args()
    asyncio.run(main(args))
