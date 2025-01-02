import os
# Get the program's file name without the extension 
program_name = os.path.splitext(os.path.basename(__file__))[0] 
import sys
import io
import copy
import pickle
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
# import signal
import ibapi
import pandas as pd
import numpy as np
import scipy.optimize
np.set_printoptions(precision=2, suppress=True)
import scipy
from scipy.ndimage import gaussian_filter1d
import logging
import datetime
import zoneinfo
local_tz = zoneinfo.ZoneInfo('US/Eastern')  # Adjust for your local timezone, America/New_York

MKTOPEN = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9, 30)).astimezone()
MKTCLOSE = datetime.datetime.combine(datetime.datetime.today(), datetime.time(16, 0)).astimezone()
# import time
import dateutil
import argparse
import json
# import email.utils
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Optional
import typing
import numbers
# import pdb
import telegram
if telegram.__version__ < '20.0':
    print("Requires python-telegram-bot library version 20.0 or higher")
    sys.exit(1)
import rich
from rich.logging import RichHandler
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

async def initial_resample_hook(start: str, end: str, bars: BarDataList):
    logger.info(f"start={start}, end={end}, len(bars)={len(bars)}")
    N = 2000 # 
    for n,b in enumerate(bars, start=1):
        await resample_from_5s_core(b, False)
        if n % N == 0:
            await asyncio.sleep(0) # yield to other tasks
    logger.info(f"len(resampled)={len(resampled)} {resampled._npidx} {resampled._npidx_rth_start} {resampled._npidx_rth_end}")
    # logger.info(f"len(self.bars10s)={len(self.bars10s)}")
    # logger.info(f"{self.bars10s._npidx} {self.bars10s._npidx_rth_start} {self.bars10s._npidx_rth_end}")
    # logger.info(f"{pd.DataFrame({'date': self.bars10s.npdate, 'open': self.bars10s.npopen,
    #                              'close': self.bars10s.npclose, 'high': self.bars10s.nphigh,
    #                              'low': self.bars10s.nplow}).iloc[:10]}")
    # logger.info(f"len(self.bars15s)={len(self.bars15s)}")
    # logger.info(f"len(self.bars30s)={len(self.bars30s)}")
    # logger.info(f"len(self.bars2m)={len(self.bars2m)}")
    # logger.info(f"len(outBars5m)={len(outBars5m)}")
    # logger.info(f"len(self.bars10m)={len(self.bars10m)}")
    # logger.info(f"len(outBars15m)={len(outBars15m)}")
    # util.df(resampled).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars1m.csv', index=False)
    # util.df(self.bars10s).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars10s.csv', index=False)
    # util.df(self.bars15s).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars15s.csv', index=False)
    # util.df(self.bars30s).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars30s.csv', index=False)
    # exit(0)

async def resample(inBars: BarDataList, inBarHasNewBar: bool):
    """
    Resample 5s bars to 1m, 2m, 5m, 10m, and 15m bars.
    """
    global bars_tick
    b = inBars[-1] # shortcut to the last bar
    if inBarHasNewBar:
        bars_tick = []
    # unravel the bar
    if not inBarHasNewBar:
        # logger.info(bars_tick)
        if bars_tick: # b.date 5, 10, 20, 25, 35, 40, 50, 55 (all 5s ticks except 0, 15, 30, 45)
            bc_diff = b.barCount - bars_tick[-1].barCount
            v_diff = b.volume - bars_tick[-1].volume
            current_sum = b.volume * b.average
            prev_sum = bars_tick[-1].volume * bars_tick[-1].average
            avg_inc = (current_sum - prev_sum) / v_diff if v_diff > 0 else b.close
            new_date = b.date + datetime.timedelta(seconds=len(bars_tick)*5)
            # logger.info(f"new_date={new_date}")
            new_b = BarData(new_date, b.open, b.high, b.low, b.close, v_diff, avg_inc, bc_diff, b.timestamp)
        else: # bar_tick == []
            new_b = BarData(b.date, b.open, b.high, b.low, b.close, b.volume, b.average, b.barCount, b.timestamp)
    elif inBarHasNewBar:
        if len(inBars) > 1: # b.date 0, 15, 30, 45
            new_b = BarData(b.date, b.open, b.high, b.low, b.close, b.volume, b.average, b.barCount, b.timestamp)
            # bc_diff = b.barCount - inBars[-2].barCount
            # v_diff = b.volume - inBars[-2].volume
            # current_sum = b.volume * b.average
            # prev_sum = inBars[-2].volume * inBars[-2].average
            # avg_inc = (current_sum - prev_sum) / v_diff if v_diff > 0 else b.close
            # new_b = BarData(b.date, b.open, b.high, b.low, b.close, v_diff, avg_inc, bc_diff, b.timestamp)
        else: # len(inBars) <= 1, just send the only bar
            new_b = BarData(b.date, b.open, b.high, b.low, b.close, b.volume, b.average, b.barCount, b.timestamp)
    # else:
    #     v_diff = 0
    #     avg_inc = b.close
    #     bc_diff = 0
    #     new_b = BarData(b.date, b.open, b.high, b.low, b.close, b.volume, b.average, b.barCount, b.timestamp)
    # logger.info(f"used_date={new_b.date}")

    bars_tick.append(copy.copy(b))

    await resample_from_5s_core(new_b, inBarHasNewBar)

    hasNewBar30s = new_b.date.second % 30 == 0
    hasNewBar1m = new_b.date.second == 0
    hasNewBar2m = hasNewBar1m and new_b.date.minute % 2 == 0
    hasNewBar5m = hasNewBar1m and new_b.date.minute % 5 == 0
    hasNewBar10m = hasNewBar1m and new_b.date.minute % 10 == 0
    hasNewBar15m = hasNewBar1m and new_b.date.minute % 15 == 0
    hasNewBar30m = hasNewBar1m and new_b.date.minute % 30 == 0
    onResampledBar(resampled, hasNewBar1m) # every 5 secs
    # onResampledBar30s(outBars30s, hasNewBar30s) # every 5 secs
    # onResampledBar2m(outBars2m, hasNewBar2m) # every 5 secs

async def resample_from_5s_core(inBar: BarData, inBarHasNewBar: bool):
    """
    Resample 5s bars to 1m, 2m, 5m, 10m, and 15m bars.
    """
    def update_bar(outBar: BarData, newBar: BarData, inBarHasNewBar: bool):
        sumVolume = outBar.volume + newBar.volume
        sumValues = outBar.volume * outBar.average + newBar.volume * newBar.average
        outBar.timestamp = newBar.timestamp
        outBar.close = newBar.close
        outBar.high = max(outBar.high, newBar.high)
        outBar.low = min(outBar.low, newBar.low)
        outBar.volume += newBar.volume
        outBar.barCount += newBar.barCount
        outBar.average = sumValues / sumVolume if sumVolume > 0 else newBar.close

    def handle_new_bar(outBars: BarDataList, newBar: BarData, hasNewBar: bool, inBarHasNewBar: bool):
        newcopy = copy.copy(newBar)
        if hasNewBar or not outBars:
            outBars.append(newcopy)
            outBars._add_npdata(newcopy)
        else:
            newcopy.date = outBars[-1].date # 
            update_bar(outBars[-1], newcopy, inBarHasNewBar)
            outBars._set_last_npdata(outBars[-1])

    # logger.info(f"used_date={inBar.date}")
    b = z = inBar
    # b = BarData(z.date, z.open, z.high, z.low, z.close, z.volume, z.average, z.barCount, z.timestamp)
    # if b.volume == 0:
    #     logger.warning(f"zero volume: {b}")
    atTopMinute = b.date.second % 60 == 0
    hasNewBar10s = b.date.second % 10 == 0
    hasNewBar15s = b.date.second % 15 == 0
    hasNewBar30s = b.date.second % 30 == 0
    hasNewBar1m = b.date.second == 0
    hasNewBar2m = hasNewBar1m and b.date.minute % 2 == 0
    hasNewBar5m = hasNewBar1m and b.date.minute % 5 == 0
    hasNewBar10m = hasNewBar1m and b.date.minute % 10 == 0
    hasNewBar15m = hasNewBar1m and b.date.minute % 15 == 0
    hasNewBar30m = hasNewBar1m and b.date.minute % 30 == 0

    handle_new_bar(resampled, b, hasNewBar1m, inBarHasNewBar)
    # if not hasattr(self, 'bars10s_log_count'):
    #     self.bars10s_log_count = 0
    # if self.bars10s_log_count < 10:
    #     logger.info(f"hasNewBar10s={hasNewBar10s}, {b.date.second}")
    #     self.bars10s_log_count += 1
    # handle_new_bar(self.bars10s, b, hasNewBar10s)
    # handle_new_bar(self.bars15s, b, hasNewBar15s)
    handle_new_bar(outBars30s, b, hasNewBar30s, inBarHasNewBar)
    handle_new_bar(outBars2m, b, hasNewBar2m, inBarHasNewBar)
    handle_new_bar(outBars5m, b, hasNewBar5m, inBarHasNewBar)
    handle_new_bar(outBars10m, b, hasNewBar10m, inBarHasNewBar)
    handle_new_bar(outBars15m, b, hasNewBar15m, inBarHasNewBar)
    handle_new_bar(outBars30m, b, hasNewBar30m, inBarHasNewBar)

outBars30s: BarDataList = BarDataList() # resampled 30s bars
outBars2m: BarDataList = BarDataList() # resampled 2m bars
outBars5m: BarDataList = BarDataList() # resampled 5m bars
outBars10m: BarDataList = BarDataList() # resampled 10m bars
outBars15m: BarDataList = BarDataList() # resampled 15m bars
outBars30m: BarDataList = BarDataList() # resampled 30m bars

# Global variables
logger = None

bars_tick: List[BarData] = [] # 5s ticks
bars5s: Optional[BarDataList] = None
resampled: BarDataList = BarDataList() # resampled 1m bars
bars1m: BarDataList = BarDataList()

hml: list[float] = [] # high minus low

def onError(reqId, errorCode, errorString, contract):
    logger.error(f"Error. Id: {reqId}, Code: {errorCode}, Msg: {errorString}")

def onBarUpdate1m(bars: BarDataList, hasNewBar: bool):
    logger.info(f"    real1m[-1]={bars1m[-1]._repr_()} hasNewBar={hasNewBar}")
    # if hasNewBar:
    #     logger.info(f"    real1m[-2]={bars1m[-2]._repr_()}") # the one just closed

    # high minus low
    currentBar = bars[-1] # bar that is being built, never full
    currentFullBar = bars[-2] # the most recent fully formed bar

def onResampledBar(bars: BarDataList, hasNewBar: bool):
    logger.info(f"resampled[-1]={bars[-1]._repr_()} hasNewBar={hasNewBar}")
    # if hasNewBar:
    #     if len(bars) <= 1:
    #         logger.info("resampled[-2] is not available")
    #     else:
    #         logger.info(f"resampled[-2]={bars[-2]._repr_()}") # the one just closed

def onResampledBar30s(bars: BarDataList, hasNewBar: bool):
    logger.info(f"rspl30s[-1]={bars[-1]._repr_()} hasNewBar={hasNewBar}")
    if hasNewBar:
        if len(bars) <= 1:
            logger.info("rspl30s[-2] is not available")
        else:
            logger.info(f"rspl30s[-2]={bars[-2]._repr_()}") # the one just closed

def onResampledBar2m(bars: BarDataList, hasNewBar: bool):
    logger.info(f"rspld2m[-1]={bars[-1]._repr_()} hasNewBar={hasNewBar}")
    if hasNewBar:
        if len(bars) <= 1:
            logger.info("rspld2m[-2] is not available")
        else:
            logger.info(f"rspld2m[-2]={bars[-2]}") # the one just closed

def onResampledBar5m(bars: BarDataList, hasNewBar: bool):
    logger.info(f"resampled[-1]={bars[-1]} hasNewBar={hasNewBar}")
    if hasNewBar:
        if len(bars) <= 1:
            logger.info("resampled[-2] is not available")
        else:
            logger.info(f"resampled[-2]={bars[-2]}") # the one just closed

def onResampledBar10m(bars: BarDataList, hasNewBar: bool):
    logger.info(f"resampled[-1]={bars[-1]} hasNewBar={hasNewBar}")
    if hasNewBar:
        if len(bars) <= 1:
            logger.info("resampled[-2] is not available")
        else:
            logger.info(f"resampled[-2]={bars[-2]}") # the one just closed

def onResampledBar15m(bars: BarDataList, hasNewBar: bool):
    logger.info(f"resampled[-1]={bars[-1]} hasNewBar={hasNewBar}")
    if hasNewBar:
        if len(bars) <= 1:
            logger.info("resampled[-2] is not available")
        else:
            logger.info(f"resampled[-2]={bars[-2]}") # the one just closed

def onBarUpdate5s_ib(bars: BarDataList, hasNewBar: bool):
    msg = f"bars[-1]={bars[-1]._repr_()}"
    logging.info(msg)

def onBarUpdate5s(bars: BarDataList, hasNewBar: bool):
    """
    bars: ohlcv every 5 seconds
    """
    logging.info("-"*40)
    # msg = f"      bars[-1]={bars[-1]._repr_()}"
    # if hasNewBar == False: # we don't expect False for 5s
    #     msg += " hasNewBar=False" # in case it happens, print warning
    #     logging.warning(msg)
    # else:
    #     logging.info(msg)
    # logging.info("-"*40)
    return # end of onBarUpdate5s

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
            #RichHandler(markup=True)
            logging.StreamHandler()
        ]
    )

    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol(s)') # nargs='+' means one or more
    # argparser.add_argument('numshares', type=int, nargs='?', help='Number of shares to trade')
    # argparser.add_argument('maxloss', type=float, nargs='?', help='Max loss threshold')
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID. Default is random between 1k and 10k.')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
    argparser.add_argument('--enddate', type=datetime.datetime.fromisoformat, help='End date')
    # argparser.add_argument('--live_trading', action='store_true', help='Live trading')
    args = argparser.parse_args()
    print(args)

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

    # Connect to IB Gateway
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))
    ib.errorEvent += onError

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
        if args.dryrun:
            continue

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
        initialize_bars(outBars30s, '30 secs', rthfactor_pad=rthfactor_pad)
        initialize_bars(resampled, '1 min', rthfactor_pad=rthfactor_pad)
        initialize_bars(outBars2m, '2 mins', rthfactor_pad=rthfactor_pad)
        initialize_bars(outBars5m, '5 mins', rthfactor_pad=rthfactor_pad)
        initialize_bars(outBars10m, '10 mins', rthfactor_pad=rthfactor_pad)
        initialize_bars(outBars15m, '15 mins', rthfactor_pad=rthfactor_pad)
        initialize_bars(outBars30m, '30 mins', rthfactor_pad=rthfactor_pad)

        bars5s = ib.reqHistoricalDataExt(
                contract_,
                endDateTime=endDateTime,
                durationStr='1 D',
                barSizeSetting='15 secs',
                whatToShow='TRADES',
                useRTH=useRTH,
                keepUpToDate=keepUpToDate,
                formatDate=1,
                _historicalDataEndHook=initial_resample_hook)
        # b5s_eventhandler.initialize(bars5s)
        # bars5s.updateEvent += b5s_eventhandler.__call__
        bars5s.updateEvent += onBarUpdate5s
        bars5s.updateEvent += resample
        # ib.barUpdateEvent += onBarUpdate5s_ib
        logger.info(f"{len(bars5s)} bars5s downloaded")

        bars1m = ib.reqHistoricalData(
                contract_,
                endDateTime=endDateTime,
                durationStr='1 D',
                barSizeSetting='1 min',
                whatToShow='TRADES',
                useRTH=useRTH,
                keepUpToDate=keepUpToDate,
                formatDate=1)
        bars1m.updateEvent += onBarUpdate1m
        logger.info(f"{len(bars1m)} bars1m downloaded")
    
    if datetime.datetime.now().time() < datetime.time(16, 0, 0):
        logger.info("Waiting until 4:02pm...")
        ib.waitUntil(datetime.time(16, 2, 0))
    else:
        s = 60 * 60
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

    filename5s = f"./data/{sym}_5s_{dtnow:%y%m%d_%H%M}.csv"
    filename1m = f"./data/{sym}_1m_{dtnow:%y%m%d_%H%M}.csv"
    filename1m_resampled = f"./data/{sym}_resampled_{dtnow:%y%m%d_%H%M}.csv"
    filename2m_resampled = f"./data/{sym}_resampled2m_{dtnow:%y%m%d_%H%M}.csv"
    filename5m_resampled = f"./data/{sym}_resampled5m_{dtnow:%y%m%d_%H%M}.csv"
    filename10m_resampled = f"./data/{sym}_resampled10m_{dtnow:%y%m%d_%H%M}.csv"
    filename15m_resampled = f"./data/{sym}_resampled15m_{dtnow:%y%m%d_%H%M}.csv"
    filename30m_resampled = f"./data/{sym}_resampled30m_{dtnow:%y%m%d_%H%M}.csv"

    bars5s_df = util.df(bars5s)
    bars1m_df = util.df(bars1m)
    resampled_df = util.df(resampled)
    resampled2m_df = util.df(outBars2m)
    resampled5m_df = util.df(outBars5m)
    # resampled10m_df = util.df(outBars10m)
    resampled15m_df = util.df(outBars15m)
    resampled30m_df = util.df(outBars30m)

    bars5s_df.to_csv(filename5s, index=False)
    bars1m_df.to_csv(filename1m, index=False)
    if resampled_df is not None:
        resampled_df.round({'average': 4}).to_csv(filename1m_resampled, index=False)
        buf = io.StringIO()
        resampled_df.info(buf=buf, verbose=True)
        logger.info(f"\n{buf}")
        logger.info(f"\n{resampled_df.describe().to_string()}")
        logger.info(f"File written: {filename1m_resampled}")
        
    if resampled2m_df is not None:
        resampled2m_df.round({'average': 4}).to_csv(filename2m_resampled, index=False)
        buf = io.StringIO()
        resampled2m_df.info(buf=buf, verbose=True)
        logger.info(f"\n{buf}")
        logger.info(f"\n{resampled2m_df.describe().to_string()}")
        logger.info(f"File written: {filename2m_resampled}")

    if resampled5m_df is not None:
        resampled5m_df.to_csv(filename5m_resampled, index=False)
        buf = io.StringIO()
        resampled5m_df.info(buf=buf, verbose=True)
        logger.info(f"\n{buf}")
        logger.info(f"\n{resampled5m_df.describe().to_string()}")
        logger.info(f"File written: {filename5m_resampled}")

    # if resampled10m_df is not None:
    #     resampled10m_df.to_csv(filename10m_resampled, index=False)
    #     buf = io.StringIO()
    #     resampled10m_df.info(buf=buf, verbose=True)
    #     logger.info(f"\n{buf}")
    #     logger.info(f"\n{resampled10m_df.describe().to_string()}")
    if resampled15m_df is not None:
        resampled15m_df.to_csv(filename15m_resampled, index=False)
        buf = io.StringIO()
        resampled15m_df.info(buf=buf, verbose=True)
        logger.info(f"\n{buf}")
        logger.info(f"\n{resampled15m_df.describe().to_string()}")
        logger.info(f"File written: {filename15m_resampled}")
    
    if resampled30m_df is not None:
        resampled30m_df.to_csv(filename30m_resampled, index=False)
        buf = io.StringIO()
        resampled30m_df.info(buf=buf, verbose=True)
        logger.info(f"\n{buf}")
        logger.info(f"\n{resampled30m_df.describe().to_string()}")
        logger.info(f"File written: {filename30m_resampled}")
    
    logger.info(f"Script done.")

    ib.disconnect()

    return # end of main

if __name__ == '__main__':
    main()
