import asyncio
import inspect
import logging

from ib_insync.order import LimitOrder, Trade
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logger = logging.getLogger(__name__)
import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    logger.info(f"{parent_dir} added to sys.path")

from ib_insync import IB, util
from ib_insync.contract import *  # noqa
logger.info(inspect.getfile(IB))
logging.getLogger('ib_insync').setLevel(logging.DEBUG) # shut up ib_insync logging

onOpenOrderEventCount = 0

def onOpenOrder(t: Trade):
    global onOpenOrderEventCount
    onOpenOrderEventCount += 1
    logger.info(f"[EVENT] #{onOpenOrderEventCount} {t}")

def closeEvent(self, ev):
    loop = util.getLoop()
    loop.stop()

if __name__ == '__main__':
    (host, port, clientId) = ('127.0.0.1', 7497, 9999)
    connectInfo = (host, port, clientId)
    ib = IB()
    ib.openOrderEvent += onOpenOrder
    ib.connect(*connectInfo)

    loop = util.getLoop()
    loop.run_until_complete(asyncio.sleep(3))
    logger.info("Placing an order to trigger openOrderEvent...")
    stk = Stock('AAPL', 'SMART', 'USD')
    if ib.qualifyContracts(stk):
        order = LimitOrder('BUY', 1, 700.0, tif='OVERNIGHT')
        ib.placeOrder(stk, order)
    # logger.info("=== ib.openOrders() ===")
    # orders = ib.openOrders() # will trigger openOrderEvent

    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=4*60)
    except TimeoutError:
        logger.warning('timeout')
    finally:
        logger.info(f"Open Order events received: {onOpenOrderEventCount}")
        ib.disconnect()
