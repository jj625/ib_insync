import os
# Get the program's file name without the extension 
program_name = os.path.splitext(os.path.basename(__file__))[0] 
import sys
import io
import copy
import inspect
import re
import asyncio
def get_asyncio_running_loop(prefix: str = '') -> str:
    try:
        running_loop = asyncio.get_running_loop()
        result = f"{prefix} asyncio.get_running_loop() -> {running_loop} ({id(running_loop)})"
    except Exception as e:
        result = f"{prefix} asyncio.get_running_loop() -> {e}"
    return result

# print(get_asyncio_running_loop('0. '))
import pandas as pd
import numpy as np
np.set_printoptions(precision=2, suppress=True)
import logging
import datetime
import zoneinfo
local_tz = zoneinfo.ZoneInfo('US/Eastern')  # Adjust for your local timezone, America/New_York

MKTOPEN = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9, 30)).astimezone()
MKTCLOSE = datetime.datetime.combine(datetime.datetime.today(), datetime.time(16, 0)).astimezone()
import argparse
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional
import typing
import numbers
from concurrent.futures import ThreadPoolExecutor
import zoneinfo
local_tz = zoneinfo.ZoneInfo('US/Eastern') # Adjust for your local timezone, America/New_York

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    print(f"{parent_dir} added to sys.path")

# cmd /c mklink /D "eventkit" "C:\Users\Jimmy\source\erdewit\eventkit"
import pathlib

search_dirs = ['..', '../..', '../../..']
pkg_needed = ['eventkit', 'rlabbe/filterpy', 'jj625/python-telegram-bot', 'jj625/mplfinance']
pkg_dirs = {}

for pkg in pkg_needed:
    for dir in search_dirs:
        potential_dir = pathlib.Path(dir, pkg).resolve()
        if potential_dir.exists() and potential_dir.is_dir():
            pkg_dirs[pkg] = potential_dir
            break

for pkg, pkg_dir in pkg_dirs.items():
    if str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir))
        print(f"{pkg_dir} added to sys.path")

missing_pkgs = [pkg for pkg in pkg_needed if pkg not in pkg_dirs]
if missing_pkgs:
    print(f"Expected directories not found for: {', '.join(missing_pkgs)}")

import eventkit
import ib_insync
import ib_insync.ib
ib_insync.ib.install_custom_repr_()

from ib_insync import IB, MarketOrder, LimitOrder, BarData, BarDataList, Stock, Future, util

# probe if IB class has reqHistoricalDataExt()
if not hasattr(ib_insync.IB, 'reqHistoricalDataExt'):
    print(f"{ib_insync.IB} does not have reqHistoricalDataExt()")
    sys.exit(1)

# probe for numpy support in BarDataList
if not hasattr(BarDataList, '_init_npdata'):
    print(f"{BarDataList} does not have numpy extension")
    sys.exit(1)

import filterpy
from filterpy.kalman import KalmanFilter as kf

from collections import deque
from scipy.stats import skew, kurtosis, mode

import time
import functools

# Works with regular functions, instance methods, class methods, static methods, and coroutines.
# Correctly identifies and displays the class name for methods.
# Distinguishes between functions and coroutines in the output.

def measure_time(func):
    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print_result(func, args, execution_time)
        return result

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = await func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        print_result(func, args, execution_time)
        return result

    def print_result(func, args, execution_time):
        if inspect.ismethod(func):
            func_name = f"{func.__self__.__class__.__name__}.{func.__name__}"
        elif args and hasattr(args[0].__class__, func.__name__):
            func_name = f"{args[0].__class__.__name__}.{func.__name__}"
        else:
            func_name = func.__name__

        print(f"{'Coroutine' if asyncio.iscoroutinefunction(func) else 'Function'} "
              f"'{func_name}' took {execution_time:.6f} seconds to execute.")

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

class LoggerFilter(logging.Filter):
    def __init__(self, logger_name, pattern=r'.*'):
        super().__init__()
        self.logger_name = logger_name
        self.pattern = re.compile(pattern)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not (record.name == self.logger_name and
            self.pattern.search(msg) and 
            record.levelno >= logging.INFO
        )

def onError(reqId, errorCode, errorString, contract):
    logger.error(f"Error. Id: {reqId}, Code: {errorCode}, Msg: {errorString}")

def onPendingTickers(tickers):
    for ticker in tickers:
        x = (ticker.time.astimezone().__str__(), ticker.contract.localSymbol, ticker.bid, ticker.ask, ticker.last)
        logger.info(x)

def onTickSnapshotEnd(reqId: int):
    logger.info("Tick snapshot end {reqId}")

def onBarUpdate(bars: BarDataList, hasNewBar: bool):
    logger.info(f"{len(bars)} {hasNewBar}")

def future_done_callback(future: asyncio.Future):
    loop = future.get_loop()
    logger.info(f"future was bound to event loop {loop}")
    if future.cancelled():
        logger.info(f"future cancelled")
    elif future.done():
        # even if timeout
        exception = future.exception()
        logger.info(f"future done: {len(future.result())}")
        if exception:
            logger.error(f"future exception: {exception}")
    else:
        logger.error(f"future is neither done nor cancelled")
    count = future.remove_done_callback(future_done_callback)
    logger.info(f"future_done_callback removed: {count}")

def main():
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    filesuffix = f'_{datetime.datetime.now():%y%m%d_%H%M}'
    log_file = os.path.join(scriptdir, 'logs', f'{program_name}_{filesuffix}.log')

    # Initial logging setup
    # Set up logging to file and console
    logging.basicConfig(
        level=logging.INFO,
        format=('%(asctime)s:%(levelname)s:%(funcName)s:%(message)s'), #  + logging.BASIC_FORMAT
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol(s)') # nargs='+' means one or more
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID. Default is random between 1k and 10k.')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--enddate', type=datetime.datetime.fromisoformat, help='End date')
    args = argparser.parse_args()

    # Set up logging
    logging.basicConfig(level=args.loglevel, format=('%(asctime)s:' + logging.BASIC_FORMAT))
    global logger
    logger = logging.getLogger(__name__)
    
    if args.loglevel != 'INFO':
        logger.setLevel(args.loglevel)

    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    logger.info(args)

    # Connect to IB Gateway
    ib = IB()
    ib.tickSnapshotEndEvent += onTickSnapshotEnd
    ib.errorEvent += onError
    ib.pendingTickersEvent += onPendingTickers
    ib.barUpdateEvent += onBarUpdate

    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

    dtnow = datetime.datetime.now()
    syms = args.symbols or ['MES']
    useRTH = False # from 4:00am
    endDateTime = '' # datetime.datetime.now() + datetime.timedelta(days=-1)
    keepUpToDate = True
    for sym in syms:
        # contract_ = Stock(sym, 'SMART', 'USD')
        contract_ = Future(sym, '202503', 'CME')
        contractDetails = temp = ib.reqContractDetails(contract_)
        if len(temp) != 1:
            logger.error(f"Contract must be unique, expected 1 contractDetails, got {len(contractDetails)}")
            if contractDetails: logger.error(f"{contractDetails}")
            logger.error(f"Contract details not found for {sym}")
            continue
        else:
            logger.info(f"Contract details {temp[0].contract}")
            contract_ = temp[0].contract

            cdliquid = contractDetails[0].liquidSessions()[0]
            logger.info(f"liquid trading hours: {cdliquid.start.astimezone()} to {cdliquid.end.astimezone()}")

            cdl_full = contractDetails[0].tradingSessions()[0]
            logger.info(f"full trading hours: {cdl_full.start.astimezone()} to {cdl_full.end.astimezone()}")


        logger.info(f"Requesting historical bars for {sym}...")

        global bars5s, bars1m
        def initialize_bars(bars: BarDataList, barSizeSetting, rthfactor_pad=0.):
            # bars.reqId = agent.bars5s.reqId
            bars.contract = contract_
            bars.endDateTime = ''
            bars.durationStr = '1 D'
            bars.barSizeSetting = barSizeSetting
            bars.whatToShow = 'TRADES'
            bars.useRTH = False
            # bars.formatDate = agent.bars5s.formatDate
            bars.keepUpToDate = True
            bars._init_npdata('', '', rthfactor_pad=rthfactor_pad)

        # must init before initial_resample_hook
        # initialize_bars(agent.bars10s, '10 secs')
        # initialize_bars(agent.bars15s, '15 secs')
        rthfactor_pad = 7
        # initialize_bars(outBars30s, '30 secs', rthfactor_pad=rthfactor_pad)
        # initialize_bars(resampled, '1 min', rthfactor_pad=rthfactor_pad)
        # initialize_bars(outBars2m, '2 mins', rthfactor_pad=rthfactor_pad)
        # initialize_bars(outBars5m, '5 mins', rthfactor_pad=rthfactor_pad)
        # initialize_bars(outBars10m, '10 mins', rthfactor_pad=rthfactor_pad)
        # initialize_bars(outBars15m, '15 mins', rthfactor_pad=rthfactor_pad)
        # initialize_bars(outBars30m, '30 mins', rthfactor_pad=rthfactor_pad)

        # create_task() failed with "RuntimeError: no running event loop"
        future = asyncio.ensure_future(ib.reqHistoricalDataAsync(
                contract_,
                endDateTime=endDateTime,
                durationStr='1 D',
                barSizeSetting='5 secs',
                whatToShow='TRADES',
                useRTH=useRTH,
                keepUpToDate=keepUpToDate,
                formatDate=1,
                timeout=5, # if timeout, future is still marked as done, not cancelled
                # _historicalDataEndHook=initial_resample_hook
                )
        )
        future.add_done_callback(future_done_callback)
        # run the coroutine in the background
        # ib.run(coro)

        # logger.info(f"{len(bars5s)} bars5s downloaded")
        logger.info(f"future started: {future}")
        # bars1m = ib.reqHistoricalData(
        #         contract_,
        #         endDateTime=endDateTime,
        #         durationStr='1 D',
        #         barSizeSetting='1 min',
        #         whatToShow='TRADES',
        #         useRTH=useRTH,
        #         keepUpToDate=keepUpToDate,
        #         formatDate=1)
        # bars1m.updateEvent += onBarUpdate1m
        # logger.info(f"{len(bars1m)} bars1m downloaded")

    bars: Optional[BarDataList] = None # hold result from ib.reqHistoricalDataAsync()
    # request market data
    ib.reqMarketDataType(1)
    tkr = ib.reqMktData(contract_, '', False, False, None)
    ib.sleep(0.5)
    if len(ib.tickers()) != 1:
        logger.error(f"{ib.tickers()}: expected 1 ticker")
        return -1
    assert tkr == ib.tickers()[0], f"{tkr} != {ib.tickers()[0]}"
    for i in range(10):
        if hasattr(tkr, 'time') and tkr.time is not None:
            break
        logger.info(f"waiting for ticker to be fully populated")
        ib.sleep(0.5)
    else: # no break
        logger.error(f"ticker is not populating")
        return -1
    tdiff = (tkr.time - datetime.datetime.now(local_tz)).total_seconds()
    if abs(tdiff) > 2.0:
        # report clock skew
        logger.warning(f"Tick time is {tdiff:.2f} seconds" + (" ahead" if tdiff > 0 else " behind") + " of current time")
    if np.isnan(tkr.bid) or np.isnan(tkr.ask) or np.isnan(tkr.last) or np.isnan(tkr.close) or np.isnan(tkr.open_):
        bidasklast = f"bid {tkr.bid} ask {tkr.ask} last {tkr.last} close {tkr.close} open {tkr.open_}"
    else:
        bidasklast = f"bid {tkr.bid} ask {tkr.ask} last {tkr.last} chg {(tkr.ask+tkr.bid)/2.0/tkr.close-1.0:+.2%} open {tkr.open_} close {tkr.close} volume {tkr.volume:n}"
    logger.info(f"{tkr.contract.localSymbol}: {tkr.time.astimezone():%H:%M:%S} {bidasklast}")

    s = 10
    hours, remainder = divmod(s, 3600)
    minutes, seconds = divmod(remainder, 60)
    time_parts = []
    if hours > 0:
        time_parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0:
        time_parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    if seconds > 0:
        time_parts.append(f"{seconds} second{'s' if seconds > 1 else ''}")
    time_str = ", ".join(time_parts)
    logger.info(f"Waiting {time_str}...")
    ib.sleep(s)
    # await future
    while not future.done():
        logger.info(f"Waiting for future to complete...")
        ib.sleep(2)
    bars = future.result()
    print("result: len(bars) ", len(bars))
    ib.cancelMktData(contract_)
    # Disconnect
    ib.disconnect()
    logger.info("Done")

if __name__ == '__main__':
    main()
