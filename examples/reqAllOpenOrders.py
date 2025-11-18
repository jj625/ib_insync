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
from ib_insync import IB, util, AccountValue
import time
from ib_insync.contract import *  # noqa
logger.info(inspect.getfile(IB))
logging.getLogger('ib_insync').setLevel(logging.WARNING) # shut up ib_insync logging

class myClass:
    def __init__(self, ib: IB):
        self.ib = ib
        # self.ib.accountSummaryEvent += self.onAcctSummaryDebounce3Async

    _logger = logging.getLogger("myClass")


if __name__ == '__main__':
    (host, port, clientId) = ('127.0.0.1', 7497, 9998)
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

    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=5)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        # logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
        ib.disconnect()
