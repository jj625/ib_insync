import asyncio
import logging
import random
import re
import inspect

import eventkit as ek
import ib_insync
print(inspect.getfile(ib_insync), inspect.getfile(ek))
print(ib_insync.__version_info__, ek.__version_info__)

from ib_insync import IB, Forex, Future, Stock, Crypto,Ticker, util

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s:%(message)s')
logger = logging.getLogger(__name__)

def on_accountDownloadEnd(account: str):
    print(f"Account Download End {account}")

def on_accountUpdateMultiEnd(reqId: int):
    print(f"Account Update Multi End {reqId}")

def onErrorEvent(reqId, errorCode, errorString, contract):
    print(f"Error Event {reqId} {errorCode} {errorString} {contract}")

def onTimeoutEvent(idlePeriod: float):
    print(f"Timeout Event {idlePeriod}")

def apiStartEvent():
    print("API Start Event")

def apiEndEvent():
    print("API End Event")

def apiErrorEvent(errorMsg: str):
    print(f"API Error {errorMsg}")

def throttleStartEvent():
    print("Throttle Start Event")

def throttleEndEvent():
    print("Throttle End Event")

def onConnectedEvent():
    print("Connected Event")

def onDisconnectedEvent():
    print("Disconnected Event")

async def main():
    (host, port, clientId) = ('127.0.0.1', 7497, random.randint(9000, 9998))
    connectInfo = (host, port, clientId)
    ib = IB()
    ib.connectedEvent += onConnectedEvent
    ib.disconnectedEvent += onDisconnectedEvent
    ib.accountDownloadEndEvent += on_accountDownloadEnd
    ib.accountUpdateMultiEndEvent += on_accountUpdateMultiEnd

    ib.client.apiStart.connect(apiStartEvent)
    ib.client.apiEnd.connect(apiEndEvent)
    ib.client.apiError.connect(apiErrorEvent)
    ib.client.throttleStart.connect(throttleStartEvent)
    ib.client.throttleEnd.connect(throttleEndEvent)

    def onPendingTickers(tickers):
        print(f"Pending Tickers Event: {len(tickers)} tickers")
    # ib.pendingTickersEvent += onPendingTickers
    ib.errorEvent += onErrorEvent
    # myC = myClass(ib)
    # ib.connect(*connectInfo)

    if not ib.isConnected():
        # ib.connect(host_1, port_3, clientId=102)
        await ib.connectAsync(*connectInfo)
        # ib.connect(*connectInfo)
    # ib.portfolio()
    # ib.managedAccounts()

    _l = logging.getLogger('ib_insync')
    _l.setLevel(logging.DEBUG)

    # nkdh6 = Future('NKD', '202603', 'CME')
    # await ib.qualifyContractsAsync(nkdh6)

    # spy = Stock('SPY', 'ARCA', 'USD')
    # ticker = ib.reqMktData(spy, genericTickList='104') # 221,225,233,236,258,

    btc = Crypto("BTC", "ZEROHASH", "USD")
    await ib.qualifyContractsAsync(btc)
    ticker = ib.reqMktData(btc)
    # contract = Forex('EURUSD')
    # ticker = ib.reqMktData(contract)
    def onTicker(ticker: Ticker):
        print(f"Ticker Update: {ticker.ticks}")
    ticker.updateEvent += onTicker

    while True:
        # print(ticker)
        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
    # # create a dummy asyncio awaitable that does nothing to keep the event loop running
    # async def aw():
    #     while True:
    #         await asyncio.sleep(1)
    # try:
    #     IB.run(aw(), timeout=60*10)
    # except TimeoutError:
    #     logger.warning('timeout')
    # finally:
    #     logger.info(f"Account Summary events received: {onAcctSummaryEventCount}")
    #     ib.disconnect()
