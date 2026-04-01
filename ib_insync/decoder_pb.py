"""Protobuf decoder for IB API messages.

Drop-in companion to the text-based Decoder. Handles incoming protobuf
messages (server version >= MIN_SERVER_VER_PROTOBUF) and dispatches to
the same Wrapper methods that the legacy Decoder calls.

Only the messages needed for the connectAsync / disconnect flow are
implemented here. Extend as needed for other API calls.
"""

import logging
from typing import Dict, Callable

from functools import lru_cache

from .msg_names import in_msg_name as _in_msg_name
from .contract import (
    ComboLeg, Contract, ContractDescription, ContractDetails,
    DeltaNeutralContract, ScanData)
from .objects import (
    BarData, CommissionReport, DepthMktDataDescription, Execution,
    FamilyCode, HistogramData, HistoricalNews, HistoricalSchedule,
    HistoricalSession, HistoricalTick, HistoricalTickBidAsk,
    HistoricalTickLast, NewsArticle, NewsBulletin, NewsProvider,
    OptionChain, OptionComputation, PnL, PnLSingle, PriceIncrement,
    SmartComponent, SoftDollarTier, TagValue,
    TickAttribBidAsk, TickAttribLast)
from .order import Order, OrderComboLeg, OrderCondition, OrderState
from .wrapper import Wrapper

# -- Protobuf generated message types (from ibapi package) --
# connect-flow
from ibapi.protobuf.NextValidId_pb2 import NextValidId as NextValidIdProto
from ibapi.protobuf.ManagedAccounts_pb2 import ManagedAccounts as ManagedAccountsProto
from ibapi.protobuf.ErrorMessage_pb2 import ErrorMessage as ErrorMessageProto
from ibapi.protobuf.OrderStatus_pb2 import OrderStatus as OrderStatusProto
from ibapi.protobuf.OpenOrder_pb2 import OpenOrder as OpenOrderProto
from ibapi.protobuf.OpenOrdersEnd_pb2 import OpenOrdersEnd as OpenOrdersEndProto
from ibapi.protobuf.CompletedOrder_pb2 import CompletedOrder as CompletedOrderProto
from ibapi.protobuf.CompletedOrdersEnd_pb2 import CompletedOrdersEnd as CompletedOrdersEndProto
from ibapi.protobuf.OrderBound_pb2 import OrderBound as OrderBoundProto
from ibapi.protobuf.ExecutionDetails_pb2 import ExecutionDetails as ExecutionDetailsProto
from ibapi.protobuf.ExecutionDetailsEnd_pb2 import ExecutionDetailsEnd as ExecutionDetailsEndProto
from ibapi.protobuf.CommissionAndFeesReport_pb2 import CommissionAndFeesReport as CommissionAndFeesReportProto
from ibapi.protobuf.AccountValue_pb2 import AccountValue as AccountValueProto
from ibapi.protobuf.PortfolioValue_pb2 import PortfolioValue as PortfolioValueProto
from ibapi.protobuf.AccountUpdateTime_pb2 import AccountUpdateTime as AccountUpdateTimeProto
from ibapi.protobuf.AccountDataEnd_pb2 import AccountDataEnd as AccountDataEndProto
from ibapi.protobuf.Position_pb2 import Position as PositionProto
from ibapi.protobuf.PositionEnd_pb2 import PositionEnd as PositionEndProto
from ibapi.protobuf.PositionMulti_pb2 import PositionMulti as PositionMultiProto
from ibapi.protobuf.PositionMultiEnd_pb2 import PositionMultiEnd as PositionMultiEndProto
from ibapi.protobuf.AccountSummary_pb2 import AccountSummary as AccountSummaryProto
from ibapi.protobuf.AccountSummaryEnd_pb2 import AccountSummaryEnd as AccountSummaryEndProto
from ibapi.protobuf.AccountUpdateMulti_pb2 import AccountUpdateMulti as AccountUpdateMultiProto
from ibapi.protobuf.AccountUpdateMultiEnd_pb2 import AccountUpdateMultiEnd as AccountUpdateMultiEndProto
# tick data
from ibapi.protobuf.TickPrice_pb2 import TickPrice as TickPriceProto
from ibapi.protobuf.TickSize_pb2 import TickSize as TickSizeProto
from ibapi.protobuf.TickGeneric_pb2 import TickGeneric as TickGenericProto
from ibapi.protobuf.TickString_pb2 import TickString as TickStringProto
from ibapi.protobuf.TickOptionComputation_pb2 import TickOptionComputation as TickOptionComputationProto
from ibapi.protobuf.TickSnapshotEnd_pb2 import TickSnapshotEnd as TickSnapshotEndProto
from ibapi.protobuf.TickReqParams_pb2 import TickReqParams as TickReqParamsProto
from ibapi.protobuf.MarketDataType_pb2 import MarketDataType as MarketDataTypeProto
from ibapi.protobuf.TickByTickData_pb2 import TickByTickData as TickByTickDataProto
from ibapi.protobuf.TickNews_pb2 import TickNews as TickNewsProto
# contract data
from ibapi.protobuf.ContractData_pb2 import ContractData as ContractDataProto
from ibapi.protobuf.ContractDataEnd_pb2 import ContractDataEnd as ContractDataEndProto
# market depth
from ibapi.protobuf.MarketDepth_pb2 import MarketDepth as MarketDepthProto
from ibapi.protobuf.MarketDepthL2_pb2 import MarketDepthL2 as MarketDepthL2Proto
from ibapi.protobuf.MarketDepthExchanges_pb2 import MarketDepthExchanges as MarketDepthExchangesProto
# historical / bars
from ibapi.protobuf.HistoricalData_pb2 import HistoricalData as HistoricalDataProto
from ibapi.protobuf.HistoricalDataUpdate_pb2 import HistoricalDataUpdate as HistoricalDataUpdateProto
from ibapi.protobuf.HistoricalDataEnd_pb2 import HistoricalDataEnd as HistoricalDataEndProto
from ibapi.protobuf.RealTimeBarTick_pb2 import RealTimeBarTick as RealTimeBarTickProto
from ibapi.protobuf.HeadTimestamp_pb2 import HeadTimestamp as HeadTimestampProto
from ibapi.protobuf.HistogramData_pb2 import HistogramData as HistogramDataProto
from ibapi.protobuf.HistoricalTicks_pb2 import HistoricalTicks as HistoricalTicksProto
from ibapi.protobuf.HistoricalTicksBidAsk_pb2 import HistoricalTicksBidAsk as HistoricalTicksBidAskProto
from ibapi.protobuf.HistoricalTicksLast_pb2 import HistoricalTicksLast as HistoricalTicksLastProto
from ibapi.protobuf.HistoricalSchedule_pb2 import HistoricalSchedule as HistoricalScheduleProto
# news
from ibapi.protobuf.NewsBulletin_pb2 import NewsBulletin as NewsBulletinProto
from ibapi.protobuf.NewsArticle_pb2 import NewsArticle as NewsArticleProto
from ibapi.protobuf.NewsProviders_pb2 import NewsProviders as NewsProvidersProto
from ibapi.protobuf.HistoricalNews_pb2 import HistoricalNews as HistoricalNewsProto
from ibapi.protobuf.HistoricalNewsEnd_pb2 import HistoricalNewsEnd as HistoricalNewsEndProto
# scanner / fundamental
from ibapi.protobuf.ScannerParameters_pb2 import ScannerParameters as ScannerParametersProto
from ibapi.protobuf.ScannerData_pb2 import ScannerData as ScannerDataProto
from ibapi.protobuf.FundamentalsData_pb2 import FundamentalsData as FundamentalsDataProto
# pnl
from ibapi.protobuf.PnL_pb2 import PnL as PnLProto
from ibapi.protobuf.PnLSingle_pb2 import PnLSingle as PnLSingleProto
# fa
from ibapi.protobuf.ReceiveFA_pb2 import ReceiveFA as ReceiveFAProto
from ibapi.protobuf.ReplaceFAEnd_pb2 import ReplaceFAEnd as ReplaceFAEndProto
# sec def opt params
from ibapi.protobuf.SecDefOptParameter_pb2 import SecDefOptParameter as SecDefOptParameterProto
from ibapi.protobuf.SecDefOptParameterEnd_pb2 import SecDefOptParameterEnd as SecDefOptParameterEndProto
# misc
from ibapi.protobuf.SoftDollarTiers_pb2 import SoftDollarTiers as SoftDollarTiersProto
from ibapi.protobuf.FamilyCodes_pb2 import FamilyCodes as FamilyCodesProto
from ibapi.protobuf.SymbolSamples_pb2 import SymbolSamples as SymbolSamplesProto
from ibapi.protobuf.SmartComponents_pb2 import SmartComponents as SmartComponentsProto
from ibapi.protobuf.MarketRule_pb2 import MarketRule as MarketRuleProto
from ibapi.protobuf.RerouteMarketDataRequest_pb2 import RerouteMarketDataRequest as RerouteMarketDataRequestProto
from ibapi.protobuf.RerouteMarketDepthRequest_pb2 import RerouteMarketDepthRequest as RerouteMarketDepthRequestProto
from ibapi.protobuf.WshMetaData_pb2 import WshMetaData as WshMetaDataProto
from ibapi.protobuf.WshEventData_pb2 import WshEventData as WshEventDataProto
from ibapi.protobuf.UserInfo_pb2 import UserInfo as UserInfoProto
from ibapi.protobuf.CurrentTime_pb2 import CurrentTime as CurrentTimeProto
from ibapi.protobuf.CurrentTimeInMillis_pb2 import CurrentTimeInMillis as CurrentTimeInMillisProto
from ibapi.protobuf.VerifyMessageApi_pb2 import VerifyMessageApi as VerifyMessageApiProto
from ibapi.protobuf.VerifyCompleted_pb2 import VerifyCompleted as VerifyCompletedProto
from ibapi.protobuf.DisplayGroupList_pb2 import DisplayGroupList as DisplayGroupListProto
from ibapi.protobuf.DisplayGroupUpdated_pb2 import DisplayGroupUpdated as DisplayGroupUpdatedProto
# ibapi decoder_utils for complex protobuf → native type conversions
from ibapi.decoder_utils import (
    decodeContractDetails as _ibapi_decodeContractDetails,
    setLastTradeDate as _ibapi_setLastTradeDate,
)

from ibapi.message import IN


def _proto_fields(proto_msg) -> frozenset[str]:
    """Return the set of field names defined in a proto message's schema.

    Cached per message type so the descriptor reflection cost is paid
    only once.
    """
    return _proto_fields_by_type(type(proto_msg))


@lru_cache(maxsize=None)
def _proto_fields_by_type(cls) -> frozenset[str]:
    return frozenset(f.name for f in cls.DESCRIPTOR.fields)


class ProtobufDecoder:
    """Decode protobuf IB messages and invoke corresponding wrapper methods."""

    def __init__(self, wrapper: Wrapper, serverVersion: int):
        self.wrapper = wrapper
        self.serverVersion = serverVersion
        self.logger = logging.getLogger('ib_insync.ProtobufDecoder')
        self._handlers: Dict[int, Callable[[bytes], None]] = {
            # connect-flow (original)
            IN.NEXT_VALID_ID: self._nextValidId,
            IN.MANAGED_ACCTS: self._managedAccounts,
            IN.ERR_MSG: self._errorMsg,
            IN.ORDER_STATUS: self._orderStatus,
            IN.OPEN_ORDER: self._openOrder,
            IN.OPEN_ORDER_END: self._openOrderEnd,
            IN.ACCT_VALUE: self._accountValue,
            IN.PORTFOLIO_VALUE: self._portfolioValue,
            IN.ACCT_UPDATE_TIME: self._accountUpdateTime,
            IN.ACCT_DOWNLOAD_END: self._accountDownloadEnd,
            IN.POSITION_DATA: self._position,
            IN.POSITION_END: self._positionEnd,
            IN.POSITION_MULTI: self._positionMulti,
            IN.POSITION_MULTI_END: self._positionMultiEnd,
            IN.ACCOUNT_SUMMARY: self._accountSummary,
            IN.ACCOUNT_SUMMARY_END: self._accountSummaryEnd,
            IN.ACCOUNT_UPDATE_MULTI: self._accountUpdateMulti,
            IN.ACCOUNT_UPDATE_MULTI_END: self._accountUpdateMultiEnd,
            IN.EXECUTION_DATA: self._execDetails,
            IN.EXECUTION_DATA_END: self._execDetailsEnd,
            IN.COMMISSION_AND_FEES_REPORT: self._commissionReport,
            IN.ORDER_BOUND: self._orderBound,
            IN.COMPLETED_ORDER: self._completedOrder,
            IN.COMPLETED_ORDERS_END: self._completedOrdersEnd,
            # tick data
            IN.TICK_PRICE: self._tickPrice,
            IN.TICK_SIZE: self._tickSize,
            IN.TICK_GENERIC: self._tickGeneric,
            IN.TICK_STRING: self._tickString,
            IN.TICK_OPTION_COMPUTATION: self._tickOptionComputation,
            IN.TICK_SNAPSHOT_END: self._tickSnapshotEnd,
            IN.TICK_REQ_PARAMS: self._tickReqParams,
            IN.MARKET_DATA_TYPE: self._marketDataType,
            IN.TICK_BY_TICK: self._tickByTick,
            IN.TICK_NEWS: self._tickNews,
            # contract
            IN.CONTRACT_DATA: self._contractData,
            IN.BOND_CONTRACT_DATA: self._bondContractData,
            IN.CONTRACT_DATA_END: self._contractDataEnd,
            # market depth
            IN.MARKET_DEPTH: self._marketDepth,
            IN.MARKET_DEPTH_L2: self._marketDepthL2,
            IN.MKT_DEPTH_EXCHANGES: self._mktDepthExchanges,
            # historical / bars
            IN.HISTORICAL_DATA: self._historicalData,
            IN.HISTORICAL_DATA_UPDATE: self._historicalDataUpdate,
            IN.HISTORICAL_DATA_END: self._historicalDataEnd,
            IN.REAL_TIME_BARS: self._realtimeBar,
            IN.HEAD_TIMESTAMP: self._headTimestamp,
            IN.HISTOGRAM_DATA: self._histogramData,
            IN.HISTORICAL_TICKS: self._historicalTicks,
            IN.HISTORICAL_TICKS_BID_ASK: self._historicalTicksBidAsk,
            IN.HISTORICAL_TICKS_LAST: self._historicalTicksLast,
            IN.HISTORICAL_SCHEDULE: self._historicalSchedule,
            # news
            IN.NEWS_BULLETINS: self._newsBulletin,
            IN.NEWS_ARTICLE: self._newsArticle,
            IN.NEWS_PROVIDERS: self._newsProviders,
            IN.HISTORICAL_NEWS: self._historicalNews,
            IN.HISTORICAL_NEWS_END: self._historicalNewsEnd,
            # scanner / fundamental
            IN.SCANNER_PARAMETERS: self._scannerParameters,
            IN.SCANNER_DATA: self._scannerData,
            IN.FUNDAMENTAL_DATA: self._fundamentalData,
            # pnl
            IN.PNL: self._pnl,
            IN.PNL_SINGLE: self._pnlSingle,
            # fa
            IN.RECEIVE_FA: self._receiveFA,
            IN.REPLACE_FA_END: self._replaceFAEnd,
            # sec def opt params
            IN.SECURITY_DEFINITION_OPTION_PARAMETER: self._secDefOptParam,
            IN.SECURITY_DEFINITION_OPTION_PARAMETER_END: self._secDefOptParamEnd,
            # misc
            IN.SOFT_DOLLAR_TIERS: self._softDollarTiers,
            IN.FAMILY_CODES: self._familyCodes,
            IN.SYMBOL_SAMPLES: self._symbolSamples,
            IN.SMART_COMPONENTS: self._smartComponents,
            IN.MARKET_RULE: self._marketRule,
            IN.REROUTE_MKT_DATA_REQ: self._rerouteMktDataReq,
            IN.REROUTE_MKT_DEPTH_REQ: self._rerouteMktDepthReq,
            IN.WSH_META_DATA: self._wshMetaData,
            IN.WSH_EVENT_DATA: self._wshEventData,
            IN.USER_INFO: self._userInfo,
            IN.CURRENT_TIME: self._currentTime,
            IN.CURRENT_TIME_IN_MILLIS: self._currentTimeInMillis,
            IN.VERIFY_MESSAGE_API: self._verifyMessageAPI,
            IN.VERIFY_COMPLETED: self._verifyCompleted,
            IN.DISPLAY_GROUP_LIST: self._displayGroupList,
            IN.DISPLAY_GROUP_UPDATED: self._displayGroupUpdated,
        }

    def processProtoBuf(self, payload: bytes, msgId: int):
        """Dispatch a protobuf message to the appropriate handler."""
        handler = self._handlers.get(msgId)
        if handler is None:
            self.logger.warning(
                'No protobuf handler for %s, payload length %d',
                _in_msg_name(msgId), len(payload))
            return
        try:
            handler(payload)
        except Exception:
            self.logger.exception(
                'Error handling protobuf %s', _in_msg_name(msgId))

    # ---- helpers ----

    @staticmethod
    def _decodeContract(contractProto) -> Contract:
        """Convert a protobuf Contract to an ib_insync Contract."""
        c = Contract()
        if contractProto.HasField('conId'):
            c.conId = contractProto.conId
        if contractProto.HasField('symbol'):
            c.symbol = contractProto.symbol
        if contractProto.HasField('secType'):
            c.secType = contractProto.secType
        if contractProto.HasField('lastTradeDateOrContractMonth'):
            c.lastTradeDateOrContractMonth = contractProto.lastTradeDateOrContractMonth
        if contractProto.HasField('strike'):
            c.strike = contractProto.strike
        if contractProto.HasField('right'):
            c.right = contractProto.right
        if contractProto.HasField('multiplier'):
            c.multiplier = str(contractProto.multiplier) if contractProto.multiplier else ''
        if contractProto.HasField('exchange'):
            c.exchange = contractProto.exchange
        if contractProto.HasField('currency'):
            c.currency = contractProto.currency
        if contractProto.HasField('localSymbol'):
            c.localSymbol = contractProto.localSymbol
        if contractProto.HasField('tradingClass'):
            c.tradingClass = contractProto.tradingClass
        if contractProto.HasField('primaryExch'):
            c.primaryExchange = contractProto.primaryExch
        if contractProto.HasField('comboLegsDescrip'):
            c.comboLegsDescrip = contractProto.comboLegsDescrip
        # comboLegs
        if contractProto.comboLegs:
            c.comboLegs = []
            for lp in contractProto.comboLegs:
                leg = ComboLeg()
                if lp.HasField('conId'):
                    leg.conId = lp.conId
                if lp.HasField('ratio'):
                    leg.ratio = lp.ratio
                if lp.HasField('action'):
                    leg.action = lp.action
                if lp.HasField('exchange'):
                    leg.exchange = lp.exchange
                if lp.HasField('openClose'):
                    leg.openClose = lp.openClose
                if lp.HasField('shortSalesSlot'):
                    leg.shortSaleSlot = lp.shortSalesSlot
                if lp.HasField('designatedLocation'):
                    leg.designatedLocation = lp.designatedLocation
                if lp.HasField('exemptCode'):
                    leg.exemptCode = lp.exemptCode
                c.comboLegs.append(leg)
        # deltaNeutralContract
        if contractProto.HasField('deltaNeutralContract'):
            dnp = contractProto.deltaNeutralContract
            dnc = DeltaNeutralContract()
            if dnp.HasField('conId'):
                dnc.conId = dnp.conId
            if dnp.HasField('delta'):
                dnc.delta = dnp.delta
            if dnp.HasField('price'):
                dnc.price = dnp.price
            c.deltaNeutralContract = dnc
        return c

    @staticmethod
    def _decodeOrder(orderId, contractProto, orderProto) -> Order:
        """Convert protobuf Order to ib_insync Order (simplified)."""
        o = Order()
        if orderId is not None:
            o.orderId = orderId
        # overwrite with proto's orderId if present
        if orderProto.HasField('orderId'):
            o.orderId = orderProto.orderId
        # proto_field_name -> ib_insync Order attr name
        _simple_fields = [
            ('action', 'action'), ('orderType', 'orderType'),
            ('lmtPrice', 'lmtPrice'), ('auxPrice', 'auxPrice'),
            ('tif', 'tif'), ('ocaGroup', 'ocaGroup'),
            ('account', 'account'), ('openClose', 'openClose'),
            ('origin', 'origin'), ('orderRef', 'orderRef'),
            ('clientId', 'clientId'), ('permId', 'permId'),
            ('outsideRth', 'outsideRth'), ('hidden', 'hidden'),
            ('discretionaryAmt', 'discretionaryAmt'),
            ('goodAfterTime', 'goodAfterTime'),
            ('faGroup', 'faGroup'), ('faMethod', 'faMethod'),
            ('faPercentage', 'faPercentage'),
            ('modelCode', 'modelCode'),
            ('goodTillDate', 'goodTillDate'),
            ('rule80A', 'rule80A'),
            ('percentOffset', 'percentOffset'),
            ('settlingFirm', 'settlingFirm'),
            ('shortSaleSlot', 'shortSaleSlot'),
            ('designatedLocation', 'designatedLocation'),
            ('exemptCode', 'exemptCode'),
            ('displaySize', 'displaySize'),
            ('blockOrder', 'blockOrder'),
            ('sweepToFill', 'sweepToFill'),
            ('allOrNone', 'allOrNone'),
            ('minQty', 'minQty'),
            ('ocaType', 'ocaType'),
            ('parentId', 'parentId'),
            ('triggerMethod', 'triggerMethod'),
            ('volatility', 'volatility'),
            ('volatilityType', 'volatilityType'),
            ('deltaNeutralOrderType', 'deltaNeutralOrderType'),
            ('deltaNeutralAuxPrice', 'deltaNeutralAuxPrice'),
            ('continuousUpdate', 'continuousUpdate'),
            ('referencePriceType', 'referencePriceType'),
            ('trailStopPrice', 'trailStopPrice'),
            ('trailingPercent', 'trailingPercent'),
            ('basisPoints', 'basisPoints'),
            ('basisPointsType', 'basisPointsType'),
            ('scaleInitLevelSize', 'scaleInitLevelSize'),
            ('scaleSubsLevelSize', 'scaleSubsLevelSize'),
            ('scalePriceIncrement', 'scalePriceIncrement'),
            ('scalePriceAdjustValue', 'scalePriceAdjustValue'),
            ('scalePriceAdjustInterval', 'scalePriceAdjustInterval'),
            ('scaleProfitOffset', 'scaleProfitOffset'),
            ('scaleAutoReset', 'scaleAutoReset'),
            ('scaleInitPosition', 'scaleInitPosition'),
            ('scaleInitFillQty', 'scaleInitFillQty'),
            ('scaleRandomPercent', 'scaleRandomPercent'),
            ('scaleTable', 'scaleTable'),
            ('hedgeType', 'hedgeType'),
            ('hedgeParam', 'hedgeParam'),
            ('clearingAccount', 'clearingAccount'),
            ('clearingIntent', 'clearingIntent'),
            ('notHeld', 'notHeld'),
            ('solicited', 'solicited'),
            ('randomizeSize', 'randomizeSize'),
            ('randomizePrice', 'randomizePrice'),
            ('dontUseAutoPriceForHedge', 'dontUseAutoPriceForHedge'),
            ('isOmsContainer', 'isOmsContainer'),
            ('discretionaryUpToLimitPrice', 'discretionaryUpToLimitPrice'),
            ('usePriceMgmtAlgo', 'usePriceMgmtAlgo'),
            ('duration', 'duration'),
            ('postToAts', 'postToAts'),
            ('autoCancelParent', 'autoCancelParent'),
            ('transmit', 'transmit'),
        ]
        # Only check fields that actually exist in the proto schema
        proto_field_names = _proto_fields(orderProto)
        for proto_name, order_name in _simple_fields:
            if proto_name in proto_field_names and orderProto.HasField(proto_name):
                setattr(o, order_name, getattr(orderProto, proto_name))
        # totalQuantity is a Decimal in tws-api but float in ib_insync
        if orderProto.HasField('totalQuantity'):
            o.totalQuantity = float(orderProto.totalQuantity)
        # algoStrategy / algoParams
        if orderProto.HasField('algoStrategy'):
            o.algoStrategy = orderProto.algoStrategy
        if orderProto.algoParams:
            o.algoParams = [
                TagValue(p.tag, p.value) for p in orderProto.algoParams]
        # smartComboRoutingParams
        if orderProto.smartComboRoutingParams:
            o.smartComboRoutingParams = [
                TagValue(p.tag, p.value)
                for p in orderProto.smartComboRoutingParams]
        # orderComboLegs from contract proto
        if contractProto and contractProto.comboLegs:
            o.orderComboLegs = []
            for lp in contractProto.comboLegs:
                ocl = OrderComboLeg()
                if lp.HasField('perLegPrice'):
                    ocl.price = lp.perLegPrice
                o.orderComboLegs.append(ocl)
        # softDollarTier
        if orderProto.HasField('softDollarTier'):
            sdt = orderProto.softDollarTier
            o.softDollarTier = SoftDollarTier(
                name=sdt.name if sdt.HasField('name') else '',
                value=sdt.val if sdt.HasField('val') else '',
                displayName=sdt.displayName if sdt.HasField('displayName') else '')
        return o

    @staticmethod
    def _decodeOrderState(orderStateProto) -> OrderState:
        """Convert protobuf OrderState to ib_insync OrderState."""
        os = OrderState()
        _fields = [
            ('status', 'status'),
            ('initMarginBefore', 'initMarginBefore'),
            ('maintMarginBefore', 'maintMarginBefore'),
            ('equityWithLoanBefore', 'equityWithLoanBefore'),
            ('initMarginChange', 'initMarginChange'),
            ('maintMarginChange', 'maintMarginChange'),
            ('equityWithLoanChange', 'equityWithLoanChange'),
            ('initMarginAfter', 'initMarginAfter'),
            ('maintMarginAfter', 'maintMarginAfter'),
            ('equityWithLoanAfter', 'equityWithLoanAfter'),
            ('commissionAndFees', 'commission'),
            ('minCommissionAndFees', 'minCommission'),
            ('maxCommissionAndFees', 'maxCommission'),
            ('commissionCurrency', 'commissionCurrency'),
            ('warningText', 'warningText'),
            ('completedTime', 'completedTime'),
            ('completedStatus', 'completedStatus'),
        ]
        proto_field_names = _proto_fields(orderStateProto)
        for proto_name, os_name in _fields:
            if proto_name in proto_field_names and orderStateProto.HasField(proto_name):
                setattr(os, os_name, getattr(orderStateProto, proto_name))
        return os

    @staticmethod
    def _decodeExecution(executionProto) -> Execution:
        """Convert protobuf Execution to ib_insync Execution."""
        e = Execution()
        _fields = [
            ('orderId', 'orderId'), ('clientId', 'clientId'),
            ('execId', 'execId'), ('time', 'time'),
            ('acctNumber', 'acctNumber'), ('exchange', 'exchange'),
            ('side', 'side'), ('price', 'price'),
            ('permId', 'permId'), ('avgPrice', 'avgPrice'),
            ('orderRef', 'orderRef'), ('evRule', 'evRule'),
            ('evMultiplier', 'evMultiplier'),
            ('modelCode', 'modelCode'),
            ('lastLiquidity', 'lastLiquidity'),
        ]
        proto_field_names = _proto_fields(executionProto)
        for proto_name, exec_name in _fields:
            if proto_name in proto_field_names and executionProto.HasField(proto_name):
                setattr(e, exec_name, getattr(executionProto, proto_name))
        if executionProto.HasField('shares'):
            e.shares = float(executionProto.shares)
        if executionProto.HasField('cumQty'):
            e.cumQty = float(executionProto.cumQty)
        if executionProto.HasField('isLiquidation'):
            e.liquidation = 1 if executionProto.isLiquidation else 0
        if executionProto.HasField('isPriceRevisionPending'):
            e.pendingPriceRevision = executionProto.isPriceRevisionPending
        return e

    # ---- protobuf message handlers ----

    def _nextValidId(self, payload: bytes):
        proto = NextValidIdProto()
        proto.ParseFromString(payload)
        orderId = proto.orderId if proto.HasField('orderId') else 0
        self.wrapper.nextValidId(orderId)

    def _managedAccounts(self, payload: bytes):
        proto = ManagedAccountsProto()
        proto.ParseFromString(payload)
        accountsList = proto.accountsList if proto.HasField('accountsList') else ''
        self.wrapper.managedAccounts(accountsList)

    def _errorMsg(self, payload: bytes):
        proto = ErrorMessageProto()
        proto.ParseFromString(payload)
        reqId = proto.id if proto.HasField('id') else 0
        errorCode = proto.errorCode if proto.HasField('errorCode') else 0
        errorMsg = proto.errorMsg if proto.HasField('errorMsg') else ''
        advancedOrderRejectJson = (
            proto.advancedOrderRejectJson
            if proto.HasField('advancedOrderRejectJson') else '')
        # ib_insync wrapper.error does not take errorTime
        self.wrapper.error(reqId, errorCode, errorMsg, advancedOrderRejectJson)

    def _orderStatus(self, payload: bytes):
        proto = OrderStatusProto()
        proto.ParseFromString(payload)
        orderId = proto.orderId if proto.HasField('orderId') else 0
        status = proto.status if proto.HasField('status') else ''
        filled = float(proto.filled) if proto.HasField('filled') else 0.0
        remaining = float(proto.remaining) if proto.HasField('remaining') else 0.0
        avgFillPrice = proto.avgFillPrice if proto.HasField('avgFillPrice') else 0.0
        permId = proto.permId if proto.HasField('permId') else 0
        parentId = proto.parentId if proto.HasField('parentId') else 0
        lastFillPrice = proto.lastFillPrice if proto.HasField('lastFillPrice') else 0.0
        clientId = proto.clientId if proto.HasField('clientId') else 0
        whyHeld = proto.whyHeld if proto.HasField('whyHeld') else ''
        mktCapPrice = proto.mktCapPrice if proto.HasField('mktCapPrice') else 0.0
        self.wrapper.orderStatus(
            orderId, status, filled, remaining, avgFillPrice,
            permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)

    def _openOrder(self, payload: bytes):
        proto = OpenOrderProto()
        proto.ParseFromString(payload)
        orderId = proto.orderId if proto.HasField('orderId') else 0
        if not proto.HasField('contract'):
            return
        contract = self._decodeContract(proto.contract)
        if not proto.HasField('order'):
            return
        order = self._decodeOrder(orderId, proto.contract, proto.order)
        if not proto.HasField('orderState'):
            return
        orderState = self._decodeOrderState(proto.orderState)
        self.wrapper.openOrder(contract, order, orderState)

    def _openOrderEnd(self, payload: bytes):
        # proto is empty but we still parse it
        proto = OpenOrdersEndProto()
        proto.ParseFromString(payload)
        self.wrapper.openOrderEnd()

    def _accountValue(self, payload: bytes):
        proto = AccountValueProto()
        proto.ParseFromString(payload)
        key = proto.key if proto.HasField('key') else ''
        value = proto.value if proto.HasField('value') else ''
        currency = proto.currency if proto.HasField('currency') else ''
        accountName = proto.accountName if proto.HasField('accountName') else ''
        self.wrapper.updateAccountValue(key, value, currency, accountName)

    def _portfolioValue(self, payload: bytes):
        proto = PortfolioValueProto()
        proto.ParseFromString(payload)
        if not proto.HasField('contract'):
            return
        contract = self._decodeContract(proto.contract)
        position = float(proto.position) if proto.HasField('position') else 0.0
        marketPrice = proto.marketPrice if proto.HasField('marketPrice') else 0.0
        marketValue = proto.marketValue if proto.HasField('marketValue') else 0.0
        averageCost = proto.averageCost if proto.HasField('averageCost') else 0.0
        unrealizedPNL = proto.unrealizedPNL if proto.HasField('unrealizedPNL') else 0.0
        realizedPNL = proto.realizedPNL if proto.HasField('realizedPNL') else 0.0
        accountName = proto.accountName if proto.HasField('accountName') else ''
        self.wrapper.updatePortfolio(
            contract, position, marketPrice, marketValue,
            averageCost, unrealizedPNL, realizedPNL, accountName)

    def _accountUpdateTime(self, payload: bytes):
        proto = AccountUpdateTimeProto()
        proto.ParseFromString(payload)
        timeStamp = proto.timeStamp if proto.HasField('timeStamp') else ''
        self.wrapper.updateAccountTime(timeStamp)

    def _accountDownloadEnd(self, payload: bytes):
        proto = AccountDataEndProto()
        proto.ParseFromString(payload)
        accountName = proto.accountName if proto.HasField('accountName') else ''
        self.wrapper.accountDownloadEnd(accountName)

    def _position(self, payload: bytes):
        proto = PositionProto()
        proto.ParseFromString(payload)
        if not proto.HasField('contract'):
            return
        contract = self._decodeContract(proto.contract)
        position = float(proto.position) if proto.HasField('position') else 0.0
        avgCost = proto.avgCost if proto.HasField('avgCost') else 0.0
        account = proto.account if proto.HasField('account') else ''
        self.wrapper.position(account, contract, position, avgCost)

    def _positionEnd(self, payload: bytes):
        PositionEndProto().ParseFromString(payload)
        self.wrapper.positionEnd()

    def _positionMulti(self, payload: bytes):
        proto = PositionMultiProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        account = proto.account if proto.HasField('account') else ''
        modelCode = proto.modelCode if proto.HasField('modelCode') else ''
        if not proto.HasField('contract'):
            return
        contract = self._decodeContract(proto.contract)
        position = float(proto.position) if proto.HasField('position') else 0.0
        avgCost = proto.avgCost if proto.HasField('avgCost') else 0.0
        self.wrapper.positionMulti(
            reqId, account, modelCode, contract, position, avgCost)

    def _positionMultiEnd(self, payload: bytes):
        proto = PositionMultiEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.positionMultiEnd(reqId)

    def _accountSummary(self, payload: bytes):
        proto = AccountSummaryProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        account = proto.account if proto.HasField('account') else ''
        tag = proto.tag if proto.HasField('tag') else ''
        value = proto.value if proto.HasField('value') else ''
        currency = proto.currency if proto.HasField('currency') else ''
        self.wrapper.accountSummary(reqId, account, tag, value, currency)

    def _accountSummaryEnd(self, payload: bytes):
        proto = AccountSummaryEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.accountSummaryEnd(reqId)

    def _accountUpdateMulti(self, payload: bytes):
        proto = AccountUpdateMultiProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        account = proto.account if proto.HasField('account') else ''
        modelCode = proto.modelCode if proto.HasField('modelCode') else ''
        key = proto.key if proto.HasField('key') else ''
        value = proto.value if proto.HasField('value') else ''
        currency = proto.currency if proto.HasField('currency') else ''
        self.wrapper.accountUpdateMulti(
            reqId, account, modelCode, key, value, currency)

    def _accountUpdateMultiEnd(self, payload: bytes):
        proto = AccountUpdateMultiEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.accountUpdateMultiEnd(reqId)

    def _execDetails(self, payload: bytes):
        proto = ExecutionDetailsProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        if not proto.HasField('contract'):
            return
        contract = self._decodeContract(proto.contract)
        if not proto.HasField('execution'):
            return
        execution = self._decodeExecution(proto.execution)
        self.wrapper.execDetails(reqId, contract, execution)

    def _execDetailsEnd(self, payload: bytes):
        proto = ExecutionDetailsEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.execDetailsEnd(reqId)

    def _commissionReport(self, payload: bytes):
        proto = CommissionAndFeesReportProto()
        proto.ParseFromString(payload)
        cr = CommissionReport()
        cr.execId = proto.execId if proto.HasField('execId') else ''
        cr.commission = proto.commissionAndFees if proto.HasField('commissionAndFees') else 0.0
        cr.currency = proto.currency if proto.HasField('currency') else ''
        cr.realizedPNL = proto.realizedPNL if proto.HasField('realizedPNL') else 0.0
        cr.yield_ = proto.bondYield if proto.HasField('bondYield') else 0.0
        cr.yieldRedemptionDate = int(proto.yieldRedemptionDate) if proto.HasField('yieldRedemptionDate') else 0
        self.wrapper.commissionReport(cr)

    def _orderBound(self, payload: bytes):
        proto = OrderBoundProto()
        proto.ParseFromString(payload)
        permId = proto.permId if proto.HasField('permId') else 0
        clientId = proto.clientId if proto.HasField('clientId') else 0
        orderId = proto.orderId if proto.HasField('orderId') else 0
        self.wrapper.orderBound(permId, clientId, orderId)

    def _completedOrder(self, payload: bytes):
        proto = CompletedOrderProto()
        proto.ParseFromString(payload)
        if not proto.HasField('contract'):
            return
        contract = self._decodeContract(proto.contract)
        if not proto.HasField('order'):
            return
        order = self._decodeOrder(None, proto.contract, proto.order)
        if not proto.HasField('orderState'):
            return
        orderState = self._decodeOrderState(proto.orderState)
        self.wrapper.completedOrder(contract, order, orderState)

    def _completedOrdersEnd(self, payload: bytes):
        CompletedOrdersEndProto().ParseFromString(payload)
        self.wrapper.completedOrdersEnd()

    # ---- tick data handlers ----

    def _tickPrice(self, payload: bytes):
        proto = TickPriceProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tickType = proto.tickType if proto.HasField('tickType') else 0
        price = proto.price if proto.HasField('price') else 0.0
        size = float(proto.size) if proto.HasField('size') else 0.0
        # ib_insync uses priceSizeTick instead of separate price/size callbacks
        if price:
            self.wrapper.priceSizeTick(reqId, tickType, price, size)

    def _tickSize(self, payload: bytes):
        proto = TickSizeProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tickType = proto.tickType if proto.HasField('tickType') else 0
        size = float(proto.size) if proto.HasField('size') else 0.0
        self.wrapper.tickSize(reqId, tickType, size)

    def _tickGeneric(self, payload: bytes):
        proto = TickGenericProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tickType = proto.tickType if proto.HasField('tickType') else 0
        value = proto.value if proto.HasField('value') else 0.0
        self.wrapper.tickGeneric(reqId, tickType, value)

    def _tickString(self, payload: bytes):
        proto = TickStringProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tickType = proto.tickType if proto.HasField('tickType') else 0
        value = proto.value if proto.HasField('value') else ''
        self.wrapper.tickString(reqId, tickType, value)

    def _tickOptionComputation(self, payload: bytes):
        proto = TickOptionComputationProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tickType = proto.tickType if proto.HasField('tickType') else 0
        tickAttrib = proto.tickAttrib if proto.HasField('tickAttrib') else 0
        impliedVol = proto.impliedVol if proto.HasField('impliedVol') else -1.0
        delta = proto.delta if proto.HasField('delta') else -2.0
        optPrice = proto.optPrice if proto.HasField('optPrice') else -1.0
        pvDividend = proto.pvDividend if proto.HasField('pvDividend') else -1.0
        gamma = proto.gamma if proto.HasField('gamma') else -2.0
        vega = proto.vega if proto.HasField('vega') else -2.0
        theta = proto.theta if proto.HasField('theta') else -2.0
        undPrice = proto.undPrice if proto.HasField('undPrice') else -1.0
        self.wrapper.tickOptionComputation(
            reqId, tickType, tickAttrib,
            impliedVol, delta, optPrice, pvDividend,
            gamma, vega, theta, undPrice)

    def _tickSnapshotEnd(self, payload: bytes):
        proto = TickSnapshotEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.tickSnapshotEnd(reqId)

    def _tickReqParams(self, payload: bytes):
        proto = TickReqParamsProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        minTick = float(proto.minTick) if proto.HasField('minTick') else 0.0
        bboExchange = proto.bboExchange if proto.HasField('bboExchange') else ''
        snapshotPermissions = proto.snapshotPermissions if proto.HasField('snapshotPermissions') else 0
        self.wrapper.tickReqParams(reqId, minTick, bboExchange, snapshotPermissions)

    def _marketDataType(self, payload: bytes):
        proto = MarketDataTypeProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        marketDataType = proto.marketDataType if proto.HasField('marketDataType') else 0
        self.wrapper.marketDataType(reqId, marketDataType)

    def _tickByTick(self, payload: bytes):
        proto = TickByTickDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tickType = proto.tickType if proto.HasField('tickType') else 0
        if tickType in (1, 2):  # Last or AllLast
            if proto.HasField('historicalTickLast'):
                t = proto.historicalTickLast
                time = t.time if t.HasField('time') else 0
                price = t.price if t.HasField('price') else 0.0
                size = float(t.size) if t.HasField('size') else 0.0
                mask = t.tickAttribLast if t.HasField('tickAttribLast') else 0
                attrib = TickAttribLast(
                    pastLimit=bool(mask & 1), unreported=bool(mask & 2))
                exchange = t.exchange if t.HasField('exchange') else ''
                specialConditions = t.specialConditions if t.HasField('specialConditions') else ''
                self.wrapper.tickByTickAllLast(
                    reqId, tickType, time, price, size,
                    attrib, exchange, specialConditions)
        elif tickType == 3:  # BidAsk
            if proto.HasField('historicalTickBidAsk'):
                t = proto.historicalTickBidAsk
                time = t.time if t.HasField('time') else 0
                mask = t.tickAttribBidAsk if t.HasField('tickAttribBidAsk') else 0
                attrib = TickAttribBidAsk(
                    bidPastLow=bool(mask & 1), askPastHigh=bool(mask & 2))
                bidPrice = t.priceBid if t.HasField('priceBid') else 0.0
                askPrice = t.priceAsk if t.HasField('priceAsk') else 0.0
                bidSize = float(t.sizeBid) if t.HasField('sizeBid') else 0.0
                askSize = float(t.sizeAsk) if t.HasField('sizeAsk') else 0.0
                self.wrapper.tickByTickBidAsk(
                    reqId, time, bidPrice, askPrice, bidSize, askSize, attrib)
        elif tickType == 4:  # MidPoint
            if proto.HasField('historicalTickMidPoint'):
                t = proto.historicalTickMidPoint
                time = t.time if t.HasField('time') else 0
                midPoint = t.price if t.HasField('price') else 0.0
                self.wrapper.tickByTickMidPoint(reqId, time, midPoint)

    def _tickNews(self, payload: bytes):
        proto = TickNewsProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        timestamp = proto.timestamp if proto.HasField('timestamp') else 0
        providerCode = proto.providerCode if proto.HasField('providerCode') else ''
        articleId = proto.articleId if proto.HasField('articleId') else ''
        headline = proto.headline if proto.HasField('headline') else ''
        extraData = proto.extraData if proto.HasField('extraData') else ''
        self.wrapper.tickNews(reqId, timestamp, providerCode, articleId, headline, extraData)

    # ---- contract data handlers ----

    def _contractData(self, payload: bytes):
        proto = ContractDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        if not proto.HasField('contract') or not proto.HasField('contractDetails'):
            return
        cd = self._decodeContractDetails(proto.contract, proto.contractDetails, isBond=False)
        self.wrapper.contractDetails(reqId, cd)

    def _bondContractData(self, payload: bytes):
        proto = ContractDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        if not proto.HasField('contract') or not proto.HasField('contractDetails'):
            return
        cd = self._decodeContractDetails(proto.contract, proto.contractDetails, isBond=True)
        self.wrapper.bondContractDetails(reqId, cd)

    def _contractDataEnd(self, payload: bytes):
        proto = ContractDataEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.contractDetailsEnd(reqId)

    @staticmethod
    def _decodeContractDetails(contractProto, detailsProto, isBond: bool) -> ContractDetails:
        """Decode protobuf ContractData into ib_insync ContractDetails.

        Uses ibapi's decoder_utils for the heavy lifting, then patches
        ib_insync-specific field names.
        """
        # ibapi's decodeContractDetails returns an ibapi ContractDetails;
        # ib_insync's ContractDetails has the same field names, so we
        # convert by instantiating our own and copying fields.
        ibapi_cd = _ibapi_decodeContractDetails(contractProto, detailsProto, isBond)
        cd = ContractDetails()
        cd.contract = ProtobufDecoder._decodeContract(contractProto)
        # copy detail fields via proto field names
        detail_fields = _proto_fields(detailsProto)
        for fname in detail_fields:
            if detailsProto.HasField(fname):
                val = getattr(ibapi_cd, fname, None)
                if val is not None and hasattr(cd, fname):
                    setattr(cd, fname, val)
        # fields with different names between ibapi and ib_insync
        if hasattr(ibapi_cd, 'longName'):
            cd.longName = ibapi_cd.longName
        if hasattr(ibapi_cd, 'marketName'):
            cd.marketName = ibapi_cd.marketName
        if hasattr(ibapi_cd, 'orderTypes'):
            cd.orderTypes = ibapi_cd.orderTypes
        if hasattr(ibapi_cd, 'validExchanges'):
            cd.validExchanges = ibapi_cd.validExchanges
        if hasattr(ibapi_cd, 'notes') and ibapi_cd.notes:
            cd.notes = ibapi_cd.notes
        # parse lastTradeDateOrContractMonth
        ltdc = cd.contract.lastTradeDateOrContractMonth
        if ltdc:
            times = ltdc.split('-' if '-' in ltdc else None)
            if len(times) > 0:
                cd.contract.lastTradeDateOrContractMonth = times[0]
            if len(times) > 1:
                cd.lastTradeTime = times[1]
            if len(times) > 2:
                cd.timeZoneId = times[2]
        return cd

    # ---- market depth handlers ----

    def _marketDepth(self, payload: bytes):
        proto = MarketDepthProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        if not proto.HasField('marketDepthData'):
            return
        d = proto.marketDepthData
        position = d.position if d.HasField('position') else 0
        operation = d.operation if d.HasField('operation') else 0
        side = d.side if d.HasField('side') else 0
        price = d.price if d.HasField('price') else 0.0
        size = float(d.size) if d.HasField('size') else 0.0
        self.wrapper.updateMktDepth(reqId, position, operation, side, price, size)

    def _marketDepthL2(self, payload: bytes):
        proto = MarketDepthL2Proto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        if not proto.HasField('marketDepthData'):
            return
        d = proto.marketDepthData
        position = d.position if d.HasField('position') else 0
        marketMaker = d.marketMaker if d.HasField('marketMaker') else ''
        operation = d.operation if d.HasField('operation') else 0
        side = d.side if d.HasField('side') else 0
        price = d.price if d.HasField('price') else 0.0
        size = float(d.size) if d.HasField('size') else 0.0
        isSmartDepth = d.isSmartDepth if d.HasField('isSmartDepth') else False
        self.wrapper.updateMktDepthL2(
            reqId, position, marketMaker, operation, side, price, size, isSmartDepth)

    def _mktDepthExchanges(self, payload: bytes):
        proto = MarketDepthExchangesProto()
        proto.ParseFromString(payload)
        descriptions = []
        for d in proto.depthMarketDataDescriptions:
            desc = DepthMktDataDescription(
                exchange=d.exchange if d.HasField('exchange') else '',
                secType=d.secType if d.HasField('secType') else '',
                listingExch=d.listingExch if d.HasField('listingExch') else '',
                serviceDataType=d.serviceDataType if d.HasField('serviceDataType') else '',
                aggGroup=d.aggGroup if d.HasField('aggGroup') else 0)
            descriptions.append(desc)
        self.wrapper.mktDepthExchanges(descriptions)

    # ---- historical / bars handlers ----

    def _historicalData(self, payload: bytes):
        proto = HistoricalDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        from datetime import datetime, timezone
        for bar_proto in proto.historicalDataBars:
            bar = BarData(
                date=bar_proto.date if bar_proto.HasField('date') else '',
                open_=bar_proto.open if bar_proto.HasField('open') else 0.0,
                high=bar_proto.high if bar_proto.HasField('high') else 0.0,
                low=bar_proto.low if bar_proto.HasField('low') else 0.0,
                close=bar_proto.close if bar_proto.HasField('close') else 0.0,
                volume=float(bar_proto.volume) if bar_proto.HasField('volume') else 0.0,
                average=float(bar_proto.WAP) if bar_proto.HasField('WAP') else 0.0,
                barCount=bar_proto.barCount if bar_proto.HasField('barCount') else 0,
                timestamp=datetime.now(timezone.utc).astimezone())
            self.wrapper.historicalData(reqId, bar)

    def _historicalDataUpdate(self, payload: bytes):
        proto = HistoricalDataUpdateProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        if not proto.HasField('historicalDataBar'):
            return
        b = proto.historicalDataBar
        from datetime import datetime, timezone
        bar = BarData(
            date=b.date if b.HasField('date') else '',
            open_=b.open if b.HasField('open') else 0.0,
            high=b.high if b.HasField('high') else 0.0,
            low=b.low if b.HasField('low') else 0.0,
            close=b.close if b.HasField('close') else 0.0,
            volume=float(b.volume) if b.HasField('volume') else 0.0,
            average=float(b.WAP) if b.HasField('WAP') else 0.0,
            barCount=b.barCount if b.HasField('barCount') else 0,
            timestamp=datetime.now(timezone.utc).astimezone())
        self.wrapper.historicalDataUpdate(reqId, bar)

    def _historicalDataEnd(self, payload: bytes):
        proto = HistoricalDataEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        start = proto.startDateStr if proto.HasField('startDateStr') else ''
        end = proto.endDateStr if proto.HasField('endDateStr') else ''
        self.wrapper.historicalDataEnd(reqId, start, end)

    def _realtimeBar(self, payload: bytes):
        proto = RealTimeBarTickProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        time = proto.time if proto.HasField('time') else 0
        open_ = proto.open if proto.HasField('open') else 0.0
        high = proto.high if proto.HasField('high') else 0.0
        low = proto.low if proto.HasField('low') else 0.0
        close = proto.close if proto.HasField('close') else 0.0
        volume = float(proto.volume) if proto.HasField('volume') else 0.0
        wap = float(proto.WAP) if proto.HasField('WAP') else 0.0
        count = proto.count if proto.HasField('count') else 0
        self.wrapper.realtimeBar(reqId, time, open_, high, low, close, volume, wap, count)

    def _headTimestamp(self, payload: bytes):
        proto = HeadTimestampProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        headTimestamp = proto.headTimestamp if proto.HasField('headTimestamp') else ''
        self.wrapper.headTimestamp(reqId, headTimestamp)

    def _histogramData(self, payload: bytes):
        proto = HistogramDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        histogram = []
        for entry in proto.histogramDataEntries:
            histogram.append(HistogramData(
                price=entry.price if entry.HasField('price') else 0.0,
                count=int(entry.size) if entry.HasField('size') else 0))
        self.wrapper.histogramData(reqId, histogram)

    def _historicalTicks(self, payload: bytes):
        proto = HistoricalTicksProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        isDone = proto.isDone if proto.HasField('isDone') else False
        from datetime import datetime, timezone
        ticks = []
        for t in proto.historicalTicks:
            time = t.time if t.HasField('time') else 0
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(HistoricalTick(
                time=dt,
                price=t.price if t.HasField('price') else 0.0,
                size=float(t.size) if t.HasField('size') else 0.0))
        self.wrapper.historicalTicks(reqId, ticks, isDone)

    def _historicalTicksBidAsk(self, payload: bytes):
        proto = HistoricalTicksBidAskProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        isDone = proto.isDone if proto.HasField('isDone') else False
        from datetime import datetime, timezone
        ticks = []
        for t in proto.historicalTicksBidAsk:
            time = t.time if t.HasField('time') else 0
            mask = t.tickAttribBidAsk if t.HasField('tickAttribBidAsk') else 0
            attrib = TickAttribBidAsk(
                askPastHigh=bool(mask & 1), bidPastLow=bool(mask & 2))
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(HistoricalTickBidAsk(
                time=dt, tickAttribBidAsk=attrib,
                priceBid=t.priceBid if t.HasField('priceBid') else 0.0,
                priceAsk=t.priceAsk if t.HasField('priceAsk') else 0.0,
                sizeBid=float(t.sizeBid) if t.HasField('sizeBid') else 0.0,
                sizeAsk=float(t.sizeAsk) if t.HasField('sizeAsk') else 0.0))
        self.wrapper.historicalTicksBidAsk(reqId, ticks, isDone)

    def _historicalTicksLast(self, payload: bytes):
        proto = HistoricalTicksLastProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        isDone = proto.isDone if proto.HasField('isDone') else False
        from datetime import datetime, timezone
        ticks = []
        for t in proto.historicalTicksLast:
            time = t.time if t.HasField('time') else 0
            mask = t.tickAttribLast if t.HasField('tickAttribLast') else 0
            attrib = TickAttribLast(
                pastLimit=bool(mask & 1), unreported=bool(mask & 2))
            dt = datetime.fromtimestamp(time, timezone.utc)
            ticks.append(HistoricalTickLast(
                time=dt, tickAttribLast=attrib,
                price=t.price if t.HasField('price') else 0.0,
                size=float(t.size) if t.HasField('size') else 0.0,
                exchange=t.exchange if t.HasField('exchange') else '',
                specialConditions=t.specialConditions if t.HasField('specialConditions') else ''))
        self.wrapper.historicalTicksLast(reqId, ticks, isDone)

    def _historicalSchedule(self, payload: bytes):
        proto = HistoricalScheduleProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        startDateTime = proto.startDateTime if proto.HasField('startDateTime') else ''
        endDateTime = proto.endDateTime if proto.HasField('endDateTime') else ''
        timeZone = proto.timeZone if proto.HasField('timeZone') else ''
        sessions = []
        for s in proto.historicalSessions:
            sessions.append(HistoricalSession(
                startDateTime=s.startDateTime if s.HasField('startDateTime') else '',
                endDateTime=s.endDateTime if s.HasField('endDateTime') else '',
                refDate=s.refDate if s.HasField('refDate') else ''))
        self.wrapper.historicalSchedule(reqId, startDateTime, endDateTime, timeZone, sessions)

    # ---- news handlers ----

    def _newsBulletin(self, payload: bytes):
        proto = NewsBulletinProto()
        proto.ParseFromString(payload)
        msgId = proto.newsMsgId if proto.HasField('newsMsgId') else 0
        msgType = proto.newsMsgType if proto.HasField('newsMsgType') else 0
        message = proto.newsMessage if proto.HasField('newsMessage') else ''
        origExch = proto.originatingExch if proto.HasField('originatingExch') else ''
        self.wrapper.updateNewsBulletin(msgId, msgType, message, origExch)

    def _newsArticle(self, payload: bytes):
        proto = NewsArticleProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        articleType = proto.articleType if proto.HasField('articleType') else 0
        articleText = proto.articleText if proto.HasField('articleText') else ''
        self.wrapper.newsArticle(reqId, articleType, articleText)

    def _newsProviders(self, payload: bytes):
        proto = NewsProvidersProto()
        proto.ParseFromString(payload)
        providers = []
        for np in proto.newsProviders:
            providers.append(NewsProvider(
                code=np.providerCode if np.HasField('providerCode') else '',
                name=np.providerName if np.HasField('providerName') else ''))
        self.wrapper.newsProviders(providers)

    def _historicalNews(self, payload: bytes):
        proto = HistoricalNewsProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        time = proto.time if proto.HasField('time') else ''
        providerCode = proto.providerCode if proto.HasField('providerCode') else ''
        articleId = proto.articleId if proto.HasField('articleId') else ''
        headline = proto.headline if proto.HasField('headline') else ''
        self.wrapper.historicalNews(reqId, time, providerCode, articleId, headline)

    def _historicalNewsEnd(self, payload: bytes):
        proto = HistoricalNewsEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        hasMore = proto.hasMore if proto.HasField('hasMore') else False
        self.wrapper.historicalNewsEnd(reqId, hasMore)

    # ---- scanner / fundamental handlers ----

    def _scannerParameters(self, payload: bytes):
        proto = ScannerParametersProto()
        proto.ParseFromString(payload)
        xml = proto.xml if proto.HasField('xml') else ''
        self.wrapper.scannerParameters(xml)

    def _scannerData(self, payload: bytes):
        proto = ScannerDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        for elem in proto.scannerDataElement:
            rank = elem.rank if elem.HasField('rank') else 0
            cd = ContractDetails()
            if elem.HasField('contract'):
                cd.contract = self._decodeContract(elem.contract)
            cd.marketName = elem.marketName if elem.HasField('marketName') else ''
            distance = elem.distance if elem.HasField('distance') else ''
            benchmark = elem.benchmark if elem.HasField('benchmark') else ''
            projection = elem.projection if elem.HasField('projection') else ''
            legsStr = elem.comboKey if elem.HasField('comboKey') else ''
            self.wrapper.scannerData(reqId, rank, cd, distance, benchmark, projection, legsStr)
        self.wrapper.scannerDataEnd(reqId)

    def _fundamentalData(self, payload: bytes):
        proto = FundamentalsDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        data = proto.data if proto.HasField('data') else ''
        self.wrapper.fundamentalData(reqId, data)

    # ---- pnl handlers ----

    def _pnl(self, payload: bytes):
        proto = PnLProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        dailyPnL = proto.dailyPnL if proto.HasField('dailyPnL') else 0.0
        unrealizedPnL = proto.unrealizedPnL if proto.HasField('unrealizedPnL') else 0.0
        realizedPnL = proto.realizedPnL if proto.HasField('realizedPnL') else 0.0
        self.wrapper.pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)

    def _pnlSingle(self, payload: bytes):
        proto = PnLSingleProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        pos = float(proto.position) if proto.HasField('position') else 0.0
        dailyPnL = proto.dailyPnL if proto.HasField('dailyPnL') else 0.0
        unrealizedPnL = proto.unrealizedPnL if proto.HasField('unrealizedPnL') else 0.0
        realizedPnL = proto.realizedPnL if proto.HasField('realizedPnL') else 0.0
        value = proto.value if proto.HasField('value') else 0.0
        self.wrapper.pnlSingle(reqId, pos, dailyPnL, unrealizedPnL, realizedPnL, value)

    # ---- fa handlers ----

    def _receiveFA(self, payload: bytes):
        proto = ReceiveFAProto()
        proto.ParseFromString(payload)
        faDataType = proto.faDataType if proto.HasField('faDataType') else 0
        xml = proto.xml if proto.HasField('xml') else ''
        self.wrapper.receiveFA(faDataType, xml)

    def _replaceFAEnd(self, payload: bytes):
        proto = ReplaceFAEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        text = proto.text if proto.HasField('text') else ''
        self.wrapper.replaceFAEnd(reqId, text)

    # ---- sec def opt params handlers ----

    def _secDefOptParam(self, payload: bytes):
        proto = SecDefOptParameterProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        exchange = proto.exchange if proto.HasField('exchange') else ''
        underlyingConId = proto.underlyingConId if proto.HasField('underlyingConId') else 0
        tradingClass = proto.tradingClass if proto.HasField('tradingClass') else ''
        multiplier = proto.multiplier if proto.HasField('multiplier') else ''
        expirations = set(proto.expirations) if proto.expirations else set()
        strikes = set(proto.strikes) if proto.strikes else set()
        self.wrapper.securityDefinitionOptionParameter(
            reqId, exchange, underlyingConId, tradingClass, multiplier,
            expirations, strikes)

    def _secDefOptParamEnd(self, payload: bytes):
        proto = SecDefOptParameterEndProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        self.wrapper.securityDefinitionOptionParameterEnd(reqId)

    # ---- misc handlers ----

    def _softDollarTiers(self, payload: bytes):
        proto = SoftDollarTiersProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        tiers = []
        for t in proto.softDollarTiers:
            tiers.append(SoftDollarTier(
                name=t.name if t.HasField('name') else '',
                val=t.value if t.HasField('value') else '',
                displayName=t.displayName if t.HasField('displayName') else ''))
        self.wrapper.softDollarTiers(reqId, tiers)

    def _familyCodes(self, payload: bytes):
        proto = FamilyCodesProto()
        proto.ParseFromString(payload)
        codes = []
        for fc in proto.familyCodes:
            codes.append(FamilyCode(
                accountID=fc.accountID if fc.HasField('accountID') else '',
                familyCodeStr=fc.familyCodeStr if fc.HasField('familyCodeStr') else ''))
        self.wrapper.familyCodes(codes)

    def _symbolSamples(self, payload: bytes):
        proto = SymbolSamplesProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        descriptions = []
        for cdp in proto.contractDescriptions:
            cd = ContractDescription()
            if cdp.HasField('contract'):
                cd.contract = self._decodeContract(cdp.contract)
            cd.derivativeSecTypes = list(cdp.derivativeSecTypes) if cdp.derivativeSecTypes else []
            descriptions.append(cd)
        self.wrapper.symbolSamples(reqId, descriptions)

    def _smartComponents(self, payload: bytes):
        proto = SmartComponentsProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        components = []
        for sc in proto.smartComponents:
            components.append(SmartComponent(
                bitNumber=sc.bitNumber if sc.HasField('bitNumber') else 0,
                exchange=sc.exchange if sc.HasField('exchange') else '',
                exchangeLetter=sc.exchangeLetter if sc.HasField('exchangeLetter') else ''))
        self.wrapper.smartComponents(reqId, components)

    def _marketRule(self, payload: bytes):
        proto = MarketRuleProto()
        proto.ParseFromString(payload)
        marketRuleId = proto.marketRuleId if proto.HasField('marketRuleId') else 0
        increments = []
        for pi in proto.priceIncrements:
            increments.append(PriceIncrement(
                lowEdge=pi.lowEdge if pi.HasField('lowEdge') else 0.0,
                increment=pi.increment if pi.HasField('increment') else 0.0))
        self.wrapper.marketRule(marketRuleId, increments)

    def _rerouteMktDataReq(self, payload: bytes):
        proto = RerouteMarketDataRequestProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        conId = proto.conId if proto.HasField('conId') else 0
        exchange = proto.exchange if proto.HasField('exchange') else ''
        self.wrapper.rerouteMktDataReq(reqId, conId, exchange)

    def _rerouteMktDepthReq(self, payload: bytes):
        proto = RerouteMarketDepthRequestProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        conId = proto.conId if proto.HasField('conId') else 0
        exchange = proto.exchange if proto.HasField('exchange') else ''
        self.wrapper.rerouteMktDepthReq(reqId, conId, exchange)

    def _wshMetaData(self, payload: bytes):
        proto = WshMetaDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        dataJson = proto.dataJson if proto.HasField('dataJson') else ''
        self.wrapper.wshMetaData(reqId, dataJson)

    def _wshEventData(self, payload: bytes):
        proto = WshEventDataProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        dataJson = proto.dataJson if proto.HasField('dataJson') else ''
        self.wrapper.wshEventData(reqId, dataJson)

    def _userInfo(self, payload: bytes):
        proto = UserInfoProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        whiteBrandingId = proto.whiteBrandingId if proto.HasField('whiteBrandingId') else ''
        self.wrapper.userInfo(reqId, whiteBrandingId)

    def _currentTime(self, payload: bytes):
        proto = CurrentTimeProto()
        proto.ParseFromString(payload)
        time = proto.currentTime if proto.HasField('currentTime') else 0
        self.wrapper.currentTime(time)

    def _currentTimeInMillis(self, payload: bytes):
        proto = CurrentTimeInMillisProto()
        proto.ParseFromString(payload)
        timeInMillis = proto.currentTimeInMillis if proto.HasField('currentTimeInMillis') else 0
        self.wrapper.currentTimeInMillis(timeInMillis)

    def _verifyMessageAPI(self, payload: bytes):
        proto = VerifyMessageApiProto()
        proto.ParseFromString(payload)
        apiData = proto.apiData if proto.HasField('apiData') else ''
        self.wrapper.verifyMessageAPI(apiData)

    def _verifyCompleted(self, payload: bytes):
        proto = VerifyCompletedProto()
        proto.ParseFromString(payload)
        isSuccessful = proto.isSuccessful if proto.HasField('isSuccessful') else False
        errorText = proto.errorText if proto.HasField('errorText') else ''
        self.wrapper.verifyCompleted(isSuccessful, errorText)

    def _displayGroupList(self, payload: bytes):
        proto = DisplayGroupListProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        groups = proto.groups if proto.HasField('groups') else ''
        self.wrapper.displayGroupList(reqId, groups)

    def _displayGroupUpdated(self, payload: bytes):
        proto = DisplayGroupUpdatedProto()
        proto.ParseFromString(payload)
        reqId = proto.reqId if proto.HasField('reqId') else -1
        contractInfo = proto.contractInfo if proto.HasField('contractInfo') else ''
        self.wrapper.displayGroupUpdated(reqId, contractInfo)
