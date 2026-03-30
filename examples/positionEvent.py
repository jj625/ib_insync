import asyncio
import inspect
from posixpath import basename
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
        
        self.position_event_count = 0
        self.ib.positionEvent.connect(self.onPositionEvent, once=True)
        
        self.portfolio_event_count = 0
        self.ib.updatePortfolioEvent.connect(self.onPortfolioEvent, once=True)
        # self.ib.accountSummaryEvent += self.onAcctSummaryDebounce3Async
        # self.ib.openOrderEvent += self.onOpenOrder
        # self.ib.orderStatusEvent += self.onOrderStatus
    def onPositionEvent(self, position):
        self.position_event_count += 1
        self._logger.info(f"[EVENT] onPositionEvent #{self.position_event_count}: {position.position} of {position.contract.localSymbol}")
    def onPortfolioEvent(self, portfolioItem):
        self.portfolio_event_count += 1
        self._logger.info(f"[EVENT] onPortfolioEvent #{self.portfolio_event_count}: {portfolioItem.position} of {portfolioItem.contract.localSymbol}")
    # def onOpenOrder(self, trade):
    #     self._logger.info(f"onOpenOrder: {trade}")
    # def onOrderStatus(self, trade):
    #     self.order_status_count += 1
    #     self._logger.info(f"[EVENT] onOrderStatus #{self.order_status_count}: status={trade.orderStatus.status}")
    #     if trade.isDone():
    #         self._logger.info(f"Trade is done. Final status={trade.orderStatus.status}")
    #     else:
    #         self._logger.info(f"Trade is not done yet. Status={trade.orderStatus.status}")

async def main():
    (host, port, clientId) = ('127.0.0.1', 7497, 9997)
    connectInfo = (host, port, clientId)
    ib = IB()
    setattr(ib.wrapper, '_ExtraArgs', {"_keep_zero_positions": True})
    # ib.accountSummaryEvent += onAcctSummary
    myC = myClass(ib)
    await ib.connectAsync(*connectInfo)
    logger.info(f"Managed Accounts: {ib.managedAccounts()}")
    # logger.info(f"Position:\n{pprint.pformat(ib.positions())}")
    # logger.info(f"Portfolio:\n{pprint.pformat(ib.portfolio())}")
    # logger.info(f"Wrapper Positions:\n{pprint.pformat(ib.client.wrapper.positions)}")
    # logger.info(f"Wrapper Portfolio:\n{pprint.pformat(ib.client.wrapper.portfolio)}")

    # logger.info("=== ib.reqContractDetails() ===")
    # contract = Future('BRR', '202511', 'CME')
    # cd = ib.reqContractDetails(contract)
    # logger.info(f"ContractDetails {cd}")

    # Create events to signal when callbacks are received
    position_event = asyncio.Event()
    portfolio_event = asyncio.Event()
    
    # Wrap the original callbacks to set the events
    original_position_callback = myC.onPositionEvent
    original_portfolio_callback = myC.onPortfolioEvent
    
    def wrapped_position_callback(position):
        original_position_callback(position)
        position_event.set()
    
    def wrapped_portfolio_callback(portfolioItem):
        original_portfolio_callback(portfolioItem)
        portfolio_event.set()
    
    # Replace callbacks with wrapped versions
    myC.ib.positionEvent.clear()
    myC.ib.positionEvent += wrapped_position_callback
    myC.ib.updatePortfolioEvent.clear()
    myC.ib.updatePortfolioEvent += wrapped_portfolio_callback
    
    # Place the order
    contract = Future('MES', '202512', 'CME')
    mktorder_buy = MarketOrder('BUY', 1, tif='GTC')
    trade_buy = ib.placeOrder(contract, mktorder_buy)
    logger.info(f"Buy trade placed:\n{trade_buy}")

    # Wait for the buy order to be processed
    await asyncio.sleep(1)

    # Now place the sell order
    mktorder_sell = MarketOrder('SELL', 1, tif='GTC')
    trade_sell = ib.placeOrder(contract, mktorder_sell)
    logger.info(f"Sell trade placed:\n{trade_sell}")
    
    # Wait for both callbacks with timeout - test independently
    position_success = False
    portfolio_success = False
    
    try:
        await asyncio.wait_for(position_event.wait(), timeout=2.0)
        logger.info("Position event received!")
        position_success = True
    except asyncio.TimeoutError:
        logger.error("Position event not received within 2 seconds")
    
    try:
        await asyncio.wait_for(portfolio_event.wait(), timeout=2.0)
        logger.info("Portfolio event received!")
        portfolio_success = True
    except asyncio.TimeoutError:
        logger.error("Portfolio event not received within 2 seconds")
    
    match (position_success, portfolio_success):
        case (True, True):
            print("Success: Both events received")
        case (True, False):
            print("Partial success: Only position event received")
        case (False, True):
            print("Partial success: Only portfolio event received")
        case (False, False):
            print("Failure: No events received")
    await asyncio.sleep(1)  # Give some time for cleanup
    ib.disconnect()
    return
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

    contract = Future('MES', '202512', 'CME')
    # stop_order = StopOrder('SELL', 1, 6700.0, tif='GTC')
    mktorder = MarketOrder('BUY', 1, tif='GTC')
    trade = ib.placeOrder(contract, mktorder)
    logger.info(f"Trade placed:\n{trade}")
    time.sleep(1)  # wait a bit for order to be processed
    # ib.cancelOrder(trade.order)
    # logger.info(f"Cancelled StopOrder: {trade}")
    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=10)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        # logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
        ib.disconnect()

if __name__ == '__main__':
    asyncio.run(main())