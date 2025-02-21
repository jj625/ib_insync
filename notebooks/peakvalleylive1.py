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
from numpy.typing import NDArray
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

from ib_insync import IB, MarketOrder, LimitOrder, BarData, BarDataList, Stock, util

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

def _repr_bar(bar: BarData) -> str:
    if isinstance(bar.date, datetime.datetime):
        time_str = (r'%Y-%m-%d ' if bar.date.date() != datetime.date.today() else '') + ("%H:%M" if bar.date.second == 0 else "%H:%M:%S")
        d = bar.date.strftime(time_str)
    else:
        d = bar.date
    return f"[{d} o={bar.open_:.2f} h={bar.high:.2f} l={bar.low:.2f} c={bar.close:.2f} v={int(bar.volume)} a={bar.average:.3f} bc={bar.barCount:n}]"
BarData.__repr__ = _repr_bar

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

def onBarUpdate(bars: BarDataList, hasNewBar: bool):
    currentBar = bars[-1] # bar that is being built, never full
    currentFullBar = bars[-2:][0] # the most recent fully formed bar
    # logger.info(f"{hasNewBar} {currentBar} {currentFullBar}")
    if hasNewBar:
        logger.info(f"{currentBar.date:%H:%M:%S} {currentBar.average:.3f}") # {currentFullBar.date:%H:%M:%S} {currentFullBar.average:.3f}

        prev_avg, cur_avg, peak, valley = pkvl0.process_price(currentBar.average, currentBar.date)
        if peak:
            logger.info(f"0 peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
        if valley:
            logger.info(f"0 valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")

        prev_avg, cur_avg, peak, valley = pkvl0b.process_price(currentBar.average, currentBar.date)
        if peak:
            logger.info(f"0b peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
            p = pkvl0b.get_peaks()
            logger.info(f"0b p({len(p)}): {_repr_pkvl(p)}")
        if valley:
            logger.info(f"0b valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")
            v = pkvl0b.get_valleys()
            logger.info(f"0b v({len(v)}): {_repr_pkvl(v)}")

        prev_avg, cur_avg, peak, valley = pkvl1.process_price(currentBar.average, currentBar.date)
        if peak:
            logger.info(f"1 peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
        if valley:
            logger.info(f"1 valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")

        prev_avg, cur_avg, peak, valley = pkvl2.process_price(currentBar.average, currentBar.date)
        if peak:
            logger.info(f"2 peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
        if valley:
            logger.info(f"2 valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")

def _repr_pkvl(lst: list):
    res = []
    for pkvl in lst:
        res.append(f"{pkvl[0]:.2f} {pkvl[1]:%H:%M:%S}")
    return '[' + ', '.join(res) + ']'

def onHistDataEnd(start: str, end: str, bars: BarDataList):
    logger.info(f"start={start}, end={end}, len(bars)={len(bars)}")
    for bar in bars:
        logger.info(f"{bar.date:%H:%M:%S} {bar.average:.2f}")

        prev_avg, cur_avg, peak, valley = pkvl0.process_price(bar.average, bar.date)
        if peak:
            logger.info(f"0 peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
        if valley:
            logger.info(f"0 valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")

        prev_avg, cur_avg, peak, valley = pkvl0b.process_price(bar.average, bar.date)
        if peak:
            logger.info(f"0b peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
            logger.info(f"0b p: {_repr_pkvl(pkvl0b.get_peaks())}")
        if valley:
            logger.info(f"0b valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")
            logger.info(f"0b v: {_repr_pkvl(pkvl0b.get_valleys())}")

        prev_avg, cur_avg, peak, valley = pkvl1.process_price(bar.average, bar.date)
        if peak:
            logger.info(f"1 peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
        if valley:
            logger.info(f"1 valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")

        prev_avg, cur_avg, peak, valley = pkvl2.process_price(bar.average, bar.date)
        if peak:
            logger.info(f"2 peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
        if valley:
            logger.info(f"2 valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")

# function to convert timestamp to minute
def timestamp_to_minute(timestamp):
    return timestamp.hour * 60 + timestamp.minute


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

class PriceDetector:
    def __init__(self):
        self.prev_price = None
        self.current_price = None
        self.minutes = deque(maxlen=2)
        self.peak = None
        self.valley = None
        self.peaks = []
        self.valleys = []

    def process_price(self, price, minute):
        self.prev_price = self.current_price
        self.current_price = price
        self.minutes.append(minute)

        if self.prev_price is not None:
            if self.current_price > self.prev_price:
                # self._handle_price_increase(minute)
                if self.peak is None or self.current_price > self.peak[0]:
                    self.peak = (self.current_price, minute)
                if self.valley is not None:
                    self.valleys.append(self.valley)
                    self.valley = None
            elif self.current_price < self.prev_price:
                # self._handle_price_decrease(minute)
                if self.valley is None or self.current_price < self.valley[0]:
                    self.valley = (self.current_price, minute)
                if self.peak is not None:
                    self.peaks.append(self.peak)
                    self.peak = None
        
        return self.prev_price, self.current_price, self.peak, self.valley

    # def _handle_price_increase(self, minute):
    #     if self.peak is None or self.current_price > self.peak:
    #         self.peak = self.current_price
    #     if self.valley is not None:
    #         self.valleys.append((self.valley, minute))
    #         self.valley = None

    # def _handle_price_decrease(self, minute):
    #     if self.valley is None or self.current_price < self.valley:
    #         self.valley = self.current_price
    #     if self.peak is not None:
    #         self.peaks.append(self.peak)
    #         self.peak = None

    def get_peaks(self):
        return self.peaks

    def get_valleys(self):
        return self.valleys

class PD2(PriceDetector):
    def process_price(self, price, minute):
        prev_price, current_price, peak, valley = super().process_price(price, minute)

        if peak and not self.peaks:
            self.peaks.append(peak)
        elif peak and self.peaks and peak[0] >= self.peaks[-1][0]: # if higher peaks
            if len(self.minutes) > 1 and self.peaks[-1][1] == self.minutes[-2]:
                self.peaks.pop()
            self.peaks.append(peak)
        elif peak:
            self.peaks.append(peak)
        self.peak = None
        
        if valley and not self.valleys:
            self.valleys.append(valley)
        elif valley and self.valleys and valley[0] <= self.valleys[-1][0]: # if successively lower valleys
            if len(self.minutes) > 1 and self.valleys[-1][1] == self.minutes[-2]:
                self.valleys.pop()
            self.valleys.append(valley)
        elif valley:
            self.valleys.append(valley)
        self.valley = None
    
        return prev_price, current_price, peak, valley

class IntradayPeakValleyDetectorBase:
    def __init__(self, window_size=3, lag=2): # window_size=3, lag=2 yields the same behavior as PriceDetector()
        self.window_size = window_size
        self.lag = lag
        self.prices = []
        self.peaks = []
        self.valleys = []
        self.current_time = []

    def process_price(self, price, timestamp):
        raise NotImplementedError

    def get_peaks(self):
        return self.peaks

    def get_valleys(self):
        return self.valleys
    
    def get_results(self):
        return {
            'peaks': self.peaks,
            'valleys': self.valleys
        }

    def get_peaks_ts(self):
        return [(p, timestamp_to_minute(ts)) for p, ts in self.peaks]

    def get_valleys_ts(self):
        return [(v, timestamp_to_minute(ts)) for v, ts in self.valleys]

class IntradayPeakValleyDetector1(IntradayPeakValleyDetectorBase):
    def process_price(self, price, timestamp): # original method
        self.current_time.append(timestamp)
        prev_price = self.prices[-1] if self.prices else None
        self.prices.append(price)
        peak = valley = None

        if len(self.prices) >= self.window_size:
            # mid = self.window_size // 2
            mid = self.window_size - self.lag
            window = self.prices[-self.window_size:]
            mid_time = self.current_time[-self.window_size + mid]
            peak = valley = None

            if all(window[mid] > p for p in window[:mid]) and all(window[mid] > p for p in window[mid+1:]):
                peak = (window[mid], mid_time)
                self.peaks.append((window[mid], mid_time))
            elif all(window[mid] < p for p in window[:mid]) and all(window[mid] < p for p in window[mid+1:]):
                valley = (window[mid], mid_time)
                self.valleys.append((window[mid], mid_time))

            self.prices.pop(0)
            self.current_time.pop(0)

        return prev_price, price, peak, valley

class IntradayPeakValleyDetector1b(IntradayPeakValleyDetectorBase):
    def process_price(self, price, timestamp): # original method
        self.current_time.append(timestamp)
        prev_price = self.prices[-1] if self.prices else None
        self.prices.append(price)
        peak = valley = None

        if len(self.prices) >= self.window_size:
            # mid = self.window_size // 2
            mid = self.window_size - self.lag
            window = self.prices[-self.window_size:]
            mid_time = self.current_time[-self.window_size + mid]
            peak = valley = None

            if all(window[mid] > p for p in window[:mid]) and all(window[mid] > p for p in window[mid+1:]):
                peak = (window[mid], mid_time)
                self.peaks.append((window[mid], mid_time))
            elif all(window[mid] < p for p in window[:mid]) and all(window[mid] < p for p in window[mid+1:]):
                valley = (window[mid], mid_time)
                self.valleys.append((window[mid], mid_time))

            self.prices.pop(0)
            self.current_time.pop(0)

        return prev_price, price, peak, valley

class IntradayPeakValleyDetector2(IntradayPeakValleyDetectorBase):
    def __init__(self, window_size=3, lag=2, depth=1.): # window_size=3, lag=2 yields the same behavior as PriceDetector()
        super().__init__(window_size, lag)
        self.depth = depth

    def process_price(self, price, timestamp): # new method
        self.current_time.append(timestamp)
        prev_price = self.prices[-1] if self.prices else None
        self.prices.append(price) # keep full price history since beginning, irrespective of window size
        peak = valley = None

        # define "valley" as the lowest price in the window and "peak" as the highest price in the closed interval "window"
        # as we slide the window along the price history
        # if an end point is the lowest or highest, respectively, in the window, it should not be considered a valley or peak
        # in addition, if there is a local "valley" but not the lowest price in the interval, and the depth of the valley is
        # more than "depth" parameter from the surrounding prices, then it is considered a "valley"
        # the "lag" parameter is used to determine the position of the peak or valley in the window.
        # the fewest number of observations to the right of the sought feature is "lag". feature could in any position to the left
        # of "lag" in the window. record the price and timestamp of the peak or valley found in a set.
        if len(self.prices) >= self.window_size:
            window = self.prices[-self.window_size:]
            i = self.window_size - self.lag
            time_i = self.current_time[-self.window_size + i]
            peak = valley = None

            if window[i] == max(window): # and window[i] > max(window[:i]) + depth:
                peak = (window[i], self.current_time[-self.window_size + i])
                self.peaks.append(peak)
            elif window[i] == min(window) or (max(window) - window[i] >= self.depth and window[i] == min(window)):
                # logger.info(f"window: {window}, i: {i}, window[i]: {window[i]}, max: {max(window)}, min: {min(window)}")
                valley = (window[i], self.current_time[-self.window_size + i])
                self.valleys.append(valley)

            self.prices.pop(0)
            self.current_time.pop(0)

        return prev_price, price, peak, valley

class OnlineAnomalyDetector:
    def __init__(self, window_size=100, threshold=7):
        self.window_size = window_size
        self.threshold = threshold
        self.data_window = deque(maxlen=window_size)
        self.anomaly_count = deque(maxlen=window_size) # parallel to data_window
        # self.mean = np.zeros(4) # assume zero mean
        self.var = np.zeros(4) # sum of squares
        self.n = 0 # number of samples included in sum of squares

    def update_stats(self, diff: NDArray):
        self.n += 1
        if self.n == 1:
            # self.mean = diff
            self.var = np.zeros(4)
        else:
            # old_mean = self.mean.copy()
            # self.mean += (diff - old_mean) / self.n
            # self.var += (diff - old_mean) * (diff - self.mean)
            self.var += diff * diff

    def undo_update_stats(self, diff: NDArray):
        """
        Undo the update of stats for the previous data point because it was an anomaly
        """
        self.n -= 1
        if self.n == 0:
            self.var = np.zeros(4)
        else:
            self.var -= diff * diff

    def detect_anomaly(self, current_data, /, update_stats=True):
        if len(self.data_window) < 2:
            self.data_window.append(current_data)
            return False, []

        self.prev_data = prev_data = self.data_window[-1]
        diff = np.array(current_data) - np.array(prev_data)

        self.update_stats(diff)

        if self.n > 1:
            masked_var = np.ma.masked_values(self.var, 0.) # ignore zero variance
            std_dev = np.sqrt(masked_var / (self.n - 1))
            # print(f"std_dev: {std_dev.data}, abs diff: {np.abs(diff)}")
            # z_scores = np.abs(diff - self.mean) / std_dev
            z_scores = np.abs(diff) / std_dev

            anomalies = np.where(z_scores > self.threshold)[0]
            is_anomaly = len(anomalies) > 0
            if is_anomaly:
                self.undo_update_stats(diff)
                # print(f"Anomaly detected: {current_data}")
                # print(f"Mean: {self.mean}, Std Dev: {std_dev}")
                print(f"Diff: {diff}, std_dev: {std_dev.data}, z_scores: {z_scores.data}")
                # print(f"Anomalies: {anomalies}")

            self.data_window.append(current_data)
            return is_anomaly, anomalies
        else:
            self.data_window.append(current_data)
            return False, []
    
    def get_prev_data(self):
        return self.prev_data

    def process_data_point(self, data_point, /, index: Optional[pd.Timestamp|datetime.datetime]=None, update_stats=True):
        is_anomaly, anomalous_features = self.detect_anomaly(data_point, update_stats)
        if is_anomaly and (index is None or index.time() >= datetime.time(9, 30)):
            feature_names = ['Open', 'High', 'Low', 'Close']
            anomalous_features = [feature_names[i] for i in anomalous_features]
            logger.info(f"Anomaly detected in: {', '.join(anomalous_features)}")
            logger.info(f"Data point: {data_point}" + (f" (index: {index})" if index is not None else ""))
            logger.info(f"Previous data point: {self.prev_data}")
        return is_anomaly

def main():
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    filesuffix = f'_{datetime.datetime.now():%y%m%d_%H%M}'
    log_file = os.path.join(scriptdir, 'logs', f'{program_name}_{filesuffix}.log')

    # Initial logging setup
    # Set up logging to file and console
    logging.basicConfig(
        level=logging.INFO,
        format=('%(asctime)s:%(levelname)s:%(funcName)s:%(message)s'), #  + logging.BASIC_FORMAT
        # handlers=[
        #     logging.FileHandler(log_file),
        #     #RichHandler(markup=True)
        #     logging.StreamHandler()
        # ]
    )

    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, default=['NVDA'], help='Just run for this symbol(s)') # nargs='+' means one or more
    # argparser.add_argument('numshares', type=int, nargs='?', help='Number of shares to trade')
    # argparser.add_argument('maxloss', type=float, nargs='?', help='Max loss threshold')
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID. Default is random between 1k and 10k.')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
    argparser.add_argument('--enddate', type=datetime.datetime.fromisoformat, help='End date')
    argparser.add_argument('--barsize', type=str, default='15 secs', help='Bar size')
    argparser.add_argument('--windowsize', type=int, default=5, help='Window size for peak-valley detection')
    argparser.add_argument('--lag', type=int, default=2, help='Lag for peak-valley detection')
    argparser.add_argument('--usecache', action='store_true', help='Use cached data')

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

    global pkvl0, pkvl1, pkvl2
    global pkvl0b
    pkvl0 = PriceDetector()
    pkvl0b = PD2()
    pkvl1 = IntradayPeakValleyDetector1(window_size=args.windowsize, lag=args.lag)
    pkvl2 = IntradayPeakValleyDetector2(window_size=args.windowsize, lag=args.lag)

    dtnow = datetime.datetime.now()
    cachefilename = f'data/{args.symbols[0]}_{args.barsize.replace(' ', '_')}_data_{dtnow:%y%m%d}.pkl'
    logger.info(f"Cache file: {cachefilename}")

    global bars1m

    if args.usecache and os.path.exists(cachefilename):
        logger.info("Using cached data...")
        with open(cachefilename, 'rb') as f:
            data = pickle.load(f)
            logger.info(f"Loaded {len(data)} symbols")
            ekHistDataInitEnd = eventkit.Event('barsInitEnd')
            ekHistDataInitEnd += onHistDataEnd
            ekHistData = eventkit.Event('bars')
            ekHistData += onBarUpdate
            bars1m = BarDataList()
            for sym, bars in data.items():
                logger.info(f"Processing {sym}...")
                for bar in bars:
                    bars1m.append(bar)
                    ekHistData.emit(bars1m, True)
                    # prev_avg, cur_avg, peak, valley = pkvl2.process_price(bar.average, bar.date, method=2)
                    # if peak:
                    #     logger.info(f"peak detected: {peak[0]:.2f} {peak[1]:%H:%M:%S}")
                    # if valley:
                    #     logger.info(f"valley detected: {valley[0]:.2f} {valley[1]:%H:%M:%S}")
        logger.info("Done processing cached data.")
        return
    
    elif args.usecache and not os.path.exists(cachefilename):
        logger.info(f"Cache file {cachefilename} not found.")
        return

    # Connect to IB Gateway
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))
    # ib.errorEvent += onError

    syms = args.symbols or ['NVDA']
    useRTH = True # from 4:00am
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

        bars1m = ib.reqHistoricalDataExt(
                contract_,
                endDateTime=endDateTime,
                durationStr='1 D',
                barSizeSetting=args.barsize,
                whatToShow='TRADES',
                useRTH=useRTH,
                keepUpToDate=keepUpToDate,
                formatDate=1,
                _historicalDataEndHook=onHistDataEnd,
                )
        bars1m.updateEvent += onBarUpdate
        logger.info(f"{len(bars1m)} bars1m downloaded")
    
    if datetime.datetime.now().time() < datetime.time(16, 0, 0):
        logger.info("Waiting until 4:02pm...")
        ib.waitUntil(datetime.time(16, 2, 0))
    else:
        logger.info("Waiting 1 minute...")
        ib.sleep(1 * 60)

    # write to cache so we can use it next time
    with open(cachefilename, 'wb') as f:
        data = {sym: bars1m for sym in syms}
        pickle.dump(data, f)
        logger.info(f"Saved {len(data)} symbols to cache")

    logger.info(f"Script done.")

    ib.disconnect()

    return # end of main

if __name__ == '__main__':
    main()
