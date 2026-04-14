"""Test protobuf connect/disconnect against a live TWS/gateway on localhost:7296."""

import collections
import datetime
import colorama
import argparse
import asyncio
import logging
import sys
import pprint
from typing import Any

import ib_insync as ibi
from ib_insync.objects import TickTypeEnum
from ib_insync.client import MIN_SERVER_VER_PROTOBUF

logger = logging.getLogger(__name__)

HOST = '127.0.0.1'
CLIENT_ID = 99
WAIT_SECONDS = 60*5

# counter
_tickTypeCount = collections.Counter()

async def _on_update_event(t: ibi.Ticker):
    assert t.contract
    _localsym = t.contract.localSymbol
    for tt in t.ticks:
        _tickTypeCount[(TickTypeEnum(tt.tickType), _localsym)] += 1
        logger.info(tt)

async def main(args):
    ib = ibi.IB()

    PORT = args.port

    print(f'Connecting to {HOST}:{PORT} clientId={CLIENT_ID} ...')
    _account = 'U2575725'
    _account = ''
    await ib.connectAsync(HOST, PORT, CLIENT_ID, readonly=True, account=_account, timeout=10, _MaxClientVer=args.maxclientversion)

    sv = ib.client.serverVersion()
    print(f'Server version: {sv}')
    print(f'Protobuf active: {sv >= MIN_SERVER_VER_PROTOBUF}')
    print(f'Accounts: {ib.managedAccounts()}')

    # assert sv >= MIN_SERVER_VER_PROTOBUF, (
    #     f'Server version {sv} < {MIN_SERVER_VER_PROTOBUF}; '
    #     f'protobuf not supported by this server')

    # assert ib.client._useProtobuf(), 'Client did not enter protobuf mode'

    assert ib.isConnected(), 'IB reports not connected after connectAsync'

    print('-'*10 + ' Current Time ' + '-'*10)
    print(f'Current time: {await ib.reqCurrentTimeAsync()}')
    print(f'Current time in millis: {await ib.reqCurrentTimeInMillisAsync()}')

    spxidx = ibi.Index('SPX', 'CBOE', 'USD')
    esfut = ibi.Future('ES', '202606', 'CME')
    spy = ibi.Stock('SPY', 'SMART', 'USD')
    qqq = ibi.Stock('QQQ', 'NASDAQ', 'USD')
    eurusd = ibi.Forex('EURUSD')
    vfiax = ibi.MutualFund(symbol='VFIAX')
    btczh = ibi.Crypto('BTC', 'ZEROHASH', 'USD')
    await ib.qualifyContractsAsync(spxidx,esfut, spy, qqq, eurusd, vfiax, btczh)

    if 100 in args.test:
        async def _on_tickbytick(t: ibi.Ticker):
            print(t)

        print('-'*10 + ' Some Test 100 ' + '-'*10)
        await ib.qualifyContractsAsync(esfut)
        tickType = 'Last' # Last, AllLast, BidAsk, MidPoint
        ticker = ib.reqTickByTickData(esfut, tickType, 0, False)
        print(ticker)
        ticker.updateEvent.connect(_on_tickbytick)
        await asyncio.sleep(10)
        ib.cancelTickByTickData(esfut, tickType)
    if 10 in args.test:
        print('-'*10 + ' pnlSingle ' + '-'*10)
        ib.reqPnLSingle('U2575725', '', esfut.conId)
        print(f'Portfolio PnL:\n{pprint.pformat(ib.pnlSingle('U2575725'))}')
        ib.pnlSingleEvent.connect(lambda pnl: print(f'PnL update:\n{pprint.pformat(pnl)}'))

    if 11 in args.test:
        ib.reqPnL('U2575725')
        print(f'Portfolio PnL:\n{pprint.pformat(ib.pnl('U2575725'))}')
        ib.pnlEvent.connect(lambda pnl: print(f'PnL update:\n{pprint.pformat(pnl)}'))

    if 12 in args.test:
        print('-'*10 + ' Config ' + '-'*10)

        # print(await ib.reqConfigAsync())

        # print(f'Soft Dollar Tiers:\n{pprint.pformat(await ib.reqSoftDollarTiersAsync())}')

        print(f'Family Codes:\n{pprint.pformat(await ib.reqFamilyCodesAsync())}')
        
        # print(f'Market Rule:\n{pprint.pformat(await ib.reqMarketRuleAsync(2963))}')

        # z = await ib.reqMktDepthExchangesAsync()
        # print(f'Market Depth Exchanges:\nlen={len(z)}\n{pprint.pformat(z, indent=1)}')

        # ticker = ib.reqMktDepth(esfut)
        # ticker.updateEvent.connect(lambda t: print(t))
        # await asyncio.sleep(10)
        # ib.cancelMktDepth(esfut)

    if 1000 in args.test:
        print('-'*10 + ' Some Test 13 ' + '-'*10)
        ib.placeOrder(esfut, ibi.LimitOrder('BUY', 1, 6933, tif='GTC', account='DUP666283', transmit=True))
        # ib.reqNewsBulletins(True)

    if 0 in args.test:
        from adebouncer import AsyncDebouncer
        logging.getLogger('adebouncer').setLevel(logging.DEBUG)
        async def on_acct_summary_flush(a: list[ibi.AccountValue]):
            # get unique account
            accounts = set(av.account for av in a)
            # get unique AccountValue without lastUpdateTime element
            unique_av = { (av.account, av.tag): av for av in a }.values()
            # get account value item where tag contains 'cash'
            cash_items = [av for av in a if 'cash' in av.tag.lower()]
            logger.info(f'Unique accounts: {accounts}')
            # logger.info(f'Cash items:\n{pprint.pformat(cash_items, indent=1)}')
            logger.info(f'Total items: {len(a)}, Unique items: {len(unique_av)}')
            return
        adeb = AsyncDebouncer(on_acct_summary_flush, debounce=0.5, max_wait=2.0, max_batch=1000)
        # async def _on_apiEnd():
        #     logger.info("API end event received")
        #     await adeb.stop()
        # ib.client.apiEnd.connect(_on_apiEnd)
        await adeb.start()
        async def on_acct_summary(av: ibi.AccountValue):
            await adeb.add(av)
            # print(av)
        print('-'*10 + ' Account Summary ' + '-'*10)
        ib.accountSummaryEvent.connect(on_acct_summary)
        print(await ib.reqAccountSummaryAsync('ES2100'))
    if 1 in args.test:
        print('-'*10 + ' reqHistoricalDataAsync ' + '-'*10)

        h = await ib.reqHistoricalDataAsync(
            esfut, '', '5 D', '1 day', 'TRADES', False, keepUpToDate=False
        )
        # h = ib.reqHistoricalData()
        print(len(h), '\n', pprint.pformat(h))

        def _on_histbar(bars, newBar):
            print(len(bars), bars[-1], newBar)
        ib.barUpdateEvent.connect(_on_histbar)
        h = await ib.reqHistoricalDataAsync(
            esfut, '', '30 S', '10 secs', 'TRADES', False, keepUpToDate=True
        )
        print(len(h), '\n', pprint.pformat(h))

    print('-'*10 + ' Portfolio ' + '-'*10)
    print(f'Portfolio:\n{pprint.pformat(ib.portfolio())}')

    if 2 in args.test:
        print('-'*10 + ' FA Groups ' + '-'*10)
        print(f'FA groups:\n{await ib.requestFAAsync(1), {await ib.requestFAAsync(2)}}')
        
        print('-'*10 + ' User Info ' + '-'*10)
        print(await ib.reqUserInfoAsync())

    if 3 in args.test:
        print('-'*10 + ' Contract Details ' + '-'*10)
        cd = await ib.reqContractDetailsAsync(esfut)
        print(pprint.pformat(cd))

        # logging.getLogger('ib_insync.Decoder').setLevel(logging.DEBUG)
        await ib.qualifyContractsAsync(vfiax)
        print(vfiax)

        print('-'*10 + ' Matching Symbols ' + '-'*10)
        ms = await ib.reqMatchingSymbolsAsync('BTC')
        print(pprint.pformat(ms))

    if 4 in args.test:
        # simple reqMktData
        print('-'*10 + ' reqMktData ' + '-'*10)
        ticker = ib.reqMktData(eurusd)
        ticker.updateEvent.connect(lambda t: print(f'Ticker update:\n{pprint.pformat(t.ticks)}'))

    if 5 in args.test:
        # reqMktData with genericTickList
        # genericTickList = '38,39,40,41,42,43,44'
    
        # Legal ones for (FUT) are: 
        # 100(Option Volume),101(Option Open Interest),105(Average Opt Volume),106(impvolat),
        # 165(Misc. Stats),221/220(Creditman Mark Price),225(Auction),232/221(Pl Price),233(RTVolume),
        # 236(inventory),258/47(Fundamentals),292(Wide_news),293(TradeCount),294(TradeRate),
        # 295(VolumeRate),318(LastRTHTrade),375(RTTrdVolume),411(rthistvol),456/59(IBDividends),
        # 460(Bond Factor Multiplier),577(EtfNavLast(navlast)),586(IPOHLMPRC),587(Pl Price Delayed),
        # 588(Futures Open Interest),595(Short-Term Volume X Mins),614(EtfNavMisc(high/low)),
        # 619(Creditman Slow Mark Price),623(EtfFrozenNavLast(fznavlast))
            
        genericTickList = '100,101,105,106,165,221,220,225,232,233,236,293,294,295' \
          ',318,375,411,456,460,577,586,587,588,595,614,619,623'
        genericTickList = '232,588'
        tkr1 = ib.reqMktData(esfut, genericTickList, False, False)
        tkr1.updateEvent.connect(_on_update_event)
        # tkr1.updateEvent.connect(lambda t: print(f'Ticker update:\n{pprint.pformat(t.ticks)}'))

    if 6 in args.test:
        # reqMktData with genericTickList
        
        # Legal ones for (STK) are: 100(Option Volume),101(Option Open Interest),105(Average Opt Volume),
        # 106(impvolat),165(Misc. Stats),221/220(Creditman Mark Price),225(Auction),232/221(Pl Price),
        # 233(RTVolume),236(inventory),258/47(Fundamentals),292(Wide_news),293(TradeCount),
        # 294(TradeRate),295(VolumeRate),318(LastRTHTrade),375(RTTrdVolume),411(rthistvol),
        # 456/59(IBDividends),460(Bond Factor Multiplier),577(EtfNavLast(navlast)),586(IPOHLMPRC),
        # 587(Pl Price Delayed),588(Futures Open Interest),595(Short-Term Volume X Mins),
        # 614(EtfNavMisc(high/low)),619(Creditman Slow Mark Price),623(EtfFrozenNavLast(fznavlast))
        genericTickList = '100,101,105,106,165,221,220,225,232,233,236,293,294,295' \
          ',318,375,411,456,460,577,586,587,588,595,614,619,623'
        genericTickList = '577,623,614'
        tkr1 = ib.reqMktData(qqq, genericTickList, False, False)
        tkr1.updateEvent.connect(_on_update_event)
        # tkr1.updateEvent.connect(lambda t: print(f'Ticker update:\n{pprint.pformat(t.ticks)}'))

    if 7 in args.test:
        # reqMktData with genericTickList
        genericTickList = '38,39,40,41,42,43,44'
        # for (IND) are: 100(Option Volume),101(Option Open Interest),
        # 105(Average Opt Volume),106(impvolat),165(Misc. Stats),221/220(Creditman Mark Price),
        # 225(Auction),232/221(Pl Price),233(RTVolume),236(inventory),258/47(Fundamentals),
        # 292(Wide_news),293(TradeCount),294(TradeRate),295(VolumeRate),318(LastRTHTrade),
        # 375(RTTrdVolume),411(rthistvol),456/59(IBDividends),460(Bond Factor Multiplier),
        # 577(EtfNavLast(navlast)),586(IPOHLMPRC),587(Pl Price Delayed),588(Futures Open Interest),
        # 595(Short-Term Volume X Mins),614(EtfNavMisc(high/low)),619(Creditman Slow Mark Price),
        # 623(EtfFrozenNavLast(fznavlast))
        genericTickList = '100,101,105,106,165,221,220,225,232,221,233,236,293,294,295' \
           ',318,375,411,456,460,577,586,587,588,614,619,623'
        genericTickList = '162'
        tkr1 = ib.reqMktData(spxidx, genericTickList, False, False)
        tkr1.updateEvent.connect(_on_update_event)
        # tkr1.updateEvent.connect(lambda t: print(f'Ticker update:\n{pprint.pformat(t.ticks)}'))

    # TODO: fix this
    # t = ib.reqTickByTickData(esfut, 'AllLast', 0, False)
    # print(t)

    print(f'Connected OK — waiting {WAIT_SECONDS}s ...')
    await asyncio.sleep(WAIT_SECONDS)

    print('Disconnecting ...')
    ib.disconnect()
    assert not ib.isConnected(), 'IB still reports connected after disconnect'
    print('Done.')

class ColorLevelFormatter(logging.Formatter):
    def format_no_pad(self, record):
        level = record.levelname
        if record.levelno >= logging.ERROR:
            record.levelname = f"{colorama.Fore.RED}{level}{colorama.Style.RESET_ALL}"
        return super().format(record)
    def format(self, record):
        raw = record.levelname  # e.g. "ERROR"
        padded = f"{raw:<8}"    # pad BEFORE coloring

        if record.levelno >= logging.ERROR:
            colored = f"{colorama.Fore.RED}{padded}{colorama.Style.RESET_ALL}"
            record.levelname = colored
        else:
            record.levelname = padded

        return super().format(record)

if __name__ == '__main__':
    colorama.init()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorLevelFormatter('%(asctime)s %(name)-20s %(levelname)-8s %(message)s'))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
        handlers=[handler]
    )
    # bump client/decoder to DEBUG for protocol-level visibility
    logging.getLogger('ib_insync.client').setLevel(logging.DEBUG)
    logging.getLogger('ib_insync.wrapper').setLevel(logging.DEBUG)
    logging.getLogger('ib_insync.ProtobufDecoder').setLevel(logging.DEBUG)

    # add cli `-test N` (N=int)
    
    parser = argparse.ArgumentParser()
    # -test should accept a list of ints, comma separated
    parser.add_argument('-test', type=str, default=[], help='Run specific tests, comma separated, 999=all')
    parser.add_argument('-maxclientversion', type=int, default=178, help='Maximum client version to use. 178..223.')
    parser.add_argument('-port', type=int, default=7497, help='IB port to connect to.')
    args = parser.parse_args()
    if args.test:
        args.test = [int(x) for x in args.test.split(',')]
    
    print(args)

    # filter out log messages that contain certain keywords
    class KeywordFilter(logging.Filter):
        def __init__(self, keywords):
            super().__init__()
            self.keywords = keywords

        def filter(self, record):
            return not any(keyword in record.getMessage() for keyword in self.keywords)

    keywords_to_filter = ['updateAccountValue', 'accountUpdateMulti',
        'commissionReport', 'COMMISSION_AND_FEES_REPORT',
        'ACCOUNT_UPDATE_MULTI', 'ACCT_UPDATE_TIME', 'updateAccountTime',
        'updatePortfolio', 'PORTFOLIO_VALUE', 'ACCT_VALUE', 
        'REQ_ACCOUNT_UPDATES_MULTI', 'reqAccountUpdatesMultiAsync'
    ]
    logging.getLogger('ib_insync.client').addFilter(KeywordFilter(keywords_to_filter))
    logging.getLogger('ib_insync.wrapper').addFilter(KeywordFilter(keywords_to_filter))

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")

    print(f'_tickTypeCount:\n{pprint.pformat(_tickTypeCount, indent=2)}')
