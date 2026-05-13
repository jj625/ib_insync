"""Test protobuf connect/disconnect against a live TWS/gateway on localhost:7296."""

import os
import collections
import datetime, zoneinfo
from datetime import timedelta
from random import randint
import time
import arrow
import colorama
from rich import print
from rich.style import Style
from rich.console import Console

import argparse
import asyncio
import logging
import json
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

log = logging.getLogger("tickstitch")

def jlog(event, **fields):
    """
    Structured JSON log helper.
    All logs are single-line JSON objects with an 'event' field.
    """
    payload = {"event": event, **fields}
    log.info(json.dumps(payload, default=str))


# ---------------------------
# Query a window (trim drift)
# ---------------------------
async def query_window(ib: ibi.IB, contract, start_dt: datetime.datetime, end_dt: datetime.datetime, window_id):
    jlog("query_window_start",
         window_id=window_id,
         start=str(start_dt),
         end=str(end_dt))

    # eastern = zoneinfo.ZoneInfo('America/New_York')
    # print(f'{start_dt.astimezone(datetime.timezone.utc):%Y%m%d %H:%M:%S} UTC ',
    #     f'{end_dt.astimezone(datetime.timezone.utc):%Y%m%d %H:%M:%S} UTC')
    ticks = await ib.reqHistoricalTicksAsync(
        contract,
        f'{start_dt.astimezone(datetime.timezone.utc):%Y%m%d %H:%M:%S} UTC',
        f'{end_dt.astimezone(datetime.timezone.utc):%Y%m%d %H:%M:%S} UTC',
        1000,
        'Trades',
        False,
        True
    )

    raw_count = len(ticks)

    # Trim drift
    ticks = [t for t in ticks if start_dt <= t.time <= end_dt]
    trimmed_count = len(ticks)

    jlog("query_window_end",
         window_id=window_id,
         raw_count=raw_count,
         trimmed_count=trimmed_count)

    return ticks


# ---------------------------
# Deduplication helper
# ---------------------------
def dedupe_ticks(ticks):
    seen = set()
    out = []
    for t in ticks:
        key = (t.time, t.price, t.size, getattr(t, 'exchange', None))
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


# ---------------------------
# Compare overlap between windows
# ---------------------------
def compare_overlap(prev_ticks, curr_ticks, overlap_start, overlap_end, window_id):
    prev_overlap = [t for t in prev_ticks if overlap_start <= t.time <= overlap_end]
    curr_overlap = [t for t in curr_ticks if overlap_start <= t.time <= overlap_end]

    prev_overlap = dedupe_ticks(prev_overlap)
    curr_overlap = dedupe_ticks(curr_overlap)

    jlog("overlap_compare",
         window_id=window_id,
         overlap_start=str(overlap_start),
         overlap_end=str(overlap_end),
         prev_overlap=len(prev_overlap),
         curr_overlap=len(curr_overlap))

    # Perfect match
    if len(prev_overlap) == len(curr_overlap) and all(
        (a.time == b.time and a.price == b.price and a.size == b.size)
        for a, b in zip(prev_overlap, curr_overlap)
    ):
        jlog("overlap_match", window_id=window_id)
        return None

    # Otherwise find missing ranges
    prev_times = {t.time for t in prev_overlap}
    curr_times = {t.time for t in curr_overlap}

    missing = []

    missing_in_prev = sorted(curr_times - prev_times)
    missing_in_curr = sorted(prev_times - curr_times)

    if missing_in_prev:
        missing.append((missing_in_prev[0], missing_in_prev[-1]))

    if missing_in_curr:
        missing.append((missing_in_curr[0], missing_in_curr[-1]))

    jlog("overlap_mismatch",
         window_id=window_id,
         missing_count=len(missing),
         missing_ranges=[(str(a), str(b)) for (a, b) in missing])

    return missing


# ---------------------------
# Main adaptive fetcher
# ---------------------------
async def fetch_ticks_adaptive(ib, contract, dt: arrow.Arrow):
    dt_local = dt.to('local')
    start = dt_local.replace(hour=15, minute=59, second=30, microsecond=0).datetime
    end   = dt_local.replace(hour=16, minute=0, second=0, microsecond=0).datetime

    window_size = timedelta(seconds=5)
    min_window  = timedelta(seconds=1)
    max_window  = timedelta(seconds=5)
    overlap     = timedelta(seconds=1)

    merged = []
    prev_ticks = None
    prev_start = None
    prev_end = None
    window_id = 0

    t0 = start

    jlog("fetch_start",
         start=str(start),
         end=str(end),
         initial_window_size=str(window_size))

    while t0 < end:
        t1 = min(t0 + window_size, end)
        window_id += 1

        jlog("window_begin",
             window_id=window_id,
             start=str(t0),
             end=str(t1),
             window_size=str(window_size))

        ticks = await query_window(ib, contract, t0, t1, window_id)

        # If truncated → shrink window
        if len(ticks) == 1000 and window_size > min_window:
            old = window_size
            window_size /= 2
            jlog("window_shrink_truncation",
                 window_id=window_id,
                 old=str(old),
                 new=str(window_size))
            continue  # retry same window

        # If we have a previous window, compare overlap
        if prev_ticks is not None and prev_start is not None and prev_end is not None:
            overlap_start = max(prev_start, t0)
            overlap_end   = min(prev_end, t1)

            mismatch = compare_overlap(prev_ticks, ticks,
                                       overlap_start, overlap_end,
                                       window_id)

            if mismatch:
                # Shrink window and re-query only the mismatch region
                if window_size > min_window:
                    old = window_size
                    window_size /= 2
                    jlog("window_shrink_mismatch",
                         window_id=window_id,
                         old=str(old),
                         new=str(window_size))

                for (gap_start, gap_end) in mismatch:
                    jlog("gap_query",
                         window_id=window_id,
                         gap_start=str(gap_start),
                         gap_end=str(gap_end))

                    gap_ticks = await query_window(
                        ib, contract, gap_start, gap_end, f"{window_id}_gap"
                    )
                    ticks.extend(gap_ticks)

                ticks = dedupe_ticks(ticks)

            else:
                # Overlap matches → consider growing window
                if window_size < max_window:
                    old = window_size
                    window_size = min(max_window, window_size * 1.2)
                    jlog("window_grow",
                         window_id=window_id,
                         old=str(old),
                         new=str(window_size))

        # Merge
        merged.extend(ticks)
        prev_ticks = ticks
        prev_start, prev_end = t0, t1

        # Move forward
        next_t0 = t0 + window_size - overlap

        # Strong forward-progress guard
        if next_t0 <= t0:
            jlog("forward_progress_guard_triggered",
                window_id=window_id,
                t0=str(t0),
                attempted_next=str(next_t0),
                window_size=str(window_size))

            # Force a minimum forward step of 100 ms
            next_t0 = t0 + timedelta(milliseconds=100)

        t0 = next_t0

        jlog("window_end",
             window_id=window_id,
             next_start=str(t0))

    # Final dedupe + sort
    merged = dedupe_ticks(merged)
    merged.sort(key=lambda t: t.time)

    jlog("fetch_complete",
         total_ticks=len(merged))

    return merged

def compute_vwap(ticks):
    """
    Compute VWAP from a deduped, gap-free, time-ordered tick list.
    """
    total_volume = 0
    total_dollar = 0

    for t in ticks:
        px = t.price
        vol = t.size

        total_volume += vol
        total_dollar += px * vol

    if total_volume == 0:
        return None

    return total_dollar / total_volume

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

    fut = ibi.Future(args.fut, '202606', 'CME')

    # await ib.qualifyContractsAsync(spxidx,esfut, spy, qqq, eurusd, vfiax, btczh)

    if 102 in args.test:
        x = await fetch_ticks_adaptive(ib, fut, args.date)
        vwap = compute_vwap(x)
        # print(x)
        print(f'VWAP: {vwap}')
    if 101 in args.test:
        _startDate = arrow.now().replace(hour=15, minute=59, second=30)
        _endDate = _startDate.shift(seconds=5)
        x = []
        for i in range(1):
            y = await ib.reqHistoricalTicksAsync(fut, _startDate.datetime, _endDate.datetime, 1000, 'Trades', False, True)
            print(y[:5], y[-5:])
            x.append(y)
            _startDate = _endDate
            _endDate = _startDate.shift(seconds=5)
        # for i in range(1):
        #     y = await ib.reqHistoricalTicksAsync(fut, _startDate.datetime, _endDate.datetime, 1000, 'Trades', False, True)
        #     print(y[:5], y[-5:])
        #     x.append(y)
        #     _startDate = _endDate
        #     _endDate = _startDate.shift(seconds=1)

        # print(x)
    if 100 in args.test:
        ts: float = time.time()
        # next clock cut at precisely 5s boundary
        next_ts_5s_cut: float = ts + (5 - ts % 5)
        next_ts_1s_cut: float = ts + (1 - ts % 1)
        acc_size_net, acc_size_buy, acc_size_sell = 0, 0, 0 # accummulated size in the period
        current_bid, current_ask = 0, 0
        N: int = 0 # number of ticks recorded
        eod_vwap: float = 0
        price_size_cumulative: float = 0
        size_cumulative: float = 0
        _eod_start_ts = arrow.now().replace(hour=15, minute=59, second=30).timestamp()
        _eod_end_ts = arrow.now().replace(hour=16, minute=0, second=0).timestamp()

        # coloring
        my_style = Style(bold=False)
        console = Console(highlight=False)
        async def _on_tickbytick(ticker, tickType, time_, args):
            nonlocal current_bid, current_ask, N
            nonlocal acc_size_net, acc_size_buy, acc_size_sell, ts, next_ts_5s_cut, next_ts_1s_cut
            nonlocal eod_vwap, price_size_cumulative, size_cumulative
            N += 1
            if tickType in (1, 2): # Last, AllLast
                price, size, attrib, exchange, specialConditions = args

                # determine sides
                sides = 1 if price >= current_ask else -1

                _now = time.time()
                _in_eod_vwap = (_eod_start_ts <= _now <= _eod_end_ts)
                if _now >= next_ts_1s_cut:
                    console.print(
                        '  '
                        f'{datetime.datetime.fromtimestamp(next_ts_1s_cut).strftime(r"%H:%M:%S.%f")[:-3]} {N} '
                        f'{datetime.datetime.fromtimestamp(_now).strftime(r"%H:%M:%S.%f")[:-3] } '
                        f'{current_bid} / {current_ask} '
                        + (f'{eod_vwap:.4f}' if _in_eod_vwap else '')
                    )
                    # reset counters
                    next_ts_1s_cut = _now + (1 - _now % 1)
                    price_size_cumulative = 0
                    size_cumulative = 0
                    # eod_vwap = 0

                if _now >= next_ts_5s_cut:                  
                    # histo

                    # print time down to milliseconds
                    # color = colorama.Fore.GREEN if acc_size_buy > acc_size_sell else colorama.Fore.RED

                    color = "[not bold]" "[green]" if acc_size_buy > acc_size_sell else "[red]"
                    buy_ratio = acc_size_buy/acc_size_net if acc_size_net > 0 else 0
                    print(
                        f'{color}{datetime.datetime.fromtimestamp(next_ts_5s_cut).strftime(r"%H:%M:%S.%f")[:-3]} {N} '
                        f'{current_bid} / {current_ask} {next_ts_5s_cut} {acc_size_net} B:{acc_size_buy} S:{acc_size_sell} '
                        + (f'{buy_ratio-0.5:.2f}')
                    )
                    ts = time.time()
                    next_ts_5s_cut = ts + (5 - ts % 5)
                    next_ts_1s_cut = ts + (1 - ts % 1)
                    acc_size_net, acc_size_buy, acc_size_sell = 0, 0, 0
                    N = 0
                # update stats

                # calculate vwap during 3:59-4:00pm
                if _in_eod_vwap:
                    price_size_cumulative += price * size
                    size_cumulative += size
                    eod_vwap = price_size_cumulative / size_cumulative if size_cumulative > 0 else 0
                    # print(eod_vwap)
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
        await ib.qualifyContractsAsync(fut)
        tickTypeLast = 'AllLast' # Last, AllLast, BidAsk, MidPoint
        tickTypeBidAsk = 'BidAsk'
        ticker = ib.reqTickByTickData(fut, tickTypeLast, 0, True)
        # print(ticker, id(ticker))
        # ticker.updateEvent.connect(_on_tickbytick, once=True)
        ticker._updateEventRaw.connect(_on_tickbytick, once=True)
        tickerBidAsk = ib.reqTickByTickData(fut, tickTypeBidAsk, 0, True)
        # print(tickerBidAsk, id(tickerBidAsk))
        # tickerBidAsk.updateEvent.connect(_on_tickbytick, once=True)
        tickerBidAsk._updateEventRaw.connect(_on_tickbytick, once=True)

        await asyncio.Event().wait()
        ib.cancelTickByTickData(fut, tickTypeLast)
        # ib.cancelTickByTickData(fut, tickTypeBidAsk)

    # print(f'Connected OK — waiting {WAIT_SECONDS}s ...')
    # await asyncio.sleep(WAIT_SECONDS)

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

def _parsedate(d) -> arrow.Arrow:
    """
    Parse a date string into an arrow.Arrow object with Eastern Time zone.
    """
    return arrow.get(d, tzinfo=zoneinfo.ZoneInfo('America/New_York'))

if __name__ == '__main__':
    colorama.init()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColorLevelFormatter('%(asctime)s %(name)-20s %(levelname)-8s %(message)s'))
    # add parallel logging to file, path same as script folder
    file_path = os.path.join(os.path.dirname(__file__), 'test_tickbytick.log')
    file_handler = logging.FileHandler(file_path)
    file_handler.setFormatter(ColorLevelFormatter('%(asctime)s %(name)-20s %(levelname)-8s %(message)s'))
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)-20s %(levelname)-8s %(message)s',
        handlers=[handler, file_handler]
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
    parser.add_argument('-fut', type=str, default='ES', help='Futures contract to use.')
    parser.add_argument('-date', type=_parsedate, default=arrow.get(), help='Date for the test.')
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
