import asyncio
import inspect
import pprint
import logging
from typing import ClassVar

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logger = logging.getLogger(__name__)
import os, sys
for d in ['../../ib_insync', '../../eventkit']:
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), d))
    if parent_dir not in sys.path:
        # sys.path.append(parent_dir)
        sys.path.insert(0, parent_dir)
        logger.info(f"{parent_dir} added to sys.path")
import eventkit
logger.info(inspect.getfile(eventkit))
from ib_insync import IB, util, AccountValue, StopOrder, MarketOrder
import time
from ib_insync.contract import *  # noqa
logger.info(inspect.getfile(IB))
# add file logging (debug to file, keep console at INFO from basicConfig)
_dirname, _basename = os.path.split(__file__)
log_file = os.path.join(_dirname, f'{os.path.splitext(_basename)[0]}.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s'))
logging.getLogger().addHandler(file_handler)
# allow ib_insync debug to be captured by the file handler while console remains at INFO
logging.getLogger('ib_insync').setLevel(logging.WARNING) # shut up ib_insync logging

class myClass:
    _logger:ClassVar[logging.Logger] = logging.getLogger("myClass")

    def __init__(self, ib: IB):
        self.ib = ib
        self.order_status_count = 0
        self.account_summary_count = 0
        self.update_portfolio_count = 0
        self.account_value_count = 0
        # self.ib.accountSummaryEvent += self.onAcctSummaryDebounce3Async
        # self.ib.openOrderEvent += self.onOpenOrder
        self.ib.orderStatusEvent += self.onOrderStatus
        self.ib.accountUpdateMultiEndEvent += self.onAccountUpdateMultiEnd
        self.ib.accountSummaryEvent += self.onAccountSummary
        self.ib.updatePortfolioEvent += self.onUpdatePortfolio
        # self.ib.accountValueEvent += self.onAccountValue
    
    def onUpdatePortfolio(self, portfItem):
        self.update_portfolio_count += 1
        self._logger.info(f"Portfolio Update Event: {portfItem.contract.localSymbol} {portfItem.position} {portfItem.marketPrice} {portfItem.marketValue} {portfItem.unrealizedPNL} {portfItem.realizedPNL} {portfItem.averageCost}")
    def onAccountSummary(self, acctSum: AccountValue):
        self.account_summary_count += 1
        self._logger.info(f"Account Summary Event: {acctSum.account} {acctSum.tag} {acctSum.value} {acctSum.currency} {acctSum.modelCode}")
    def onAccountValue(self, acctVal: AccountValue):
        self.account_value_count += 1
        self._logger.info(f"Account Value Event: {acctVal.account} {acctVal.tag} {acctVal.value} {acctVal.currency} {acctVal.modelCode}")
    def onAccountUpdateMultiEnd(self, reqId):
        self._logger.info(f"Account update multi end event received for reqId: {reqId}")

    def onOpenOrder(self, trade):
        self._logger.info(f"onOpenOrder: {trade}")
    def onOrderStatus(self, trade):
        self.order_status_count += 1
        self._logger.info(f"[EVENT] onOrderStatus #{self.order_status_count}: status={trade.orderStatus.status}")
        if trade.isDone():
            self._logger.info(f"Trade is done. Final status={trade.orderStatus.status}")
        else:
            self._logger.info(f"Trade is not done yet. Status={trade.orderStatus.status}")

if __name__ == '__main__':
    (host, port, clientId) = ('127.0.0.1', 7496, 9997)
    connectInfo = (host, port, clientId)
    ib = IB()
    setattr(ib.wrapper, '_ExtraArgs', {"_keep_zero_positions": True})
    # ib.accountSummaryEvent += onAcctSummary
    myC = myClass(ib)
    ib.connect(*connectInfo)
    accounts = ib.managedAccounts()
    logger.info(f"Managed Accounts: {accounts}")
    # ib.reqPositionsMulti("U2575725")
    # ib.reqAccountSummary()
    # if len(accounts) > 1:
    #     ib.reqAccountUpdates("All")
    #     logger.info("Requested account updates for all managed accounts")
    # logger.info(f"Position:\n{pprint.pformat(ib.positions())}")
    # logger.info(f"Portfolio:\n{pprint.pformat(ib.portfolio())}")
    logger.info(f"{len(ib.portfolio())} portfolio items")
    # logger.info(f"Wrapper Positions:\n{pprint.pformat(ib.client.wrapper.positions)}")
    # logger.info(f"Wrapper Portfolio:\n{pprint.pformat(ib.client.wrapper.portfolio)}")

    # logger.info("=== ib.reqContractDetails() ===")
    # contract = Future('BRR', '202511', 'CME')
    # cd = ib.reqContractDetails(contract)
    # logger.info(f"ContractDetails {cd}")

    # logger.info(f"{ib.openOrders()}")
    async def reqOpenOrders():
        logger.info("=== ib.reqOpenOrdersAsync() ===")
        trds = await ib.reqAllOpenOrdersAsync()
        for t in trds:
            logger.info(f"OpenOrder {t.order.transmit} {t.order.orderType} {t.order.tif} {t.orderStatus.status}")
        # logger.info(pprint.pformat(trds))
        return trds
        
    # IB.run(reqOpenOrders())

    # contract = Stock('AAPL', 'SMART', 'USD')
    # stop_order = StopOrder('BUY', 1, 300.0)

    # contract = Future('MES', '202512', 'CME')
    # stop_order = StopOrder('SELL', 1, 6700.0, tif='GTC')
    # mktorder = MarketOrder('BUY', 1, tif='GTC')
    # trade = ib.placeOrder(contract, mktorder)
    # logger.info(f"Trade placed:\n{trade}")
    time.sleep(1)  # wait a bit for order to be processed
    acctVals = ib.accountValues()
    # count records per account
    acct_count = {}
    for av in acctVals:
        acct_count[av.account] = acct_count.get(av.account, 0) + 1
    for acct, count in acct_count.items():
        logger.info(f"Account {acct} has {count} AccountValue records")
    # ib.cancelOrder(trade.order)
    # logger.info(f"Cancelled StopOrder: {trade}")
    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=60*5)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        # logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
        ib.disconnect()
