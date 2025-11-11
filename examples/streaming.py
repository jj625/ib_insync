import asyncio

from ib_insync import IB, util
from ib_insync.contract import *  # noqa

headers = [
    'symbol', 'bidSize', 'bid', 'ask', 'askSize',
    'last', 'lastSize', 'close']

def onPendingTickers(tickers: set):
    # print(len(tickers), type(tickers), tickers)
    for t in tickers:
        print(t.contract.localSymbol, t.bidSize, t.bid, t.ask, t.askSize, t.last, t.lastSize, t.time.astimezone())
    # for ticker in tickers:
    #     row = conId2Row[ticker.contract.conId]
    #     for col, header in enumerate(headers):
    #         if col == 0:
    #             continue
    #         item = item(row, col)
    #         val = getattr(ticker, header)
    #         item.setText(str(val))


def closeEvent(self, ev):
    loop = util.getLoop()
    loop.stop()


if __name__ == '__main__':
    (host, port, clientId) = ('127.0.0.1', 7497, 9999)
    connectInfo = (host, port, clientId)
    ib = IB()
    ib.pendingTickersEvent += onPendingTickers
    ib.connect(*connectInfo)
    ib.reqMarketDataType(1) # live (1), frozen (2), delayed (3), delayed-frozen (4)
    contracts = [
        Stock('TSLA', 'SMART', 'USD'),
        Stock('AAPL', 'SMART', 'USD'),
        Future('ES', '202512', 'CME'),
        Forex('EURUSD'),
        Forex('USDJPY'),
    ]
    for contract in contracts:
        if (contract and ib.qualifyContracts(contract)):
            ticker = ib.reqMktData(contract, '', False, False, [])

    # create a dummy asyncio awaitable that does nothing to keep the event loop running
    async def aw():
        while True:
            await asyncio.sleep(1)
    try:
        IB.run(aw(), timeout=5)
    except TimeoutError:
        print('timeout')
    finally:
        ib.disconnect()
