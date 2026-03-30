"""Protobuf decoder for IB API messages.

Drop-in companion to the text-based Decoder. Handles incoming protobuf
messages (server version >= MIN_SERVER_VER_PROTOBUF) and dispatches to
the same Wrapper methods that the legacy Decoder calls.

Only the messages needed for the connectAsync / disconnect flow are
implemented here. Extend as needed for other API calls.
"""

import logging
from typing import Dict, Callable

from .contract import (
    ComboLeg, Contract, ContractDetails, DeltaNeutralContract)
from .objects import (
    CommissionReport, Execution, SoftDollarTier, TagValue)
from .order import Order, OrderComboLeg, OrderCondition, OrderState
from .wrapper import Wrapper

# -- Protobuf generated message types (from ibapi package) --
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

# IN message IDs (same as ibapi.message.IN)
IN_TICK_PRICE = 1
IN_TICK_SIZE = 2
IN_ORDER_STATUS = 3
IN_ERR_MSG = 4
IN_OPEN_ORDER = 5
IN_ACCT_VALUE = 6
IN_PORTFOLIO_VALUE = 7
IN_ACCT_UPDATE_TIME = 8
IN_NEXT_VALID_ID = 9
IN_MANAGED_ACCTS = 15
IN_OPEN_ORDER_END = 53
IN_ACCT_DOWNLOAD_END = 54
IN_EXECUTION_DATA_END = 55
IN_EXECUTION_DATA = 11
IN_MARKET_DATA_TYPE = 58
IN_COMMISSION_AND_FEES_REPORT = 59
IN_POSITION_DATA = 61
IN_POSITION_END = 62
IN_ACCOUNT_SUMMARY = 63
IN_ACCOUNT_SUMMARY_END = 64
IN_POSITION_MULTI = 71
IN_POSITION_MULTI_END = 72
IN_ACCOUNT_UPDATE_MULTI = 73
IN_ACCOUNT_UPDATE_MULTI_END = 74
IN_ORDER_BOUND = 100
IN_COMPLETED_ORDER = 101
IN_COMPLETED_ORDERS_END = 102


class ProtobufDecoder:
    """Decode protobuf IB messages and invoke corresponding wrapper methods."""

    def __init__(self, wrapper: Wrapper, serverVersion: int):
        self.wrapper = wrapper
        self.serverVersion = serverVersion
        self.logger = logging.getLogger('ib_insync.ProtobufDecoder')
        self._handlers: Dict[int, Callable[[bytes], None]] = {
            IN_NEXT_VALID_ID: self._nextValidId,
            IN_MANAGED_ACCTS: self._managedAccounts,
            IN_ERR_MSG: self._errorMsg,
            IN_ORDER_STATUS: self._orderStatus,
            IN_OPEN_ORDER: self._openOrder,
            IN_OPEN_ORDER_END: self._openOrderEnd,
            IN_ACCT_VALUE: self._accountValue,
            IN_PORTFOLIO_VALUE: self._portfolioValue,
            IN_ACCT_UPDATE_TIME: self._accountUpdateTime,
            IN_ACCT_DOWNLOAD_END: self._accountDownloadEnd,
            IN_POSITION_DATA: self._position,
            IN_POSITION_END: self._positionEnd,
            IN_POSITION_MULTI: self._positionMulti,
            IN_POSITION_MULTI_END: self._positionMultiEnd,
            IN_ACCOUNT_SUMMARY: self._accountSummary,
            IN_ACCOUNT_SUMMARY_END: self._accountSummaryEnd,
            IN_ACCOUNT_UPDATE_MULTI: self._accountUpdateMulti,
            IN_ACCOUNT_UPDATE_MULTI_END: self._accountUpdateMultiEnd,
            IN_EXECUTION_DATA: self._execDetails,
            IN_EXECUTION_DATA_END: self._execDetailsEnd,
            IN_COMMISSION_AND_FEES_REPORT: self._commissionReport,
            IN_ORDER_BOUND: self._orderBound,
            IN_COMPLETED_ORDER: self._completedOrder,
            IN_COMPLETED_ORDERS_END: self._completedOrdersEnd,
        }

    def processProtoBuf(self, payload: bytes, msgId: int):
        """Dispatch a protobuf message to the appropriate handler."""
        handler = self._handlers.get(msgId)
        if handler is None:
            self.logger.warning(
                f'No protobuf handler for msgId {msgId}, '
                f'payload length {len(payload)}')
            return
        try:
            handler(payload)
        except Exception:
            self.logger.exception(
                f'Error handling protobuf msgId {msgId}')

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
        for proto_name, order_name in _simple_fields:
            if orderProto.HasField(proto_name):
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
        for proto_name, os_name in _fields:
            if orderStateProto.HasField(proto_name):
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
        for proto_name, exec_name in _fields:
            if executionProto.HasField(proto_name):
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
