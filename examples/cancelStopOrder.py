import asyncio
import inspect
import pprint
import logging

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
log_file = os.path.join(os.path.dirname(__file__), 'cancelStopOrder.log')
file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(name)s:%(message)s'))
logging.getLogger().addHandler(file_handler)
# allow ib_insync debug to be captured by the file handler while console remains at INFO
logging.getLogger('ib_insync').setLevel(logging.DEBUG)

class myClass:
    def __init__(self, ib: IB):
        self.ib = ib
        # self.ib.accountSummaryEvent += self.onAcctSummaryDebounce3Async
        self.ib.openOrderEvent += self.onOpenOrder
    def onOpenOrder(self, trade):
        self._logger.info(f"onOpenOrder: {trade}")

    _logger = logging.getLogger("myClass")


if __name__ == '__main__':
    (host, port, clientId) = ('127.0.0.1', 7496, 9997)
    connectInfo = (host, port, clientId)
    ib = IB()
    setattr(ib.wrapper, '_ExtraArgs', {"_keep_zero_positions": True})
    # ib.accountSummaryEvent += onAcctSummary
    ib.connect(*connectInfo)
    logger.info(f"Managed Accounts: {ib.managedAccounts()}")
    logger.info(f"Position:\n{pprint.pformat(ib.positions())}")
    logger.info(f"Portfolio:\n{pprint.pformat(ib.portfolio())}")
    logger.info(f"Wrapper Positions:\n{pprint.pformat(ib.client.wrapper.positions)}")
    logger.info(f"Wrapper Portfolio:\n{pprint.pformat(ib.client.wrapper.portfolio)}")
    myC = myClass(ib)

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
        
    IB.run(reqOpenOrders())

    # contract = Stock('AAPL', 'SMART', 'USD')
    # stop_order = StopOrder('BUY', 1, 300.0)

    contract = Future('MES', '202512', 'CME')
    stop_order = StopOrder('SELL', 1, 6700.0, tif='GTC')
    trade = ib.placeOrder(contract, stop_order)
    logger.info(f"Placed StopOrder: {trade}")
    time.sleep(10)  # wait a bit for order to be processed
    ib.cancelOrder(trade.order)
    logger.info(f"Cancelled StopOrder: {trade}")
    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=60)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        # logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
        ib.disconnect()
