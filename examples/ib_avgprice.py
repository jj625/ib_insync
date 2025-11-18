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
import ib_insync
from ib_insync import IB, util, AccountValue, PortfolioItem, Trade, Order
import time
from ib_insync.contract import *  # noqa
logger.info(inspect.getfile(IB))
logging.getLogger('ib_insync').setLevel(logging.WARNING) # shut up ib_insync logging

class myClass:
    def __init__(self, ib: IB):
        self.ib = ib
        self.ib.updatePortfolioEvent += self.onPortfolioUpdate
        # self.ib.accountSummaryEvent += self.onAcctSummaryDebounce3Async

    _logger = logging.getLogger("myClass")

    def onPortfolioUpdate(self, portfItem: PortfolioItem):
        logger.info(f"PortfolioUpdate: {portfItem.contract.localSymbol} {portfItem.position} {portfItem.marketPrice} {portfItem.marketValue} {portfItem.unrealizedPNL} {portfItem.realizedPNL} {portfItem.averageCost}")

        # for each trades, calculate the average buy price and average sell price across all fills
        buyValue = 0.0
        buyQuantity = 0
        sellValue = 0.0
        sellQuantity = 0
        trds = self.ib.trades()
        portfItemLocalSymbol = portfItem.contract.localSymbol
        portfItemConId = portfItem.contract.conId
        trds = [t for t in trds if t.contract.conId == portfItemConId]
        for trade in trds:
            logger.info(f"Trade: {pprint.pformat(trade.fills)}")
            buyValue += sum(fill.execution.price * fill.execution.shares for fill in trade.fills if fill.execution.side == 'BOT')
            buyQuantity += sum(fill.execution.shares for fill in trade.fills if fill.execution.side == 'BOT')
            sellValue += sum(fill.execution.price * fill.execution.shares for fill in trade.fills if fill.execution.side == 'SLD')
            sellQuantity += sum(fill.execution.shares for fill in trade.fills if fill.execution.side == 'SLD')

        # verify position matches
        if portfItem.position != (buyQuantity - sellQuantity):
            self._logger.warning(
                f"Position mismatch for {portfItem.contract.localSymbol}: "
                f"PortfolioItem.position={portfItem.position} vs calculated={buyQuantity - sellQuantity} "
                f"(BuyQty={buyQuantity}, SellQty={sellQuantity})"
            )

        # summarize average prices
        avgBuyPrice = buyValue / buyQuantity if buyQuantity > 0 else 0
        avgSellPrice = sellValue / sellQuantity if sellQuantity > 0 else 0
        logger.info(f"bot {buyQuantity} Average Buy Price: {avgBuyPrice}, sold {sellQuantity} Average Sell Price: {avgSellPrice}")


def testconnect(host, port, clientId):
    # write a simple tcp client to test connection parameters
    import socket
    try:
        with socket.create_connection((host, port), timeout=5) as s:
            logger.info(f"Successfully connected to {host}:{port} with clientId {clientId}")
            # do IB protocol handshake
            s.sendall(b'API v157..178\0')
            data = s.recv(14)
            logger.info(f"Received handshake response: {data}")

    except Exception as e:
        logger.error(f"Failed to connect to {host}:{port} with clientId {clientId}: {e}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Calculate average buy and sell prices from trades.')
    parser.add_argument('--host', type=str, default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7496)
    parser.add_argument('--clientId', type=int, default=9998)
    parser.add_argument('--testconnect', action='store_true', help='Test connection parameters and exit')
    args = parser.parse_args()
    if args.testconnect:
        print(f"Connection parameters: host={args.host}, port={args.port}, clientId={args.clientId}")
        testconnect(args.host, args.port, args.clientId)
        sys.exit(0)
    (host, port, clientId) = (args.host, args.port, args.clientId)
    connectInfo = (host, port, clientId)
    ib = IB()
    myC = myClass(ib)

    setattr(ib.wrapper, '_ExtraArgs', {"_keep_zero_positions": True})
    # ib.accountSummaryEvent += onAcctSummary
    ib.connect(*connectInfo)
    logger.info(f"Managed Accounts: {ib.managedAccounts()}")
    # logger.info(f"Position:\n{pprint.pformat(ib.positions())}")
    # logger.info(f"Portfolio:\n{pprint.pformat(ib.portfolio())}")
    # logger.info(f"Wrapper Positions:\n{pprint.pformat(ib.client.wrapper.positions)}")
    # logger.info(f"Wrapper Portfolio:\n{pprint.pformat(ib.client.wrapper.portfolio)}")

    # logger.info("=== ib.reqContractDetails() ===")
    # contract = Future('BRR', '202511', 'CME')
    # cd = ib.reqContractDetails(contract)
    # logger.info(f"ContractDetails {cd}")

    # logger.info(f"{ib.openOrders()}")
    async def reqOpenOrders():
        trds = await ib.reqAllOpenOrdersAsync()
        if trds:
            logger.info("=== ib.reqOpenOrdersAsync() ===")
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
