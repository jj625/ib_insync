"""Test protobuf connect/disconnect against a live TWS/gateway on localhost:7296."""

import collections
import datetime
from random import randint
import time
import arrow
import colorama
import argparse
import asyncio
import logging
import sys
import pprint
from typing import Any

import eventkit as ek
import ib_insync as ibi
from ib_insync.objects import TickTypeEnum
from ib_insync.client import MIN_SERVER_VER_PROTOBUF

import colorama

# from histogr import VolumeSpikeHistogramNP, DynamicCompressedHistogramNP

logger = logging.getLogger(__name__)

HOST = '127.0.0.1'
CLIENT_ID = randint(99, 999)
WAIT_SECONDS = 60*5

# counter
_tickTypeCount = collections.Counter()

async def _on_update_event(t: ibi.Ticker):
    assert t.contract
    _localsym = t.contract.localSymbol
    for tt in t.ticks:
        _tickTypeCount[(TickTypeEnum(tt.tickType), _localsym)] += 1
        logger.info(tt)

class IBErrorAwaiter:
    def __init__(self, ib):
        self.ib = ib
        self.future = ib.loop.create_future()

        def _handler(info):
            if not self.future.done():
                self.future.set_exception(RuntimeError(str(info)))

        ib.apiError.connect(_handler)

async def main(args):
    ib = ibi.IB()

    PORT = args.port

    print(f'Connecting to {HOST}:{PORT} clientId={CLIENT_ID} ...')
    _account = ''
    await ib.connectAsync(HOST, PORT, CLIENT_ID, readonly=True, account=_account, timeout=10, 
        _MaxClientVer=args.maxclientversion, 
        _opts =  {
            'sync_multi_accounts': False, 
            'reqPositions': False, 
            'reqExecutions': False,
            'skip_reqOpenOrders': True,
            'skip_reqCompletedOrders': True,
        },
    )

    sv = ib.client.serverVersion()
    print(f'Server version: {sv}')
    print(f'Protobuf active: {sv >= MIN_SERVER_VER_PROTOBUF}')
    print(f'Accounts: {ib.managedAccounts()}')

    # assert sv >= MIN_SERVER_VER_PROTOBUF, (
    #     f'Server version {sv} < {MIN_SERVER_VER_PROTOBUF}; '
    #     f'protobuf not supported by this server')

    # assert ib.client._useProtobuf(), 'Client did not enter protobuf mode'

    assert ib.isConnected(), 'IB reports not connected after connectAsync'

    if 99 in args.test:
        print('-'*10 + ' Current Time ' + '-'*10)
        print(f'Current time: {await ib.reqCurrentTimeAsync()}')
        print(f'Current time in millis: {await ib.reqCurrentTimeInMillisAsync()}')
        await asyncio.Event().wait()

    spxidx = ibi.Index('SPX', 'CBOE', 'USD')
    esfut = ibi.Future('ES', '202606', 'CME')
    spy = ibi.Stock('SPY', 'SMART', 'USD')
    qqq = ibi.Stock('QQQ', 'NASDAQ', 'USD')
    eurusd = ibi.Forex('EURUSD')
    vfiax = ibi.MutualFund(symbol='VFIAX')
    btczh = ibi.Crypto('BTC', 'ZEROHASH', 'USD')
    # await ib.qualifyContractsAsync(spxidx,esfut, spy, qqq, eurusd, vfiax, btczh)

    if 100 in args.test:
        ts: float = time.time()
        # next clock cut at precisely 5s boundary
        next_ts_cut: float = ts + (5 - ts % 5)
        acc_size_net, acc_size_buy, acc_size_sell = 0, 0, 0 # accummulated size in the period
        current_bid, current_ask = 0, 0
        N: int = 0 # number of ticks recorded
        eod_vwap: float = 0
        price_size_cumulative: float = 0
        size_cumulative: float = 0
        _eod_start_ts = arrow.now().replace(hour=15, minute=59, second=30).timestamp()
        _eod_end_ts = arrow.now().replace(hour=16, minute=0, second=0).timestamp()
        async def _on_tickbytick(ticker, tickType, time_, args):
            nonlocal current_bid, current_ask, N
            nonlocal acc_size_net, acc_size_buy, acc_size_sell, ts, next_ts_cut
            nonlocal eod_vwap, price_size_cumulative, size_cumulative
            N += 1
            if tickType in (1, 2): # Last, AllLast
                price, size, attrib, exchange, specialConditions = args

                # determine sides
                sides = 1 if price >= current_ask else -1

                _now = time.time()
                # calculate vwap during 3:59-4:00pm
                if _eod_start_ts <= _now <= _eod_end_ts:
                    price_size_cumulative += price * size
                    size_cumulative += size
                    eod_vwap = price_size_cumulative / size_cumulative if size_cumulative > 0 else 0

                if _now >= next_ts_cut:                  
                    # histo

                    # print time down to milliseconds
                    color = colorama.Fore.GREEN if acc_size_buy > acc_size_sell else colorama.Fore.RED
                    buy_ratio = acc_size_buy/acc_size_net if acc_size_net > 0 else 0
                    print(
                        f'{color}{datetime.datetime.fromtimestamp(next_ts_cut).strftime(r"%H:%M:%S.%f")[:-3]} {N} '
                        f'{current_bid} / {current_ask} {next_ts_cut} {acc_size_net} B:{acc_size_buy} S:{acc_size_sell} '
                        + (f'{buy_ratio-0.5:.2f}')
                    )
                    ts = time.time()
                    next_ts_cut = ts + (5 - ts % 5)
                    acc_size_net, acc_size_buy, acc_size_sell = 0, 0, 0
                    N = 0
                # update stats
                # update accumulated size
                acc_size_net += size
                if sides == 1:
                    acc_size_buy += size
                else:
                    acc_size_sell += size
            elif tickType == 3:
                current_bid, current_ask, bidSize, askSize, attrib = args
                # handle bid/ask updates
            # print(tickType, time_, args)

        print('-'*10 + ' TickByTick ' + '-'*10)
        await ib.qualifyContractsAsync(esfut)
        tickTypeLast = 'AllLast' # Last, AllLast, BidAsk, MidPoint
        tickTypeBidAsk = 'BidAsk'
        ticker = ib.reqTickByTickData(esfut, tickTypeLast, 0, True)
        # print(ticker, id(ticker))
        # ticker.updateEvent.connect(_on_tickbytick, once=True)
        ticker._updateEventRaw.connect(_on_tickbytick, once=True)
        tickerBidAsk = ib.reqTickByTickData(esfut, tickTypeBidAsk, 0, True)
        # print(tickerBidAsk, id(tickerBidAsk))
        # tickerBidAsk.updateEvent.connect(_on_tickbytick, once=True)
        tickerBidAsk._updateEventRaw.connect(_on_tickbytick, once=True)

        await asyncio.Event().wait()
        ib.cancelTickByTickData(esfut, tickTypeLast)
        # ib.cancelTickByTickData(esfut, tickTypeBidAsk)

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
    # logging.getLogger('ib_insync.client').setLevel(logging.DEBUG)
    # logging.getLogger('ib_insync.wrapper').setLevel(logging.DEBUG)
    # logging.getLogger('ib_insync.ProtobufDecoder').setLevel(logging.DEBUG)

    # add cli `-test N` (N=int)
    
    parser = argparse.ArgumentParser()
    # -test should accept a list of ints, comma separated
    parser.add_argument('-test', type=str, default=[], help='Run specific tests, comma separated, 999=all')
    parser.add_argument('-maxclientversion', type=int, default=178, help='Maximum client version to use. 178..225.')
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
    # logging.getLogger('ib_insync.client').addFilter(KeywordFilter(keywords_to_filter))
    # logging.getLogger('ib_insync.wrapper').addFilter(KeywordFilter(keywords_to_filter))

    try:
        asyncio.run(main(args))
    except KeyboardInterrupt:
        print("Interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")

    print(f'_tickTypeCount:\n{pprint.pformat(_tickTypeCount, indent=2)}')
