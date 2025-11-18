import asyncio
import inspect
import pprint
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logger = logging.getLogger(__name__)
import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    logger.info(f"{parent_dir} added to sys.path")

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
    (host, port, clientId) = ('127.0.0.1', 7496, 9999)
    connectInfo = (host, port, clientId)
    ib = IB()
    # ib.accountSummaryEvent += onAcctSummary
    ib.connect(*connectInfo)

    myC = myClass(ib)

    # logger.info("=== ib.reqContractDetails() ===")
    # contract = Future('BRR', '202511', 'CME')
    # cd = ib.reqContractDetails(contract)
    # logger.info(f"ContractDetails {cd}")

    async def reqMatchingSymbolsAsync():
        logger.info("=== ib.reqMatchingSymbolsAsync() ===")
        symlist = await ib.reqMatchingSymbolsAsync('SI')
        # logger.info(f"MatchingSymbols {pprint.pformat(symlist)}")
        for cd in symlist:
            if (cd.contract and cd.contract.secType in ['FUT','IND']) or ('FUT' in cd.derivativeSecTypes):
                logger.info(f"ContractDetails {pprint.pformat(cd)}")
        return symlist
    
    IB.run(reqMatchingSymbolsAsync())

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
