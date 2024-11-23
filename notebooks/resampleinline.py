import os
# Get the program's file name without the extension 
program_name = os.path.splitext(os.path.basename(__file__))[0] 
import sys
import io
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

from ib_insync import IB, MarketOrder, LimitOrder, BarData, Stock, util

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

class OnlineStatsInt:
    def __init__(self, val_max: int = 1000):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0
        self.val_max = val_max
        self.counts = np.zeros(val_max + 1, dtype=int)

    def update(self, x: int):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2
        self.counts[x] += 1

    def variance(self):
        return self.M2 / self.n if self.n > 1 else 0.0

    def stddev(self):
        return np.sqrt(self.variance())

    def skewness(self):
        return skew(self.counts)

    def kurtosis(self):
        return kurtosis(self.counts)

    def mode(self):
        return np.argmax(self.counts)

    def quartiles(self):
        cumulative_counts = np.cumsum(self.counts)
        total = cumulative_counts[-1]
        return [np.searchsorted(cumulative_counts, total * q / 4) for q in range(1, 4)]

    def deciles(self):
        cumulative_counts = np.cumsum(self.counts)
        total = cumulative_counts[-1]
        return [np.searchsorted(cumulative_counts, total * d / 10) for d in range(1, 10)]

class OnlineStatsReal:
    def __init__(self, qlen=1000):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0
        self.values = deque(maxlen=qlen)  # Keep a limited history for mode, quartiles, and deciles

    def update(self, x: numbers.Real):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2
        self.values.append(x)

    def variance(self):
        return self.M2 / self.n if self.n > 1 else 0.0

    def stddev(self):
        return np.sqrt(self.variance())

    def skewness(self):
        return skew(self.values)

    def kurtosis(self):
        return kurtosis(self.values)

    def mode(self):
        return mode(self.values, keepdims=True).mode[0]

    def quartiles(self):
        return np.percentile(self.values, [25, 50, 75])

    def deciles(self):
        return np.percentile(self.values, np.arange(10, 100, 10))

class BarEventHandler:
    def __init__(self):
        self.first_call = True
    
    def __call__(self, bars: List[BarData], hasNewBar: bool):
        if self.first_call:
            self.first_call = False
            self.onFirstCall(bars, hasNewBar)
        self.onBarUpdate(bars, hasNewBar)

    def onFirstCall(self, bars: List[BarData], hasNewBar: bool):
        logger.info(f"bars[-1]={bars[-1]} hasNewBar={hasNewBar}")
        # for b in bars:
            
    def onBarUpdate(self, bars: List[BarData], hasNewBar: bool):
        onBarUpdate5s(bars, hasNewBar)
        r, h = self.resampler_5s_1m(bars, resampled)
        return # end of onBarUpdate

    def resampler_5s_1m(self, inBars: List[BarData], outBars: List[BarData]):
        """
        we don't need hasNewBar because 5s bars are always complete
        inBars: 5s bars
        outBars: 1m bars
        """
        outBarsHasNewBar = False
        z = inBars[-1]
        b: BarData = BarData(z.date, z.open, z.high, z.low, z.close
            , z.volume, z.average, z.barCount) # make sure b is a copy so we don't inadvertently change bar5s
        # logger.info(f"{inBars[-1]} hasNewBar={hasNewBar}")
        atTopMinute = b.date.second % 60 == 0 # at the top of the minute
        if atTopMinute or outBars == []:
            # resample to 60 seconds/1 min
            if atTopMinute and outBars:
                logger.debug(f"outBars[-2]={outBars[-1]}") # the one just closed
            outBars.append(b)
            assert b == outBars[-1]
            outBarsHasNewBar = True
            logger.debug(f"outBars[-1]={outBars[-1]} hasNewBar=True")
        elif outBars:
            sumVolume = outBars[-1].volume + b.volume
            sumValues = outBars[-1].volume * outBars[-1].average + b.volume * b.average
            outBars[-1].close = b.close
            if b.high > outBars[-1].high:
                outBars[-1].high = b.high
            if b.low < outBars[-1].low:
                outBars[-1].low = b.low
            outBars[-1].volume += b.volume
            outBars[-1].barCount += b.barCount
            outBars[-1].average = sumValues / sumVolume if sumVolume > 0 else b.close # has average even if volume is 0
            logger.debug(f"outBars[-1]={outBars[-1]} hasNewBar=False")

        onResampledBar(outBars, outBarsHasNewBar) # forward to resampled bar event
        return (outBars, outBarsHasNewBar)

# Global variables
logger = None

bars5s: List[BarData] = []
b5s_eventhandler = BarEventHandler()
resampled: List[BarData] = [] # resampled 1m bars
bars1m: List[BarData] = []

hml: list[float] = [] # high minus low
hmlstat: OnlineStatsInt = OnlineStatsInt(val_max=1000) # hml in cents

# def downsample(bars: List[BarData], b, n: int):
#     if b.date.minute % n == 0:
#         # resample to n minutes
#         bars.append(b)
#     else:
#         bars[-1].close = b.close
#         if b.high > bars[-1].high:
#             bars[-1].high = b.high
#         if b.low < bars[-1].low:
#             bars[-1].low = b.low
#         bars[-1].volume += b.volume

def onError(reqId, errorCode, errorString, contract):
    logger.error(f"Error. Id: {reqId}, Code: {errorCode}, Msg: {errorString}")

def onBarUpdate1m(bars: List[BarData], hasNewBar: bool):
    logger.info(f"bars1m[-1]={bars1m[-1]} hasNewBar={hasNewBar}")
    if hasNewBar:
        logger.info(f"bars1m[-2]={bars1m[-2]}") # the one just closed

    # high minus low
    currentBar = bars[-1] # bar that is being built, never full
    currentFullBar = bars[-2] # the most recent fully formed bar
    hmlfb_ = currentFullBar.high - currentFullBar.low
    hml_ = currentBar.high - currentBar.low
    logger.info(f"hmlfb={hmlfb_:0.2f} hml={hml_:0.2f}")
    if hasNewBar or hml == []: # new bar or first bar
        fbhml_ = currentFullBar.high - currentFullBar.low
        # if hml and fbhml_ != hml[-1]:
        #     logger.warning(f"currentFullBar hml != hml[-1]: {currentFullBar} != {hml[-1]}")
        #     hml[-1] = currentFullBar.high - currentFullBar.low
        hml.append(hml_)
        # hml_pct.append(hml_ / prevclose)
    else:
        hml[-1] = hml_ # update the last element
        # hml_pct[-1] = hml_ / prevclose
    # lastPrice = get_market_price() # sample the market price # was bars[-1].close
    hmlstat.update(int(hml_*100.))
    logger.info(f"hml={hml[-1]:0.2f} mean={hmlstat.mean:0.3f} stddev={hmlstat.stddev():0.3f} quartiles={hmlstat.quartiles()}")

def onResampledBar(bars: List[BarData], hasNewBar: bool):
    logger.info(f"resampled[-1]={bars[-1]} hasNewBar={hasNewBar}")
    if hasNewBar:
        if len(bars) <= 1:
            logger.info("resampled[-2] is not available")
        else:
            logger.info(f"resampled[-2]={bars[-2]}") # the one just closed

# def resample(bars: List[BarData], b, n: int):
#     if b.date.minute % n == 0:
#         # resample to n minutes
#         bars.append(b)
#     else:
#         bars[-1].close = b.close
#         if b.high > bars[-1].high:
#             bars[-1].high = b.high
#         if b.low < bars[-1].low:
#             bars[-1].low = b.low
#         bars[-1].volume += b.volume

def onBarUpdate5s(bars: List[BarData], hasNewBar: bool):
    """
    bars: ohlcv every 5 seconds
    """
    logging.info("-"*40)
    msg = f"bars[-1]={bars[-1]}"
    if hasNewBar == False: # we don't expect False for 5s
        msg += " hasNewBar=False" # in case it happens, print warning
        logging.warning(msg)
    else:
        logging.info(msg)
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
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
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
    syms = args.symbols or ['SPY']
    useRTH = False # from 4:00am
    endDateTime = '' # datetime.datetime.now() + datetime.timedelta(days=-1)
    keepUpToDate = True
    for sym in syms:
        contract_ = Stock(sym, 'SMART', 'USD')
        temp = ib.reqContractDetails(contract_)
        if len(temp) == 0:
            logger.error(f"Contract details not found for {sym}")
            continue
        else:
            logger.info(f"Contract details {temp[0].contract}")
            contract_ = temp[0].contract
        logger.info(f"Requesting historical bars for {sym}...")
        if args.dryrun:
            continue

        global bars5s, bars1m
        bars5s = ib.reqHistoricalData(
                contract_,
                endDateTime=endDateTime,
                durationStr='1 D',
                barSizeSetting='5 secs',
                whatToShow='TRADES',
                useRTH=useRTH,
                keepUpToDate=keepUpToDate,
                formatDate=1)
        bars5s.updateEvent += b5s_resampler.__call__
        # bars5s.updateEvent += onBarUpdate5s

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
    
    if datetime.datetime.now().time() < datetime.time(16, 0, 0):
        ib.waitUntil(datetime.time(16, 2, 0))
    else:
        ib.sleep(3 * 60)

    # # compare with the real 1m bars
    # bars1m_real = ib.reqHistoricalData(
    #         contract_,
    #         endDateTime=endDateTime,
    #         durationStr='1 D',
    #         barSizeSetting='1 min',
    #         whatToShow='TRADES',
    #         useRTH=useRTH,
    #         keepUpToDate=keepUpToDate,
    #         formatDate=1)
    
    filename5s = f"./data/{sym}_5s_{dtnow:%y%m%d_%H%M}.csv"
    filename1m = f"./data/{sym}_1m_{dtnow:%y%m%d_%H%M}.csv"
    filename1m_resampled = f"./data/{sym}_resampled_{dtnow:%y%m%d_%H%M}.csv"
    bars5s_df = util.df(bars5s)
    bars1m_df = util.df(bars1m)
    resampled_df = util.df(resampled)
    bars5s_df.to_csv(filename5s, index=False)
    bars1m_df.to_csv(filename1m, index=False)
    if resampled_df is not None:
        resampled_df.to_csv(filename1m_resampled, index=False)
        buf = io.StringIO()
        resampled_df.info(buf=buf, verbose=True)
        logger.info(f"\n{buf}")
        logger.info(f"\n{resampled_df.describe().to_string()}")
    logger.info(f"Script done. Files saved to:\n{filename5s}\n{filename1m}\n{filename1m_resampled}")

    ib.disconnect()

    return # end of main

if __name__ == '__main__':
    main()
