"""Socket client for communicating with Interactive Brokers."""

import asyncio
import io
import logging
import math
import struct
import time
from collections import deque
from typing import Deque, List, Optional

from eventkit import Event

from .connection import Connection
from .contract import Contract
from .decoder import Decoder
from .decoder_pb import ProtobufDecoder
from .objects import ConnectionStats, WshEventData
from .order import Order
from .util import UNSET_DOUBLE, UNSET_INTEGER, dataclassAsTuple, getLoop, run

from .wrapper import Wrapper

# Protobuf protocol constants
PROTOBUF_MSG_ID = 200
MIN_SERVER_VER_PROTOBUF = 201

# Outgoing protobuf request types (only what's needed for connectAsync)
from ibapi.protobuf.StartApiRequest_pb2 import StartApiRequest as StartApiRequestProto
from ibapi.protobuf.PositionsRequest_pb2 import PositionsRequest as PositionsRequestProto
from ibapi.protobuf.OpenOrdersRequest_pb2 import OpenOrdersRequest as OpenOrdersRequestProto
from ibapi.protobuf.CompletedOrdersRequest_pb2 import CompletedOrdersRequest as CompletedOrdersRequestProto
from ibapi.protobuf.AccountDataRequest_pb2 import AccountDataRequest as AccountDataRequestProto
from ibapi.protobuf.AccountUpdatesMultiRequest_pb2 import AccountUpdatesMultiRequest as AccountUpdatesMultiRequestProto
from ibapi.protobuf.ExecutionRequest_pb2 import ExecutionRequest as ExecutionRequestProto
from ibapi.protobuf.ExecutionFilter_pb2 import ExecutionFilter as ExecutionFilterProto
from ibapi.protobuf.AutoOpenOrdersRequest_pb2 import AutoOpenOrdersRequest as AutoOpenOrdersRequestProto
from ibapi.protobuf.AllOpenOrdersRequest_pb2 import AllOpenOrdersRequest as AllOpenOrdersRequestProto
from ibapi.protobuf.AccountSummaryRequest_pb2 import AccountSummaryRequest as AccountSummaryRequestProto
from ibapi.protobuf.CancelAccountSummary_pb2 import CancelAccountSummary as CancelAccountSummaryProto
from ibapi.protobuf.CancelPositions_pb2 import CancelPositions as CancelPositionsProto
from ibapi.protobuf.PositionsMultiRequest_pb2 import PositionsMultiRequest as PositionsMultiRequestProto
from ibapi.protobuf.CancelPositionsMulti_pb2 import CancelPositionsMulti as CancelPositionsMultiProto
from ibapi.protobuf.CancelAccountUpdatesMulti_pb2 import CancelAccountUpdatesMulti as CancelAccountUpdatesMultiProto
# market data
from ibapi.protobuf.MarketDataRequest_pb2 import MarketDataRequest as MarketDataRequestProto
from ibapi.protobuf.CancelMarketData_pb2 import CancelMarketData as CancelMarketDataProto
from ibapi.protobuf.MarketDataTypeRequest_pb2 import MarketDataTypeRequest as MarketDataTypeRequestProto
# contract data
from ibapi.protobuf.ContractDataRequest_pb2 import ContractDataRequest as ContractDataRequestProto
from ibapi.protobuf.CancelContractData_pb2 import CancelContractData as CancelContractDataProto
# historical data
from ibapi.protobuf.HistoricalDataRequest_pb2 import HistoricalDataRequest as HistoricalDataRequestProto
from ibapi.protobuf.CancelHistoricalData_pb2 import CancelHistoricalData as CancelHistoricalDataProto
from ibapi.protobuf.RealTimeBarsRequest_pb2 import RealTimeBarsRequest as RealTimeBarsRequestProto
from ibapi.protobuf.CancelRealTimeBars_pb2 import CancelRealTimeBars as CancelRealTimeBarsProto
from ibapi.protobuf.HeadTimestampRequest_pb2 import HeadTimestampRequest as HeadTimestampRequestProto
from ibapi.protobuf.CancelHeadTimestamp_pb2 import CancelHeadTimestamp as CancelHeadTimestampProto
from ibapi.protobuf.HistogramDataRequest_pb2 import HistogramDataRequest as HistogramDataRequestProto
from ibapi.protobuf.CancelHistogramData_pb2 import CancelHistogramData as CancelHistogramDataProto
from ibapi.protobuf.HistoricalTicksRequest_pb2 import HistoricalTicksRequest as HistoricalTicksRequestProto
from ibapi.protobuf.CancelHistoricalTicks_pb2 import CancelHistoricalTicks as CancelHistoricalTicksProto
from ibapi.protobuf.TickByTickRequest_pb2 import TickByTickRequest as TickByTickRequestProto
from ibapi.protobuf.CancelTickByTick_pb2 import CancelTickByTick as CancelTickByTickProto
# pnl
from ibapi.protobuf.PnLRequest_pb2 import PnLRequest as PnLRequestProto
from ibapi.protobuf.CancelPnL_pb2 import CancelPnL as CancelPnLProto
from ibapi.protobuf.PnLSingleRequest_pb2 import PnLSingleRequest as PnLSingleRequestProto
from ibapi.protobuf.CancelPnLSingle_pb2 import CancelPnLSingle as CancelPnLSingleProto
# fa
from ibapi.protobuf.FARequest_pb2 import FARequest as FARequestProto
from ibapi.protobuf.FAReplace_pb2 import FAReplace as FAReplaceProto
# calc implied vol / option price
from ibapi.protobuf.CalculateImpliedVolatilityRequest_pb2 import CalculateImpliedVolatilityRequest as CalculateImpliedVolatilityRequestProto
from ibapi.protobuf.CancelCalculateImpliedVolatility_pb2 import CancelCalculateImpliedVolatility as CancelCalculateImpliedVolatilityProto
from ibapi.protobuf.CalculateOptionPriceRequest_pb2 import CalculateOptionPriceRequest as CalculateOptionPriceRequestProto
from ibapi.protobuf.CancelCalculateOptionPrice_pb2 import CancelCalculateOptionPrice as CancelCalculateOptionPriceProto
# orders
from ibapi.protobuf.GlobalCancelRequest_pb2 import GlobalCancelRequest as GlobalCancelRequestProto
from ibapi.protobuf.PlaceOrderRequest_pb2 import PlaceOrderRequest as PlaceOrderRequestProto
from ibapi.protobuf.CancelOrderRequest_pb2 import CancelOrderRequest as CancelOrderRequestProto
# sec def, family codes, matching symbols, smart components, market rule
from ibapi.protobuf.SecDefOptParamsRequest_pb2 import SecDefOptParamsRequest as SecDefOptParamsRequestProto
from ibapi.protobuf.FamilyCodesRequest_pb2 import FamilyCodesRequest as FamilyCodesRequestProto
from ibapi.protobuf.MatchingSymbolsRequest_pb2 import MatchingSymbolsRequest as MatchingSymbolsRequestProto
from ibapi.protobuf.SmartComponentsRequest_pb2 import SmartComponentsRequest as SmartComponentsRequestProto
from ibapi.protobuf.MarketRuleRequest_pb2 import MarketRuleRequest as MarketRuleRequestProto
from ibapi.protobuf.MarketDepthExchangesRequest_pb2 import MarketDepthExchangesRequest as MarketDepthExchangesRequestProto
# user info, IDs, current time
from ibapi.protobuf.UserInfoRequest_pb2 import UserInfoRequest as UserInfoRequestProto
from ibapi.protobuf.IdsRequest_pb2 import IdsRequest as IdsRequestProto
from ibapi.protobuf.CurrentTimeRequest_pb2 import CurrentTimeRequest as CurrentTimeRequestProto
from ibapi.protobuf.SetServerLogLevelRequest_pb2 import SetServerLogLevelRequest as SetServerLogLevelRequestProto
# verify, display groups
from ibapi.protobuf.VerifyRequest_pb2 import VerifyRequest as VerifyRequestProto
from ibapi.protobuf.VerifyMessageRequest_pb2 import VerifyMessageRequest as VerifyMessageRequestProto
from ibapi.protobuf.QueryDisplayGroupsRequest_pb2 import QueryDisplayGroupsRequest as QueryDisplayGroupsRequestProto
from ibapi.protobuf.SubscribeToGroupEventsRequest_pb2 import SubscribeToGroupEventsRequest as SubscribeToGroupEventsRequestProto
from ibapi.protobuf.UpdateDisplayGroupRequest_pb2 import UpdateDisplayGroupRequest as UpdateDisplayGroupRequestProto
from ibapi.protobuf.UnsubscribeFromGroupEventsRequest_pb2 import UnsubscribeFromGroupEventsRequest as UnsubscribeFromGroupEventsRequestProto
# WSH
from ibapi.protobuf.WshMetaDataRequest_pb2 import WshMetaDataRequest as WshMetaDataRequestProto
from ibapi.protobuf.CancelWshMetaData_pb2 import CancelWshMetaData as CancelWshMetaDataProto
from ibapi.protobuf.WshEventDataRequest_pb2 import WshEventDataRequest as WshEventDataRequestProto
from ibapi.protobuf.CancelWshEventData_pb2 import CancelWshEventData as CancelWshEventDataProto
# fundamental data
from ibapi.protobuf.FundamentalsDataRequest_pb2 import FundamentalsDataRequest as FundamentalsDataRequestProto
from ibapi.protobuf.CancelFundamentalsData_pb2 import CancelFundamentalsData as CancelFundamentalsDataProto
# ibapi client_utils for building contract/order protos
from ibapi.client_utils import (
    createContractProto as _createContractProto,
    createPlaceOrderRequestProto as _createPlaceOrderRequestProto,
    createCancelOrderRequestProto as _createCancelOrderRequestProto,
)

# Outgoing message IDs (matching ibapi.message.OUT)
_OUT_START_API = 71
_OUT_REQ_OPEN_ORDERS = 5
_OUT_REQ_ACCT_DATA = 6
_OUT_REQ_EXECUTIONS = 7
_OUT_REQ_AUTO_OPEN_ORDERS = 15
_OUT_REQ_ALL_OPEN_ORDERS = 16
_OUT_REQ_POSITIONS = 61
_OUT_REQ_ACCOUNT_SUMMARY = 62
_OUT_CANCEL_ACCOUNT_SUMMARY = 63
_OUT_CANCEL_POSITIONS = 64
_OUT_REQ_POSITIONS_MULTI = 74
_OUT_CANCEL_POSITIONS_MULTI = 75
_OUT_REQ_ACCOUNT_UPDATES_MULTI = 76
_OUT_CANCEL_ACCOUNT_UPDATES_MULTI = 77
_OUT_REQ_COMPLETED_ORDERS = 99
_OUT_REQ_MKT_DATA = 1
_OUT_CANCEL_MKT_DATA = 2
_OUT_REQ_CONTRACT_DATA = 9
_OUT_REQ_HISTORICAL_DATA = 20
_OUT_CANCEL_HISTORICAL_DATA = 25
_OUT_REQ_CURRENT_TIME = 49
_OUT_REQ_REAL_TIME_BARS = 50
_OUT_CANCEL_REAL_TIME_BARS = 51
_OUT_REQ_MARKET_DATA_TYPE = 59
_OUT_REQ_HEAD_TIMESTAMP = 87
_OUT_CANCEL_HEAD_TIMESTAMP = 90
_OUT_REQ_HISTOGRAM_DATA = 88
_OUT_CANCEL_HISTOGRAM_DATA = 89
_OUT_REQ_HISTORICAL_TICKS = 96
_OUT_CANCEL_HISTORICAL_TICKS = 107
_OUT_REQ_TICK_BY_TICK_DATA = 97
_OUT_CANCEL_TICK_BY_TICK_DATA = 98
_OUT_REQ_PNL = 92
_OUT_CANCEL_PNL = 93
_OUT_REQ_PNL_SINGLE = 94
_OUT_CANCEL_PNL_SINGLE = 95
_OUT_REQ_FA = 18
_OUT_REPLACE_FA = 19
_OUT_CANCEL_CONTRACT_DATA = 106
_OUT_PLACE_ORDER = 3
_OUT_CANCEL_ORDER = 4
_OUT_REQ_IDS = 8
_OUT_SET_SERVER_LOGLEVEL = 14
_OUT_REQ_GLOBAL_CANCEL = 58
_OUT_VERIFY_REQUEST = 65
_OUT_VERIFY_MESSAGE = 66
_OUT_QUERY_DISPLAY_GROUPS = 67
_OUT_SUBSCRIBE_TO_GROUP_EVENTS = 68
_OUT_UPDATE_DISPLAY_GROUP = 69
_OUT_UNSUBSCRIBE_FROM_GROUP_EVENTS = 70
_OUT_REQ_SEC_DEF_OPT_PARAMS = 78
_OUT_REQ_FAMILY_CODES = 80
_OUT_REQ_MATCHING_SYMBOLS = 81
_OUT_REQ_MKT_DEPTH_EXCHANGES = 82
_OUT_REQ_SMART_COMPONENTS = 83
_OUT_REQ_MARKET_RULE = 91
_OUT_REQ_CALC_IMPLIED_VOLAT = 54
_OUT_REQ_CALC_OPTION_PRICE = 55
_OUT_CANCEL_CALC_IMPLIED_VOLAT = 56
_OUT_CANCEL_CALC_OPTION_PRICE = 57
_OUT_REQ_FUNDAMENTAL_DATA = 52
_OUT_CANCEL_FUNDAMENTAL_DATA = 53
_OUT_REQ_WSH_META_DATA = 100
_OUT_CANCEL_WSH_META_DATA = 101
_OUT_REQ_WSH_EVENT_DATA = 102
_OUT_CANCEL_WSH_EVENT_DATA = 103
_OUT_REQ_USER_INFO = 104

# Min server versions for protobuf per request category
_MIN_PB_COMPLETED_ORDER = 204  # MIN_SERVER_VER_PROTOBUF_COMPLETED_ORDER
_MIN_PB_CONTRACT_DATA = 205  # MIN_SERVER_VER_PROTOBUF_CONTRACT_DATA
_MIN_PB_MARKET_DATA = 206  # MIN_SERVER_VER_PROTOBUF_MARKET_DATA
_MIN_PB_ACCOUNTS_POSITIONS = 207  # MIN_SERVER_VER_PROTOBUF_ACCOUNTS_POSITIONS
_MIN_PB_HISTORICAL_DATA = 208  # MIN_SERVER_VER_PROTOBUF_HISTORICAL_DATA
_MIN_PB_SCAN_DATA = 210  # MIN_SERVER_VER_PROTOBUF_SCAN_DATA (also PnL, fundamental)
_MIN_PB_SCAN_DATA_NEWS = 209  # MIN_SERVER_VER_PROTOBUF_NEWS_DATA (also WSH)
_MIN_PB_REST_1 = 211  # MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_1 (FA, exercise, calc)
_MIN_PB_REST_2 = 212  # MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_2 (sec def, family, etc)
_MIN_PB_REST_3 = 213  # MIN_SERVER_VER_PROTOBUF_REST_MESSAGES_3
_MIN_PB_CANCEL_CONTRACT_DATA = 215  # MIN_SERVER_VER_CANCEL_CONTRACT_DATA
_MIN_PB_PLACE_ORDER = 203  # MIN_SERVER_VER_PROTOBUF_PLACE_ORDER

from .msg_names import in_msg_name as _in_msg_name, out_msg_name as _out_msg_name

class Client:
    """
    Replacement for ``ibapi.client.EClient`` that uses asyncio.

    The client is fully asynchronous and has its own
    event-driven networking code that replaces the
    networking code of the standard EClient.
    It also replaces the infinite loop of ``EClient.run()``
    with the asyncio event loop. It can be used as a drop-in
    replacement for the standard EClient as provided by IBAPI.

    Compared to the standard EClient this client has the following
    additional features:

    * ``client.connect()`` will block until the client is ready to
      serve requests; It is not necessary to wait for ``nextValidId``
      to start requests as the client has already done that.
      The reqId is directly available with :py:meth:`.getReqId()`.

    * ``client.connectAsync()`` is a coroutine for connecting asynchronously.

    * When blocking, ``client.connect()`` can be made to time out with
      the timeout parameter (default 2 seconds).

    * Optional ``wrapper.priceSizeTick(reqId, tickType, price, size)`` that
      combines price and size instead of the two wrapper methods
      priceTick and sizeTick.

    * Automatic request throttling.

    * Optional ``wrapper.tcpDataArrived()`` method;
      If the wrapper has this method it is invoked directly after
      a network packet has arrived.
      A possible use is to timestamp all data in the packet with
      the exact same time.

    * Optional ``wrapper.tcpDataProcessed()`` method;
      If the wrapper has this method it is invoked after the
      network packet's data has been handled.
      A possible use is to write or evaluate the newly arrived data in
      one batch instead of item by item.

    Parameters:
      MaxRequests (int):
        Throttle the number of requests to ``MaxRequests`` per
        ``RequestsInterval`` seconds. Set to 0 to disable throttling.
      RequestsInterval (float):
        Time interval (in seconds) for request throttling.
      MinClientVersion (int):
        Client protocol version.
      MaxClientVersion (int):
        Client protocol version.

    Events:
      * ``apiStart`` ()
      * ``apiEnd`` ()
      * ``apiError`` (errorMsg: str)
      * ``throttleStart`` ()
      * ``throttleEnd`` ()
    """

    events = ('apiStart', 'apiEnd', 'apiError', 'throttleStart', 'throttleEnd')

    MaxRequests = 45
    RequestsInterval = 1

    MinClientVersion = 157
    MaxClientVersion = 223  # raised to negotiate protobuf-capable server versions

    (DISCONNECTED, CONNECTING, CONNECTED) = range(3)

    import weakref, threading
    _live_instances: weakref.WeakSet = weakref.WeakSet()
    _lock = threading.Lock()
    def _check_single_instance(self):
        """Ensure only a single class instance is created."""
        cls = type(self)
        with cls._lock:
            cls._live_instances.add(self)
            count = len(cls._live_instances)
            if count > 1:
                raise RuntimeError(
                    f'Only a single {cls.__name__} instance is allowed, '
                    f'found {count} instances')
    @classmethod
    def live_count(cls):
        with cls._lock:
            return len(cls._live_instances)

    @classmethod
    def all_instances(cls):
        with cls._lock:
            return list(cls._live_instances)

    def __init__(self, wrapper: Wrapper):
        self._check_single_instance()
        self.version = '0.0.1'
        self.wrapper: Wrapper = wrapper
        self.decoder = Decoder(wrapper, 0)
        self.pbDecoder = ProtobufDecoder(wrapper, 0)
        self.apiStart = Event('apiStart')
        self.apiEnd = Event('apiEnd')
        self.apiError = Event('apiError')
        self.throttleStart = Event('throttleStart')
        self.throttleEnd = Event('throttleEnd')
        self._logger = logging.getLogger('ib_insync.client')
        self._logger.debug('Client::__init__')

        self.conn = Connection()
        self.conn.hasData += self._onSocketHasData
        self.conn.disconnected += self._onSocketDisconnected

        # extra optional wrapper methods
        self._priceSizeTick = getattr(wrapper, 'priceSizeTick', None)
        self._tcpDataArrived = getattr(wrapper, 'tcpDataArrived', None)
        self._tcpDataProcessed = getattr(wrapper, 'tcpDataProcessed', None)

        self.host = ''
        self.port = -1
        self.clientId = -1
        self.optCapab = ''
        self.connectOptions = b''
        self.reset()

    def reset(self):
        self.connState = Client.DISCONNECTED
        self._apiReady = False
        self._serverVersion = 0
        self._data = b''
        self._hasReqId = False
        self._reqIdSeq = 0
        self._accounts = []
        self._startTime = time.time()
        self._numBytesRecv = 0
        self._numMsgRecv = 0
        self._isThrottling = False
        self._msgQ: Deque[str] = deque()
        self._timeQ: Deque[float] = deque()
        self._logger.debug('Client::reset')

    def serverVersion(self) -> int:
        return self._serverVersion

    def run(self):
        self._logger.debug('Client::run')
        loop = getLoop()
        loop.run_forever()

    def isConnected(self):
        # self._logger.debug('Client::isConnected')
        return self.connState == Client.CONNECTED

    def isReady(self) -> bool:
        """Is the API connection up and running?"""
        return self._apiReady

    def connectionStats(self) -> ConnectionStats:
        """Get statistics about the connection."""
        # self._logger.debug('Client::connectionStats')
        if not self.isReady():
            raise ConnectionError('Not connected')
        return ConnectionStats(
            self._startTime,
            time.time() - self._startTime,
            self._numBytesRecv, self.conn.numBytesSent,
            self._numMsgRecv, self.conn.numMsgSent)

    def getReqId(self) -> int:
        """Get new request ID."""
        if not self.isReady():
            raise ConnectionError('Not connected')
        newId = self._reqIdSeq
        self._reqIdSeq += 1
        self._logger.debug(f'Client::getReqId {newId}')
        return newId

    def updateReqId(self, minReqId: int):
        """Update the next reqId to be at least ``minReqId``."""
        self._reqIdSeq = max(self._reqIdSeq, minReqId)

    def getAccounts(self) -> List[str]:
        """Get the list of account names that are under management."""
        if not self.isReady():
            raise ConnectionError('Not connected')
        return self._accounts

    def setConnectOptions(self, connectOptions: str):
        """
        Set additional connect options.

        Args:
            connectOptions: Use "+PACEAPI" to use request-pacing built
                into TWS/gateway 974+ (obsolete).
        """
        self.connectOptions = connectOptions.encode()

    def connect(
            self, host: str, port: int, clientId: int,
            timeout: float = 2.0):
        """
        Connect to a running TWS or IB gateway application.

        Args:
            host: Host name or IP address.
            port: Port number.
            clientId: ID number to use for this client; must be unique per
                connection.
            timeout: If establishing the connection takes longer than
                ``timeout`` seconds then the ``asyncio.TimeoutError`` exception
                is raised. Set to 0 to disable timeout.
        """
        run(self.connectAsync(host, port, clientId, timeout))

    async def connectAsync(self, host: str, port: int, clientId: int, timeout: Optional[float]=2.0):
        try:
            self._logger.info(
                f'Connecting to {host}:{port} with clientId {clientId}...')
            self.host = host
            self.port = int(port)
            self.clientId = int(clientId)
            self.connState = Client.CONNECTING
            timeout = timeout or None
            await asyncio.wait_for(self.conn.connectAsync(host, port), timeout)
            self._logger.info('Connected')
            msg = b'API\0' + self._prefix(b'v%d..%d%s' % (
                self.MinClientVersion, self.MaxClientVersion,
                b' ' + self.connectOptions if self.connectOptions else b''))
            self.conn.sendMsg(msg)
            await asyncio.wait_for(self.apiStart, timeout)
            self._logger.info('API connection ready')
        except BaseException as e:
            self.disconnect()
            msg = f'API connection failed: {e!r}'
            self._logger.error(msg)
            self.apiError.emit(msg)
            if isinstance(e, ConnectionRefusedError):
                self._logger.error('Make sure API port on TWS/IBG is open')
            raise

    def disconnect(self):
        """Disconnect from IB connection."""
        self._logger.info('Disconnecting')
        self.connState = Client.DISCONNECTED
        self.conn.disconnect()
        self.reset()

    def send(self, *fields, makeEmpty: bool = True) -> None:
        """Serialize and send the given fields using the IB socket protocol."""
        if not self.isConnected():
            raise ConnectionError('Not connected')

        msg = io.StringIO()
        empty = (None, UNSET_INTEGER, UNSET_DOUBLE) if makeEmpty else (None,)
        for field in fields:
            typ = type(field)
            if field in empty: # check for special values
                s = ''
            elif typ is str: # the rests are checked by type
                s = field
            elif typ is int:
                s = str(field)
            elif typ is float:
                s = 'Infinite' if field == math.inf else str(field)
            elif typ is bool:
                s = '1' if field else '0'
            elif typ is list:
                # list of TagValue
                s = ''.join(f'{v.tag}={v.value};' for v in field)
            elif isinstance(field, Contract):
                c = field
                s = '\0'.join(str(f) for f in (
                    c.conId, c.symbol, c.secType,
                    c.lastTradeDateOrContractMonth, c.strike,
                    c.right, c.multiplier, c.exchange,
                    c.primaryExchange, c.currency,
                    c.localSymbol, c.tradingClass))
            else:
                s = str(field)
            msg.write(s)
            msg.write('\0')
        self.sendMsg(msg.getvalue())

    def sendMsg(self, msg: str):
        loop = getLoop()
        t = loop.time()
        times = self._timeQ
        msgs = self._msgQ
        while times and t - times[0] > self.RequestsInterval:
            times.popleft()
        if msg:
            msgs.append(msg)
        while msgs and (len(times) < self.MaxRequests or not self.MaxRequests):
            msg = msgs.popleft()
            self.conn.sendMsg(self._prefix(msg.encode()))
            # times.append(t)
            times.append(loop.time())  # Capture actual send time
            if self._logger.isEnabledFor(logging.DEBUG):
                self._logger.debug('>>> %s', msg[:-1].replace('\0', ','))
        if msgs:
            if not self._isThrottling:
                self._isThrottling = True
                self.throttleStart.emit()
                self._logger.debug('Started to throttle requests')
            loop.call_at(
                times[0] + self.RequestsInterval,
                lambda: self.sendMsg(''))
        else:
            if self._isThrottling:
                self._isThrottling = False
                self.throttleEnd.emit()
                self._logger.debug('Stopped to throttle requests')

    def _prefix(self, msg):
        # prefix a message with its length
        return struct.pack('>I', len(msg)) + msg

    def _useProtobuf(self) -> bool:
        """Whether the current server version supports protobuf framing."""
        return self._serverVersion >= MIN_SERVER_VER_PROTOBUF

    def sendProto(self, msgId: int, proto_msg) -> None:
        """Serialize and send a protobuf request message."""
        if not self.isConnected():
            raise ConnectionError('Not connected')
        payload = proto_msg.SerializeToString()
        # outgoing protobuf: msgId + PROTOBUF_MSG_ID offset, as big-endian int32
        byteArray = (msgId + PROTOBUF_MSG_ID).to_bytes(4, 'big') + payload
        self.conn.sendMsg(self._prefix(byteArray))
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(
                '>>> proto %s len=%d', _out_msg_name(msgId), len(payload))

    def _onSocketHasData(self, data):
        debug = self._logger.isEnabledFor(logging.DEBUG)
        if self._tcpDataArrived:
            self._tcpDataArrived()

        self._data += data
        self._numBytesRecv += len(data)

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
            self._numMsgRecv += 1

            if not self._serverVersion:
                # Handshake: always text, 2 null-delimited fields
                msg = rawMsg.decode(errors='backslashreplace')
                fields = msg.split('\0')
                fields.pop()
                if debug:
                    self._logger.debug('<<< %s', ','.join(fields))
                if len(fields) == 2:
                    version, _connTime = fields
                    self._serverVersion = int(version)
                    if self._serverVersion < self.MinClientVersion:
                        self._onSocketDisconnected(
                            'TWS/gateway version must be >= 972')
                        return
                    self.decoder.serverVersion = self._serverVersion
                    self.pbDecoder.serverVersion = self._serverVersion
                    self.connState = Client.CONNECTED
                    self.startApi()
                    self.wrapper.connectAck()
                    self._logger.info(
                        f'Logged on to server version {self._serverVersion}')
                continue

            # Post-handshake message routing
            if self._useProtobuf():
                # New framing: first 4 bytes are msgId as big-endian int32
                msgId = int.from_bytes(rawMsg[:4], 'big')
                msgPayload = rawMsg[4:]

                if msgId > PROTOBUF_MSG_ID:
                    # Protobuf message
                    realMsgId = msgId - PROTOBUF_MSG_ID
                    if debug:
                        self._logger.debug(
                            '<<< proto %s len=%d',
                            _in_msg_name(realMsgId), len(msgPayload))

                    # Snoop for nextValidId and managedAccounts
                    if not self._apiReady:
                        self._snoopProtobuf(realMsgId, msgPayload)

                    self.pbDecoder.processProtoBuf(msgPayload, realMsgId)
                else:
                    # Legacy text message with binary msgId prefix
                    text = msgPayload.decode(errors='backslashreplace')
                    fields = text.split('\0')
                    if fields and fields[-1] == '':
                        fields.pop()
                    # Prepend msgId as first field for Decoder compatibility
                    fields = [str(msgId)] + fields
                    if debug:
                        self._logger.debug('<<< %s', ','.join(fields))

                    if not self._apiReady:
                        self._snoopText(msgId, fields)

                    self.decoder.interpret(fields)
            else:
                # Legacy framing: all text, null-delimited
                msg = rawMsg.decode(errors='backslashreplace')
                fields = msg.split('\0')
                fields.pop()
                if debug:
                    self._logger.debug('<<< %s', ','.join(fields))

                if not self._apiReady:
                    msgId = int(fields[0])
                    self._snoopText(msgId, fields)

                self.decoder.interpret(fields)

        if self._tcpDataProcessed:
            self._tcpDataProcessed()

    def _snoopText(self, msgId: int, fields: list):
        """Snoop text messages for nextValidId / managedAccounts during init."""
        if msgId == 9:  # NEXT_VALID_ID
            _, _, validId = fields
            self.updateReqId(int(validId))
            self._hasReqId = True
        elif msgId == 15:  # MANAGED_ACCTS
            _, _, accts = fields
            self._accounts = [a for a in accts.split(',') if a]
        if self._hasReqId and self._accounts:
            self._apiReady = True
            self.apiStart.emit()

    def _snoopProtobuf(self, msgId: int, payload: bytes):
        """Snoop protobuf messages for nextValidId / managedAccounts."""
        from ibapi.protobuf.NextValidId_pb2 import NextValidId as NextValidIdProto
        from ibapi.protobuf.ManagedAccounts_pb2 import ManagedAccounts as ManagedAccountsProto
        if msgId == 9:  # NEXT_VALID_ID
            proto = NextValidIdProto()
            proto.ParseFromString(payload)
            validId = proto.orderId if proto.HasField('orderId') else 0
            self.updateReqId(validId)
            self._hasReqId = True
        elif msgId == 15:  # MANAGED_ACCTS
            proto = ManagedAccountsProto()
            proto.ParseFromString(payload)
            accts = proto.accountsList if proto.HasField('accountsList') else ''
            self._accounts = [a for a in accts.split(',') if a]
        if self._hasReqId and self._accounts:
            self._apiReady = True
            self.apiStart.emit()

    def _onSocketDisconnected(self, msg):
        wasReady = self.isReady()
        if not self.isConnected():
            self._logger.info('Disconnected.')
        elif not msg:
            msg = 'Peer closed connection.'
            if not wasReady:
                msg += f' clientId {self.clientId} already in use?'
        if msg:
            self._logger.error(msg)
            self.apiError.emit(msg)
        self.wrapper.setEventsDone()
        if wasReady:
            self.wrapper.connectionClosed()
        self.reset()
        if wasReady:
            self.apiEnd.emit()

    # client request methods
    # the message type id is sent first, often followed by a version number

    def reqMktData(
            self, reqId, contract, genericTickList, snapshot,
            regulatorySnapshot, mktDataOptions):
        if self._serverVersion >= _MIN_PB_MARKET_DATA:
            proto = MarketDataRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if genericTickList:
                proto.genericTickList = genericTickList
            if snapshot:
                proto.snapshot = snapshot
            if regulatorySnapshot:
                proto.regulatorySnapshot = regulatorySnapshot
            self.sendProto(_OUT_REQ_MKT_DATA, proto)
            return
        fields = [1, 11, reqId, contract]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.conId, leg.ratio, leg.action, leg.exchange]

        dnc = contract.deltaNeutralContract
        if dnc:
            fields += [True, dnc.conId, dnc.delta, dnc.price]
        else:
            fields += [False]

        fields += [
            genericTickList, snapshot, regulatorySnapshot, mktDataOptions]
        self.send(*fields)

    def cancelMktData(self, reqId):
        if self._serverVersion >= _MIN_PB_MARKET_DATA:
            proto = CancelMarketDataProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_MKT_DATA, proto)
            return
        self.send(2, 2, reqId)

    def placeOrder(self, orderId, contract, order: Order):
        version = self.serverVersion()
        if version < 183 and order.customerAccount: # MIN_SERVER_VER_BOND_ACCRUED_INTEREST=183
            raise ValueError('customerAccount only available with server version 183+')
        if version < 184 and order.professionalCustomer: # MIN_SERVER_VER_PROFESSIONAL_CUSTOMER=184
            raise ValueError('professionalCustomer only available with server version 184+')
        if version < 187 and (order.externalUserId or order.manualOrderIndicator != UNSET_INTEGER): # MIN_SERVER_VER_RFQ_FIELDS=187
            raise ValueError('externalUserId and manualOrderIndicator only available with server version 187+')
        fields = [
            3, orderId,
            contract,
            contract.secIdType,
            contract.secId,
            order.action,
            order.totalQuantity,
            order.orderType,
            order.lmtPrice,
            order.auxPrice,
            order.tif,
            order.ocaGroup,
            order.account,
            order.openClose,
            order.origin,
            order.orderRef,
            order.transmit,
            order.parentId,
            order.blockOrder,
            order.sweepToFill,
            order.displaySize,
            order.triggerMethod,
            order.outsideRth,
            order.hidden]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [
                    leg.conId,
                    leg.ratio,
                    leg.action,
                    leg.exchange,
                    leg.openClose,
                    leg.shortSaleSlot,
                    leg.designatedLocation,
                    leg.exemptCode]

            legs = order.orderComboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.price]

            params = order.smartComboRoutingParams or []
            fields += [len(params)]
            for param in params:
                fields += [param.tag, param.value]

        fields += [
            '',
            order.discretionaryAmt,
            order.goodAfterTime,
            order.goodTillDate,
            order.faGroup,
            order.faMethod,
            order.faPercentage]
        if version < 177:
            fields += [order.faProfile]
        fields += [
            order.modelCode,
            order.shortSaleSlot,
            order.designatedLocation,
            order.exemptCode,
            order.ocaType,
            order.rule80A,
            order.settlingFirm,
            order.allOrNone,
            order.minQty,
            order.percentOffset,
            order.eTradeOnly,
            order.firmQuoteOnly,
            order.nbboPriceCap,
            order.auctionStrategy,
            order.startingPrice,
            order.stockRefPrice,
            order.delta,
            order.stockRangeLower,
            order.stockRangeUpper,
            order.overridePercentageConstraints,
            order.volatility,
            order.volatilityType,
            order.deltaNeutralOrderType,
            order.deltaNeutralAuxPrice]

        if order.deltaNeutralOrderType:
            fields += [
                order.deltaNeutralConId,
                order.deltaNeutralSettlingFirm,
                order.deltaNeutralClearingAccount,
                order.deltaNeutralClearingIntent,
                order.deltaNeutralOpenClose,
                order.deltaNeutralShortSale,
                order.deltaNeutralShortSaleSlot,
                order.deltaNeutralDesignatedLocation]

        fields += [
            order.continuousUpdate,
            order.referencePriceType,
            order.trailStopPrice,
            order.trailingPercent,
            order.scaleInitLevelSize,
            order.scaleSubsLevelSize,
            order.scalePriceIncrement]

        if (0 < order.scalePriceIncrement < UNSET_DOUBLE):
            fields += [
                order.scalePriceAdjustValue,
                order.scalePriceAdjustInterval,
                order.scaleProfitOffset,
                order.scaleAutoReset,
                order.scaleInitPosition,
                order.scaleInitFillQty,
                order.scaleRandomPercent]

        fields += [
            order.scaleTable,
            order.activeStartTime,
            order.activeStopTime,
            order.hedgeType]

        if order.hedgeType:
            fields += [order.hedgeParam]

        fields += [
            order.optOutSmartRouting,
            order.clearingAccount,
            order.clearingIntent,
            order.notHeld]

        dnc = contract.deltaNeutralContract
        if dnc:
            fields += [True, dnc.conId, dnc.delta, dnc.price]
        else:
            fields += [False]

        fields += [order.algoStrategy]
        if order.algoStrategy:
            params = order.algoParams or []
            fields += [len(params)]
            for param in params:
                fields += [param.tag, param.value]

        fields += [
            order.algoId,
            order.whatIf,
            order.orderMiscOptions,
            order.solicited,
            order.randomizeSize,
            order.randomizePrice]

        if order.orderType in ('PEG BENCH', 'PEGBENCH'):
            fields += [
                order.referenceContractId,
                order.isPeggedChangeAmountDecrease,
                order.peggedChangeAmount,
                order.referenceChangeAmount,
                order.referenceExchangeId]

        fields += [len(order.conditions)]
        if order.conditions:
            for cond in order.conditions:
                fields += dataclassAsTuple(cond)
            fields += [
                order.conditionsIgnoreRth,
                order.conditionsCancelOrder]

        fields += [
            order.adjustedOrderType,
            order.triggerPrice,
            order.lmtPriceOffset,
            order.adjustedStopPrice,
            order.adjustedStopLimitPrice,
            order.adjustedTrailingAmount,
            order.adjustableTrailingUnit,
            order.extOperator,
            order.softDollarTier.name,
            order.softDollarTier.val,
            order.cashQty,
            order.mifid2DecisionMaker,
            order.mifid2DecisionAlgo,
            order.mifid2ExecutionTrader,
            order.mifid2ExecutionAlgo,
            order.dontUseAutoPriceForHedge,
            order.isOmsContainer,
            order.discretionaryUpToLimitPrice,
            order.usePriceMgmtAlgo]

        if version >= 158:
            fields += [order.duration]
        if version >= 160:
            fields += [order.postToAts]
        if version >= 162:
            fields += [order.autoCancelParent]
        if version >= 166:
            fields += [order.advancedErrorOverride]
        if version >= 169:
            fields += [order.manualOrderTime]
        if version >= 170:
            if contract.exchange == 'IBKRATS':
                fields += [order.minTradeQty]
            if order.orderType in ('PEG BEST', 'PEGBEST'):
                fields += [
                    order.minCompeteSize,
                    order.competeAgainstBestOffset]
                if order.competeAgainstBestOffset == math.inf:
                    fields += [order.midOffsetAtWhole, order.midOffsetAtHalf]
            elif order.orderType in ('PEG MID', 'PEGMID'):
                fields += [order.midOffsetAtWhole, order.midOffsetAtHalf]
        if version >= 183: # MIN_SERVER_VER_CUSTOMER_ACCOUNT=183
            fields += [order.customerAccount]
        if version >= 184: # MIN_SERVER_VER_PROFESSIONAL_CUSTOMER=184
            fields += [order.professionalCustomer]
        if version >= 187: # MIN_SERVER_VER_RFQ_FIELDS=187
            fields += [order.externalUserId, order.manualOrderIndicator]

        self.send(*fields)

    def cancelOrder(self, orderId, manualCancelOrderTime=''):
        fields = [4, 1, orderId]
        if self.serverVersion() >= 169:
            fields += [manualCancelOrderTime]
        self.send(*fields)

    def reqOpenOrders(self):
        if self._serverVersion >= _MIN_PB_COMPLETED_ORDER:
            self.sendProto(_OUT_REQ_OPEN_ORDERS, OpenOrdersRequestProto())
            return
        self.send(5, 1)

    def reqAccountUpdates(self, subscribe: bool, acctCode):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = AccountDataRequestProto()
            proto.subscribe = subscribe
            if acctCode:
                proto.acctCode = acctCode
            self.sendProto(_OUT_REQ_ACCT_DATA, proto)
            return
        self.send(6, 2, subscribe, acctCode)

    def reqExecutions(self, reqId, execFilter):
        if self._serverVersion >= MIN_SERVER_VER_PROTOBUF:
            filterProto = ExecutionFilterProto()
            if execFilter.clientId:
                filterProto.clientId = int(execFilter.clientId)
            if execFilter.acctCode:
                filterProto.acctCode = execFilter.acctCode
            if execFilter.time:
                filterProto.time = execFilter.time
            if execFilter.symbol:
                filterProto.symbol = execFilter.symbol
            if execFilter.secType:
                filterProto.secType = execFilter.secType
            if execFilter.exchange:
                filterProto.exchange = execFilter.exchange
            if execFilter.side:
                filterProto.side = execFilter.side
            reqProto = ExecutionRequestProto()
            reqProto.reqId = reqId
            reqProto.executionFilter.CopyFrom(filterProto)
            self.sendProto(_OUT_REQ_EXECUTIONS, reqProto)
            return
        self.send(
            7, 3, reqId,
            execFilter.clientId,
            execFilter.acctCode,
            execFilter.time,
            execFilter.symbol,
            execFilter.secType,
            execFilter.exchange,
            execFilter.side)

    def reqContractDetails(self, reqId, contract):
        if self._serverVersion >= _MIN_PB_CONTRACT_DATA:
            proto = ContractDataRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            self.sendProto(_OUT_REQ_CONTRACT_DATA, proto)
            return
        fields = [
            9, 8, reqId,
            contract,
            contract.includeExpired,
            contract.secIdType,
            contract.secId]
        if self.serverVersion() >= 176:
            fields += [contract.issuerId]
        self.send(*fields)

    def reqMktDepth(
            self, reqId, contract, numRows, isSmartDepth, mktDepthOptions):
        self.send(
            10, 5, reqId,
            contract.conId,
            contract.symbol,
            contract.secType,
            contract.lastTradeDateOrContractMonth,
            contract.strike,
            contract.right,
            contract.multiplier,
            contract.exchange,
            contract.primaryExchange,
            contract.currency,
            contract.localSymbol,
            contract.tradingClass,
            numRows,
            isSmartDepth,
            mktDepthOptions)

    def cancelMktDepth(self, reqId, isSmartDepth):
        self.send(11, 1, reqId, isSmartDepth)

    def reqNewsBulletins(self, allMsgs):
        self.send(12, 1, allMsgs)

    def cancelNewsBulletins(self):
        self.send(13, 1)

    def reqAutoOpenOrders(self, bAutoBind):
        if self._serverVersion >= _MIN_PB_COMPLETED_ORDER:
            proto = AutoOpenOrdersRequestProto()
            proto.bAutoBind = bAutoBind
            self.sendProto(_OUT_REQ_AUTO_OPEN_ORDERS, proto)
            return
        self.send(15, 1, bAutoBind)

    def reqAllOpenOrders(self):
        if self._serverVersion >= _MIN_PB_COMPLETED_ORDER:
            self.sendProto(_OUT_REQ_ALL_OPEN_ORDERS, AllOpenOrdersRequestProto())
            return
        self.send(16, 1)

    def reqManagedAccts(self):
        self.send(17, 1)

    def requestFA(self, faData):
        if self._serverVersion >= _MIN_PB_REST_1:
            proto = FARequestProto()
            proto.faDataType = faData
            self.sendProto(_OUT_REQ_FA, proto)
            return
        self.send(18, 1, faData)

    def replaceFA(self, reqId, faData, cxml):
        if self._serverVersion >= _MIN_PB_REST_1:
            proto = FAReplaceProto()
            proto.reqId = reqId
            proto.faDataType = faData
            if cxml:
                proto.xml = cxml
            self.sendProto(_OUT_REPLACE_FA, proto)
            return
        self.send(19, 1, faData, cxml, reqId)

    def reqHistoricalData(
            self, reqId, contract, endDateTime, durationStr, barSizeSetting,
            whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = HistoricalDataRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if endDateTime:
                proto.endDateTime = str(endDateTime)
            if durationStr:
                proto.duration = durationStr
            if barSizeSetting:
                proto.barSizeSetting = barSizeSetting
            if whatToShow:
                proto.whatToShow = whatToShow
            if useRTH:
                proto.useRTH = useRTH
            proto.formatDate = formatDate
            if keepUpToDate:
                proto.keepUpToDate = keepUpToDate
            self.sendProto(_OUT_REQ_HISTORICAL_DATA, proto)
            return
        fields = [
            20, reqId, contract, contract.includeExpired,
            endDateTime, barSizeSetting, durationStr, useRTH,
            whatToShow, formatDate]

        if contract.secType == 'BAG':
            legs = contract.comboLegs or []
            fields += [len(legs)]
            for leg in legs:
                fields += [leg.conId, leg.ratio, leg.action, leg.exchange]

        fields += [keepUpToDate, chartOptions]
        self.send(*fields)

    def exerciseOptions(
            self, reqId, contract, exerciseAction: int,
            exerciseQuantity: int, account: str, override: int,
            manualOrderTime: str, customerAccount: str, professionalCustomer: Optional[bool]
            ):
        serverVersion = self.serverVersion()
        if serverVersion < 180 and manualOrderTime: # MIN_SERVER_VER_MANUAL_ORDER_TIME_EXERCISE_OPTIONS=180
            raise ValueError('manualOrderTime only available with server version 180+')
        if serverVersion < 183 and customerAccount: # MIN_SERVER_VER_CUSTOMER_ACCOUNT=183
            raise ValueError('customerAccount only available with server version 183+')
        if serverVersion < 184 and professionalCustomer is not None: # MIN_SERVER_VER_PROFESSIONAL_CUSTOMER=184
            raise ValueError('professionalCustomer only available with server version 184+')
        fields = [
            21, 2, reqId,
            contract.conId,
            contract.symbol,
            contract.secType,
            contract.lastTradeDateOrContractMonth,
            contract.strike,
            contract.right,
            contract.multiplier,
            contract.exchange,
            contract.currency,
            contract.localSymbol,
            contract.tradingClass,
            exerciseAction, exerciseQuantity, account, override]
        if serverVersion >= 180:
            fields += [manualOrderTime]
        if serverVersion >= 183:
            fields += [customerAccount]
        if serverVersion >= 184 and professionalCustomer is not None:
            fields += [professionalCustomer]
        self.send(*fields)

    def reqScannerSubscription(
            self, reqId, subscription, scannerSubscriptionOptions,
            scannerSubscriptionFilterOptions):
        sub = subscription
        self.send(
            22, reqId,
            sub.numberOfRows,
            sub.instrument,
            sub.locationCode,
            sub.scanCode,
            sub.abovePrice,
            sub.belowPrice,
            sub.aboveVolume,
            sub.marketCapAbove,
            sub.marketCapBelow,
            sub.moodyRatingAbove,
            sub.moodyRatingBelow,
            sub.spRatingAbove,
            sub.spRatingBelow,
            sub.maturityDateAbove,
            sub.maturityDateBelow,
            sub.couponRateAbove,
            sub.couponRateBelow,
            sub.excludeConvertible,
            sub.averageOptionVolumeAbove,
            sub.scannerSettingPairs,
            sub.stockTypeFilter,
            scannerSubscriptionFilterOptions,
            scannerSubscriptionOptions)

    def cancelScannerSubscription(self, reqId):
        self.send(23, 1, reqId)

    def reqScannerParameters(self):
        self.send(24, 1)

    def cancelHistoricalData(self, reqId):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = CancelHistoricalDataProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_HISTORICAL_DATA, proto)
            return
        self.send(25, 1, reqId)

    def reqRealTimeBars(
            self, reqId, contract, barSize, whatToShow,
            useRTH, realTimeBarsOptions):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = RealTimeBarsRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            proto.barSize = barSize
            if whatToShow:
                proto.whatToShow = whatToShow
            if useRTH:
                proto.useRTH = useRTH
            self.sendProto(_OUT_REQ_REAL_TIME_BARS, proto)
            return
        self._logger.debug('Client::reqRealTimeBars')
        self.send(
            50, 3, reqId, contract, barSize, whatToShow,
            useRTH, realTimeBarsOptions)

    def cancelRealTimeBars(self, reqId):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = CancelRealTimeBarsProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_REAL_TIME_BARS, proto)
            return
        self._logger.debug('Client::cancelRealTimeBars')
        self.send(51, 1, reqId)

    def reqFundamentalData(
            self, reqId, contract, reportType, fundamentalDataOptions):
        if self._serverVersion >= _MIN_PB_SCAN_DATA:
            proto = FundamentalsDataRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if reportType:
                proto.reportType = reportType
            self.sendProto(_OUT_REQ_FUNDAMENTAL_DATA, proto)
            return
        options = fundamentalDataOptions or []
        self.send(
            52, 2, reqId,
            contract.conId,
            contract.symbol,
            contract.secType,
            contract.exchange,
            contract.primaryExchange,
            contract.currency,
            contract.localSymbol,
            reportType, len(options), options)

    def cancelFundamentalData(self, reqId):
        if self._serverVersion >= _MIN_PB_SCAN_DATA:
            proto = CancelFundamentalsDataProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_FUNDAMENTAL_DATA, proto)
            return
        self.send(53, 1, reqId)

    def calculateImpliedVolatility(
            self, reqId, contract, optionPrice, underPrice, implVolOptions):
        if self._serverVersion >= _MIN_PB_REST_1:
            proto = CalculateImpliedVolatilityRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            proto.optionPrice = optionPrice
            proto.underPrice = underPrice
            self.sendProto(_OUT_REQ_CALC_IMPLIED_VOLAT, proto)
            return
        self.send(
            54, 3, reqId, contract, optionPrice, underPrice,
            len(implVolOptions), implVolOptions)

    def calculateOptionPrice(
            self, reqId, contract, volatility, underPrice, optPrcOptions):
        if self._serverVersion >= _MIN_PB_REST_1:
            proto = CalculateOptionPriceRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            proto.volatility = volatility
            proto.underPrice = underPrice
            self.sendProto(_OUT_REQ_CALC_OPTION_PRICE, proto)
            return
        self.send(
            55, 3, reqId, contract, volatility, underPrice,
            len(optPrcOptions), optPrcOptions)

    def cancelCalculateImpliedVolatility(self, reqId):
        if self._serverVersion >= _MIN_PB_REST_1:
            proto = CancelCalculateImpliedVolatilityProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_CALC_IMPLIED_VOLAT, proto)
            return
        self.send(56, 1, reqId)

    def cancelCalculateOptionPrice(self, reqId):
        if self._serverVersion >= _MIN_PB_REST_1:
            proto = CancelCalculateOptionPriceProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_CALC_OPTION_PRICE, proto)
            return
        self.send(57, 1, reqId)

    def reqGlobalCancel(self):
        if self._serverVersion >= _MIN_PB_PLACE_ORDER:
            self.sendProto(_OUT_REQ_GLOBAL_CANCEL, GlobalCancelRequestProto())
            return
        self.send(58, 1)

    def reqMarketDataType(self, marketDataType):
        if self._serverVersion >= _MIN_PB_MARKET_DATA:
            proto = MarketDataTypeRequestProto()
            proto.marketDataType = marketDataType
            self.sendProto(_OUT_REQ_MARKET_DATA_TYPE, proto)
            return
        self.send(59, 1, marketDataType)

    def reqPositions(self):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            self.sendProto(_OUT_REQ_POSITIONS, PositionsRequestProto())
            return
        self.send(61, 1)

    def reqAccountSummary(self, reqId, groupName, tags):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = AccountSummaryRequestProto()
            proto.reqId = reqId
            if groupName:
                proto.groupName = groupName
            if tags:
                proto.tags = tags
            self.sendProto(_OUT_REQ_ACCOUNT_SUMMARY, proto)
            return
        self.send(62, 1, reqId, groupName, tags)

    def cancelAccountSummary(self, reqId):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = CancelAccountSummaryProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_ACCOUNT_SUMMARY, proto)
            return
        self.send(63, 1, reqId)

    def cancelPositions(self):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            self.sendProto(_OUT_CANCEL_POSITIONS, CancelPositionsProto())
            return
        self.send(64, 1)

    def verifyRequest(self, apiName, apiVersion):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = VerifyRequestProto()
            if apiName:
                proto.apiName = apiName
            if apiVersion:
                proto.apiVersion = apiVersion
            self.sendProto(_OUT_VERIFY_REQUEST, proto)
            return
        self.send(65, 1, apiName, apiVersion)

    def verifyMessage(self, apiData):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = VerifyMessageRequestProto()
            if apiData:
                proto.apiData = apiData
            self.sendProto(_OUT_VERIFY_MESSAGE, proto)
            return
        self.send(66, 1, apiData)

    def queryDisplayGroups(self, reqId):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = QueryDisplayGroupsRequestProto()
            proto.reqId = reqId
            self.sendProto(_OUT_QUERY_DISPLAY_GROUPS, proto)
            return
        self.send(67, 1, reqId)

    def subscribeToGroupEvents(self, reqId, groupId):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = SubscribeToGroupEventsRequestProto()
            proto.reqId = reqId
            proto.groupId = groupId
            self.sendProto(_OUT_SUBSCRIBE_TO_GROUP_EVENTS, proto)
            return
        self.send(68, 1, reqId, groupId)

    def updateDisplayGroup(self, reqId, contractInfo):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = UpdateDisplayGroupRequestProto()
            proto.reqId = reqId
            if contractInfo:
                proto.contractInfo = contractInfo
            self.sendProto(_OUT_UPDATE_DISPLAY_GROUP, proto)
            return
        self.send(69, 1, reqId, contractInfo)

    def unsubscribeFromGroupEvents(self, reqId):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = UnsubscribeFromGroupEventsRequestProto()
            proto.reqId = reqId
            self.sendProto(_OUT_UNSUBSCRIBE_FROM_GROUP_EVENTS, proto)
            return
        self.send(70, 1, reqId)

    def startApi(self):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = StartApiRequestProto()
            proto.clientId = self.clientId
            if self.optCapab:
                proto.optionalCapabilities = self.optCapab
            self.sendProto(_OUT_START_API, proto)
            return
        self.send(71, 2, self.clientId, self.optCapab)

    def verifyAndAuthRequest(self, apiName, apiVersion, opaqueIsvKey):
        self.send(72, 1, apiName, apiVersion, opaqueIsvKey)

    def verifyAndAuthMessage(self, apiData, xyzResponse):
        self.send(73, 1, apiData, xyzResponse)

    def reqPositionsMulti(self, reqId, account, modelCode):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = PositionsMultiRequestProto()
            proto.reqId = reqId
            if account:
                proto.account = account
            if modelCode:
                proto.modelCode = modelCode
            self.sendProto(_OUT_REQ_POSITIONS_MULTI, proto)
            return
        self.send(74, 1, reqId, account, modelCode)

    def cancelPositionsMulti(self, reqId):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = CancelPositionsMultiProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_POSITIONS_MULTI, proto)
            return
        self.send(75, 1, reqId)

    def reqAccountUpdatesMulti(self, reqId, account, modelCode, ledgerAndNLV):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = AccountUpdatesMultiRequestProto()
            proto.reqId = reqId
            if account:
                proto.account = account
            if modelCode:
                proto.modelCode = modelCode
            proto.ledgerAndNLV = ledgerAndNLV
            self.sendProto(_OUT_REQ_ACCOUNT_UPDATES_MULTI, proto)
            return
        self.send(76, 1, reqId, account, modelCode, ledgerAndNLV)

    def cancelAccountUpdatesMulti(self, reqId):
        if self._serverVersion >= _MIN_PB_ACCOUNTS_POSITIONS:
            proto = CancelAccountUpdatesMultiProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_ACCOUNT_UPDATES_MULTI, proto)
            return
        self.send(77, 1, reqId)

    def reqSecDefOptParams(
            self, reqId, underlyingSymbol, futFopExchange,
            underlyingSecType, underlyingConId):
        if self._serverVersion >= _MIN_PB_REST_2:
            proto = SecDefOptParamsRequestProto()
            proto.reqId = reqId
            if underlyingSymbol:
                proto.underlyingSymbol = underlyingSymbol
            if futFopExchange:
                proto.futFopExchange = futFopExchange
            if underlyingSecType:
                proto.underlyingSecType = underlyingSecType
            proto.underlyingConId = underlyingConId
            self.sendProto(_OUT_REQ_SEC_DEF_OPT_PARAMS, proto)
            return
        self.send(
            78, reqId, underlyingSymbol, futFopExchange,
            underlyingSecType, underlyingConId)

    def reqSoftDollarTiers(self, reqId):
        self.send(79, reqId)

    def reqFamilyCodes(self):
        if self._serverVersion >= _MIN_PB_REST_2:
            self.sendProto(_OUT_REQ_FAMILY_CODES, FamilyCodesRequestProto())
            return
        self.send(80)

    def reqMatchingSymbols(self, reqId, pattern):
        if self._serverVersion >= _MIN_PB_REST_2:
            proto = MatchingSymbolsRequestProto()
            proto.reqId = reqId
            if pattern:
                proto.pattern = pattern
            self.sendProto(_OUT_REQ_MATCHING_SYMBOLS, proto)
            return
        self.send(81, reqId, pattern)

    def reqMktDepthExchanges(self):
        if self._serverVersion >= _MIN_PB_REST_3:
            self.sendProto(_OUT_REQ_MKT_DEPTH_EXCHANGES, MarketDepthExchangesRequestProto())
            return
        self.send(82)

    def reqSmartComponents(self, reqId, bboExchange):
        if self._serverVersion >= _MIN_PB_REST_2:
            proto = SmartComponentsRequestProto()
            proto.reqId = reqId
            if bboExchange:
                proto.bboExchange = bboExchange
            self.sendProto(_OUT_REQ_SMART_COMPONENTS, proto)
            return
        self.send(83, reqId, bboExchange)

    def reqNewsArticle(
            self, reqId, providerCode, articleId, newsArticleOptions):
        self.send(84, reqId, providerCode, articleId, newsArticleOptions)

    def reqNewsProviders(self):
        self.send(85)

    def reqHistoricalNews(
            self, reqId, conId, providerCodes, startDateTime, endDateTime,
            totalResults, historicalNewsOptions):
        self.send(
            86, reqId, conId, providerCodes, startDateTime, endDateTime,
            totalResults, historicalNewsOptions)

    def reqHeadTimeStamp(
            self, reqId, contract, whatToShow, useRTH, formatDate):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = HeadTimestampRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if whatToShow:
                proto.whatToShow = whatToShow
            if useRTH:
                proto.useRTH = useRTH
            proto.formatDate = formatDate
            self.sendProto(_OUT_REQ_HEAD_TIMESTAMP, proto)
            return
        self.send(
            87, reqId, contract, contract.includeExpired,
            useRTH, whatToShow, formatDate)

    def reqHistogramData(self, tickerId, contract, useRTH, timePeriod):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = HistogramDataRequestProto()
            proto.reqId = tickerId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if useRTH:
                proto.useRTH = useRTH
            if timePeriod:
                proto.timePeriod = timePeriod
            self.sendProto(_OUT_REQ_HISTOGRAM_DATA, proto)
            return
        self.send(
            88, tickerId, contract, contract.includeExpired,
            useRTH, timePeriod)

    def cancelHistogramData(self, tickerId):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = CancelHistogramDataProto()
            proto.reqId = tickerId
            self.sendProto(_OUT_CANCEL_HISTOGRAM_DATA, proto)
            return
        self.send(89, tickerId)

    def cancelHeadTimeStamp(self, reqId):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = CancelHeadTimestampProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_HEAD_TIMESTAMP, proto)
            return
        self.send(90, reqId)

    def reqMarketRule(self, marketRuleId):
        if self._serverVersion >= _MIN_PB_REST_2:
            proto = MarketRuleRequestProto()
            proto.marketRuleId = marketRuleId
            self.sendProto(_OUT_REQ_MARKET_RULE, proto)
            return
        self.send(91, marketRuleId)

    def reqPnL(self, reqId, account, modelCode):
        if self._serverVersion >= _MIN_PB_SCAN_DATA:
            proto = PnLRequestProto()
            proto.reqId = reqId
            if account:
                proto.account = account
            if modelCode:
                proto.modelCode = modelCode
            self.sendProto(_OUT_REQ_PNL, proto)
            return
        self.send(92, reqId, account, modelCode)

    def cancelPnL(self, reqId):
        if self._serverVersion >= _MIN_PB_SCAN_DATA:
            proto = CancelPnLProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_PNL, proto)
            return
        self.send(93, reqId)

    def reqPnLSingle(self, reqId, account, modelCode, conid):
        if self._serverVersion >= _MIN_PB_SCAN_DATA:
            proto = PnLSingleRequestProto()
            proto.reqId = reqId
            if account:
                proto.account = account
            if modelCode:
                proto.modelCode = modelCode
            proto.conId = conid
            self.sendProto(_OUT_REQ_PNL_SINGLE, proto)
            return
        self.send(94, reqId, account, modelCode, conid)

    def cancelPnLSingle(self, reqId):
        if self._serverVersion >= _MIN_PB_SCAN_DATA:
            proto = CancelPnLSingleProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_PNL_SINGLE, proto)
            return
        self.send(95, reqId)

    def reqHistoricalTicks(
            self, reqId, contract, startDateTime, endDateTime,
            numberOfTicks, whatToShow, useRth, ignoreSize, miscOptions):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = HistoricalTicksRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if startDateTime:
                proto.startDateTime = str(startDateTime)
            if endDateTime:
                proto.endDateTime = str(endDateTime)
            proto.numberOfTicks = numberOfTicks
            if whatToShow:
                proto.whatToShow = whatToShow
            if useRth:
                proto.useRTH = useRth
            if ignoreSize:
                proto.ignoreSize = ignoreSize
            self.sendProto(_OUT_REQ_HISTORICAL_TICKS, proto)
            return
        self.send(
            96, reqId, contract, contract.includeExpired,
            startDateTime, endDateTime, numberOfTicks, whatToShow,
            useRth, ignoreSize, miscOptions)

    def reqTickByTickData(
            self, reqId, contract, tickType, numberOfTicks, ignoreSize):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = TickByTickRequestProto()
            proto.reqId = reqId
            cp = _createContractProto(contract, None)
            if cp:
                proto.contract.CopyFrom(cp)
            if tickType:
                proto.tickType = tickType
            proto.numberOfTicks = numberOfTicks
            if ignoreSize:
                proto.ignoreSize = ignoreSize
            self.sendProto(_OUT_REQ_TICK_BY_TICK_DATA, proto)
            return
        self.send(97, reqId, contract, tickType, numberOfTicks, ignoreSize)

    def cancelTickByTickData(self, reqId):
        if self._serverVersion >= _MIN_PB_HISTORICAL_DATA:
            proto = CancelTickByTickProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_TICK_BY_TICK_DATA, proto)
            return
        self.send(98, reqId)

    def reqCompletedOrders(self, apiOnly):
        if self._serverVersion >= _MIN_PB_COMPLETED_ORDER:
            proto = CompletedOrdersRequestProto()
            proto.apiOnly = apiOnly
            self.sendProto(_OUT_REQ_COMPLETED_ORDERS, proto)
            return
        self.send(99, apiOnly)

    def reqWshMetaData(self, reqId):
        if self._serverVersion >= _MIN_PB_SCAN_DATA_NEWS:
            proto = WshMetaDataRequestProto()
            proto.reqId = reqId
            self.sendProto(_OUT_REQ_WSH_META_DATA, proto)
            return
        self.send(100, reqId)

    def cancelWshMetaData(self, reqId):
        if self._serverVersion >= _MIN_PB_SCAN_DATA_NEWS:
            proto = CancelWshMetaDataProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_WSH_META_DATA, proto)
            return
        self.send(101, reqId)

    def reqWshEventData(self, reqId, data: WshEventData):
        if self._serverVersion >= _MIN_PB_SCAN_DATA_NEWS:
            proto = WshEventDataRequestProto()
            proto.reqId = reqId
            if data.conId:
                proto.conId = data.conId
            if data.filter:
                proto.filter = data.filter
            if data.fillWatchlist:
                proto.fillWatchlist = data.fillWatchlist
            if data.fillPortfolio:
                proto.fillPortfolio = data.fillPortfolio
            if data.fillCompetitors:
                proto.fillCompetitors = data.fillCompetitors
            if data.startDate:
                proto.startDate = data.startDate
            if data.endDate:
                proto.endDate = data.endDate
            if data.totalLimit:
                proto.totalLimit = data.totalLimit
            self.sendProto(_OUT_REQ_WSH_EVENT_DATA, proto)
            return
        fields = [102, reqId, data.conId]
        if self.serverVersion() >= 171:
            fields += [
                data.filter,
                data.fillWatchlist,
                data.fillPortfolio,
                data.fillCompetitors]
        if self.serverVersion() >= 173:
            fields += [
                data.startDate,
                data.endDate,
                data.totalLimit]
        self.send(*fields, makeEmpty=False)

    def cancelWshEventData(self, reqId):
        if self._serverVersion >= _MIN_PB_SCAN_DATA_NEWS:
            proto = CancelWshEventDataProto()
            proto.reqId = reqId
            self.sendProto(_OUT_CANCEL_WSH_EVENT_DATA, proto)
            return
        self.send(103, reqId)

    def reqUserInfo(self, reqId):
        if self._serverVersion >= _MIN_PB_REST_2:
            proto = UserInfoRequestProto()
            proto.reqId = reqId
            self.sendProto(_OUT_REQ_USER_INFO, proto)
            return
        self.send(104, reqId)

    def reqIds(self, numIds):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = IdsRequestProto()
            proto.numIds = numIds
            self.sendProto(_OUT_REQ_IDS, proto)
            return
        self.send(8, 1, numIds)

    def reqCurrentTime(self):
        if self._serverVersion >= _MIN_PB_REST_3:
            self.sendProto(_OUT_REQ_CURRENT_TIME, CurrentTimeRequestProto())
            return
        self.send(49, 1)

    def setServerLogLevel(self, logLevel):
        if self._serverVersion >= _MIN_PB_REST_3:
            proto = SetServerLogLevelRequestProto()
            proto.logLevel = logLevel
            self.sendProto(_OUT_SET_SERVER_LOGLEVEL, proto)
            return
        self.send(14, 1, logLevel)
