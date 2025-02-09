import sys
import copy
import platform
computername = platform.node()
import contextlib
import pickle
import inspect
import asyncio
def get_asyncio_running_loop(prefix: str = '') -> str:
    try:
        running_loop = asyncio.get_running_loop()
        result = f"{prefix} asyncio.get_running_loop() -> {running_loop} ({id(running_loop)})"
    except Exception as e:
        result = f"{prefix} asyncio.get_running_loop() -> {e}"
    return result

# print(get_asyncio_running_loop('0. '))
import ibapi
import pandas as pd
import numpy as np
from numpy.typing import NDArray
np_pct = {'float_kind': lambda x: f"{x:.2%}"} # pass to np.array2string as formatter
import scipy.optimize
np.set_printoptions(linewidth=150, precision=2, suppress=True)
import scipy
from scipy.ndimage import gaussian_filter1d, minimum_filter1d, maximum_filter1d
import math
import logging
import datetime
import zoneinfo
tz_ny = local_tz = zoneinfo.ZoneInfo('US/Eastern')  # Adjust for your local timezone, America/New_York

# NYMKTOPEN = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9, 30), tzinfo=tz_ny)
MKTOPEN = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9, 30), tzinfo=tz_ny)
# PDMKTOPEN = pd.to_datetime(MKTOPEN)
NPMKTOPEN = np.datetime64(MKTOPEN.replace(tzinfo=None), 's')
# NPMKTOPENIDX = -1
# NYMKTCLOSE = datetime.datetime.combine(datetime.datetime.today(), datetime.time(16, 0), tzinfo=tz_ny)
MKTCLOSE = datetime.datetime.combine(datetime.datetime.today(), datetime.time(16, 0), tzinfo=tz_ny)
# PDMKTCLOSE = pd.to_datetime(MKTCLOSE)
NPMKTCLOSE = np.datetime64(MKTCLOSE.replace(tzinfo=None), 's')

def set_market_hours(start, end):
    # global NYMKTOPEN, MKTOPEN, PDMKTOPEN, NPMKTOPEN, NYMKTCLOSE, MKTCLOSE, PDMKTCLOSE, NPMKTCLOSE
    global MKTOPEN, NPMKTOPEN, MKTCLOSE, NPMKTCLOSE

    # NYMKTOPEN = start.astimezone()
    MKTOPEN = start.astimezone()
    # PDMKTOPEN = pd.to_datetime(MKTOPEN)
    NPMKTOPEN = np.datetime64(MKTOPEN.replace(tzinfo=None), 's')

    # NYMKTCLOSE = end.astimezone()
    MKTCLOSE = end.astimezone()
    # PDMKTCLOSE = pd.to_datetime(MKTCLOSE)
    NPMKTCLOSE = np.datetime64(MKTCLOSE.replace(tzinfo=None), 's')
    logger.info(f"Market hours set to {MKTOPEN.astimezone()} - {MKTCLOSE.astimezone()}")

    # util.NYMKTOPEN = NYMKTOPEN
    util.MKTOPEN = MKTOPEN # for compatibility
    # util.NYNPMKTOPEN = np.datetime64(MKTOPEN.replace(tzinfo=None), 's')
    util.NPMKTOPEN = np.datetime64(MKTOPEN.replace(tzinfo=None), 's')
    # util.NYMKTCLOSE = NYMKTCLOSE
    # util.MKTOPEN = NYMKTOPEN
    util.MKTCLOSE = MKTCLOSE
    # util.NYNPMKTCLOSE = np.datetime64(MKTCLOSE.replace(tzinfo=None), 's')
    util.NPMKTCLOSE = np.datetime64(MKTCLOSE.replace(tzinfo=None), 's')

def get_market_hours():
    return MKTOPEN, MKTCLOSE

import dateutil
import argparse
import json
from collections import defaultdict, deque
from itertools import islice, pairwise
from more_itertools import windowed
from dataclasses import dataclass, field
from typing import List, Optional
import typing
from typing import Iterable
import numbers
# import pdb
import telegram
if telegram.__version__ < '20.0':
    print("Requires python-telegram-bot library version 20.0 or higher")
    sys.exit(1)

from concurrent.futures import ThreadPoolExecutor
# import pytz
# local_tz = pytz.timezone('US/Eastern')  # Adjust for your local timezone, America/New_York

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
mpl_dir = pathlib.Path('../../eventkit').resolve()
if mpl_dir.exists() and mpl_dir.is_dir() and str(mpl_dir) not in sys.path:
    sys.path.insert(0, str(mpl_dir))
    mpl_dir
elif not mpl_dir.exists():
    print(f"Expected {mpl_dir} does not exist")

import eventkit
import ib_insync
import ib_insync.ib
ib_insync.ib.install_custom_repr_()
from ib_insync.ib import _execution_repr, _fill_repr

from ib_insync import IB, MarketOrder, LimitOrder, Trade, Fill, CommissionReport, BarData, BarDataList, \
    Stock, Option, Future, Forex, MutualFund, util, PortfolioItem, Ticker, \
    Execution, ExecutionFilter, ExecutionCondition

# probe for numpy support
probe = BarDataList()
if not hasattr(probe, '_init_npdata'):
    print("ib_insync.BarDataList does not have numpy extension")
    sys.exit(1)

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
# import matplotlib.ticker as mticker
# import matplotlib.colors as mcolors
# import matplotlib.cm as cm
# import matplotlib.patches as mpatches
# import matplotlib.lines as mlines
# import matplotlib.transforms as mtransforms
# import matplotlib.collections as mcollections
# import matplotlib.path as mpath

search_paths = ['../../filterpy', '../../../filterpy']
for p in search_paths:
    potential_dir = pathlib.Path(p).resolve()
    if potential_dir.exists() and potential_dir.is_dir() and str(potential_dir) not in sys.path:
        sys.path.insert(0, str(potential_dir))
        print(f"{potential_dir} added to sys.path")
        break
else:
    print(f"Expected {mpl_dir} does not exist")
import filterpy
from filterpy.kalman import KalmanFilter, UnscentedKalmanFilter, JulierSigmaPoints, unscented_transform, MerweScaledSigmaPoints, IMMEstimator
from filterpy.common import Q_discrete_white_noise, Q_continuous_white_noise, Saver

def make_ca_filter(dt, std_R):
    cafilter = KalmanFilter(dim_x=3, dim_z=1)
    # cafilter.x = np.array([0., 0., 0.])
    cafilter.P *= 3
    cafilter.R *= std_R*std_R
    cafilter.Q = Q_discrete_white_noise(dim=3, dt=dt, var=0.02)
    cafilter.F = np.array([[1, dt, 0.5*dt*dt],
                           [0, 1,         dt], 
                           [0, 0,          1]])
    cafilter.H = np.array([[1., 0, 0]])
    return cafilter

# # asyncio
# # asyncio.run() cannot be nested
# # get_event_loop() is deprecated in Python 3.12
# # get_running_loop() is preferred to get_event_loop() in callbacks (and coro?)
# def run_asyncio_task(task):
#     try:
#         loop = asyncio.get_running_loop()
#     except RuntimeError:  # No running event loop
#         loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(loop)
#         loop.run_until_complete(task)
#     else:
#         loop.run_until_complete(task)

# def run_asyncio_task_in_foreground(task):
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(task)

# def run_asyncio_task_in_background(task):
#     loop = asyncio.get_event_loop()
#     loop.create_task(task)

# Get the program's file name without the extension 
program_name = os.path.splitext(os.path.basename(__file__))[0] 
scriptdir = os.path.dirname(os.path.realpath(__file__))

# hold strong references to tasks. remember to remove them when done
background_tasks: set[asyncio.Task] = set()

# globals
ib: IB = None
logger: logging.Logger = None
h5store: pd.HDFStore = None
fpkl: typing.BinaryIO = None

TELEGRAM_TOKEN = os.environ.get('TELEGRAMTOKEN', '')
telegram_bot = telegram.Bot(TELEGRAM_TOKEN)
telegram_tasks = set() # hold strong references to tasks
TELEGRAM_CHAT_ID = '5215848738'

import traceback

def fmt_elapsed_time(elapsed_time: float) -> str:
    if elapsed_time >= 1:
        s = f"{elapsed_time:.2f} s"
    elif elapsed_time >= 1e-3:
        s = f"{elapsed_time * 1e3:.2f} ms"
    elif elapsed_time >= 1e-6:
        s = f"{elapsed_time * 1e6:.2f} µs"
    else:
        s = f"{elapsed_time * 1e9:.2f} ns"
    return s

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

    def print_result(func, args, execution_time, printfn=print):
        if inspect.ismethod(func):
            func_name = f"{func.__self__.__class__.__name__}.{func.__name__}"
        elif args and hasattr(args[0].__class__, func.__name__):
            func_name = f"{args[0].__class__.__name__}.{func.__name__}"
        else:
            func_name = func.__name__

        printfn(f"{'Coroutine' if asyncio.iscoroutinefunction(func) else 'Function'} "
              f"'{func_name}' took {fmt_elapsed_time(execution_time)} to execute.")

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

from scipy.stats import skew, kurtosis, mode
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

class OnlineDeque:
    def __init__(self, qlen=1000):
        self.n = 0
        self.mean = 0.0
        self.M2 = 0.0
        self.deq = deque(maxlen=qlen)  # Keep a limited history for mode, quartiles, and deciles

    def update(self, x: numbers.Real):
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.M2 += delta * delta2
        self.values.append(x)

# async def send_telegram_message_async(text):
#     # bot = Bot(token='YOUR_BOT_TOKEN')
#     return await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

# def send_telegram_message(text):
#     util.run(send_telegram_message_async(text))
#     # task = asyncio.create_task(send_telegram_message_async(text))
#     # telegram_tasks.add(task)
#     # task.add_done_callback(telegram_tasks.discard)

def send_telegram_message(chat_id: str, text: str):
    # https://github.com/python/cpython/issues/104091
    # https://superfastpython.com/asyncio-task-exceptions/
    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(telegram_bot.send_message(chat_id=chat_id, text=text))
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)
        exception = task.exception()
    except Exception as e:
        logger.error(f"Failed to send telegram message: {e}")
        logger.error(traceback.format_exc())

# def run_async_task(chat_id, text):
#     loop = asyncio.get_event_loop()
#     asyncio.run_coroutine_threadsafe(send_telegram_message(chat_id, text), loop)

# # Example usage
# if __name__ == "__main__":
#     chat_id = 'YOUR_CHAT_ID'
#     text = 'Hello, this is an asynchronous message!'
#     executor = ThreadPoolExecutor()
#     executor.submit(run_async_task, chat_id, text)

def almost_zero_vector(v: NDArray, tol: float = 0.0001) -> tuple[bool, float]:
    norm = np.linalg.norm(v)
    return (np.all(np.abs(v) < tol), norm)

def extract_field_as_list(group: Iterable, field_name: str) -> list:
    return [getattr(item, field_name) for item in group]

def extract_field_as_array(group: Iterable, field_name: str) -> NDArray:
    return np.asarray(extract_field_as_list(group, field_name))

def slice_deque(dq: deque, start=None, end=None) -> list:
    length = len(dq)
    if length == 0:
        return []
    
    if start is None:
        start = 0
    elif start < 0:
        start += length
    
    if end is None:
        end = length
    elif end < 0:
        end += length
    
    start = max(0, min(start, length))
    end = max(0, min(end, length))
    
    return list(islice(dq, start, end))

def custom_formatter(value):
    if isinstance(value, (bool, int, float, str, bytes)):
        return str(value)
    if isinstance(value, datetime.datetime):
        value_local = value.astimezone()  # Convert to local time
        if value_local.date() == datetime.datetime.now(local_tz).date():
            return value_local.strftime('%H:%M:%S')
        else:
            return value_local.strftime(r'%Y-%m-%d %H:%M:%S %Z')
    elif isinstance(value, list):
        return '[' + ", ".join([custom_formatter(v) for v in value]) + ']'
    elif isinstance(value, dict):
        return {k: custom_formatter(v) for k, v in value.items()}
    # elif util.isnamedtupleinstance(value):
    #     return {f: custom_formatter(getattr(value, f)) for f in value._fields}
    # elif util.is_dataclass(value):
    #     return {value.__class__.__qualname__: custom_formatter(util.dataclassNonDefaults(value))}
    else:
        # logger.warning(f"Unknown type: {type(value)}")
        return str(value)

def format_dict(d: dict) -> str:
    return '{' + ", ".join(f"{k}: {custom_formatter(v)}" for k, v in d.items()) + '}'

def _repr_vol_tup(vol_tup: tuple) -> str:
    return f"({vol_tup[0]:.3%} {vol_tup[1]:.3%} {vol_tup[2]:.3%})"
def _repr_vol_tup_lst(vol_tup_lst: list) -> str:
    return '[' + ', '.join([_repr_vol_tup(vol_tup) for vol_tup in vol_tup_lst]) + ']' # if vol_tup_lst else '[]'

def _repr_bar(bar: BarData) -> str:
    return f"[{bar.date:%H:%M} o={bar.open_:.2f} h={bar.high:.2f} l={bar.low:.2f} c={bar.close:.2f} v={int(bar.volume):_} a={bar.average:.2f} bc={bar.barCount:n}]"
def _repr_barlist(bars: BarDataList) -> str:
    return ', '.join([_repr_bar(bar) for bar in bars])
def _repr_hilopcttup(hilotup: tuple) -> str:
    return f"({hilotup[0]:.2%}, {hilotup[1]:.2%}, {hilotup[2]:.2%}, {hilotup[3]:.2%}, {hilotup[4]:%H:%M})"
def _repr_hilopctbd(hilobd: BarData) -> str:
    return f"({hilobd.average:.2%}, {hilobd.high:.2%}, {hilobd.low:.2%}, {hilobd.close:.2%}, {hilobd.date:%H:%M})"
def _repr_hilopctlst(hilopctlst: list) -> str:
    if hilopctlst:
        if type(hilopctlst[0]) == tuple:
            return '[' + ', '.join([_repr_hilopcttup(hilotup) for hilotup in hilopctlst]) + ']'
        elif type(hilopctlst[0]) == BarData:
            return '[' + ', '.join([_repr_hilopctbd(pct) for pct in hilopctlst]) + ']'
        else:
            return '[' + ', '.join([str(x) for x in hilopctlst]) + ']'

def is_integer(value: numbers.Real) -> bool:
    return value == int(value)

def format_value(value: numbers.Real, intexpected: bool = False) -> str:
    """
    Format a float value to 2 decimal places if it has a decimal part, otherwise to 0 decimal places
    intexpected: if True means we're expecting an integer value
    """
    if not isinstance(value, int) and intexpected and not is_integer(value):
        logger.warning(f"Expected integer value, got {value}")
    return f"{value:.2f}" if value % 1 != 0 else f"{value:.0f}"

def plus(num: numbers.Real) -> numbers.Real:
    """Return the positive part of the number"""
    return max(0, num)

def neg(num: numbers.Real) -> numbers.Real:
    """Return the negative part of the number"""
    return min(0, num)

def last_business_dt() -> datetime.date:
    """Return the last business date"""
    today = datetime.datetime.now(local_tz).date() + datetime.timedelta(days=0)
    # before 9:30am, use previous business day
    if datetime.datetime.now(local_tz).time() < datetime.time(16, 0):
        today -= datetime.timedelta(days=1)
    # if today is Saturday or Sunday, use Friday
    while today.weekday() >= 5:  # Saturday or Sunday
        today -= datetime.timedelta(days=1)
    return today
    # if today.weekday() == 0: # Monday
    #     return today + datetime.timedelta(days=-3)
    # else:
    #     return today + datetime.timedelta(days=-1)

class TradeManager:
    def __init__(self, trade: Trade):
        self.trade = trade
        self.trade.statusEvent += self.on_status_event
        self.trade.modifyEvent += self.on_modify_event
        self.trade.fillEvent += self.on_fill_event
        self.trade.commissionReportEvent += self.on_commission_report_event
        self.trade.filledEvent += self.on_filled_event
        self.trade.cancelEvent += self.on_cancel_event
        self.trade.cancelledEvent += self.on_cancelled_event
        self.ok2clear = False
        self.lastErrorCode = 0

    def clear(self):
        if not self.ok2clear:
            logger.error("Trade is not done yet, please check")
            return
        self.trade.statusEvent -= self.on_status_event
        self.trade.modifyEvent -= self.on_modify_event
        self.trade.fillEvent -= self.on_fill_event
        self.trade.commissionReportEvent -= self.on_commission_report_event
        self.trade.filledEvent -= self.on_filled_event
        self.trade.cancelEvent -= self.on_cancel_event
        self.trade.cancelledEvent -= self.on_cancelled_event
        self.trade = None

    def __call__(self):
        return self.trade

    def place_order(self, order: ib_insync.order.Order, ib: IB):
        ib.placeOrder(self.trade.contract, self.trade.order)
        return self.trade

    def on_status_event(self, trade: Trade):
        # logger.info(f"{trade}")
        if trade.isDone() or trade.remaining() == 0:
            self.ok2clear = True
            logger.info(f"Trade is done, orderStatus.status={trade.orderStatus.status}")

    def on_modify_event(self, trade: Trade):
        logger.info(f"{trade}")

    def on_fill_event(self, trade: Trade, fill: Fill):
        # logger.info(f"{trade}, {fill}")
        if trade.isDone() or trade.remaining() == 0:
            self.ok2clear = True
            logger.info(f"Trade is done, orderStatus.status={trade.orderStatus.status}, fill={fill}")
        else:
            logger.info(f"Trade is not done yet, orderStatus.status={trade.orderStatus.status}")

    def on_commission_report_event(self, trade: Trade, fill: Fill, report: CommissionReport):
        logger.info(f"{trade}, {fill}, {report}")

    def on_filled_event(self, trade: Trade):
        # logger.info(f"{trade}")
        if trade.isDone() or trade.remaining() == 0:
            self.ok2clear = True
            logger.info(f"Trade is done, orderStatus.status={trade.orderStatus.status}, trade.fills={trade.fills}")
        else:
            logger.info(f"Trade is not done yet, orderStatus.status={trade.orderStatus.status}")

    def on_cancel_event(self, trade: Trade):
        logger.info(f"{trade}")

    def on_cancelled_event(self, trade: Trade):
        if trade.orderStatus.status == 'Cancelled':
            if trade.log and trade.log[-1].status == 'Cancelled' and trade.log[-1].errorCode in {451,460}:
                # 460=no trading permissions
                # 451=order exceeds the Total Value Limit of 100,000 USD. Restriction is specified in Precautionary Settings of Global Configuration/Presets.
                self.lastErrorCode = trade.log[-1].errorCode
            else:
                self.lastErrorCode = 999
                logger.info(f"unknown error code: {trade.log[-1].errorCode}")
        logger.info(f"{trade}")

# Function to flatten the trade structure
def flatten_trade(trade: ib_insync.order.Trade):
    trade_dict = {
        'contract_symbol': trade.contract.symbol,
        'contract_secType': trade.contract.secType,
        'contract_exchange': trade.contract.exchange,
        'contract_currency': trade.contract.currency,
        'order_action': trade.order.action,
        # 'order_totalQuantity': trade.order.totalQuantity,
        'order_orderType': trade.order.orderType,
        'order_lmtPrice': trade.order.lmtPrice,
        # 'order_auxPrice': trade.order.auxPrice,
        # 'order_tif': trade.order.tif,
        # 'order_status': trade.orderStatus.status,
        # 'order_filled': trade.orderStatus.filled,
        # 'order_remaining': trade.orderStatus.remaining,
        # 'order_avgFillPrice': trade.orderStatus.avgFillPrice,
        # 'order_lastFillPrice': trade.orderStatus.lastFillPrice,
        'order_permId': trade.order.permId,
        # 'order_clientId': trade.order.clientId,
        # 'order_orderId': trade.order.orderId,
        # 'order_parentId': trade.order.parentId,
        # 'order_whyHeld': trade.orderStatus.whyHeld,
        # 'order_mktCapPrice': trade.orderStatus.mktCapPrice
    }
    return trade_dict

# Function to flatten the fill structure
def flatten_fill(fill: ib_insync.objects.Fill):
    fill_dict = {
        'exec_execId': fill.execution.execId,
        'exec_time': fill.execution.time.astimezone(),
        'exec_acctNumber': fill.execution.acctNumber,
        'exec_exchange': fill.execution.exchange,
        'exec_side': fill.execution.side,
        'exec_shares': fill.execution.shares,
        'exec_price': fill.execution.price,
        'exec_permId': fill.execution.permId,
        # 'exec_clientId': fill.execution.clientId,
        'exec_orderId': fill.execution.orderId,
        'exec_liquidation': fill.execution.liquidation,
        'exec_cumQty': fill.execution.cumQty,
        'exec_avgPrice': fill.execution.avgPrice,
        'exec_orderRef': fill.execution.orderRef,
        # 'exec_evRule': fill.execution.evRule,
        # 'exec_evMultiplier': fill.execution.evMultiplier,
        'commission_report_commission': fill.commissionReport.commission,
        'commission_report_currency': fill.commissionReport.currency,
        'commission_report_realizedPNL': fill.commissionReport.realizedPNL,
        # 'commission_report_yield': fill.commissionReport.yield_,
        # 'commission_report_yieldRedemptionDate': fill.commissionReport.yieldRedemptionDate
    }
    return fill_dict

def ibtrades_to_df(trades: list[ib_insync.order.Trade]) -> pd.DataFrame:
    if trades is None or len(trades) == 0:
        trades = ib.trades()

    # Flatten all trades and fills
    flattened_trades = [flatten_trade(trade) for trade in trades]
    flattened_fills = [flatten_fill(fill) for trade in trades for fill in trade.fills]

    # Create hierarchical pandas DataFrames
    df_trades = pd.DataFrame(flattened_trades)
    df_fills = pd.DataFrame(flattened_fills)

    # Merge trades and fills DataFrames
    df_merged = pd.merge(df_trades, df_fills, left_on='order_permId', right_on='exec_permId', how='outer')
    return df_merged

def last_5m_hml(bars: BarDataList) -> NDArray[np.float64]:
    """high minus low for the last 5 bars"""
    return np.array([bar.high - bar.low for bar in bars[-5:]])

def get_mid_price() -> float:
    return ib.tickers()[0].midpoint()

def get_market_price() -> float:
    t = ib.tickers()[0]
    mktprice = t.marketPrice()
    if mktprice is None or np.isnan(mktprice) or mktprice <= 0:
        # if market price is not available, use close price
        if t.close is None or np.isnan(t.close) or t.close <= 0:
            # if close price is not available, use bars[-1].close
            # TODO implement this
            return 0
        else:
            return t.close
    else:
        return mktprice

def get_bid_price() -> float:
    t = ib.tickers()[0]
    if t.bid is None or np.isnan(t.bid) or t.bid <= 0:
        # if bid is not available, use market price
        return get_market_price()
    else:
        return t.bid

def get_ask_price() -> float:
    return ib.tickers()[0].ask

def average_price(trade: ib_insync.order.Trade) -> float:
    return sum(fill.execution.price * fill.execution.shares for fill in trade.fills) / sum(fill.execution.shares for fill in trade.fills)

def max_exec_time(trade: ib_insync.order.Trade) -> datetime.datetime:
    return max(fill.execution.time for fill in trade.fills)

def trade_commision(trade: ib_insync.order.Trade) -> float:
    return sum(fill.commissionReport.commission for fill in trade.fills)

def trade_realized_pnl(trade: ib_insync.order.Trade) -> float:
    return sum(fill.commissionReport.realizedPNL for fill in trade.fills)

def parse_hours(hours_str: str, timeZoneId: str) -> list[dict]:
    hours_list = []
    tz = zoneinfo.ZoneInfo(timeZoneId)
    for period in hours_str.split(';'):
        t = period.split(':')
        z = period.split('-')
        # print(f"t {t}, z {z}")
        if len(t) == 2 and len(z) == 1:
            if t[1] == 'CLOSED':
                # date_start = date_end = t[0]
                date_start = date_end = datetime.datetime.strptime(t[0], r'%Y%m%d').date()
                hour_start = hour_end = None
                hours_list.append({
                    'period_str': period,
                    'date_start': date_start,
                    'start_trading_hour': None,
                    'date_end': date_end,
                    'end_trading_hour': None,
                    'is_closed': True,
                    'is_error': False
                })
            else:
                hours_list.append({'period_str': period, 'is_error': True})
                # print("format unknown: {period}")
        elif len(t) == 3 and len(z) == 2:
            date_start, hour_start = z[0].split(':')
            date_end, hour_end = z[1].split(':')
            date_start = datetime.datetime.strptime(date_start, r'%Y%m%d').date()
            hour_start = datetime.datetime.strptime(hour_start, r'%H%M').time()
            date_end = datetime.datetime.strptime(date_end, r'%Y%m%d').date()
            hour_end = datetime.datetime.strptime(hour_end, r'%H%M').time()
            hours_list.append({
                'period_str': period,
                'date_start': date_start,
                'start_trading_hour': datetime.datetime.combine(date_start, hour_start, tz),
                'date_end': date_end,
                'end_trading_hour': datetime.datetime.combine(date_end, hour_end, tz),
                'is_closed': False,
                'is_error': False
            })
        else:
            hours_list.append({'period_str': period, 'is_error': True})
            # print("format unknown: {period}")
    return hours_list

# https://dynamiproject.wordpress.com/wp-content/uploads/2016/01/measuring_historic_volatility.pdf

np_log_2 = np.log(2)
tnpln2m1 = 2 * np_log_2 - 1

def parkinson_volatility(high, low, n):
    return np.sqrt(1 / (4 * np_log_2) * np.sum(np.log(high / low)**2) / n)

def garman_klass_volatility(open_, high, low, close, n):
    return np.sqrt(np.sum(0.5 * np.log(high / low)**2 - tnpln2m1 * np.log(close / open_)**2) / n)

def rogers_satchell_volatility(open_, high, low, close, n):
    return np.sqrt(np.sum((np.log(high / open_) * np.log(high / close) + np.log(low / open_) * np.log(low / close)) / n))

def yang_zhang_volatility(open_, high, low, close, n):
    return np.sqrt(0.511 * np.log(high / low)**2 - 0.019 * np.log(close / open_)**2 + 0.386 * np.log(close / open_) * np.log(high / low))

# Annualize volatilities (assuming 252 trading days and 1440 minutes per day)
# annualization_factor = np.sqrt(252 * 1440)
# annualization_factor_252 = np.sqrt(252)
annualization_factor_252_390 = np.sqrt(252 * 390) # 1y = 252d * 390m
annualization_factor_390 = np.sqrt(390) # 1d = 390m
annualization_factor_5_390 = np.sqrt(5 * 390) # 1w = 5d * 390m
annualization_factor_21_390 = np.sqrt(21 * 390) # 1m = 21d * 390m

# class BarDataResampler():
#     def __init__(self, m, n):
#         self._logger = logging.getLogger(__name__)
#         self.first_call = True
#         self.resampled: BarDataList = [] # resampled 1m bars
#         self.m = m
#         self.n = n # number of bars to aggregate
#         self.mult = n // m
#         self.updateEvent = eventkit.Event('BarDataResampler.updateEvent')

#     def __call__(self, bars: BarDataList, hasNewBar: bool):
#         # this is the main entry point for the resampler
#         if self.first_call:
#             self.first_call = False
#             self.onFirstCall(bars, hasNewBar)
#         self.onBarUpdate(bars, hasNewBar)

#     def onFirstCall(self, bars: BarDataList, hasNewBar: bool):
#         logger.info(f"bars[-1]={bars[-1]} hasNewBar={hasNewBar}")
#         # for b in bars:
    
#     def initialize(self, bars: BarDataList):
#         logger.info(f"len(bars)={len(bars)}, len(resampled)={len(self.resampled)}")
#         for b in bars:
#             self.resampler([b], True, method='init_1m_5m')
#         logger.info(f"len(resampled)={len(self.resampled)}")

#     def onBarUpdate(self, bars: BarDataList, hasNewBar: bool):
#         r, h = self.resampler(bars, hasNewBar)
#         return # end of onBarUpdate

#     def resampler(self, inBars: BarDataList, inBarHasNewBar: bool, method=''):
#         """
#         we don't need hasNewBar because 5s bars are always complete
#         inBars: 5s bars
#         outBars: 1m bars
#         """
#         outBars = self.resampled
#         outBarsHasNewBar = False
#         z = inBars[-1]
#         b: BarData = BarData(z.date, z.open_, z.high, z.low, z.close
#             , z.volume, z.average, z.barCount) # make sure b is a copy so we don't inadvertently change bar5s
#         # logger.info(f"{inBars[-1]} hasNewBar={hasNewBar}")
#         logger.debug(f"{b.date.minute} hasNewBar={inBarHasNewBar}")
#         atTopMinute = b.date.second % 60 == 0
#         atMultiple = b.date.minute % self.mult == 0 # at the top of the minute
#         # assert atTopMinute == inBarHasNewBar, f"atTopMinute={atTopMinute}, inBarHasNewBar={inBarHasNewBar}"
#         if (atTopMinute and atMultiple and inBarHasNewBar) or outBars == []:
#             # resample to 60 seconds/1 min
#             if atTopMinute and outBars:
#                 logger.debug(f"outBars[-2]={outBars[-1]}") # the one just closed
#             outBars.append(b)
#             assert b == outBars[-1]
#             outBarsHasNewBar = True
#             logger.debug(f"outBars[-1]={outBars[-1]} hasNewBar=True")
#         elif outBars:
#             sumVolume = outBars[-1].volume + b.volume
#             sumValues = outBars[-1].volume * outBars[-1].average + b.volume * b.average
#             outBars[-1].close = b.close
#             if b.high > outBars[-1].high:
#                 outBars[-1].high = b.high
#             if b.low < outBars[-1].low:
#                 outBars[-1].low = b.low
#             if not atTopMinute:
#                 # accumulate
#                 outBars[-1].volume += b.volume
#                 outBars[-1].barCount += b.barCount
#             else:
#                 # set last
#                 outBars[-1].volume = b.volume
#                 outBars[-1].barCount = b.barCount
#             outBars[-1].average = sumValues / sumVolume if sumVolume > 0 else b.close # has average even if volume is 0
#             logger.debug(f"outBars[-1]={outBars[-1]} hasNewBar=False")

#         self.updateEvent.emit(outBars, outBarsHasNewBar) # forward to resampled bar event
#         return (outBars, outBarsHasNewBar)

# class KalmanFilter:
#     def __init__(self, A, B, H, Q, R, P, x0):
#         self.A = A  # State transition matrix
#         self.B = B  # Control input matrix
#         self.H = H  # Observation matrix
#         self.Q = Q  # Process noise covariance
#         self.R = R  # Measurement noise covariance
#         self.P = P  # Estimate error covariance
#         self.x = x0  # Initial state estimate

#     def predict(self, u=0):
#         # Predict the next state
#         self.x = np.dot(self.A, self.x) + np.dot(self.B, u)
#         self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q

#     def update(self, z):
#         # Update the state with a new measurement
#         y = z - np.dot(self.H, self.x)  # Measurement residual
#         S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R  # Residual covariance
#         K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))  # Kalman gain
#         self.x = self.x + np.dot(K, y)
#         self.P = self.P - np.dot(np.dot(K, self.H), self.P)

# Example usage
dt_one = 1.0  # Time step
dt_oneminute = 1./60. # in hours
# Simulate some data (e.g., measurements of position, velocity, and acceleration)
#measurements = [np.array([i, i, i]) for i in range(10)]
# measurements = [np.array([i]) for i in range(10)]
# for z in measurements:
#     kf.predict()
#     kf.update(z)
#     print("State estimate:", kf.x)

# # Example usage
# A = np.array([[1, 1, 0.5], [0, 1, 1], [0, 0, 1]])  # State transition matrix
# B = np.array([[0.5], [1], [1]])  # Control input matrix
# H = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])  # Observation matrix
# Q = np.eye(3) * 0.1  # Process noise covariance
# R = np.eye(3) * 0.1  # Measurement noise covariance
# P = np.eye(3)  # Estimate error covariance
# x0 = np.array([0, 0, 0])  # Initial state estimate

# kf = KalmanFilter(A, B, H, Q, R, P, x0)

# # Simulate some data
# measurements = [np.array([i, i, i]) for i in range(10)]

# for z in measurements:
#     kf.predict()
#     kf.update(z)
#     print("State estimate:", kf.x)

def singleton(cls):
    instances = {}
    def wrapper(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return wrapper

# @singleton
# class Singleton:
#     pass

# # Usage
# singleton1 = Singleton()
# singleton2 = Singleton()
# print(singleton1 is singleton2)  # True

@singleton 
@dataclass
class Agent:
    """class for keeping track of agent's state"""

    # all below are NOT instance variables, they are class variables
    ib: ib_insync.IB
    args: argparse.Namespace
    # errorqueue: deque
    strategynum: int
    symbol: str
    tradingaccount: str
    avgcost_prevclose: bool
    ibBarUpdateTime: datetime.datetime = datetime.datetime.now(local_tz)
    # resampler
    hasNewBar1m: bool = False
    hasNewBar5m: bool = False
    hasNewBar10m: bool = False
    hasNewBar15m: bool = False
    hasNewBar30m: bool = False
    bars_tick: List[BarData] = field(default_factory=list)
    # position: ib_insync.objects.Position = None
    stkpos: ib_insync.objects.Position = None
    useAvgCost: float = 0.0 # set to prev close if avgcost_prevclose is True, else set to zero
    rput: float = 0.0 # if we have position, earning rate = return per unit time (rput)
    volatility_per_min: deque = field(default_factory=deque) # volatility every minute
    volatility_pm_running: deque = field(default_factory=deque) # running per minute volatility since open
    contractType: str = 'STK'
    expiry: str = ''
    exchange: str = ''
    ibcontract: ib_insync.contract.Contract = None
    ibcontractDetails: ib_insync.contract.ContractDetails = None
    prevclose: float = 0.0
    todayopen: float = 0.0
    barsstartidx: int = 0
    beginprice: float = 0.0
    highsincestart: float = 0.0
    lowsincestart: float = 0.0
    testpnl: float = 0.0
    # position: int
    # avg_cost: float
    # last_price: float
    # realized_pnl: float
    # unrealized_pnl: float
    # daily_pnl: float
    session_start: List[datetime.datetime] = field(default_factory=list)
    session_end: List[datetime.datetime] = field(default_factory=list)
    use5s: bool = False
    bars: BarDataList = field(default_factory=BarDataList) # for compatibility, 1m bars
    hml: List[float] = field(default_factory=list) # high minus low, parallel to bars
    hml_pct: List[float] = field(default_factory=list) # high minus low as percentage of close
    hmlstat: OnlineStatsInt = OnlineStatsInt(val_max=1000) # hml in cents

    # hi/lo ratio, range
    dayhilopct: deque = field(default_factory=deque) # 30 minutes (maxlen=12*30)
    # dayhilopct: OnlineDeque = field(default_factory=OnlineDeque)
    # source bars
    bars5s: BarDataList = field(default_factory=BarDataList)
    # resampled bars
    # bars10s: BarDataList = field(default_factory=BarDataList)
    bars15s: BarDataList = field(default_factory=BarDataList)
    bars30s: BarDataList = field(default_factory=BarDataList)
    bars1m: BarDataList = field(default_factory=BarDataList)
    bars2m: BarDataList = field(default_factory=BarDataList)
    bars3m: BarDataList = field(default_factory=BarDataList)
    bars5m: BarDataList = field(default_factory=BarDataList)
    bars10m: BarDataList = field(default_factory=BarDataList)
    bars15m: BarDataList = field(default_factory=BarDataList)
    bars30m: BarDataList = field(default_factory=BarDataList)

    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    lastPrice: float = 0.0 # cache bars[-1].close
    maxloss: float = 0.0
    trade: ib_insync.order.Trade = None # trade that we placed
    orderId: int = -1
    tradePermId: int = -1
    tradeMgr: TradeManager = None
    # order: ib_insync.objects.Order = None
    liveTrading: bool = False
    strategy_tasks: set[asyncio.Task] = field(default_factory=set) # keep separate references for strategy tasks

    # state variables and methods for simpleLongStrategy1
    strategyinitstatus: int = -10 # -1 = failed, 0 = success, -10 = not initialized
    numshares: int = 0
    milestone_multiplier: float = 0.0
    upPctMilestone: List[float] = field(default_factory=list)
    dnPctMilestone: List[float] = field(default_factory=list)
    # upPriceMilestone: List[float] = field(default_factory=list)
    stopLossPct: List[float] = field(default_factory=list)
    # stopLossPrice: List[float] = field(default_factory=list)
    idxMilestone: int = -1 # initialize to an impossible value
    trapdoorIdx: int = -1 # initialize to an impossible value
    tripwireIdx: int = -1 # if set, ok to buy again
    # avgCost: float = 0.0
    state: int = 0 # state machine: 0 = seek entry, 1 = maintain position, keep ratchet up until stop loss
    prevstate: int = 0 # previous state
    recenthigh: tuple[int, BarData] = None
    recentlow: tuple[int, BarData] = None
    # execdetailTrade: list[ib_insync.order.Trade] = field(default_factory=list)
    # execdetailFill: list[ib_insync.objects.Fill] = field(default_factory=list)
    buyopen_bar1m_idx: list[int] = field(default_factory=list)
    buyopen_bar1m: list[ib_insync.objects.BarData] = field(default_factory=list) # the bar1m where buy was recorded, valid across days
    high_since_buy_bar1m: list[ib_insync.objects.BarData] = field(default_factory=list) # the bar1m where the high since buy was recorded, valid across days
    sellclose_bar1m_idx: list[int] = field(default_factory=list)
    sellclose_bar1m: list[ib_insync.objects.BarData] = field(default_factory=list) # the bar1m where sell was recorded, valid across days
    mile0_max_retracement_pct: float = 0.0
    mile0_max_retracement_absolute_min_pct: float = 0.0
    lastSalePrice: float = 0.0
    buyagainbuffer: float = 0.0 # buffer to buy again after selling
    lastSellTrade: Optional[ib_insync.order.Trade] = None
    lastSaleTime: Optional[datetime.datetime] = None
    lastSellPrice: float = 0.0
    lastBuyTrade: Optional[ib_insync.order.Trade] = None
    lastBuyTime: Optional[datetime.datetime] = None
    lastBuyPrice: float = 0.0
    # economy and indicators
    direction_s1: str = ''
    direction_s2: str = ''
    direction_s3: str = ''
    direction_s16: str = ''
    direction_s24: str = ''
    gf1: bool = False
    gf1_serial: deque = field(default_factory=lambda: deque(maxlen=12*30)) # 12 5-sec ticks per minute, 30 minutes = 0.5 hour worth of ticks
    seen_abs_low: list = field(default_factory=list)
    seen_abs_high: list = field(default_factory=list)
    absolute_low_last5m: bool = False
    absolute_low_last10m: bool = False
    absolute_low_last15m: bool = False
    absolute_low_last30m: bool = False
    absolute_high_last5m: bool = False
    absolute_high_last10m: bool = False
    absolute_high_last15m: bool = False
    absolute_high_last30m: bool = False
    absolute_low: bool = False
    absolute_high: bool = False

    def reset(self):
        pass

    def request_historical_data(self, contract_1: ib_insync.contract.Contract, cdl: ib_insync.contract.ContractDetails) -> asyncio.Future:
        # contract_1 = self.ibcontract
        # ib.qualifyContracts(contract_1) # already qualified in premkt init
        start_mkt, end_mkt = get_market_hours()
        trdSession = ib_insync.contract.TradingSession(start_mkt, end_mkt)
        cdliquid = cdl.liquidSessions()[0]
        cdl_full = cdl.tradingSessions()[0]
        if cdl_full.start.astimezone().time() == datetime.time(18, 0): # 6:00 PM
            rthfactor_pad = 7
        else:
            rthfactor_pad = 0
        if self.use5s:
            self.ib.barUpdateEvent += self.onBarUpdate_ib
            # self.ib.pendingTickersEvent += onPendingTickers
            def initialize_bars(bars, barSizeSetting):
                # bars.reqId = agent.bars5s.reqId
                bars.contract = contract_1
                bars.endDateTime = ''
                bars.durationStr = '1 D'
                bars.barSizeSetting = barSizeSetting
                bars.whatToShow = 'TRADES'
                bars.useRTH = False
                # bars.formatDate = agent.bars5s.formatDate
                bars.keepUpToDate = True
                bars._init_npdata('', '', rthfactor_pad=rthfactor_pad)

            # must init before initial_resample_hook
            # initialize_bars(self.bars10s, '10 secs')
            # initialize_bars(self.bars15s, '15 secs')
            # initialize_bars(self.bars30s, '30 secs')
            initialize_bars(self.bars, '1 min')
            initialize_bars(self.bars3m, '3 mins')
            initialize_bars(self.bars5m, '5 mins')
            initialize_bars(self.bars10m, '10 mins')
            initialize_bars(self.bars15m, '15 mins')
            initialize_bars(self.bars30m, '30 mins')

            # self.bars5s 
            useRTH = False
            future = asyncio.ensure_future(self.ib.reqHistoricalDataExtAsync(
                contract_1,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='15 secs',
                whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                useRTH=useRTH, # start from ~4:00 AM
                formatDate=1,
                keepUpToDate=True,
                _historicalDataEndHook=self.initial_resample_hook,
                _tradingHours=trdSession if useRTH else cdl_full
                )
            )
            # self.bars = BarDataList()
            # task.add_done_callback(lambda t: logger.info(f"task reqHistoricalDataExt done: len(bars) {len(t.result())}"))
            # while not task.done():
            #     logger.info(f"Waiting for task reqHistoricalDataExt() to complete...")
            #     self.ib.sleep(2)
            # self.bars5s = task.result()
            procname = 'ib.reqHistoricalDataExt'
        else:
            # self.bars 
            future = asyncio.ensure_future(self.ib.reqHistoricalDataAsync(
                contract_1,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='1 min', # '5 secs', # always ticks every 5 secs
                whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                useRTH=False, # start from ~4:00 AM
                formatDate=1,
                keepUpToDate=True
                )
            )
            procname = 'ib.reqHistoricalData'
        
        future.add_done_callback(lambda t: logger.info(f"task {procname} done: len(bars) {len(t.result())}"))
        return future
        # self.bars5m.initialize(self.bars)
        # if len(self.bars) > 0:
        #     dtnow = datetime.datetime.now(local_tz)
        #     if dtnow.weekday() >= 5:  # Saturday or Sunday
        #         logging.warning(f"{dtnow.strftime('%A')} is not trading today")
        #     else:
        #         if self.bars[0].date.date() != dtnow.date():
        #             logging.warning(f"Expect first bar {self.bars[0]} to be today")
        #         # assert self.bars[0].date.date() == dtnow.date(), f"Expect first bar {self.bars[0]} to be today"
        # else:
        #     assert False, "Expect at least one bar"
        # self.barsstartidx = len(self.bars) - 1
        # self.beginprice = self.bars[self.barsstartidx].close
        # logger.info(f"{procname}: len(bars)={len(self.bars)}, bar[0]={self.bars[0]}, bar[-1]={self.bars[-1]}")
        # # self.bars.updateEvent += lambda x, y: self.onBarUpdate(x, y) # are these two equivalent?
        # if self.use5s:
        #     logger.info(f'{self.bars.buffer_size} {self.bars._npidx} {len(self.bars.open_prices)}')
        #     self.bars5s.updateEvent += self.resample_from_5s # resample then call onBarUpdate
        # else:
        #     self.bars.updateEvent += self.onBarUpdate
        # self.bars.updateEvent += self.bars5m.__call__ # 1m to 5m resampling
        # self.bars5m.updateEvent += self.on5mBarUpdate
        # self.bars5m.updateEvent += self.bars10m.__call__ # 1m to 10m resampling
        # self.bars10m.updateEvent += self.on10mBarUpdate
        # # self.bars.updateEvent += self.bars15m.__call__ # 1m to 15m resampling


    async def initial_resample_hook(self, start: str, end: str, bars: BarDataList):
        logger.info(f"start={start}, end={end}, len(bars)={len(bars)}")
        N = 2000
        for n, b in enumerate(bars, start=1):
            await self.resample_from_5s_core(b, False)
            if n % N == 0:
                await asyncio.sleep(0) # yield control to event loop
        logger.info(f"len(self.bars)={len(self.bars)} {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
        # logger.info(f"len(self.bars10s)={len(self.bars10s)}")
        # logger.info(f"{self.bars10s._npidx} {self.bars10s._npidx_rth_start} {self.bars10s._npidx_rth_end}")
        # logger.info(f"{pd.DataFrame({'date': self.bars10s.npdate, 'open': self.bars10s.npopen,
        #                              'close': self.bars10s.npclose, 'high': self.bars10s.nphigh,
        #                              'low': self.bars10s.nplow}).iloc[:10]}")
        # logger.info(f"len(self.bars15s)={len(self.bars15s)}")
        # logger.info(f"len(self.bars30s)={len(self.bars30s)}")
        # logger.info(f"len(self.bars2m)={len(self.bars2m)}")
        # logger.info(f"len(self.bars5m)={len(self.bars5m)}")
        # logger.info(f"len(self.bars10m)={len(self.bars10m)}")
        # logger.info(f"len(self.bars15m)={len(self.bars15m)}")
        # util.df(self.bars).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars1m.csv', index=False)
        # util.df(self.bars10s).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars10s.csv', index=False)
        # util.df(self.bars15s).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars15s.csv', index=False)
        # util.df(self.bars30s).rename(columns={'open_': 'open'}).drop(columns=['timestamp']).to_csv('bars30s.csv', index=False)
        # exit(0)

    async def resample_from_5s(self, inBars: BarDataList, inBarHasNewBar: bool):
        """
        Resample 5s bars to 1m, 2m, 5m, 10m, and 15m bars.
        """
        # global bars_tick
        b = inBars[-1] # shortcut to the last bar
        if inBarHasNewBar:
            self.bars_tick = []
        # unravel the bar
        if not inBarHasNewBar:
            # logger.info(bars_tick)
            if self.bars_tick: # b.date 5, 10, 20, 25, 35, 40, 50, 55 (all 5s ticks except 0, 15, 30, 45)
                bc_diff = b.barCount - self.bars_tick[-1].barCount
                v_diff = b.volume - self.bars_tick[-1].volume
                current_sum = b.volume * b.average
                prev_sum = self.bars_tick[-1].volume * self.bars_tick[-1].average
                avg_inc = (current_sum - prev_sum) / v_diff if v_diff > 0 else b.close
                new_date = b.date + datetime.timedelta(seconds=len(self.bars_tick)*5)
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

        self.bars_tick.append(copy.copy(b))

        # await self.resample_from_5s_core(inBars[-1], inBarHasNewBar)
        await self.resample_from_5s_core(new_b, inBarHasNewBar)
        # hasNewBar1m = inBars[-1].date.second == 0
        self.hasNewBar1m = new_b.date.second == 0
        # self.hasNewBar2m = self.hasNewBar1m and new_b.date.minute % 2 == 0
        self.hasNewBar5m = self.hasNewBar1m and new_b.date.minute % 5 == 0
        self.hasNewBar10m = self.hasNewBar1m and new_b.date.minute % 10 == 0
        self.hasNewBar15m = self.hasNewBar1m and new_b.date.minute % 15 == 0
        self.hasNewBar30m = self.hasNewBar1m and new_b.date.minute % 30 == 0
        await self.onBarUpdate(self.bars, self.hasNewBar1m) # every 5 secs

    async def resample_from_5s_core(self, inBar: BarData, inBarHasNewBar: bool):
        """
        Resample 5s bars to 1m, 2m, 5m, 10m, and 15m bars.
        """
        def update_bar(outBar: BarData, newBar: BarData):
            sumVolume = outBar.volume + newBar.volume
            sumValues = outBar.volume * outBar.average + newBar.volume * newBar.average
            outBar.timestamp = newBar.timestamp
            outBar.close = newBar.close
            outBar.high = max(outBar.high, newBar.high)
            outBar.low = min(outBar.low, newBar.low)
            outBar.volume += newBar.volume
            outBar.barCount += newBar.barCount
            outBar.average = sumValues / sumVolume if sumVolume > 0 else newBar.close

        def handle_new_bar(outBars: BarDataList, newBar: BarData, hasNewBar: bool):
            newcopy = copy.copy(newBar)
            if hasNewBar or not outBars:
                outBars.append(newcopy)
                outBars._add_npdata(newcopy)
            else:
                newcopy.date = outBars[-1].date # 
                update_bar(outBars[-1], newcopy)
                outBars._set_last_npdata(outBars[-1])

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
        hasNewBar3m = hasNewBar1m and b.date.minute % 3 == 0
        hasNewBar5m = hasNewBar1m and b.date.minute % 5 == 0
        hasNewBar10m = hasNewBar1m and b.date.minute % 10 == 0
        hasNewBar15m = hasNewBar1m and b.date.minute % 15 == 0
        hasNewBar30m = hasNewBar1m and b.date.minute % 30 == 0

        handle_new_bar(self.bars, b, hasNewBar1m)
        # if not hasattr(self, 'bars10s_log_count'):
        #     self.bars10s_log_count = 0
        # if self.bars10s_log_count < 10:
        #     logger.info(f"hasNewBar10s={hasNewBar10s}, {b.date.second}")
        #     self.bars10s_log_count += 1
        # handle_new_bar(self.bars10s, b, hasNewBar10s)
        # handle_new_bar(self.bars15s, b, hasNewBar15s)
        # handle_new_bar(self.bars30s, b, hasNewBar30s)
        # handle_new_bar(self.bars2m, b, hasNewBar2m)
        handle_new_bar(self.bars3m, b, hasNewBar3m)
        handle_new_bar(self.bars5m, b, hasNewBar5m)
        handle_new_bar(self.bars10m, b, hasNewBar10m)
        handle_new_bar(self.bars15m, b, hasNewBar15m)
        handle_new_bar(self.bars30m, b, hasNewBar30m)

        # await self.onBarUpdate(self.bars, hasNewBar1m) # every 5 secs
        # onResampledBar2m(outBars2m, hasNewBar2m)
        # onResampledBar5m(outBars5m, hasNewBar5m)
        # onResampledBar10m(outBars10m, hasNewBar10m)
        # onResampledBar15m(outBars15m, hasNewBar15m)


    def resume_session(self, data: dict):
        if not data:
            logger.warning(f"previous session data is empty")
            return
        _ = data.pop('trade_list', None) # no need for this anymore
        logger.info(f"Resuming session {format_dict(data)}")
        self.session_start = data.get('session_start', []).append(datetime.datetime.now(local_tz)) or data['session_start']
        self.session_end = data.get('session_end', []) or data['session_end']
        self.buyopen_bar1m_idx = data.get('buyopen_bar1m_idx', []) or data['buyopen_bar1m_idx']
        self.buyopen_bar1m = data.get('buyopen_bar1m', []) or data['buyopen_bar1m'] # the bar1m where buy was recorded, valid across days
        self.sellclose_bar1m_idx = data.get('sellclose_bar1m_idx', []) or data['sellclose_bar1m_idx']
        self.sellclose_bar1m = data.get('sellclose_bar1m', []) or data['sellclose_bar1m'] # the bar1m where sell was recorded, valid across days
        if self.get_state() == 0:
            self.high_since_buy_bar1m = []
        else:
            # only restore high_since_buy_bar1m if we are in state 1
            self.high_since_buy_bar1m = data.get('high_since_buy_bar1m', []) or data['high_since_buy_bar1m']
        logger.info(f"session_start: {self.session_start[-1].astimezone()}")

        # if self.high_since_buy_bar1m is None:
        #     logger.warning(f"high_since_buy_bar1m is None")
        #     if len(self.bars) > 0:
        #         self.high_since_buy_bar1m = max(self.bars, key=lambda bar: bar.close)

        # get all trades so far
        trades = [t for t in ib.trades() if t.contract.symbol == self.symbol]
        # ensure each trade has fills
        tt = []
        for trade in trades:
            if not trade.fills and trade.orderStatus.status != 'Cancelled':
                logger.error(f"Trade has no fills and orderStatus is not cancelled: {trade}")
            elif not trade.fills and trade.orderStatus.status == 'Cancelled':
                pass # ignore cancelled trades
                logger.info(f"Skipping cancelled trade: {trade}")
            else: # trade has fills
                # logger.debug(f"Trade has fills: {trade}")
                tt.append(trade)
        # trades_df = ibtrades_to_df(t)
        # logger.info(f"trades: {trades_df}")
        if tt:
            t = sorted(tt, key=lambda trade: max([fill.execution.time for fill in trade.fills]))
        else:
            t = tt
        if t: # sorted or empty
            for trade in reversed(t):
                if trade.order.action == 'SELL':
                    self.lastSellTrade = trade
                    self.lastSaleTime = max(fill.execution.time for fill in trade.fills)
                    self.lastSalePrice = sum(fill.execution.price * fill.execution.shares for fill in trade.fills) / sum(fill.execution.shares for fill in trade.fills)
                    logger.info(f"last sell trade: {trade}, last sale time: {self.lastSaleTime.astimezone()}, last sale price: {self.lastSalePrice}")
                    break
            for trade in reversed(t):
                if trade.order.action == 'BUY':
                    self.lastBuyTrade = trade
                    self.lastBuyTime = max(fill.execution.time for fill in trade.fills)
                    self.lastBuyPrice = sum(fill.execution.price * fill.execution.shares for fill in trade.fills) / sum(fill.execution.shares for fill in trade.fills)
                    logger.info(f"last buy trade: {trade}, last buy time: {self.lastBuyTime.astimezone()}, last buy price: {self.lastBuyPrice}")
                    break
        else:
            logger.info(f"no trades done today")
        return # end of resume_session

    def strategyInitPreOpen(self) -> int:
        match self.strategynum:
            case 1 | 2 | 3 | 5:
                return self.simpleLongStrategy1InitPreOpen()
            case _:
                logger.error(f"Unknown strategy number {self.strategynum}")
                return -1

    def strategyInit(self) -> int:
        match self.strategynum:
            case 1:
                return self.simpleLongStrategy1Init()
            case 5:
                return self.simpleShortStrategyInit()
            case _:
                logger.error(f"Unknown strategy number {self.strategynum}")
                return -1

    def simpleLongStrategy1InitPreOpen(self) -> int:
        logger.info(f"Pre-market initialization for {self.symbol}")
        # # get historical bars for the last 6 months
        # contract_ = Stock(self.symbol, 'SMART', 'USD')
        # self.histbars = ib.reqHistoricalData( # this method is blocking
        #     contract_,
        #     endDateTime=(datetime.datetime.now(local_tz) + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
        #     durationStr='3 M',
        #     barSizeSetting='15 mins',
        #     whatToShow='TRADES',
        #     useRTH=True,
        #     formatDate=1,
        #     timeout=120) # 2 minutes timeout
        # # and may timeout
        # if self.histbars is None or len(self.histbars) == 0:
        #     logger.error(f"Failed to get historical bars for {self.symbol}")
        #     # self.strategyinitstatus = -1
        #     return -1

        filename = f'./data/{self.symbol}_1d.csv'
        dailyclose_df: pd.DataFrame = pd.DataFrame()
        prevclose_fromfile = 0.0
        yestdate = pd.to_datetime(last_business_dt())
        if os.path.exists(filename):
            dailyclose_df = pd.read_csv(filename, parse_dates=['date'])
            if yestdate not in dailyclose_df['date'].values:
                logger.error(f"{yestdate.date()} not found in historical data {filename}")
                # return -1 # check ticker for today's close
            else:
                self.prevclose = prevclose_fromfile = (dailyclose_df[ dailyclose_df['date'] == yestdate ].close).values[0]
                logger.info(f"prevclose {self.prevclose} from {filename}")
        else:
            logger.warning(f"{filename} not found")

        if self.contractType == 'STK':
            self.ibcontract = contract_1 = Stock(self.symbol, 'SMART', 'USD')
        elif self.contractType == 'FUT':
            if not self.expiry:
                logger.error(f"Future contract must specify expiry date")
                return -1
            if not self.exchange:
                logger.error(f"Future contract must specify exchange")
                return -1
            self.ibcontract = contract_1 = Future(self.symbol, self.expiry, self.exchange)
        elif self.contractType == 'CASH':
            self.ibcontract = contract_1 = Forex(self.symbol)
        elif self.contractType == 'FUND':
            self.ibcontract = contract_1 = MutualFund(symbol=self.symbol)
        elif self.contractType == 'OPT':
            self.ibcontract = contract_1 = Option(self.symbol, self.expiry, self.strike, self.right, self.exchange)
        else:
            logger.error(f"Unknown contract type {self.contractType}")
            return -1
        self.ibcontractDetails = contractDetails = ib.reqContractDetails(contract_1)
        qcon1 = contractDetails[0].contract
        qcon = ib.qualifyContracts(contract_1) # won't need this after we have contractDetails
        assert qcon1 == qcon[0]
        if len(qcon) != 1:
            logger.error(f"Contract must be unique, expected 1 contract, got {qcon}")
            return -1
        else:
            logger.info(f"Contract: {qcon[0]}")
            self.futAvgCostMult = 1.0
            self.contract_multiplier = 1.0
            if self.contractType == 'FUT':
                self.contract_multiplier = mult_ = float(qcon[0].multiplier)
                # future contract avgcost is inflated by the multiplier
                self.futAvgCostMult = 1./mult_
                expiration_date = datetime.datetime.strptime(contractDetails[0].realExpirationDate, r'%Y%m%d')
                days_to_expiration = (expiration_date - datetime.datetime.now()).days
                logger.info(f"Future contract expires in {days_to_expiration} days")
        # self.ibcontractDetails = contractDetails = ib.reqContractDetails(contract_1) # moved up
        self.ibTradingSessionIdx = 0
        if len(contractDetails) != 1:
            logger.error(f"Contract must be unique, expected 1 contractDetails, got {len(contractDetails)}")
            logger.error(f"{contractDetails}")
            return -1
        elif contractDetails[0].tradingHours == '' or contractDetails[0].liquidHours == '' or contractDetails[0].timeZoneId == '':
            logger.error(f"Missing trading hours data in contractDetails: {contractDetails[0]}")
            return -1
        dtnow = datetime.datetime.now(local_tz)
        tradingHours_ld = parse_hours(contractDetails[0].tradingHours, contractDetails[0].timeZoneId)
        liquidHours_ld = parse_hours(contractDetails[0].liquidHours, contractDetails[0].timeZoneId)
        if tradingHours_ld is None or liquidHours_ld is None:
            logger.error(f"Missing trading hours data in contractDetails")
            return -1
        if tradingHours_ld[0]['is_error']:
            logger.error(f"Cannot parse trading hours: {tradingHours_ld[0]['period_str']}")
            return -1
        elif tradingHours_ld[0]['is_closed'] and tradingHours_ld[0]['date_start'] == dtnow.date():
            logger.error(f"Market is closed: {tradingHours_ld[0]['period_str']}")
            return -1
        cdliquid = contractDetails[0].liquidSessions()[0]
        logger.info(f"liquid trading hours: {cdliquid.start.astimezone()} to {cdliquid.end.astimezone()}")
        start_mkt, end_mkt = get_market_hours()
        if (start_mkt != cdliquid.start or end_mkt != cdliquid.end) and dtnow < cdliquid.end:
            # logger.info(f"Market hours have changed from {start_mkt.astimezone()} to {cdliquid.start.astimezone()} and from {end_mkt.astimezone()} to {cdliquid.end.astimezone()}")
            set_market_hours(cdliquid.start, cdliquid.end)
        cdl_full = contractDetails[0].tradingSessions()[0]
        logger.info(f"full trading hours: {cdl_full.start.astimezone()} to {cdl_full.end.astimezone()}")
        if cdliquid.end < dtnow and dtnow <= cdl_full.end: # contractDetails[0].liquidSessions()[1].start:
            logger.info(f"Liquid trading session has ended, switching to full trading hours: {cdl_full.start.astimezone()} to {cdl_full.end.astimezone()}")
            set_market_hours(cdl_full.start, cdl_full.end)
        elif cdl_full.end < dtnow:
            cdliquid_1 = contractDetails[0].liquidSessions()[1]
            cdl_full_1 = contractDetails[0].tradingSessions()[1]
            if cdl_full_1.start < dtnow and dtnow <= cdl_full_1.end:
                logger.info(f"Trading hours have ended for today")
                logger.info(f"Switching to next full trading hours: {cdl_full_1.start.astimezone()} to {cdl_full_1.end.astimezone()}")
                self.ibTradingSessionIdx = 1
                set_market_hours(cdl_full_1.start, cdl_full_1.end)
            elif dtnow < cdl_full_1.start and dtnow <= cdl_full_1.end:
                logger.info(f"Trading hours have ended for today")
                logger.info(f"Next full trading hours: {cdl_full_1.start.astimezone()} to {cdl_full_1.end.astimezone()}")
                self.ibTradingSessionIdx = 1
                set_market_hours(cdl_full_1.start, cdl_full_1.end)
            else:
                logger.error(f"Trading hours have ended for today and the next one starts at {cdl_full_1.start.astimezone()}")
                return -1

        # request historical data
        start_mkt, end_mkt = get_market_hours()
        future = self.request_historical_data(contract_1, contractDetails[0]) # onBarUpdate could fire before this method returns

        # request market data
        self.ib.reqMarketDataType(1)
        if self.contractType == 'STK':
            genericTickList = '104,59' # 59=dividend, 104=30d historical vol
        elif self.contractType == 'FUT':
            genericTickList = '104' # 104=30d historical vol
        t = self.ib.reqMktData(contract_1, genericTickList, False, False, None)
        self.ticker: Ticker = t
        self.ib.sleep(0.5)
        if len(self.ib.tickers()) != 1:
            logger.error(f"{self.ib.tickers()}: expected 1 ticker")
            return -1
        t = self.ib.tickers()[0]
        for _ in range(10):
            if hasattr(t, 'time') and t.time is not None:
                break
            logger.info(f"waiting for ticker to be fully populated")
            self.ib.sleep(0.5)
        else: # no break
            logger.error(f"ticker is not populating")
            return -1
        tdiff = (t.time - datetime.datetime.now(local_tz)).total_seconds()
        if abs(tdiff) > 2.0:
            # report clock skew
            logger.warning(f"Tick time is {tdiff:.2f} seconds" + (" ahead" if tdiff > 0 else " behind") + " of current time")
        if math.isnan(t.bid) or math.isnan(t.ask) or math.isnan(t.last) or math.isnan(t.close) or math.isnan(t.open_):
            bidasklast = f"bid {t.bid} ask {t.ask} last {t.last} close {t.close} open {t.open_}"
        else:
            bidasklast = f"bid {t.bid} ask {t.ask} last {t.last} chg {(t.ask+t.bid)/2.0/t.close-1.0:+.2%} open {t.open_} close {t.close} volume {t.volume:n}"
        logger.info(f"{t.contract.localSymbol}: {t.time.astimezone():%H:%M:%S} {bidasklast}")

        if self.contractType == 'STK':
            for _ in range(20):
                if t.dividends:
                    logger.info(f"{t.dividends}")
                    break
                logger.info(f"waiting for dividends to be populated")
                self.ib.sleep(2)
            else: # no break
                logger.warning(f"dividends is not populating")
        if t.halted > 0:
            logger.error(f"{t.contract.localSymbol} is halted")
            return -1
        for _ in range(10):
            if t.histVolatility and t.histVolatility > 0:
                logger.info(f"30d historical volatility: {t.histVolatility:.2%}")
                break
            logger.info(f"waiting for histVolatility to be populated")
            self.ib.sleep(1)
        else: # no break
            logger.warning(f"histVolatility is not populating")

        if t.close > 0:
            self.prevclose = t.close
        elif dailyclose_df.empty or prevclose_fromfile == 0.0:
            logger.error(f"closing price is not available from ticker or file")
            return -1
        elif t.close != prevclose_fromfile:
            logger.warning(f"ticker.close={t.close} != dailyclose.close={self.prevclose}")
            if datetime.datetime.now(local_tz).weekday() >= 5:  # Saturday or Sunday
                logger.warning(f"Weekend using dailyclose.close as ticker.close is not reliable")
                self.prevclose = prevclose_fromfile
            else: # weekday
                logger.warning(f"Using ticker.close={t.close} as prevclose")
                self.prevclose = t.close
            # not fatal, just a warning
        # self.recenthigh = (-1, self.dailyclose[-1]) # initialize to last bar data from prev day
        # self.recentlow = (-1, self.dailyclose[-1]) # initialize to last bar data from prev day

        # IB avgCost is adjusted by wash-sale. 
        # Plus we sometimes sit on a gain or loss that we want to ignore
        # and use the previous close as avgCost.
        # only adjust if it's a carry over position from previous day. new trades aren't affected.
        if self.stkpos and self.stkpos.position > 0:
            if self.avgcost_prevclose:
                self.useAvgCost = self.prevclose
                logger.info(f"IB avgCost {self.stkpos.avgCost} is not used, using prevclose {self.useAvgCost} as avgcost")
                # self.stkpos.avgCost = self.useAvgCost
                # logger.info(f"Override avgcost {self.stkpos.avgCost} with {self.useAvgCost}")
            elif not self.avgcost_prevclose or self.ib.trades():
                if self.ib.trades():
                    logger.info(f"IB avgCost {self.stkpos.avgCost * self.futAvgCostMult}") #  is not adjusted
                self.useAvgCost = self.stkpos.avgCost
        else:
            self.useAvgCost = 0.0

        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)
        # while not future.done():
        #     logger.info(f"Waiting for request_historical_data() to complete...")
        #     self.ib.sleep(1)
        # self.ib.pendingTickersEvent -= onPendingTickers

        if self.use5s:
            self.bars5s = future.result() # self.bars will populate indirectly from resampler
        else:
            self.bars = future.result()

        # if len(self.bars) > 0:
        #     dtnow = datetime.datetime.now(local_tz)
        #     if dtnow.weekday() >= 5:  # Saturday or Sunday
        #         logging.warning(f"{dtnow.strftime('%A')} is not trading today")
        #     else:
        #         if self.bars[0].date.date() != dtnow.date():
        #             logging.warning(f"Expect first bar {self.bars[0]} to be today")
        #         # assert self.bars[0].date.date() == dtnow.date(), f"Expect first bar {self.bars[0]} to be today"
        # else:
        #     assert False, "Expect at least one bar"
        self.barsstartidx = len(self.bars) - 1
        self.beginprice = self.bars[self.barsstartidx].close
        isResampled = f'(resampled)' if self.use5s else ''
        logger.info(f"reqHistoricalData{isResampled}: len(bars)={len(self.bars)}, bar[0]={self.bars[0]}, bar[-1]={self.bars[-1]}")
        # self.bars.updateEvent += lambda x, y: self.onBarUpdate(x, y) # are these two equivalent?
        if self.use5s:
            logger.info(f'{self.bars.buffer_size} {self.bars._npidx} {len(self.bars.open_prices)}')
            self.bars5s.updateEvent += self.resample_from_5s # resample then call onBarUpdate
        else:
            self.bars.updateEvent += self.onBarUpdate
        # logger.info(f"dailyclose len={len(self.dailyclose)}, dailyclose[0]={self.dailyclose[0]}, dailyclose[-1]={self.dailyclose[-1]}")

        # # Newtonian kinematics model
        # # State transition matrix for constant acceleration model
        # A = np.array([[1, dt, 0.5*dt**2],
        #             [0, 1, dt],
        #             [0, 0, 1]])
        # # Control input matrix
        # B = np.array([[0.5*dt**2],
        #             [dt],
        #             [1]])
        # # # Observation matrix (assuming we can observe position, velocity, and acceleration directly)
        # # H = np.eye(3)
        # # Observation matrix (only position is observed)
        # H = np.array([[1, 0, 0]])
        # # Process noise covariance
        # Q = np.eye(3) * 0.1
        # # Measurement noise covariance
        # # R = np.eye(3) * 0.1
        # R = np.array([[0.1]])
        # # Estimate error covariance
        # P = np.eye(3)
        # # Initial state estimate (position, velocity, acceleration)
        # x0 = np.array([0, 0, 0])
        # kf = KalmanFilter(A, B, H, Q, R, P, x0)

        initial_price = get_market_price() or self.prevclose

        self.kf_ca = make_ca_filter(dt_one, std_R=1)
        self.kf_ca_saver = Saver(self.kf_ca)
        self.kf_ca.x = np.array([initial_price, 0, 0]).T
        self.kf_ca.P *= 0.05 * initial_price
        self.kf_ca.R *= 0.01 * initial_price
        self.kf_ca.Q = Q_continuous_white_noise(dim=3, dt=dt_one, spectral_density=1.)
        # self.kf_cv = make_cv_filter(dt, std_R=1)

        def fx_nonlinear(x, dt):
            """
            P_1 = P_0 * exp(return * dt), return = x[1], P_0 = x[0]
            """
            # assert x.shape == (2, 1)
            price, r = x[0], x[1]
            # exp_term = np.exp(x[1] * dt)
            # xout = np.asarray([[x[0] * exp_term], [x[1]]])
            new_price = price * np.exp(r * dt)
            xout = np.asarray([new_price, r])
            # assert xout.shape == (2, 1)
            return xout

        def hx_cv(x):
            """
            transforms state space to measurement space
            state variables: [log price, instantaneous continuously-compounded return]
            measurement variables: [price]
            """
            # assert x.shape == (2, 1)
            # xout = np.exp([x[:1]]) # log price to price
            xout = np.asarray([x[0]])
            # assert xout.shape == (1, 1)
            return xout

        sigmas_merwe = MerweScaledSigmaPoints(n=2, alpha=0.5, beta=2., kappa=1.)
        sigmas_julier = JulierSigmaPoints(n=2, kappa=1)
        self.ukf_cv = UnscentedKalmanFilter(dim_x=2, dim_z=1, dt=dt_oneminute, hx=hx_cv, fx=fx_nonlinear, points=sigmas_merwe)
        self.ukf_cv.x = np.array([initial_price, 0])
        # assert self.ukf_cv.x.shape == (2, 1)
        self.ukf_cv.P *= 0.05 * initial_price # 5% of initial price
        self.ukf_cv.R *= 0.01 * initial_price # measurement noise
        # self.ukf_cv.Q = Q_continuous_white_noise(dim=2, dt=0.05, spectral_density=1.)
        return 0

    def simpleShortStrategyInit(self) -> int:
        """
        strategy #5
        """
        self.simpleShortStrategy1.x = 0
        self.strategyinitstatus = 0
        return 0

    def simpleLongStrategy1Init(self) -> int:
        """
        return 0 if successful, -1 if failed
        """
        # self.upPctMilestone = [0, .0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05,
        #     0.055, 0.06, 0.065, 0.07, 0.075, 0.08, 0.09, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0,
        #     2.0, 3.0]
        # # self.upPriceMilestone = [0.0] * len(self.upPctMilestone)
        # self.stopLossPct = [-0.001] * len(self.upPctMilestone) # uniform -10bps for now. This is the stop loss for each milestone as we cross it, we want small buffer from previous milestone as stop loss so we don't bump into it immediately
        # self.stopLossPct[0] = -0.0025 # -25bps initial stop loss

        self.reset_milestone() # initialize to an impossible value
        with np.printoptions(suppress=True, formatter={'float': lambda x: f'{x:.2%}'}):
            logger.info(f"SimpleLongStrategy1Init: upPctMilestone={self.upPctMilestone[0:6]}"
                f", stopLossPct={self.stopLossPct[0:6]}, dnPctMilestone={self.dnPctMilestone[0:6]}")
        
        if self.stkpos and self.stkpos.position != 0:
            if self.high_since_buy_bar1m == []:
                if self.bars:
                    if self.lastBuyTime and self.bars[0].date <= self.lastBuyTime and self.lastBuyTime <= self.bars[-1].date:
                        # in self.bars, filter for the bars after lastBuyTime, then find the max
                        barsSinceBuy = [b for b in self.bars if b.date >= self.lastBuyTime]
                        if barsSinceBuy:
                            self.high_since_buy_bar1m.append(max(barsSinceBuy, key=lambda bar: bar.average))
                            logger.info(f"high_since_buy_bar1m initialized to: {self.high_since_buy_bar1m}")
                    else:
                        # lastBuyTime is not in self.bars, so we need to get the max from the entire self.bars
                        self.high_since_buy_bar1m.append(max(self.bars, key=lambda bar: bar.average))
                else:
                    logger.warning(f"has position, bars is not set and high_since_buy_bar1m is empty")
        # stockpos = [p for p in ib.positions() if p.contract.symbol in [self.symbol] and p.contract.secType == 'STK']
        # assert len(stockpos) == 1, 'Stock position not found'
        # self.avgCost = stockpos[0].avgCost
        # self.position = stockpos[0].position

        # # get historical bars for the last 6 months
        # contract_ = Stock(self.symbol, 'SMART', 'USD')
        # self.histbars = ib.reqHistoricalData( # this method is blocking
        #     contract_,
        #     endDateTime=(datetime.datetime.now(local_tz) + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
        #     durationStr='6 M',
        #     barSizeSetting='15 mins',
        #     whatToShow='TRADES',
        #     useRTH=True,
        #     formatDate=1)
        # # and may timeout
        # if self.histbars is None or len(self.histbars) == 0:
        #     logger.error(f"Failed to get historical bars for {self.symbol}")
        #     self.strategyinitstatus = -1
        #     return -1
        # self.prevclose = self.histbars[-1].close
        # # self.recenthigh = (-1, self.histbars[-1]) # initialize to last bar data from prev day
        # # self.recentlow = (-1, self.histbars[-1]) # initialize to last bar data from prev day

        # logger.info(f"SimpleLongStrategy1Init: histbars len={len(self.histbars)}")
        self.strategyinitstatus = 0
        return 0

    def __str__(self):
        return f"Symbol: {self.symbol}, trading size {self.numshares}, maxloss {self.maxloss}, account {self.tradingaccount}, stock position: {self.stkpos}"
    #, Avg Cost: {self.avg_cost}, Last Price: {self.last_price}, Realized PnL: {self.realized_pnl}, Unrealized PnL: {self.unrealized_pnl}, Daily PnL: {self.daily_pnl}"

    def set_state(self, state: int) -> 'Agent':
        if state == self.state:
            logger.warning(f"State unchanged: {state}")
            return self
        self.prevstate = self.state
        self.state = state
        return self
    
    def get_state(self) -> int:
        return self.state
    
    def reset_milestone(self) -> 'Agent':
        self.idxMilestone = -1
        logger.info(f"idxMilestone={self.idxMilestone}")
        return self

    def set_milestone(self, idx: int) -> 'Agent':
        self.idxMilestone = idx
        return self
    
    def get_milestone(self) -> int:
        return self.idxMilestone
    
    def checkpoint(self, typ: str) -> None:
        """Checkpoint agent's state and environment"""
        logger.info(f"{typ}")
        pkldump = {
            'symbol': self.symbol,
            'session_start': self.session_start,
            'session_end': self.session_end, # .append(datetime.datetime.now(local_tz)) or self.session_end,
            'buyopen_bar1m_idx': self.buyopen_bar1m_idx, # current day only, not valid the next day
            'buyopen_bar1m': self.buyopen_bar1m, # the bar1m where buy was recorded, valid across days
            'sellclose_bar1m_idx': self.sellclose_bar1m_idx, # current day only, not valid the next day
            'sellclose_bar1m': self.sellclose_bar1m, # the bar1m where sell was recorded, valid across days
            'high_since_buy_bar1m': self.high_since_buy_bar1m, # the bar1m where the high since buy was recorded, valid across days
        }
        fpkl.seek(0)
        pickle.dump(pkldump, fpkl)
        fpkl.flush()

    def onBarUpdate_ib(self, bars: BarDataList, hasNewBar: bool):
        self.ibBarUpdateTime = datetime.datetime.now(datetime.timezone.utc)
        logger.info(f"len(bars)={len(bars)} hasNewBar={hasNewBar}") # f"hasNewBar={hasNewBar}, {_repr_bar(bars[-1])}"

    # @measure_time
    async def onBarUpdate(self, bars: BarDataList, hasNewBar: bool):
        def dayhilo(bars: BarDataList) -> tuple:
            """Calculate day high/low"""
            currentBar = bars[-1]
            bars_avg = [bar.average for bar in bars if bar.date >= MKTOPEN]
            bars_high = [bar.high for bar in bars if bar.date >= MKTOPEN]
            bars_low = [bar.low for bar in bars if bar.date >= MKTOPEN]
            bars_close = [bar.close for bar in bars if bar.date >= MKTOPEN]
            dayhigh_avg = max(bars_avg)
            daylow_avg = min(bars_avg)
            dayhigh_high = max(bars_high)
            daylow_high = min(bars_high)
            dayhigh_low = max(bars_low)
            daylow_low = min(bars_low)
            dayhigh_close = max(bars_close)
            daylow_close = min(bars_close)

            dayhml_avg = dayhigh_avg - daylow_avg
            dayhml_high = dayhigh_high - daylow_high
            dayhml_low = dayhigh_low - daylow_low
            dayhml_close = dayhigh_close - daylow_close

            dayhl_avg = dayhigh_avg / daylow_avg
            dayhl_high = dayhigh_high / daylow_high
            dayhl_low = dayhigh_low / daylow_low
            dayhl_close = dayhigh_close / daylow_close

            dayloghl_avg = np.log(dayhl_avg)
            dayloghl_high = np.log(dayhl_high)
            dayloghl_low = np.log(dayhl_low)
            dayloghl_close = np.log(dayhl_close)

            curratio_avg = (currentBar.average - daylow_avg)/dayhml_avg if dayhml_avg > 0 else 0.0
            curratio_high = (currentBar.high - daylow_high)/dayhml_high if dayhml_high > 0 else 0.0
            curratio_low = (currentBar.low - daylow_low)/dayhml_low if dayhml_low > 0 else 0.0
            curratio_close = (currentBar.close - daylow_close)/dayhml_close if dayhml_close > 0 else 0.0

            return (dayhigh_avg, dayhigh_high, dayhigh_low, dayhigh_close, # [0:4]
                    daylow_avg, daylow_high, daylow_low, daylow_close, # [4:8]
                    dayhl_avg, dayhl_high, dayhl_low, dayhl_close, # [8:12]
                    dayloghl_avg, dayloghl_high, dayloghl_low, dayloghl_close, # [12:16]
                    curratio_avg, curratio_high, curratio_low, curratio_close) # [16:20]

        # logger.debug(get_asyncio_running_loop('')) # expect '<ProactorEventLoop running=True closed=False debug=False>
        dtnow = datetime.datetime.now(datetime.timezone.utc)
        # dtdiff = dtnow - self.ibBarUpdateTime
        # if dtdiff > datetime.timedelta(milliseconds=500):
        #     logger.info(f"bar update is late by {dtdiff.total_seconds():.3f} seconds")
        if self.use5s and hasNewBar:
            if len(bars)*4 != len(self.bars5s):
                logger.error(f"resampled bars out of sync: len(bars)={len(bars)}*4 != len(bars5s)={len(self.bars5s)}")
        logger.info(f"hasNewBar={hasNewBar}, {_repr_barlist(reversed(bars[-3:]))}")
        # logger.info(f"MKTOPEN {MKTOPEN.astimezone()}, MKTCLOSE {MKTCLOSE.astimezone()}")
        # util.barplot(bars)
        currentBar = bars[-1] # bar that is being built, never full
        currentFullBar = bars[-2] # the most recent fully formed bar
        if hasNewBar:
            self.kf_ca.predict()
            self.kf_ca.update(currentFullBar.average)
            self.kf_ca_saver.save()
            s = self.kf_ca_saver # shortcut
            logger.info("kf_ca")
            logger.info(f"x={s.x[-2:]}")
            logger.info(f"P={s.P[-2:]}")
            logger.info(f"K={s.K[-2:]}")
            logger.info(f"y={s.y[-2:]}")

            self.ukf_cv.predict()
            self.ukf_cv.update(np.asarray([currentFullBar.average]))
            logger.info("ukf_cv")
            logger.info(f"x={self.ukf_cv.x[-2:]}")
            logger.info(f"P={self.ukf_cv.P[-2:]}")
            logger.info(f"K={self.ukf_cv.K[-2:]}")
            logger.info(f"y={self.ukf_cv.y[-2:]}")

        if self.use5s:
            cBar3m = self.bars3m[-1]
            cBar5m = self.bars5m[-1]
            cBar10m = self.bars10m[-1]
            cBar15m = self.bars15m[-1]
            cBar30m = self.bars30m[-1]
            cFull3m = self.bars3m[-2:][-1]
            cFull5m = self.bars5m[-2:][-1]
            cFull10m = self.bars10m[-2:][-1]
            cFull15m = self.bars15m[-2:][-1]
            cFull30m = self.bars30m[-2:][-1]
            logger.info(f"cur: 5m {_repr_bar(cBar5m)}, 10m {_repr_bar(cBar10m)}, 15m {_repr_bar(cBar15m)}, 30m {_repr_bar(cBar30m)}")
            logger.info(f"full: 5m {_repr_bar(cFull5m)}, 10m {_repr_bar(cFull10m)}, 15m {_repr_bar(cFull15m)}, 30m {_repr_bar(cFull30m)}")
            if cBar5m: gkvol5m = garman_klass_volatility(cBar5m.open_, cBar5m.high, cBar5m.low, cBar5m.close, 1)
            gkvol10m = garman_klass_volatility(cBar10m.open_, cBar10m.high, cBar10m.low, cBar10m.close, 1)
            gkvol15m = garman_klass_volatility(cBar15m.open_, cBar15m.high, cBar15m.low, cBar15m.close, 1)
            gkvol30m = garman_klass_volatility(cBar30m.open_, cBar30m.high, cBar30m.low, cBar30m.close, 1)
            logger.info(f"gk spot vol 5m: {gkvol5m:.2%}, 10m: {gkvol10m:.2%}, 15m: {gkvol15m:.2%}, 30m: {gkvol30m:.2%}")
            if cFull5m: gkvol5m_full = garman_klass_volatility(cFull5m.open_, cFull5m.high, cFull5m.low, cFull5m.close, 1)
            gkvol10m_full = garman_klass_volatility(cFull10m.open_, cFull10m.high, cFull10m.low, cFull10m.close, 1)
            gkvol15m_full = garman_klass_volatility(cFull15m.open_, cFull15m.high, cFull15m.low, cFull15m.close, 1)
            gkvol30m_full = garman_klass_volatility(cFull30m.open_, cFull30m.high, cFull30m.low, cFull30m.close, 1)
            logger.info(f"gk spot vol full 5m: {gkvol5m_full:.2%}, 10m: {gkvol10m_full:.2%}, 15m: {gkvol15m_full:.2%}, 30m: {gkvol30m_full:.2%}")
        # # NPMKTOPENIDX is used throughout, make sure it's set at all times
        # global NPMKTOPENIDX
        # if NPMKTOPENIDX < 0:
        #     results = np.ravel(np.where(bars.npdate_ == NPMKTOPEN))
        #     if len(results) > 0:
        #         # FIXME
        #         NPMKTOPENIDX = results[0]
        #         # logger.info(f"market open idx={NPMKTOPENIDX} date={bars.npdate_[NPMKTOPENIDX:NPMKTOPENIDX+3]}")
        #     else:
        #         NPMKTOPENIDX = -1_000
        #         idx = bars._npidx - 3
        #         logger.warning(f"market is not open: {bars.npdate_[0:3]}..{bars.npdate_[idx:]}")
        #         # should we bail?
        
        if (currentBar.date == MKTOPEN or 
          (MKTOPEN+datetime.timedelta(seconds=-30) <= currentBar.date and currentBar.date <= MKTOPEN+datetime.timedelta(seconds=30))) and hasNewBar:
            logger.info(f"mktopen: {bars._npidx} {bars._npidx_rth_start} {bars._npidx_rth_end}")
            if self.use5s:
                logger.info(f"bars: {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
                # logger.info(f"bars10s: {self.bars10s._npidx} {self.bars10s._npidx_rth_start} {self.bars10s._npidx_rth_end}")
                # logger.info(f"bars15s: {self.bars15s._npidx} {self.bars15s._npidx_rth_start} {self.bars15s._npidx_rth_end}")
                # logger.info(f"bars30s: {self.bars30s._npidx} {self.bars30s._npidx_rth_start} {self.bars30s._npidx_rth_end}")
                # logger.info(f"bars2m: {self.bars2m._npidx} {self.bars2m._npidx_rth_start} {self.bars2m._npidx_rth_end}")
                # logger.info(f"bars5m: {self.bars5m._npidx} {self.bars5m._npidx_rth_start} {self.bars5m._npidx_rth_end}")
                # logger.info(f"bars10m: {self.bars10m._npidx} {self.bars10m._npidx_rth_start} {self.bars10m._npidx_rth_end}")
                # logger.info(f"bars15m: {self.bars15m._npidx} {self.bars15m._npidx_rth_start} {self.bars15m._npidx_rth_end}")
        elif currentBar.date == MKTCLOSE and hasNewBar:
            logger.info(f"mkclose: {bars._npidx} {bars._npidx_rth_start} {bars._npidx_rth_end}")
            if self.use5s:
                logger.info(f"bars: {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
                # logger.info(f"bars10s: {self.bars10s._npidx} {self.bars10s._npidx_rth_start} {self.bars10s._npidx_rth_end}")
                # logger.info(f"bars15s: {self.bars15s._npidx} {self.bars15s._npidx_rth_start} {self.bars15s._npidx_rth_end}")
                # logger.info(f"bars30s: {self.bars30s._npidx} {self.bars30s._npidx_rth_start} {self.bars30s._npidx_rth_end}")
                # logger.info(f"bars2m: {self.bars2m._npidx} {self.bars2m._npidx_rth_start} {self.bars2m._npidx_rth_end}")
                # logger.info(f"bars5m: {self.bars5m._npidx} {self.bars5m._npidx_rth_start} {self.bars5m._npidx_rth_end}")
                # logger.info(f"bars10m: {self.bars10m._npidx} {self.bars10m._npidx_rth_start} {self.bars10m._npidx_rth_end}")
                # logger.info(f"bars15m: {self.bars15m._npidx} {self.bars15m._npidx_rth_start} {self.bars15m._npidx_rth_end}")
        else:
            logger.info(f"{len(bars)} {bars._npidx} {bars._npidx_rth_start} {bars._npidx_rth_end}")
            # if self.use5s:
            #     logger.info(f"bars: {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
                # logger.info(f"bars10s: {self.bars10s._npidx} {self.bars10s._npidx_rth_start} {self.bars10s._npidx_rth_end}")
                # logger.info(f"bars15s: {self.bars15s._npidx} {self.bars15s._npidx_rth_start} {self.bars15s._npidx_rth_end}")
                # logger.info(f"bars30s: {self.bars30s._npidx} {self.bars30s._npidx_rth_start} {self.bars30s._npidx_rth_end}")
                # logger.info(f"bars2m: {self.bars2m._npidx} {self.bars2m._npidx_rth_start} {self.bars2m._npidx_rth_end}")
                # logger.info(f"bars5m: {self.bars5m._npidx} {self.bars5m._npidx_rth_start} {self.bars5m._npidx_rth_end}")
                # logger.info(f"bars10m: {self.bars10m._npidx} {self.bars10m._npidx_rth_start} {self.bars10m._npidx_rth_end}")
                # logger.info(f"bars15m: {self.bars15m._npidx} {self.bars15m._npidx_rth_start} {self.bars15m._npidx_rth_end}")

        if currentBar.high - currentBar.low > 0 or currentBar.close - currentBar.open_ > 0:
            gkvol_1 = garman_klass_volatility(currentBar.open_, currentBar.high, currentBar.low, currentBar.close, 1)
            rsvol_1 = rogers_satchell_volatility(currentBar.open_, currentBar.high, currentBar.low, currentBar.close, 1)
            pkvol_1 = parkinson_volatility(currentBar.high, currentBar.low, 1)
            logger.info(f"spot vol[-1] GK {gkvol_1:.3%}, RS {rsvol_1:.3%}, PK {pkvol_1:.3%}")
        else:
            gkvol_1 = rsvol_1 = pkvol_1 = 0.0
            logger.warning(f"spot vol[-1] zero")
        if currentFullBar.high - currentFullBar.low > 0 or currentFullBar.close - currentFullBar.open_ > 0:
            gkvol_2 = garman_klass_volatility(currentFullBar.open_, currentFullBar.high, currentFullBar.low, currentFullBar.close, 1)
            rsvol_2 = rogers_satchell_volatility(currentFullBar.open_, currentFullBar.high, currentFullBar.low, currentFullBar.close, 1)
            pkvol_2 = parkinson_volatility(currentFullBar.high, currentFullBar.low, 1)
            logger.info(f"spot vol[-2] GK {gkvol_2:.3%}, RS {rsvol_2:.3%}, PK {pkvol_2:.3%}")
        else:
            gkvol_2 = rsvol_2 = pkvol_2 = 0.0
            logger.warning(f"spot vol[-2] zero")

        # open_prices_old = np.asarray([bar.open_ for bar in bars if bar.date >= MKTOPEN and bar.date < MKTCLOSE])
        open_prices = bars.npopen
        high_prices = bars.nphigh
        low_prices = bars.nplow
        close_prices = bars.npclose
        # if not np.isclose(bars.npopen, open_prices_old, atol=1e-3).all():
        #     logger.warning(f"open_prices != open_prices_old: {bars.npopen} != {open_prices_old}")
        n = len(open_prices)
        if n > 0:
            # high_prices = np.asarray([bar.high for bar in bars if bar.date >= MKTOPEN and bar.date < MKTCLOSE])
            # low_prices = np.asarray([bar.low for bar in bars if bar.date >= MKTOPEN and bar.date < MKTCLOSE])
            # close_prices = np.asarray([bar.close for bar in bars if bar.date >= MKTOPEN and bar.date < MKTCLOSE])
            # if not np.isclose(bars.nphigh, high_prices, atol=1e-3).all():
            #     logger.warning(f"high_prices != high_prices_old: {bars.nphigh} != {high_prices}")
            # if not np.isclose(bars.nplow, low_prices, atol=1e-3).all():
            #     logger.warning(f"low_prices != low_prices_old: {bars.nplow} != {low_prices}")
            # if not np.isclose(bars.npclose, close_prices, atol=1e-3).all():
            #     logger.warning(f"close_prices != close_prices_old: {bars.npclose} != {close_prices}")

            # idx_end = bars._npidx # zeros beyond bars.idx, be careful
            # if (idx_end-1)>0 and bars.npdate_[idx_end-1] >= NPMKTCLOSE:
            #     j = np.ravel(np.where(bars.npdate_ >= NPMKTCLOSE))
            #     idx_end = (j[0] if len(j) > 0 else idx_end-1)
            #     # if idx_end != bars.idx - 1:
            #     logger.info(f"idx_end-1={idx_end-1}, bars.npdate_[idx_end-1:idx_end+1]={bars.npdate_[idx_end-1:idx_end+1]}")
            # nnp = len(bars.low_prices[NPMKTOPENIDX:idx_end])
            # if n != nnp:
            #     logger.error(f"vol calculation n={n} != nnp={nnp}")
            # else:
            #     logger.info(f"vol calculation, n={n}, nnp={nnp}")

            gkvol = garman_klass_volatility(open_prices, high_prices, low_prices, close_prices, n)
            # gkvolnp = garman_klass_volatility(bars.open_prices[NPMKTOPENIDX:idx_end], bars.high_prices[NPMKTOPENIDX:idx_end]
            #     , bars.low_prices[NPMKTOPENIDX:idx_end], bars.close_prices[NPMKTOPENIDX:idx_end], nnp)
            # if not math.isclose(gkvol, gkvolnp, abs_tol=1e-6):
            #     logger.info(f"garman-klass vol DIFFERENCE {gkvol:.4%} {gkvolnp:.4%}")
            logger.info(f"garman-klass run vol {gkvol:.3%}/min {annualization_factor_390 * gkvol:.2%}/d {annualization_factor_5_390 * gkvol:.2%}/5d {annualization_factor_21_390 * gkvol:.2%}/21d {annualization_factor_252_390 * gkvol:.2%}/y")

            rsvol = rogers_satchell_volatility(open_prices, high_prices, low_prices, close_prices, n)
            # rsvolnp = rogers_satchell_volatility(bars.open_prices[NPMKTOPENIDX:idx_end], bars.high_prices[NPMKTOPENIDX:idx_end]
            #     , bars.low_prices[NPMKTOPENIDX:idx_end], bars.close_prices[NPMKTOPENIDX:idx_end], nnp)
            # if not math.isclose(rsvol, rsvolnp, abs_tol=1e-6):
            #     logger.info(f"rogers-satchell vol DIFFERENCE {rsvol:.4%} {rsvolnp:.4%}")
            logger.info(f"rogers-satchell run vol {rsvol:.3%}/min {annualization_factor_390 * rsvol:.2%}/d {annualization_factor_5_390 * rsvol:.2%}/5d {annualization_factor_21_390 * rsvol:.2%}/21d {annualization_factor_252_390 * rsvol:.2%}/y")

            pkvol = parkinson_volatility(high_prices, low_prices, n)
            # pkvolnp = parkinson_volatility(bars.high_prices[NPMKTOPENIDX:idx_end], bars.low_prices[NPMKTOPENIDX:idx_end], nnp)
            # if not math.isclose(pkvol, pkvolnp, abs_tol=1e-6):
            #     logger.info(f"parkinson vol DIFFERENCE {pkvol:.4%} {pkvolnp:.4%}")
            logger.info(f"parkinson run vol {pkvol:.3%}/min {annualization_factor_390 * pkvol:.2%}/d {annualization_factor_5_390 * pkvol:.2%}/5d {annualization_factor_21_390 * pkvol:.2%}/21d {annualization_factor_252_390 * pkvol:.2%}/y")

            # logger.info(f"yang-zhang vol {annualization_factor * yang_zhang_volatility(open_prices, high_prices, low_prices, close_prices, n):.2%}")

            # logger.info(f"{bars.high_prices[NPMKTOPENIDX:idx_end]}, {bars.low_prices[NPMKTOPENIDX:idx_end]}, {nnp}")
            # logger.info(f"parkinson vol "
            #     f"(raw) {parkinson_volatility(high_prices, low_prices, n):.4%} {pkvol:.4%},"
            #     f" (day) {annualization_factor_390 * pkvol:.2%},"
            #     f" (ann) {annualization_factor_252_390 * pkvol:.2%}"
            # )
            if self.use5s:
                gkrunvol3m = garman_klass_volatility(self.bars3m.npopen, self.bars3m.nphigh, self.bars3m.nplow, self.bars3m.npclose, len(self.bars3m.npopen))
                gkrunvol5m = garman_klass_volatility(self.bars5m.npopen, self.bars5m.nphigh, self.bars5m.nplow, self.bars5m.npclose, len(self.bars5m.npopen))
                gkrunvol10m = garman_klass_volatility(self.bars10m.npopen, self.bars10m.nphigh, self.bars10m.nplow, self.bars10m.npclose, len(self.bars10m.npopen))
                gkrunvol15m = garman_klass_volatility(self.bars15m.npopen, self.bars15m.nphigh, self.bars15m.nplow, self.bars15m.npclose, len(self.bars15m.npopen))
                gkrunvol30m = garman_klass_volatility(self.bars30m.npopen, self.bars30m.nphigh, self.bars30m.nplow, self.bars30m.npclose, len(self.bars30m.npopen))
                logger.info(f"gk run vol 5m {gkrunvol5m:.3%}, 10m {gkrunvol10m:.3%}, 15m {gkrunvol15m:.3%}, 30m {gkrunvol30m:.3%}")
        else:
            logger.warning(f"outside RTH")
            open_prices = bars.open_prices[:bars._npidx]
            high_prices = bars.high_prices[:bars._npidx]
            low_prices = bars.low_prices[:bars._npidx]
            close_prices = bars.close_prices[:bars._npidx]
            n = bars._npidx
            # check for zero prices and print the index
            if (open_prices == 0).any():
                logger.warning(f"open_prices zero at {np.where(open_prices == 0)}")
            if (high_prices == 0).any():
                logger.warning(f"high_prices zero at {np.where(high_prices == 0)}")
            if (low_prices == 0).any():
                logger.warning(f"low_prices zero at {np.where(low_prices == 0)}")
            if (close_prices == 0).any():
                logger.warning(f"close_prices zero at {np.where(close_prices == 0)}")
            gkvol = rsvol = pkvol = 0.0
            gkvol = garman_klass_volatility(open_prices, high_prices, low_prices, close_prices, n)
            logger.info(f"garman-klass run vol {gkvol:.3%}/min {annualization_factor_390 * gkvol:.2%}/d {annualization_factor_5_390 * gkvol:.2%}/5d {annualization_factor_21_390 * gkvol:.2%}/21d {annualization_factor_252_390 * gkvol:.2%}/y")

            rsvol = rogers_satchell_volatility(open_prices, high_prices, low_prices, close_prices, n)
            logger.info(f"rogers-satchell run vol {rsvol:.3%}/min {annualization_factor_390 * rsvol:.2%}/d {annualization_factor_5_390 * rsvol:.2%}/5d {annualization_factor_21_390 * rsvol:.2%}/21d {annualization_factor_252_390 * rsvol:.2%}/y")

            pkvol = parkinson_volatility(high_prices, low_prices, n)
            logger.info(f"parkinson run vol {pkvol:.3%}/min {annualization_factor_390 * pkvol:.2%}/d {annualization_factor_5_390 * pkvol:.2%}/5d {annualization_factor_21_390 * pkvol:.2%}/21d {annualization_factor_252_390 * pkvol:.2%}/y")

        # logger.info(f"current bar: {currentBar.date.isoformat()}, MKTOPEN {MKTOPEN.isoformat()}, MKTCLOSE {MKTCLOSE.isoformat()}")
        if currentBar.date >= MKTOPEN and currentBar.date <= MKTCLOSE:
            if not self.dayhilopct: # initialize
                # logger.info(f"initialize dayhilopct")
                # self.dayhilopct = deque(maxlen=int(12*60*6.5))
                z = []
                for d in [b.date for b in bars if b.date >= MKTOPEN]:
                    # calculate running high/low pct
                    x = [b for b in bars if b.date >= MKTOPEN and b.date <= d]
                    y = dayhilo(x)[16:20] + (d,) # (curratio_avg, curratio_high, curratio_low, curratio_close, date)
                    z.append(BarData(average=y[0], high=y[1], low=y[2], close=y[3], date=y[4]))
                logger.debug(f"len(z)={len(z)}")
                logger.debug(f"z.head={_repr_hilopctlst(z[:5])} z.tail={_repr_hilopctlst(z[-5:])}")
                logger.debug(f"initialize dayhilopct")
                self.dayhilopct = deque(z, maxlen=int(12*60*6.5))
                # self.dayhilopct.extend(z)

            (dayhigh_avg, dayhigh_high, dayhigh_low, dayhigh_close, 
             daylow_avg, daylow_high, daylow_low, daylow_close, 
             dayhl_avg, dayhl_high, dayhl_low, dayhl_close, 
             dayloghl_avg, dayloghl_high, dayloghl_low, dayloghl_close, 
             curratio_avg, curratio_high, curratio_low, curratio_close) = dayhilo(bars)
            #logger.debug(f"self.dayhilopct={self.dayhilopct[-5:]}")
            if hasNewBar or not self.dayhilopct: # new bar or first bar
                self.dayhilopct.append(BarData(average=curratio_avg, high=curratio_high, low=curratio_low, close=curratio_close, date=currentBar.date))
            else:
                self.dayhilopct[-1] = BarData(average=curratio_avg, high=curratio_high, low=curratio_low, close=curratio_close, date=currentBar.date)

            logger.info(f"day hi (a,h,l,c): {dayhigh_avg:.2f} {dayhigh_high:.2f} {dayhigh_low:.2f} {dayhigh_close:.2f}")
            logger.info(f"day lo (a,h,l,c): {daylow_avg:.2f} {daylow_high:.2f} {daylow_low:.2f} {daylow_close:.2f}")
            logger.info(f"log day hi/lo (a,h,l,c): {dayloghl_avg:.2%} {dayloghl_high:.2%} {dayloghl_low:.2%} {dayloghl_close:.2%} ({dayhl_avg-1.:.2%} {dayhl_high-1.:.2%} {dayhl_low-1.:.2%} {dayhl_close-1.:.2%})")
            logger.info(f"cur%: {curratio_avg:.1%} {curratio_high:.1%} {curratio_low:.1%} {curratio_close:.1%}")
            absolute_low_thres = 0.0004
            self.absolute_low = (curratio_avg < absolute_low_thres and curratio_high < absolute_low_thres and curratio_low < absolute_low_thres and curratio_close < absolute_low_thres) \
                or (curratio_avg < absolute_low_thres and curratio_high < absolute_low_thres) or (curratio_low < absolute_low_thres and curratio_close < absolute_low_thres) \
                or (curratio_high < absolute_low_thres and curratio_close < absolute_low_thres) or (curratio_avg < absolute_low_thres and curratio_high < absolute_low_thres)
            absolute_high_thres = 0.9995
            self.absolute_high = curratio_avg >= absolute_high_thres and curratio_high >= absolute_high_thres and curratio_low >= absolute_high_thres and curratio_close >= absolute_high_thres
            self.absolute_low_last30m = self.absolute_low_last15m = self.absolute_low_last10m = self.absolute_low_last5m = False
            self.absolute_high_last30m = self.absolute_high_last15m = self.absolute_high_last10m = self.absolute_high_last5m = False
            five_minutes = 5*60 # 5 minutes in seconds
            ten_minutes = 10*60 # 10 minutes in seconds
            fifteen_minutes = 15*60 # 15 minutes in seconds
            thirty_minutes = 30*60 # 30 minutes in seconds
            if self.absolute_low and not self.seen_abs_low:
                self.seen_abs_low.append(dtnow)
                self.absolute_low_last5m = False # first time seen, we don't care
            elif self.absolute_low and self.seen_abs_low and (dtnow - self.seen_abs_low[-1]).total_seconds() < five_minutes:
                logger.info(f"absolute low within 5 minutes")
                self.seen_abs_low[-1] = dtnow
                self.absolute_low_last5m = True
            elif not self.absolute_low and self.seen_abs_low and (dtnow - self.seen_abs_low[-1]).total_seconds() < five_minutes:
                logger.info(f"absolute low within 5 minutes")
                self.absolute_low_last5m = True
            elif self.absolute_low and self.seen_abs_low and (dtnow - self.seen_abs_low[-1]).total_seconds() >= five_minutes:
                self.seen_abs_low.append(dtnow)
                logger.info(f"seen_abs_low: count={len(self.seen_abs_low)}")
                self.absolute_low_last5m = False # seeing it again for the first time after the previous 5 minutes interval
            else:
                pass

            if self.absolute_high and not self.seen_abs_high:
                self.seen_abs_high.append(dtnow)
                self.absolute_high_last5m = False # first time seen, we don't care
            elif self.absolute_high and self.seen_abs_high and (dtnow - self.seen_abs_high[-1]).total_seconds() < five_minutes:
                logger.info(f"absolute high within 5 minutes")
                self.seen_abs_high[-1] = dtnow
                self.absolute_high_last5m = True
            elif not self.absolute_high and self.seen_abs_high and (dtnow - self.seen_abs_high[-1]).total_seconds() < five_minutes:
                logger.info(f"absolute high within 5 minutes")
                self.absolute_high_last5m = True
            elif self.absolute_high and self.seen_abs_high and (dtnow - self.seen_abs_high[-1]).total_seconds() >= five_minutes:
                self.seen_abs_high.append(dtnow)
                logger.info(f"seen_abs_high: count={len(self.seen_abs_high)}")
                self.absolute_high_last5m = False # seeing it again for the first time after the previous 5 minutes interval
            else:
                pass

            # match (self.absolute_high, bool(self.seen_abs_high), (dtnow - self.seen_abs_high[-1]).total_seconds() if self.seen_abs_high else None):
            #     case (True, False, _):
            #         self.seen_abs_high.append(dtnow)
            #         self.absolute_high_last5m = False # first time seen, we don't care
            #     case (True, True, seconds) if seconds < 5*60:
            #         logger.info(f"absolute high within 5 minutes")
            #         self.seen_abs_high[-1] = dtnow
            #         self.absolute_high_last5m = True
            #     case (False, True, seconds) if seconds < 5*60:
            #         logger.info(f"absolute high within 5 minutes")
            #         self.absolute_high_last5m = True
            #     case (True, True, seconds) if seconds >= 5*60:
            #         self.seen_abs_high.append(dtnow)
            #         self.absolute_high_last5m = False # seeing it again for the first time after the previous 5 minutes interval
            #     case _:
            #         pass

            # logger.info(f"30m: {self.bars30m[-10:]}")
            self.b30m_serially_lower_avg = [bb[0].average > bb[1].average for bb in pairwise(self.bars30m)]
            self.b30m_serially_lower_high = [bb[0].high > bb[1].high for bb in pairwise(self.bars30m)]
            self.b30m_serially_lower_low = [bb[0].low > bb[1].low for bb in pairwise(self.bars30m)]
            self.b30m_serially_lower_close = [bb[0].close > bb[1].close for bb in pairwise(self.bars30m)]
            logger.info(f"30m serially lower avg: {list(map(int, self.b30m_serially_lower_avg[-10:]))}")
            logger.info(f"30m serially lower high: {list(map(int, self.b30m_serially_lower_high[-10:]))}")
            logger.info(f"30m serially lower low: {list(map(int, self.b30m_serially_lower_low[-10:]))}")
            logger.info(f"30m serially lower close: {list(map(int, self.b30m_serially_lower_close[-10:]))}")

            self.b15m_serially_lower_avg = [bb[0].average > bb[1].average for bb in pairwise(self.bars15m)]
            self.b15m_serially_lower_high = [bb[0].high > bb[1].high for bb in pairwise(self.bars15m)]
            self.b15m_serially_lower_low = [bb[0].low > bb[1].low for bb in pairwise(self.bars15m)]
            self.b15m_serially_lower_close = [bb[0].close > bb[1].close for bb in pairwise(self.bars15m)]
            logger.info(f"15m serially lower avg: {list(map(int, self.b15m_serially_lower_avg[-10:]))}")
            logger.info(f"15m serially lower high: {list(map(int, self.b15m_serially_lower_high[-10:]))}")
            logger.info(f"15m serially lower low: {list(map(int, self.b15m_serially_lower_low[-10:]))}")
            logger.info(f"15m serially lower close: {list(map(int, self.b15m_serially_lower_close[-10:]))}")

            self.b5m_serially_lower_avg = [bb[0].average > bb[1].average for bb in pairwise(self.bars5m)]
            self.b5m_serially_lower_high = [bb[0].high > bb[1].high for bb in pairwise(self.bars5m)]
            self.b5m_serially_lower_low = [bb[0].low > bb[1].low for bb in pairwise(self.bars5m)]
            self.b5m_serially_lower_close = [bb[0].close > bb[1].close for bb in pairwise(self.bars5m)]
            logger.info(f"5m serially lower avg: {list(map(int, self.b5m_serially_lower_avg[-10:]))}")
            logger.info(f"5m serially lower high: {list(map(int, self.b5m_serially_lower_high[-10:]))}")
            logger.info(f"5m serially lower low: {list(map(int, self.b5m_serially_lower_low[-10:]))}")
            logger.info(f"5m serially lower close: {list(map(int, self.b5m_serially_lower_close[-10:]))}")

            self.b3m_serially_lower_avg = [bb[0].average > bb[1].average for bb in pairwise(self.bars3m)]
            self.b3m_serially_lower_high = [bb[0].high > bb[1].high for bb in pairwise(self.bars3m)]
            self.b3m_serially_lower_low = [bb[0].low > bb[1].low for bb in pairwise(self.bars3m)]
            self.b3m_serially_lower_close = [bb[0].close > bb[1].close for bb in pairwise(self.bars3m)]
            logger.info(f"3m serially lower avg: {list(map(int, self.b3m_serially_lower_avg[-10:]))}")
            logger.info(f"3m serially lower high: {list(map(int, self.b3m_serially_lower_high[-10:]))}")
            logger.info(f"3m serially lower low: {list(map(int, self.b3m_serially_lower_low[-10:]))}")
            logger.info(f"3m serially lower close: {list(map(int, self.b3m_serially_lower_close[-10:]))}")

            self.b1m_serially_lower_avg = [bb[0].average > bb[1].average for bb in pairwise(self.bars)]
            self.b1m_serially_lower_high = [bb[0].high > bb[1].high for bb in pairwise(self.bars)]
            self.b1m_serially_lower_low = [bb[0].low > bb[1].low for bb in pairwise(self.bars)]
            self.b1m_serially_lower_close = [bb[0].close > bb[1].close for bb in pairwise(self.bars)]
            logger.info(f"1m serially lower avg: {list(map(int, self.b1m_serially_lower_avg[-10:]))}")
            logger.info(f"1m serially lower high: {list(map(int, self.b1m_serially_lower_high[-10:]))}")
            logger.info(f"1m serially lower low: {list(map(int, self.b1m_serially_lower_low[-10:]))}")
            logger.info(f"1m serially lower close: {list(map(int, self.b1m_serially_lower_close[-10:]))}")

            # volatility
            if not self.volatility_per_min:
                z = []
                # bars_since_open = [b for b in bars if b.date >= MKTOPEN]
                # for b in bars_since_open:
                #     # calculate per minute spot volatility
                #     gkvol_1_tmp = garman_klass_volatility(b.open_, b.high, b.low, b.close, 1)
                #     rsvol_1_tmp = rogers_satchell_volatility(b.open_, b.high, b.low, b.close, 1)
                #     pkvol_1_tmp = parkinson_volatility(b.high, b.low, 1)
                #     # x = [b for b in bars if b.date >= MKTOPEN and b.date <= d]
                #     # y = dayhilo(x)[16:20] + (d,) # (curratio_avg, curratio_high, curratio_low, curratio_close, date)
                #     vol_tup_tmp = (gkvol_1_tmp, rsvol_1_tmp, pkvol_1_tmp)
                #     z.append(vol_tup_tmp)
                # logger.debug(f"len(z)={len(z)}")
                # logger.debug(f"z.head={_repr_vol_tup_lst(z[:3])} z.tail={_repr_vol_tup_lst(z[-3:])}")
                # logger.debug(f"initialize volatility_per_min")
                # self.volatility_per_min = deque(z, maxlen=int(60*6.5)) # 1 minute resolution

                # running vols
                for i in range(1, len(self.bars.npopen)+1):
                    gkvol_tmp = garman_klass_volatility(self.bars.npopen[:i], self.bars.nphigh[:i], self.bars.nplow[:i], self.bars.npclose[:i], i)
                    rsvol_tmp = rogers_satchell_volatility(self.bars.npopen[:i], self.bars.nphigh[:i], self.bars.nplow[:i], self.bars.npclose[:i], i)
                    pkvol_tmp = parkinson_volatility(self.bars.nphigh[:i], self.bars.nplow[:i], i)
                    logger.info(f"running vol {i} GK {gkvol_tmp:.3%}, RS {rsvol_tmp:.3%}, PK {pkvol_tmp:.3%}")
                    vol_tup_tmp = (gkvol_tmp, rsvol_tmp, pkvol_tmp)
                    z.append(vol_tup_tmp)
                if len(self.bars.npopen) == 0:
                    # outside RTH
                    gkvol_tmp = rsvol_tmp = pkvol_tmp = 0.0
                    for i in range(1, self.bars._npidx+1):
                        gkvol_tmp = garman_klass_volatility(self.bars.open_prices[:i], self.bars.high_prices[:i], self.bars.low_prices[:i], self.bars.close_prices[:i], i)
                        rsvol_tmp = rogers_satchell_volatility(self.bars.open_prices[:i], self.bars.high_prices[:i], self.bars.low_prices[:i], self.bars.close_prices[:i], i)
                        pkvol_tmp = parkinson_volatility(self.bars.high_prices[:i], self.bars.low_prices[:i], i)
                        logger.info(f"running vol {i} GK {gkvol_tmp:.3%}, RS {rsvol_tmp:.3%}, PK {pkvol_tmp:.3%}")
                        vol_tup_tmp = (gkvol_tmp, rsvol_tmp, pkvol_tmp)
                        z.append(vol_tup_tmp)
                logger.debug(f"len(z)={len(z)} len(bars)={len(self.bars)} len(bars.open_prices)={len(self.bars.open_prices)}")
                logger.debug(f"z.head={_repr_vol_tup_lst(z[:3])} z.tail={_repr_vol_tup_lst(z[-3:])}")
                logger.debug(f"initialize volatility_per_min")
                # the last iteration is the current running vols
                if np.isclose(gkvol, gkvol_tmp, atol=1e-6) and np.isclose(rsvol, rsvol_tmp, atol=1e-6) and np.isclose(pkvol, pkvol_tmp, atol=1e-6):
                    logger.info(f"running vols init is looking good")
                else:
                    logger.warning(f"running vols init not matching: {gkvol:.3%} != {gkvol_tmp:.3%}, {rsvol:.3%} != {rsvol_tmp:.3%}, {pkvol:.3%} != {pkvol_tmp:.3%}")
                self.volatility_per_min = deque(z, maxlen=int(60*6.5)) # 1 minute resolution                    
            else:
                logger.info(f"volatility_per_min[-1]: {_repr_vol_tup(self.volatility_per_min[-1])}, len={len(self.volatility_per_min)}")

            # vol_tup = (gkvol_1, rsvol_1, pkvol_1)
            vol_tup = (gkvol, rsvol, pkvol) # running vol, not spot vol
            if hasNewBar or not self.volatility_per_min: # new bar or first bar
                self.volatility_per_min.append(vol_tup)
            else:
                self.volatility_per_min[-1] = vol_tup
        # rate of change
        roc = [(bars[-1].average / bars[-j].average - 1.0)/(j-1) for j in range(2, 11)]
        if len(bars) > 2:
            roc2 = [(bars[-1].average / bars[-j].average - 1.0)/(j-1) for j in range(2, min(11, len(bars)))]
            if not np.isclose(roc, roc2, atol=1e-6).all():
                logger.warning(f"roc != roc2: {roc} != {roc2}")
            logger.info(f"roc {', '.join([f"{x:.3%}" for x in roc])}")
        # high minus low
        hml_ = currentBar.high - currentBar.low
        hmlpct_ = hml_ / self.prevclose
        if hasNewBar or self.hml == []: # new bar or first bar
            fbhml_ = currentFullBar.high - currentFullBar.low
            # if self.hml and fbhml_ != self.hml[-1]:
            #     logger.warning(f"currentFullBar hml != hml[-1]: {currentFullBar} != {self.hml[-1]}")
            #     self.hml[-1] = currentFullBar.high - currentFullBar.low
            self.hml.append(hml_)
            self.hml_pct.append(hmlpct_)
        else:
            self.hml[-1] = hml_ # update the last element
            self.hml_pct[-1] = hmlpct_
        # self.lastPrice = get_market_price() # sample the market price # was bars[-1].close
        self.hmlstat.update(int(hmlpct_ * 100.0)) # update hml in cents

        # update high water mark since last buy, for the purpose of calculating drawdown
        needCheckpoint = False
        if self.high_since_buy_bar1m:
            b = self.high_since_buy_bar1m[-1] # just for shortening
            prev = BarData(b.date, b.open_, b.high, b.low, b.close, b.volume, b.average)
            if b.average <= currentBar.average:
                # prev = self.high_since_buy_bar1m[-1].copy()
                # self.high_since_buy_bar1m[-1] = currentBar
                self.high_since_buy_bar1m.clear()
                self.high_since_buy_bar1m.append(copy.copy(currentBar))
                needCheckpoint = True
                logger.info(f"high_since_buy_bar1m from {_repr_bar(prev)} to cbar {_repr_bar(self.high_since_buy_bar1m[-1])}")
            if b.average <= currentFullBar.average:
                # prev = self.high_since_buy_bar1m[-1].copy()
                # self.high_since_buy_bar1m[-1] = currentFullBar
                self.high_since_buy_bar1m.clear()
                self.high_since_buy_bar1m.append(copy.copy(currentFullBar))
                needCheckpoint = True
                logger.info(f"high_since_buy_bar1m from {_repr_bar(prev)} to fbar {_repr_bar(self.high_since_buy_bar1m[-1])}")
        # we initialize it when we buy or when session starts and have position
        # else:
        #     self.high_since_buy_bar1m.append(currentBar)
        #     needCheckpoint = True
        
        # blur filter
        if currentBar.date >= MKTOPEN:
        # if hasNewBar: # at the minute
            # vec = np.array([bar.average for bar in bars[-5:]])
            # vec_raw_old = np.asarray([bar.average for bar in bars if bar.date >= MKTOPEN and bar.date < MKTCLOSE])
            vec_raw = bars.npaverage
            # if not np.isclose(vec_raw, vec_raw_old, atol=1e-3).all():
            #     logger.warning(f"vec_raw != vec_raw_old: {vec_raw} != {vec_raw_old}")
            if len(vec_raw) > 0:
              with np.printoptions(suppress=True, formatter={'float': lambda x: f'{x:.4f}'}):
                vec = vec_raw[-60:] # (vec_raw / self.prevclose - 1.) * 1000 # 0.123% -> 1.23
                # if len(vec) >= 5:
                # mult = 1000.0/self.prevclose
                trunc_param = 36.0
                mode_param = 'nearest'
                # model = GaussianHMM(n_components=3, covariance_type="full", n_iter=1000)
                # model.fit(vec.reshape(-1, 1))
                # logger.info(f"model.means_={model.means_}, model.covars_={model.covars_}, model.transmat_={model.transmat_}")
                sm_s2 = gaussian_filter1d(vec, sigma=2, mode=mode_param, truncate=trunc_param)
                sm_s2_der1 = gaussian_filter1d(vec, sigma=2, mode=mode_param, order=1, truncate=trunc_param)
                self.direction_s2 = direction_s2 = "positive" if sm_s2_der1[-1] > 0 else "negative"
                sm_s3 = gaussian_filter1d(vec, sigma=3, mode=mode_param, truncate=trunc_param)
                sm_s3_der1 = gaussian_filter1d(vec, sigma=3, mode=mode_param, order=1, truncate=trunc_param)
                sm_s3_norm5 = np.linalg.norm(sm_s3_der1[-5:]/len(sm_s3_der1[-5:])/self.prevclose)
                self.direction_s3 = direction_s3 = "positive" if sm_s3_der1[-1] > 0 else "negative"
                sm_s5 = gaussian_filter1d(vec, sigma=5, mode=mode_param, truncate=trunc_param)
                sm_s5_der1 = gaussian_filter1d(vec, sigma=5, mode=mode_param, order=1, truncate=trunc_param)
                sm_s16 = gaussian_filter1d(vec, sigma=16, mode=mode_param, truncate=trunc_param)
                sm_s16_der1 = gaussian_filter1d(vec, sigma=16, mode=mode_param, order=1, truncate=trunc_param)
                self.direction_s16 = direction_s16 = "positive" if sm_s16_der1[-1] > 0 else "negative"
                sm_s16_norm60 = np.linalg.norm(sm_s16_der1[-5:]/len(sm_s16_der1[-5:])/self.prevclose)
                sm_s24 = gaussian_filter1d(vec, sigma=24, mode=mode_param, truncate=trunc_param)
                sm_s24_der1 = gaussian_filter1d(vec, sigma=24, mode=mode_param, order=1, truncate=trunc_param)
                sm_s24_norm60 = np.linalg.norm(sm_s24_der1[-5:]/len(sm_s24_der1[-5:])/self.prevclose)
                self.direction_s24 = direction_s24 = "positive" if sm_s24_der1[-1] > 0 else "negative"
                logger.info(f"vec: {vec[-5:]}")
                logger.info(f"sm_s2: {sm_s2[-5:]}")
                logger.info(f"sm_s2_der1: {sm_s2_der1[-5:]}")
                logger.info(f"sm_s3: {sm_s3[-5:]}")
                logger.info(f"sm_s3_der1: {sm_s3_der1[-5:]} {direction_s3} norm {sm_s3_norm5:.8f} {sm_s3_norm5/pkvol:.4%}")
                logger.info(f"sm_s5: {sm_s5[-5:]}")
                logger.info(f"sm_s5_der1: {sm_s5_der1[-5:]}")
                logger.info(f"sm_s16: {sm_s16[-5:]}")
                logger.info(f"sm_s16_der1: {sm_s16_der1[-5:]} {direction_s16} norm {sm_s16_norm60:.8f} {sm_s16_norm60/pkvol:.4%}")
                logger.info(f"sm_s24: {sm_s24[-5:]}")
                logger.info(f"sm_s24_der1: {sm_s24_der1[-5:]} {direction_s24} norm {sm_s24_norm60:.8f} {sm_s24_norm60/pkvol:.4%}")
                self.gf1 = gf1 = self.direction_s3 == 'positive' and self.direction_s16 == 'positive' and self.direction_s24 == 'positive' # gaussian filter 1
                self.gf1_serial.append(gf1)
                # if self.direction_s3 or self.direction_s16 or self.direction_s24:
                logger.info(f"gf1: direction_s3={self.direction_s3}, direction_s16={self.direction_s16}, direction_s24={self.direction_s24}")
                logger.info(f"gf1 serial: {list(map(int, slice_deque(self.gf1_serial, -12, -1)))}")
                max5m = maximum_filter1d(vec, size=5, mode=mode_param)
                min5m = minimum_filter1d(vec, size=5, mode=mode_param)
  
            # checkpoint as needed
            if needCheckpoint:
                # if currentBar.date.minute % 5 == 0 and currentBar.date.second == 0:
                self.checkpoint('high_since_buy_bar1m')

        # if (self.highsincestart == 0.0) or (self.highsincestart < bars[-1].high):
        #     self.highsincestart = bars[-1].high
        # if (self.lowsincestart == 0.0) or (self.lowsincestart > bars[-1].low):
        #     self.lowsincestart = bars[-1].low
        # self.testpnl = bars[-1].close - self.beginprice
        # logger.info(f"since start: hi/lo {self.highsincestart} {self.lowsincestart} ({self.highsincestart/self.lowsincestart:.2%})")

        # update agent's recent high and low
        # if self.recenthigh[1].high < bars[-1].high:
        #     self.recenthigh = (len(bars)-1, bars[-1])
        # if self.recentlow[1].low > bars[-1].low:
        #     self.recentlow = (len(bars)-1, bars[-1])
        
        # schedule strategy execution
        if self.strategy_tasks == set(): # if empty set, no tasks running
            match self.strategynum:
                case 1:
                    # check if strategy initialization is complete
                    if self.strategyinitstatus == -10:
                        logger.info(f"waiting for strategy initialization to complete")
                        return
                    elif self.strategyinitstatus == -1:
                        logger.error(f"Failed to initialize strategy, exiting...")
                        self.set_state(99) # bail out of main loop               
                        return
                    elif datetime.datetime.now(local_tz) > MKTCLOSE + datetime.timedelta(seconds=60):
                        start_mkt, end_mkt = get_market_hours()
                        logger.info(f"start_mkt={start_mkt}, end_mkt={end_mkt}")
                        logger.info(f"Market closed, exiting...")
                        self.set_state(99) # bail out of main loop
                    assert self.strategyinitstatus == 0, "Strategy initialization should return success"
                    logger.info(f"scheduling strategy #1")
                    task = asyncio.create_task(self.simpleLongStrategy1())
                case 2:
                    # beat daily return
                    # consider cases open to midday, 3pm to close; cases above prev close, below prev close, around prev close
                    # if long and above prev close, the usual long, milestone, hold on to gains. critical level is prev close. imagine long call with strike=prev close.
                    # if long and above prev close, trend down, sell above strike. if trend up, buy below strike.
                    # generally, want to be long above prev close, flat if not. if below prev close, wait until near close or trend up.
                    # if below prev close, no position, buy asap near low. if trend down, wait for lower low
                    # if below prev close, trend up, go long let it run
                    # if below prev close, trend down, if long sell asap, buy it back lower or after inflection point


                    pass
                case 3:
                    # stay on the right side of market most of the time. if not sure, stay out. (long/short)
                    # if long, stay long until trend changes, then sell and wait for next inflection point
                    # if short, stay short until trend changes, then buy and wait for next inflection point
                    logger.info(f"scheduling strategy #3")
                    task = asyncio.create_task(self.simplelongshort1())

                case 5:
                    # simple short strategy, sell at the day's high
                    logger.info(f"scheduling strategy #5")
                    task = asyncio.create_task(self.simpleShortStrategy1())

            self.strategy_tasks.add(task)
            task.add_done_callback(self.strategy_tasks.discard)
            await task
            task = None
        else:
            logger.info(f"strategy tasks running: {len(self.strategy_tasks)}")
            for task in self.strategy_tasks:
                logger.info(f"task: {task}")
                if task.done():
                    logger.info(f"task done: {task}")
                    self.strategy_tasks.remove(task)
                    logger.info(f"strategy tasks running: {len(self.strategy_tasks)}")
                    break
        
        return

    async def simplelongshort1(self):
        """
        Stay on the right side of market most of the time. if not sure, stay out. (long/short)
        if long, stay long until trend changes, then sell and wait for next inflection point
        if short, stay short until trend changes, then buy and wait for next inflection point
        """
        logger.info(f"simplelongshort1")
        return

    async def simpleShortStrategy1(self):
        """
        Simple short strategy, sell at the day's high
        """
        self.simpleShortStrategy1.x += 1
        logger.info(f"simpleShortStrategy1")
        if self.dayhilopct:
            dh_arr = extract_field_as_array(slice_deque(self.dayhilopct, -4, -1), 'high')
            dhmb_arr = dh_arr >= 0.98
            if dhmb_arr.all():
                logger.info(f"day high milestone breached")
        logger.info(f"high={self.ticker.high} ({self.ticker.high/self.ticker.close-1.:.2%}) low={self.ticker.low} ({self.ticker.low/self.ticker.close-1.:.2%}) close={self.ticker.close}")

        if self.get_state() in [0]:
            # no position, no outstanding trades
            if ((self.stkpos is None) or (self.stkpos.position == 0)) and self.trade is None:
                logger.info(f"No position, seeking entry ...")
                # if we see lower highs and lower lows, lower average and lower close and we are near day high and dhmb_arr is all True, sell
                pass
                return
            elif self.trade and self.trade in (openTrades := [t for t in ib.openTrades() if t.contract.symbol == self.symbol]):
                logger.info(f"Trade is still open: {openTrades}") # wait for trade to complete
                return
            elif self.trade and not (self.trade in ib.openTrades()):
                if self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade status: {self.trade}"
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                    # allow to proceed
                elif self.trade.orderStatus.status == 'Cancelled':
                    logger.error(f"Trade was cancelled: {self.trade}, undoing state change ({self.state} -> {self.prevstate}), resetting trade to None")
                    self.state = self.prevstate # undo state change
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    return
            else: # self.trade is None, stkpos is not None
                logger.error(f"Impossible state: state=0 but self.trade={self.trade} position={self.stkpos} and idxMilestone={self.idxMilestone}")
                return # don't allow to proceed
            
        elif self.get_state() == 1:
            # we have a position
            if (self.stkpos is None or self.stkpos.position == 0) and self.trade and self.trade in ib.openTrades():
                logger.info(f"Waiting for position update to complete...")
                return
            elif (self.stkpos is None or self.stkpos.position == 0) and self.trade and self.trade not in ib.openTrades():
                logger.error(f"Impossible state: state=1 but trade not in openTrades {self.trade}")
                return
            elif self.stkpos is None and not self.trade:
                logger.error(f"Impossible state: state=1 but no outstanding trade")
                return
            # if self.stkpos.position == 0:
            #     logger.error(f"Impossible state: state=1 but position={self.stkpos}")
            #     return
            # ensure no outstanding trades
            if self.trade:
                if self.trade in ib.openTrades():
                    logger.info(f"Trade is still open: {ib.openTrades()}")
                elif self.trade not in ib.openTrades() and self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade is filled: {self.trade.log}"
                    # self.state = 1
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logmsg = f"Trade not filled: {self.trade.log}"
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    logger.error(logmsg + f", resetting trade to None")
                    return # proceed or not?
        elif self.get_state() == 99:
            logger.warning(f"Exiting strategy...")
            # return # we'll exit at the end of the function
        
        return

    # @measure_time
    async def simpleLongStrategy1(self):
        """
        Simple long strategy
        input: avgCost, lastPrice, 
          maxloss: max loss threshold of the strategy
          array of upPctMilestone [0, 0.0025, 0.005, 0.0075, 0.01, ..., 10.0]
            first element is always 0, monotonically increasing, last element is some very large number
          array of stopLossPct [-0.001, -0.001, -0.001, ...] len(stopLossPct) = len(upPctMilestone)
          idx of current milestone (0, 1, 2, ...) (idx points to the last milestone crossed)
            if upPctMilestone[0] is not yet crossed, idx = -1
            we let the price stay between upPctMilestone[idx-1]+stopLossPct[idx] and upPctMilestone[idx], hoping to go to the next milestone
        the idea is every time we cross a milestone, don't let the price go below that milestone
          while keeping the position open, hoping to go to the next milestone
        when to exit? when we hit the stopLossPct for the current milestone or we hit the maxloss
        """

        def lastPctReturn():
            # avgCost_ = self.stkpos.avgCost * self.futAvgCostMult
            avgCost_ = self.useAvgCost * self.futAvgCostMult
            return (lastPrice_ / avgCost_) - 1.0 # life-to-date return

        def two_bars_green_with_one_close_near_high():
            """Check if the last two bars are green and at least one of them close near the high"""
            if len(self.bars) < 2:
                return False
            if (self.bars[-1].close > self.bars[-1].open_) and (self.bars[-2].close > self.bars[-2].open_):
                if (self.bars[-1].close > self.bars[-1].low + 0.8 * (self.bars[-1].high - self.bars[-1].low)):
                    return True
                if (self.bars[-2].close > self.bars[-2].low + 0.8 * (self.bars[-2].high - self.bars[-2].low)):
                    return True
            return False

        def two_bars_green_with_one_close_near_high_2() -> bool:
            """
            Check if the last two bars are green and at least one of them close near the high.
            Last two bars don't include the current bar.
            """
            retval = False
            if len(self.bars) < 3:
                logging.warning(f"len(bars)={len(self.bars)} < 3")
                return retval
            currentBar = self.bars[-1]
            # if currentBar.date < MKTOPEN:
            #     logging.warning(f"{currentBar.date.astimezone()} before rth")
            #     return retval
            # check if the last two bars are green
            tbg = self.bars[-2].close > self.bars[-2].open_ and self.bars[-3].close > self.bars[-3].open_
            # if one of them is yellow it's ok too
            # case in point: AMD 10/29/2024 9:35 and 9:36 bars
            tbg1y = (self.bars[-2].close > self.bars[-2].open_ and self.bars[-3].close == self.bars[-3].open_ or
                self.bars[-2].close == self.bars[-2].open_ and self.bars[-3].close > self.bars[-3].open_)
            # check if at least one of them close near the high
            cnhratio = 0.8
            hml2 = self.bars[-2].high - self.bars[-2].low
            hml3 = self.bars[-3].high - self.bars[-3].low
            cml2 = self.bars[-2].close - self.bars[-2].low
            cml3 = self.bars[-3].close - self.bars[-3].low
            cnh = (self.bars[-2].close >= self.bars[-2].low + cnhratio * hml2 or
                self.bars[-3].close >= self.bars[-3].low + cnhratio * hml3)
            cnhratio_actual2 = cml2 / hml2 if hml2 != 0 else 1.0
            cnhratio_actual3 = cml3 / hml3 if hml3 != 0 else 1.0
            if (tbg or tbg1y) and cnh:
                retval = True
            
            if tbg or tbg1y or cnh:
                logger.info(f"tbg={tbg} tbg1y={tbg1y} cnh ({cnhratio_actual2:.3},{cnhratio_actual3:.3})={cnh}")
                logger.info(f"bars[-2]={_repr_bar(self.bars[-2])} bars[-3]={_repr_bar(self.bars[-3])}")
            if hml2 <= self.ibcontractDetails[0].minTick or hml3 <= self.ibcontractDetails[0].minTick:
                logging.warning(f"hml too small, result invalid: hml2={hml2} hml3={hml3} minTick={self.ibcontractDetails[0].minTick}")
                return False
            if currentBar.date < MKTOPEN:
                logging.warning(f"{currentBar.date.astimezone()} is before rth")
                return False
            return retval

        def high_near_open():
            """Check if the last bar high is near the open"""
            if len(self.bars) < 1:
                return False
            hml = self.bars[-1].high - self.bars[-1].low # high minus low
            hmo = self.bars[-1].high - self.bars[-1].open_ # high minus open_
            hno_threshold = 0.2
            hno = hmo / hml <= hno_threshold # high near open_
            logger.info(f"high_near_open: hmo/hml={hmo/hml:.3f}")
            return hno
        
        def low_to_high_inflection_point(bars: BarDataList, n=15, m=5) -> bool:
            """check if there is a low to high inflection point in the last n bars.
            This is a sign of reversal. We want to catch the reversal early.
            Define inflection point as any of the last m bars lows is lower than any of the previous n-m bars lows
            """
            if len(bars) < n:
                # the first n bars ...
                # case in point: AMD 10/29/2024 9:35 and 9:36 bars
                if len(bars) > 3:
                    lows = [b.low for b in bars] # low so far
                    lastn_lows = lows[-3:] # last 3 lows
                    if min(lastn_lows) == min(lows):
                        logger.info(f"low_to_high_inflection_point: last 3 lows are the same: {lows} {lastn_lows}")
                        # return True
                return False
            lows = [b.low for b in bars[-n:]]
            nplows = bars.low_prices[:bars._npidx][-n:]
            if not np.isclose(lows, nplows, atol=1e-6).all():
                logger.warning(f"lows != nplows: {lows} != {nplows}")
            if min(lows[:-m]) > min(lows[-m:]):
                logger.info(f"low_to_high_inflection_point: {lows[:-m]} > {lows[-m:]}")
                return True
            return False # no inflection point
        
        def five_bars_green():
            """Check if the last five bars are green"""
            if len(self.bars) < 5:
                return False
            return all([bar.close > bar.open_ for bar in self.bars[-5:]])
        
        def lastn_bars_green(n=10, relax: bool=False) -> int:
            """
            examine the last n bars, count the longest string of successive green bars from the last
            relax: if True, allow for a yellow bar in between green bars
            """
            if len(self.bars) < n:
                return 0
            count = 0
            for bar in self.bars[-n:]:
                if bar.close > bar.open_:
                    count += 1
                elif relax and bar.close == bar.open_:
                    count += 1
                else:
                    break
            return count
        
        def lastn_bars_red(n=10, relax: bool=False) -> int:
            """examine the last n bars, count the longest string of successive red bars from the last"""
            if len(self.bars) < n:
                return 0
            count = 0
            for bar in self.bars[-n:]:
                if bar.close < bar.open_:
                    count += 1
                elif relax and bar.close == bar.open_:
                    count += 1
                else:
                    break
            return count

        # 11/26/24: when to buy? ft=True, near low of the day, last 4 bars are not green, 
        #   follow by one green, and current bar average is higher than previous at the bottom of current minute
        #   nvda 14:26
        def mn_bars_red(bars: BarDataList, start: int, end: int, relax: bool=False, consecutive: bool=False) -> int:
            """
            start, end are negative list index
            count the number of consecutive red bars from start to end
            """
            # if len(bars) < abs(start) or len(bars) < abs(end):
            #     return False
            count = 0
            # logger.info(f"bars: {bars[start:end:-1]}")
            for bar in bars[start:end:-1]: # from the tail end
                if bar.close < bar.open_:
                    count += 1
                elif relax and bar.close == bar.open_: # yellow bar ok if relax
                    count += 1
                elif not relax and bar.close == bar.open_: # yellow bar not ok if not relax
                    break
                elif consecutive: # we're looking for consecutive red bars
                    break
            return count

        def mn_bars_green(bars: BarDataList, start: int, end: int, relax: bool=False, consecutive: bool=False) -> int:
            """
            start, end are negative list index
            count the number of consecutive green bars from start to end
            """
            count = 0
            for bar in bars[start:end:-1]: # from the tail end
                if bar.close > bar.open_:
                    count += 1
                elif relax and bar.close == bar.open_: # yellow bar ok if relax
                    count += 1
                elif not relax and bar.close == bar.open_: # yellow bar not ok if not relax
                    break
                elif consecutive: # we're looking for consecutive red bars
                    break
            return count

        def seekEntry(isFollowThrough: bool = False):
            """
            pre-condition: no position, no outstanding trades, milestone has been reset
            """
            assert self.trade is None, "Expect no outstanding trades"
            isInflection_15_5 = low_to_high_inflection_point(self.bars, 15, 5)
            isInflection_10_5 = low_to_high_inflection_point(self.bars, 10, 5)
            isInflection_5_3 = low_to_high_inflection_point(self.bars, 5, 3)
            tgb1cnh = two_bars_green_with_one_close_near_high_2()
            orig_cond = tgb1cnh and isInflection_10_5 # original condition 
            ft_gb32 = isFollowThrough and lastn_bars_green(3) >= 2 # don't need to check for inflection point
            # self.gf1 = gf1 = self.direction_s3 == 'positive' and self.direction_s16 == 'positive' and self.direction_s24 == 'positive' # gaussian filter 1
            # self.gf1_serial.append(gf1)
            # if self.direction_s3 or self.direction_s16 or self.direction_s24:
            #     logger.info(f"gf1: direction_s3={self.direction_s3}, direction_s16={self.direction_s16}, direction_s24={self.direction_s24}")
            #     logger.info(f"gf1 serial: {list(map(int, self.gf1_serial[-12:]))}")
            # this is a stopgap until trapdoor or better follow-through is fully implemented
            blw_lsp: bool = False
            blw_lsp_pct: float = 0.0
            if self.lastSalePrice:
                blw_lsp_pct = lastPrice_ / self.lastSalePrice - 1.0
                blw_lsp = lastPrice_ < self.lastSalePrice # below last sold price
                logger.info(f"below_last_sold_price({self.lastSalePrice:.2f}, {blw_lsp_pct:.2%})={blw_lsp}")
            elif not self.lastSalePrice and isFollowThrough: # expect last sale price is set when follow-through, warn if not
                logger.warning(f"lastSalePrice is not set, isFollowThrough is set")
            logger.info(f"tgb1cnh={tgb1cnh}, ft_gb32={ft_gb32}, isInflection_10_5={isInflection_10_5}, isInflection_15_5={isInflection_15_5}, isInflection_5_3={isInflection_5_3}")
            # if orig_cond or ft_gb32: # ft_gb32 is broken, don't use it yet
            # when "following through" (ft), basically we got stoppped out near recent low
            # we should wait for the next opportunity to buy below last sold price and avoid trashing

            # # 11/26/24: when to buy? ft=True, near low of the day, last 4 bars are not green, 
            # #   follow by one green, and current bar average is higher than previous at the bottom of current minute
            # #   nvda 14:26
            # def mn_bars_red(bars: BarDataList, start: int, end: int, relax: bool=False, consecutive: bool=False) -> int:
            #     """
            #     start, end are negative list index
            #     count the number of consecutive red bars from start to end
            #     """
            #     # if len(bars) < abs(start) or len(bars) < abs(end):
            #     #     return False
            #     count = 0
            #     for bar in bars[start:end:-1]: # from the tail end
            #         if bar.close < bar.open_:
            #             count += 1
            #         elif relax and bar.close == bar.open_: # yellow bar ok if relax
            #             count += 1
            #         elif not relax and bar.close == bar.open_: # yellow bar not ok if not relax
            #             break
            #         elif consecutive: # we're looking for consecutive red bars
            #             break
            #     return count
            lkbk3 = -3
            nbr_actual: int = mn_bars_red(self.bars[lkbk3-20:], lkbk3, lkbk3-20, relax=True, consecutive=True)
            nbr4 = nbr_actual >= 4 # looking for strings of 4+ red bars, starting from -3

            lkbk2 = -2 # second to last bar, we'll test the last bar (most recent bar) separately
            nb5mr_actual: int = mn_bars_red(self.bars5m[lkbk2-8:], lkbk2, lkbk2-8, relax=True, consecutive=True)
            nb5mr = nb5mr_actual >= 4 # looking for strings of 4+ red bars, starting from -3

            lkbk1 = -1 # last bar (aka most recent bar)
            nbg_actual: int = mn_bars_green(self.bars5m[lkbk1-8:], lkbk1, lkbk1-8, relax=True, consecutive=True)
            nbg4 = nbg_actual >= 4 # looking for strings of 4+ red bars, starting from -3

            pbonl_threshold = 0.2
            pbhml_ = prevBar.high - prevBar.low
            pbonl_realized: float = (prevBar.open_ - prevBar.low) / pbhml_ if pbhml_ != 0.0 else 0.0 # previous bar open near low
            pbonl = pbonl_realized <= pbonl_threshold # previous bar open near low
            pbcnh_threshold = 0.8
            pbcnh_real = (prevBar.close - prevBar.low) / pbhml_ if pbhml_ != 0.0 else 0.0 # previous bar close near high
            pbcnh = pbcnh_real >= pbcnh_threshold # previous bar close near high
            pbg = prevBar.close > prevBar.open_ # previous bar green
            cbah = currentBar.average > prevBar.average # current bar average higher (than previous bar average)
            at30s = datetime.datetime.now(local_tz).second >= 30 # at 30 seconds (or later)
            dl0m = dl1m = dl2m = dl3m = 0.0
            dl0mb = dl1mb = dl2mb = dl3mb = False
            if self.dayhilopct:
                dl_arr = extract_field_as_array(slice_deque(self.dayhilopct, -4, -1), 'low')
                dlmb_arr = dl_arr <= 0.05
                # dl0m = self.dayhilopct[-1][2] # day low pct below 5%, current bar
                # dl1m = self.dayhilopct[-2][2] # day low pct below 5%, 1 bar ago
                # dl2m = self.dayhilopct[-3][2] # 2 bars ago
                # dl3m = self.dayhilopct[-4][2] # 3 bars ago
                # dl0mb = dl0m <= 0.05
                # dl1mb = dl1m <= 0.05
                # dl2mb = dl2m <= 0.05
                # dl3mb = dl3m <= 0.05
            
            # if we see higher highs and higher lows, higher average and higher close and we are near day low and dlmb_arr is all True, buy

            seconds_after_open = (datetime.datetime.now(local_tz) - MKTOPEN).seconds
            if currentBar.average < self.prevclose and (seconds_after_open < 5*60):
                logger.info(f"open lower, no action")
                return

            # buy when no more absolute low after seeing absolute low in the last X minutes
            # and bar3m is not red and bar3m serial average is lower
            # and bar3m exit is higher than average
            if currentBar.date >= MKTOPEN:
                b5m_ser_lwr_avg_4 = list(map(int, self.b5m_serially_lower_avg[-4:]))
                logger.info(f"b5m_ser_lwr_avg_4: {b5m_ser_lwr_avg_4}")
            if self.absolute_low_last5m:
                logger.info(f"bar1m: {_repr_barlist(self.bars[-3:])}")
                logger.info(f"bar3m: {_repr_barlist(self.bars3m[-3:])}")
                logger.info(f"bar5m: {_repr_barlist(self.bars5m[-3:])}")
                logger.info(f"bar15m: {_repr_barlist(self.bars15m[-3:])}")
                logger.info(f"bar30m: {_repr_barlist(self.bars30m[-3:])}")
            abs_low_buy = False
            match len(self.seen_abs_low):
                case 1:
                    abs_low_buy = not self.absolute_low and self.absolute_low_last5m
                case 2:
                    abs_low_buy = not self.absolute_low and self.absolute_low_last5m \
                        and self.bars3m[-1].close > self.bars3m[-1].average and self.b3m_serially_lower_avg[-2:] == [True, True]
                case _:
                    abs_low_buy = not self.absolute_low and self.absolute_low_last5m and not (self.b30m_serially_lower_avg[-3:] == [True, True, True])
            if orig_cond or isFollowThrough or self.gf1 or abs_low_buy: # must add additional check when isFollowThrough
                buy_action = False
                if isFollowThrough:
                    # fyi
                    ft1 = nbr4 and pbonl and pbg and cbah and at30s
                    logger.info(f"ft1={ft1}: nbr4({nbr_actual:n})={nbr4}, pbonl({pbonl_realized:.3})={pbonl}, pbg={pbg}, cbah={cbah}, at30s={at30s}")
                    ft2 = False
                    if self.dayhilopct:
                        # ft2 = (dl0mb or dl1mb or dl2mb or dl3mb) and pbg and cbah
                        ft2 = dlmb_arr.any() and pbg and cbah
                    # logger.info(f"ft2: dl0m({dl0m:.1%})={dl0mb}, dl1m({dl1m:.1%})={dl1mb}, dl2m({dl2m:.1%})={dl2mb}, dl3m({dl3m:.1%})={dl3mb}, pbcnh({pbcnh_real:.3})={pbcnh}")
                    logger.info(f"ft2={ft2}: dlmb={dlmb_arr}, pbg={pbg}, cbah={cbah}")
                    b5m_ser_lwr_avg_6_lst = list(map(int, self.b5m_serially_lower_avg[-6:]))
                    b5m_ser_lwr_avg_6 = b5m_ser_lwr_avg_6_lst == [1, 1, 1, 1, 1, 0]
                    nb5mr = nb5mr_actual >= 4 # looking for strings of 4+ red bars, starting from -3
                    ft3 = nb5mr and b5m_ser_lwr_avg_6 and currentBar.average > self.todayopen
                    logger.info(f"ft3={ft3}: b5m_ser_lwr_avg_6={b5m_ser_lwr_avg_6_lst}, nb5mr({nb5mr_actual})={nb5mr}, cBar/open={currentBar.average/self.todayopen-1.:.2%}")
                    if not blw_lsp and not self.gf1:
                        logger.info(f"blw_lsp: {blw_lsp}, gf1: {self.gf1}, no action")
                        return
                    elif (blw_lsp and ft3):
                        logger.info(f"blw_lsp: {blw_lsp}, ft3: {ft3}, buying...")
                        buy_action = True
                    elif (blw_lsp and self.gf1) or (not blw_lsp and self.gf1 and (ft1 or ft2)): # AND gf1 (19-Dec-2024)
                        # we are below last sold price OR gauss filter indic are all positives, we can buy
                        # but only if ...
                        # if (ft1 and self.gf1) or (ft2 and self.gf1) or self.gf1:
                        if (ft1 and self.gf1) or (ft2 and self.gf1):
                            buy_action = True
                            # # using limit order
                            # t = ib.tickers()[0]
                            # mintick = self.ibcontractDetails[0].minTick  # Assuming the minimum tick size is 0.01, adjust as necessary
                            # mktPrice = round(t.marketPrice() / mintick) * mintick
                            # self.order = LimitOrder('BUY', self.numshares, mktPrice, discretionaryAmt=round(0.0002 * self.milestone_multiplier * t.ask, 2))
                            # self.order.account = self.tradingaccount
                        else:
                            logger.info(f"blw_lsp: {blw_lsp}, ft1: {ft1}, ft2: {ft2}, gf1: {self.gf1}, no action")
                            return
                    elif (not self.absolute_low and self.absolute_low_last5m):
                        logger.info(f"absolute_low {self.absolute_low}, absolute_low_last5m {self.absolute_low_last5m}, buying...")
                        buy_action = True
                        # # using limit order
                        # t = ib.tickers()[0]
                        # mintick = self.ibcontractDetails[0].minTick  # Assuming the minimum tick size is 0.01, adjust as necessary
                        # mktPrice = round(t.marketPrice() / mintick) * mintick
                        # self.order = LimitOrder('BUY', self.numshares, mktPrice, discretionaryAmt=round(0.0002 * self.milestone_multiplier * t.ask, 2))
                        # self.order.account = self.tradingaccount
                    else:
                        logger.info(f"blw_lsp: {blw_lsp}, gf1: {self.gf1}, no action")
                        return
                    if buy_action:
                        # using limit order
                        t = ib.tickers()[0]
                        mintick = self.ibcontractDetails[0].minTick  # Assuming the minimum tick size is 0.01, adjust as necessary
                        mktPrice = round(t.marketPrice() / mintick) * mintick
                        self.order = LimitOrder('BUY', self.numshares, mktPrice, discretionaryAmt=round(0.0002 * self.milestone_multiplier * t.ask, 2))
                        self.order.account = self.tradingaccount

                elif not isFollowThrough and self.gf1: # original condition, AND gf1 (19-Dec-2024)
                    # ok using market order
                    logger.info(f"isFollowThrough: {isFollowThrough}, gf1: {self.gf1}, buying...")
                    self.order = MarketOrder('BUY', self.numshares)
                    self.order.account = self.tradingaccount
                elif (not self.absolute_low and self.absolute_low_last5m):
                    logger.info(f"absolute_low {self.absolute_low}, absolute_low_last5m {self.absolute_low_last5m}, buying...")
                    self.order = MarketOrder('BUY', self.numshares)
                    self.order.account = self.tradingaccount
                else:
                    logger.info(f"orig_cond: {orig_cond}, isFollowThrough: {isFollowThrough}, gf1: {self.gf1}, no action")
                    return

                # logger.info(f"seekEntry: Two bars green with one close near it's high, seeking entry...")
                # last_5m_hml_ = last_5m_hml(self.bars)
                # logger.info(f"trailing 5m hml {last_5m_hml_} ({np.array2string(last_5m_hml_ / self.lastPrice, formatter=np_pct)})")
                # check if these two are the same

                # self.order = MarketOrder('BUY', self.numshares) # see elaboration above
                # contract_ = Stock(self.symbol, 'SMART', 'USD')
                contract_ = self.ibcontract
                logger.info(f"Buying {contract_} as {self.order}")
                # before we place the order, make sure no outstanding trades
                if self.trade and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"clearing old trade {self.trade.log}")
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                if self.trade is None:
                    if self.liveTrading:
                        self.set_state(1) # because this is market order, we can change state immediately
                        self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                        self.orderId = self.trade.order.orderId # we only have orderId after the order is placed, no permId yet
                        # self.tradePermId = self.trade.order.permId
                        self.tradeMgr = TradeManager(self.trade)
                        if self.order.action == 'BUY':
                            self.lastBuyTrade = self.trade
                        logger.info(f"Trade placed: {self.trade}")
                        self.buyopen_bar1m_idx.append(len(self.bars) - 1) # remember the bar index when we placed the trade
                        self.buyopen_bar1m.append(copy.copy(self.bars[-1])) # remember the bar when we placed the trade
                        self.high_since_buy_bar1m.append(copy.copy(self.bars[-1])) # initialize high since buy
                        self.checkpoint('buyopen')
                        loop = asyncio.get_running_loop()
                        # https://github.com/python/cpython/issues/104091
                        task = loop.create_task(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Buying shares of {contract_} as {self.order} {self.trade.log}"))
                        background_tasks.add(task) # keep a reference to the task
                        task.add_done_callback(background_tasks.discard)
                        # asyncio.sleep(0.2)
                    else:
                        logger.error(f"No live trading, trade not placed: {self.order}")
                        return # just return, don't change state
                else:
                    assert False, f"Impossible state: trade outstanding: {self.trade}"
                # ib.sleep(0) # allow time for trade to complete # can't run this in async function?
                openTrades = [t for t in ib.openTrades() if t.contract.symbol == self.symbol]
                if self.trade and self.trade in openTrades:
                    logger.info(f"Trade is still open: {openTrades}")
                elif self.trade and self.trade not in openTrades and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"Trade is filled: {self.trade.log}")
                    self.set_state(1)
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                else:
                    logger.warning(f"should not reach here {self.trade}")
                #     assert False, f"Impossible state: trade {self.trade} not in {ib.openTrades() and }"
            return # end of seekEntry

        logger.debug(get_asyncio_running_loop('')) # expect '<ProactorEventLoop running=True closed=False debug=False>
        # these variables are visible to the strategy
        currentBar = self.bars[-1] # bar that is being built, never full
        prevBar = self.bars[-2] # the previous bar

        # set lastPrice_
        lastPrice_ = get_market_price()
        t = ib.tickers()[0]
        chg = lastPrice_/t.close - 1.0
        tdiff = (t.time - datetime.datetime.now(local_tz)).total_seconds()
        if abs(tdiff) > 1.0:
            logger.warning(f"Tick time is {tdiff:.2f} seconds" + (f" ahead" if tdiff > 0 else " behind") + f" current time")
        basprd = t.ask - t.bid
        logger.info(f"{t.contract.localSymbol} bid {t.bid} ask {t.ask} last {t.last} chg {chg:+.2%} b/a spread {basprd:.2f} ({basprd/lastPrice_:.3%}) high {t.high} low {t.low} volume {t.volume:n}")
        # lastPrice_ = get_market_price() # move to the top

        # volatility
        last_5m_hml_ = last_5m_hml(self.bars)
        logger.info(f"last 5m hml {last_5m_hml_} ({np.array2string(last_5m_hml_ / lastPrice_, formatter=np_pct)})")
        logger.info(f"hml {np.asarray(self.hml[-5:])} hml_pct {np.array2string(np.asarray(self.hml_pct[-5:]), formatter=np_pct)}")

       # calculate trapdoor index
        trdrIdx_ = 0
        chgDn = lastPrice_/self.prevclose-1.
        # find the highest (down) milestone crossed, i.e. dnPctMilestone[trdrIdx_] > lastPrice_ > dnPctMilestone[trdrIdx_+1]
        # chg = (lastPrice_/self.prevclose-1.)
        # logger.info(f"lastPrice_={lastPrice_:.2f}, prevclose={self.prevclose:.2f}, chg={chg:.2%}")
        while trdrIdx_ < len(self.dnPctMilestone) and chg < self.dnPctMilestone[trdrIdx_]:
            trdrIdx_ += 1
            # chg = (lastPrice_/self.prevclose-1.)
        logger.info(f"trdrIdx_={trdrIdx_}, dnPctMilestone[trdrIdx_]={self.dnPctMilestone[trdrIdx_]:.2%}")
        if trdrIdx_ > 0:
            trdrIdx_ -= 1 # Adjust because when the loop exits, dnPctMilestone[trdrIdx_] > lastPrice_
        if trdrIdx_ > self.trapdoorIdx:
            self.trapdoorIdx = trdrIdx_
            wiretripped = False
            logmsg = "Drop below trapdoor"
        elif trdrIdx_ == self.trapdoorIdx:
            wiretripped = False
            logmsg = "Current trapdoor"
        else:
            # crossing above, this is important.
            wiretripped = True
            if self.tripwireIdx == -1:
                self.tripwireIdx = trdrIdx_
                logmsg = "Tripwire tripped"
            else:
                logmsg = "Tripwire already"
        assert self.trapdoorIdx >= 0, "trapdoorIdx should be greater than zero"

        if self.trapdoorIdx > 0:
            trapdoorPrice_ = self.prevclose * (1 + self.dnPctMilestone[self.trapdoorIdx])
        else:
            trapdoorPrice_ = self.prevclose * (1 + self.dnPctMilestone[self.trapdoorIdx])
        logger.info(f"{logmsg} {self.trapdoorIdx} ({self.dnPctMilestone[self.trapdoorIdx]:.2%}) last {lastPrice_:.2f}, return {chg:.2%}, trapdoor {trapdoorPrice_:.2f} ({trapdoorPrice_/lastPrice_-1:.2%})")


        logger.info(f"state={self.get_state()}")
        # print portfolio
        sp_: List[PortfolioItem] = [p for p in ib.portfolio(self.tradingaccount) if p.contract.symbol in [self.symbol]]
        if len(sp_) > 0:
            for p in sp_:
                logger.info(f"portfolio: {p.position:n} {p.contract.symbol}, IB avgcost {p.averageCost * self.futAvgCostMult:.2f}, use avgcost {self.useAvgCost * self.futAvgCostMult}, mktprc {p.marketPrice:.2f} mv {p.marketValue:.2f}, dailypnl {p.unrealizedPNL+p.realizedPNL:.2f} ({(p.unrealizedPNL+p.realizedPNL)/self.prevclose/p.position:+.2%}), unrlzd {p.unrealizedPNL:.2f} rlzd {p.realizedPNL:.2f}")
        else:
            logger.info(f"portfolio: no position")
        if self.get_state() in [0, 2]:
            # no position, no outstanding trades and milestone has been reset
            if ((self.stkpos is None) or (self.stkpos.position == 0)) and self.idxMilestone == -1 and self.trade is None:
                isFollowThrough = (self.lastSaleTime is not None)
                logger.info(f"No position, seeking {'follow through ' if isFollowThrough else ''}entry ...")
                seekEntry(isFollowThrough=isFollowThrough)
                return
            elif self.trade and self.trade in (openTrades := [t for t in ib.openTrades() if t.contract.symbol == self.symbol]):
                logger.info(f"Trade is still open: {openTrades}") # wait for trade to complete
                return
            elif self.trade and not (self.trade in ib.openTrades()):
                if self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade status: {self.trade}"
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                    self.high_since_buy_bar1m = [] # reset high since buy
                    # allow to proceed
                elif self.trade.orderStatus.status == 'Cancelled':
                    logger.error(f"Trade was cancelled: {self.trade}, undoing state change ({self.state} -> {self.prevstate}), resetting trade to None")
                    self.state = self.prevstate # undo state change
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    return
            else: # self.trade is None, stkpos is not None
                logger.error(f"Impossible state: state=0 but self.trade={self.trade} position={self.stkpos} and idxMilestone={self.idxMilestone}")
                return # don't allow to proceed
            
        elif self.get_state() == 2: # proper follow through, using trapdoor and tripwire
            # update trapdoor index
            newIdx_ = 0
            # lastPrice_ = get_market_price()
            refPrice_ = self.lastSalePrice # trapdoor reference price
            while newIdx_ < len(self.trapdoor) and lastPrice_ > refPrice_ * (1 + self.trapdoor[newIdx_]):
                newIdx_ += 1
            assert lastPctReturn() <= self.trapdoor[newIdx_], "last price should be at or below current milestone"
            if newIdx_ > 0:
                newIdx_ -= 1  # Adjust because the loop exits after crossing the last milestone
            if newIdx_ > self.idxMilestone:
                self.set_milestone(newIdx_)
                logmsg = "Crossed milestone"
            else:
                logmsg = "Current milestone"
            assert self.idxMilestone >= 0, "idxMilestone should be greater than zero"

            pass
        elif self.get_state() == 1:
            # we have a position
            if (self.stkpos is None or self.stkpos.position == 0) and self.trade and self.trade in ib.openTrades():
                logger.info(f"Waiting for position update to complete...")
                return
            elif (self.stkpos is None or self.stkpos.position == 0) and self.trade and self.trade not in ib.openTrades():
                logger.error(f"Impossible state: state=1 but trade not in openTrades {self.trade}")
                return
            elif self.stkpos is None and not self.trade:
                logger.error(f"Impossible state: state=1 but no outstanding trade")
                return
            # if self.stkpos.position == 0:
            #     logger.error(f"Impossible state: state=1 but position={self.stkpos}")
            #     return
            # ensure no outstanding trades
            if self.trade:
                if self.trade in ib.openTrades():
                    logger.info(f"Trade is still open: {ib.openTrades()}")
                elif self.trade not in ib.openTrades() and self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade is filled: {self.trade.log}"
                    # self.state = 1
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    self.high_since_buy_bar1m.append(copy.copy(currentBar))
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logmsg = f"Trade not filled: {self.trade.log}"
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    logger.error(logmsg + f", resetting trade to None")
                    return # proceed or not?
        elif self.get_state() == 99:
            pass
            # logger.warning(f"Exiting strategy...")
            # return # we'll exit at the end of the function
        
        # if we have no position, just return
        if (self.stkpos is None) or (self.stkpos.position == 0):
            logger.warning(f"No position, returning...")
            return
        
        # update milestone index
        newIdx_ = 0
        # lastPrice_ = get_market_price()
        # avgCost_ = self.stkpos.avgCost * self.futAvgCostMult
        avgCost_ = self.useAvgCost * self.futAvgCostMult
        while newIdx_ < len(self.upPctMilestone) and lastPrice_ > avgCost_ * (1 + self.upPctMilestone[newIdx_]):
            newIdx_ += 1
        assert lastPctReturn() <= self.upPctMilestone[newIdx_], "last price should be at or below current milestone"
        if newIdx_ > 0:
            newIdx_ -= 1  # Adjust because the loop exits after crossing the last milestone
        if newIdx_ > self.idxMilestone:
            self.set_milestone(newIdx_)
            logmsg = "Crossed milestone"
        else:
            logmsg = "Current milestone"
        assert self.idxMilestone >= 0, "idxMilestone should be greater than zero"
        
        # calculate stop loss price
        # is the price below the upPctMilestone[i-1]+stopLossPct[i] for the current milestone?
        if self.idxMilestone > 0:
            stoplossPrice_ = avgCost_ * (1 + self.stopLossPct[self.idxMilestone] + self.upPctMilestone[self.idxMilestone-1])
        else:
            stoplossPrice_ = avgCost_ * (1 + self.stopLossPct[self.idxMilestone])

        rput = None
        if self.lastBuyTrade: # if we have a last buy trade
            nrpm = 60 # number of minutes per return
            T = (datetime.datetime.now(local_tz) - max_exec_time(self.lastBuyTrade)).total_seconds() / 60.0 / nrpm # in minutes
            rput = lastPctReturn() / T # return per unit time
            logger.info(f"T={T:.1f} rput={rput:.3%}/{nrpm:n}min")
        logger.info(f"{logmsg}={self.idxMilestone} ({self.upPctMilestone[self.idxMilestone]:.2%}) last {lastPrice_:.2f}, return {lastPctReturn():.2%}{f' ({rput:.3%}/5min)'.format(rput=rput) if rput else ''}, stoploss {stoplossPrice_:.2f} ({stoplossPrice_/lastPrice_-1:.2%})")
        
        # calculate drawdown
        # get the highest 1m close since we last buy. get the higher of that and current price. drawdownpct = min(0, (lastprice - highest)/highest)
        # if we are below the highest, we are in drawdown
        # if not self.buyopen_bar1m_idx:
        #     logger.warning(f"buyopen_bar1m_idx is not set")
        #     j = None
        #     j_timestamp = None
        #     highest_since_buy = max([bar.close for bar in self.bars])
        # else:
        #     j = self.buyopen_bar1m_idx[-1]
        #     highest_since_buy = max([bar.close for bar in self.bars[j:]])
        #     j_timestamp = self.bars[j].date
        #     logger.info(f"highest_since_buy bar[{j}]={self.bars[j]}")

        hsb_bar = None
        if self.high_since_buy_bar1m:
            hsb_bar = self.high_since_buy_bar1m[-1]
            highest_since_buy = hsb_bar.average # using average is more realistic
        elif currentBar.date >= MKTOPEN:
            self.high_since_buy_bar1m.append(copy.copy(currentBar)) # initialize high since buy
            highest_since_buy = currentBar.average
        elif currentBar.date < MKTOPEN:
            highest_since_buy = 0
            pass # we wait until open
        else:
            logger.warning(f"high_since_buy_bar1m is not set")
            highest_since_buy = lastPrice_
        hwm = max(highest_since_buy, lastPrice_)
        logger.info("highest_since_buy=" + (f"{_repr_bar(hsb_bar)}" if hsb_bar else f"{highest_since_buy:.2f}") + f" vs hwm={hwm:.2f}")
        drawdown = min(0, lastPrice_ - hwm) # always from today's point of view, irrespective of last buy time
        drawdown_pct = drawdown / hwm # hwm is the base
        pnl_hwm = hwm - avgCost_
        ltdpnl_hwm = hwm - avgCost_ # life-to-date pnl high water mark
        # TODO pnl should be immediately accessible through Agent
        daypnl_hwm = ltdpnl_hwm if self.lastBuyTrade else hwm - self.prevclose # day pnl high water mark
        pnl_hwm_pct = pnl_hwm / avgCost_
        ltdpnl_hwm_pct = ltdpnl_hwm / avgCost_
        daypnl_hwm_pct = daypnl_hwm / self.prevclose
        logger.info(f"px_hwm {hwm:.2f}, px_highest_since_buy {highest_since_buy:.2f}")
        logger.info(f"drawdown {drawdown:.2f} {drawdown_pct:.2%}, ltdpnl_hwm {ltdpnl_hwm:.2f} {ltdpnl_hwm_pct:.2%}, daypnl hwm {daypnl_hwm:.2f} {daypnl_hwm_pct:.2%}")
        # # report if we are in drawdown
        # if drawdown_pct < 0:
        #     logger.info(f"Drawdown: {drawdown_pct:.2%}")
        
        # this is the original exit condition
        # but this results in negative expected pnl because we are exiting at a loss
        cond1 = lastPrice_ < stoplossPrice_

        # to avoid negative expected pnl, we introduce drawdown condition from pnl high water mark
        # allow some retracement from pnl high water mark
        max_retracement_pct = -1.0 * self.mile0_max_retracement_pct * plus(daypnl_hwm_pct) # generally 20% retracement from high water mark
        _recent_vol_tuplst = slice_deque(self.volatility_per_min, -2, None) # recent volatility tuples
        logger.info(f"recent_vol_tup={_repr_vol_tup_lst(_recent_vol_tuplst)}")
        if _recent_vol_tuplst:
            _recent_vol = _recent_vol_tuplst[-2][2] # (gk,rs,pk) [2] is parkinson volatility, use the second last (full bar)
        else:
            _recent_vol = 0.006 # per minute
        vol_based_dd_limit = -1.0 * _recent_vol * 5 # 5 times the recent parkinson volatility
        vol_based_dd_limit_2 = -1.0 * _recent_vol * 4.0 * 3.0 # 3 std dev move in ~16 minutes
        # sometimes max_retracement_pct is too small (when pnl high water mark is close to zero), so we use the absolute min
        _abs_min_dd_limit = -1.0 * self.mile0_max_retracement_absolute_min_pct
        _eff_dd_limit = min(_abs_min_dd_limit, max(max_retracement_pct, vol_based_dd_limit_2), vol_based_dd_limit)
        cond2 = drawdown_pct < _eff_dd_limit and self.idxMilestone >= 0
        if self.idxMilestone >= 0:
            logger.info(f"dd limit {_eff_dd_limit:.3%} (min {_abs_min_dd_limit:.3%}, retr {max_retracement_pct:.3%}, vol based {vol_based_dd_limit:.3%}, 3stdev15 {vol_based_dd_limit_2:.3%})")
        logger.info(f"stpls={cond1}, ddrtrc={cond2}, idxMilestone={self.idxMilestone}")
        gfe2 = self.direction_s3 == 'negative' and self.direction_s16 == 'negative' and self.direction_s24 == 'negative' # gaussian filter exit, filter#2

        # are we plateauing or after a peak/inflexion point?
        pass # TODO
        
        if self.get_state() == 99:
            logger.warning(f"Exiting strategy...")
            return

        # crossed below milestone, we should liquidate
        if cond1: 
            logger.warning(f"Crossed below stopLoss {stoplossPrice_:.2f}, last {lastPrice_:.2f} (ltd return = {lastPctReturn():.2%})")
        elif cond2:
            logger.warning(f"Crossed below dd limit {drawdown_pct:.2%}, last {lastPrice_:.2f} (ltd return = {lastPctReturn():.2%})")
        elif gfe2:
            logger.warning(f"gfe2: {gfe2}, preemptive exit")
        else:
            logger.info(f"gfe2: {gfe2}, no exit condition met")
            return
        if cond1 or cond2: # (disabled for now)
            # except ....
            if self.absolute_low_last5m and self.idxMilestone > 1:
                logger.warning(f"absolute_low_last5m {self.absolute_low_last5m}, idxMilestone {self.idxMilestone}, not exiting")
                return
            # # crossed below milestone, we should liquidate
            # if cond1: 
            #     logger.warning(f"Crossed below stopLoss {stoplossPrice_:.2f}, last {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
            # elif cond2:
            #     logger.warning(f"Crossed below max retracement {drawdown_pct:.2%}, last {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
            bid_price = get_bid_price()
            mintick = self.ibcontractDetails[0].minTick  # Assuming the minimum tick size is 0.01, adjust as necessary
            bid_price = round(bid_price / mintick) * mintick
            self.order = LimitOrder('SELL', self.stkpos.position, bid_price, discretionaryAmt=round(0.0004 * self.milestone_multiplier * bid_price, 2))
            self.order.account = self.tradingaccount
            # contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
            contract_ = self.ibcontract
            logger.warning(f"Selling {contract_} as {self.order}")
            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                    self.orderId = self.trade.order.orderId # we only have orderId after the order is placed, no permId yet
                    # self.tradePermId = self.trade.order.permId
                    self.tradeMgr = TradeManager(self.trade)
                    if self.order.action == 'SELL':
                        self.lastSellTrade = self.trade
                    self.set_state(0) # reset state
                    logger.info(f"Trade placed: {self.trade}, state reset to 0")
                    self.sellclose_bar1m_idx.append(len(self.bars) - 1)
                    self.sellclose_bar1m.append(self.bars[-1]) # record the bar1m where we placed the trade
                    self.checkpoint('sellclose')
                    loop = asyncio.get_running_loop()
                    task = loop.create_task(
                        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID
                            , text=f"Selling {contract_} as {self.order} {self.trade.log}"))
                    background_tasks.add(task) # keep a reference to the task
                    task.add_done_callback(background_tasks.discard)
                else:
                    logger.error(f"No live trading, trade not placed: {self.order}")
            elif self.trade in ib.openTrades():
                logger.info(f"Trade is still open: {ib.openTrades()}")
            else: # self.trade is not in ib.openTrades()
                logmsg = f"Impossible state: trade {self.trade} not in {ib.openTrades()}"
                self.trade = None
                self.orderId = self.tradePermId = -1
                self.tradeMgr.clear()
                logger.error(logmsg + f", resetting trade to None")
            # 
            # _openTrades = ib.trades()
            # if _openTrades is not None:
            #     logger.warning(f"There is an outstanding trade: {_openTrades}")
            #     # ib.cancelOrder()

        # # assert 
        # if not ( (stoplossPrice_ < lastPrice_)
        #         and (lastPrice_ < avgCost_ * (1 + self.upPctMilestone[self.idxMilestone])) 
        #     ):
        #     logger.error(f"Price should be between previous milestone+stoploss and current milestone idx={self.idxMilestone}" \
        #         f" stoplossPrice_={stoplossPrice_} < lastPrice_={lastPrice_} < curmilestone={avgCost_ * (1 + self.upPctMilestone[self.idxMilestone]):.2f}"
        #     )
        # logger.warning(f"Crossed milestone {idx_} {self.upPctMilestone[idx_]:.2%} below idxMilestone = {self.idxMilestone}")
        # assert False, "Crossed milestone below idxMilestone, should've triggered liquidation"

        # the code below is wrong because it doesn't account for the fact that we may have crossed multiple milestones
        # if self.idxMilestone < len(self.upPctMilestone):
        #     if lastPrice_ >= self.upPctMilestone[self.idxMilestone]:
        #         logger.info(f"Crossed milestone {self.idxMilestone}: {lastPrice_:.2f}")
        #         self.upPctMilestone[self.idxMilestone] = lastPrice_
        #         self.idxMilestone += 1

    def enforceMaxLoss(self, lastPrice=None, maxloss_=None):
        logger.debug(get_asyncio_running_loop('')) # expect 'no running event loop'
        if lastPrice is None:
            lastPrice = get_market_price()
        if maxloss_ is None:
            maxloss_ = self.maxloss
        if lastPrice <= 0:
            logger.error(f"lastPrice is zero or negative: {lastPrice}, can't proceed")
            return
        # avgCost_ = self.stkpos.avgCost * self.futAvgCostMult
        avgCost_ = self.useAvgCost * self.futAvgCostMult
        maxlossPct_ = maxloss_ / avgCost_ / self.stkpos.position / self.contract_multiplier
        currentPnl = (lastPrice - avgCost_) * self.stkpos.position * self.contract_multiplier
        currentPnlPct = lastPrice / avgCost_ - 1.
        logging.info(f"last {lastPrice}, pnl: {currentPnl:.2f} ({currentPnlPct:.2%}), max loss limit: {maxloss_:.2f} ({maxlossPct_:.2%})")
        if currentPnl < maxloss_:
            logger.warning(f"Current loss: {currentPnl:.2f}, max loss limit: {maxloss_:.2f}")
            if self.stkpos.position > 0 and self.trade is None:
                # self.order = MarketOrder('SELL', self.stkpos.position)
                # watch out, with limit order we may not get filled
                # last_5m_hml_ = last_5m_hml(self.bars)
                # logger.info(f"trailing 5m hml {last_5m_hml_} ({np.array2string(last_5m_hml_ / self.lastPrice, formatter=np_pct)})")
                bid_price = get_bid_price()
                mintick = self.ibcontractDetails[0].minTick  # Assuming the minimum tick size is 0.01, adjust as necessary
                bid_price = round(bid_price / mintick) * mintick
                self.order = LimitOrder('SELL', self.stkpos.position, bid_price, discretionaryAmt=round(0.0004 * self.milestone_multiplier * bid_price, 2))
                self.order.account = self.tradingaccount
                # contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
                contract_ = self.ibcontract
                logger.warning(f"Selling {contract_} as {self.order} ...")
            if self.stkpos.position < 0 and self.trade is None:
                logger.warning(f"Buying {-self.stkpos.position} {self.symbol}...")
                # ib.placeOrder(self.stkpos.contract, MarketOrder('BUY', -self.stkpos.position))

            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                    self.orderId = self.trade.order.orderId # we only have orderId after the order is placed, no permId yet
                    # self.tradePermId = self.trade.order.permId
                    self.tradeMgr = TradeManager(self.trade)
                    if self.order.action == 'SELL':
                        self.lastSellTrade = self.trade
                    self.set_state(0) # reset state
                    logger.info(f"Trade placed: {self.trade}, state reset to 0")
                    self.sellclose_bar1m_idx.append(len(self.bars) - 1) # record the bar index when we placed the trade
                    self.sellclose_bar1m.append(self.bars[-1]) # record the bar1m where we placed the trade
                    self.checkpoint('enforceMaxLoss')
                    loop = asyncio.get_event_loop()
                    logger.debug(get_asyncio_running_loop('get_event_loop()')) # expect 'no running event loop'
                    future = asyncio.ensure_future(
                        telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID
                            , text=f"Selling {contract_} as {self.order} {self.trade.log}"))
                    loop.run_until_complete(future)
                    logger.debug(get_asyncio_running_loop('run_until_complete()')) # expect 'no running event loop'
                else:
                    logger.error(f"No live trading, trade not placed: {self.order}")
            elif self.trade in ib.openTrades():
                logger.info(f"Trade is still open: {ib.openTrades()}")
            elif self.trade not in ib.openTrades():
                if self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade is filled: {self.trade.log}"
                    self.trade = None
                    self.orderId = self.tradePermId = -1
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logger.error(f"Trade was not filled: {self.trade}")
                    self.set_state(99) # bail out of main loop
                    # assert False, "Please close out manually."
            else:
                logmsg = f"Impossible state: trade {self.trade} not in {ib.openTrades()}"
                self.trade = None
                self.orderId = self.tradePermId = -1
                self.tradeMgr.clear()
                logger.error(logmsg + f", resetting trade to None")
        return # end of enforceMaxLoss

# global
agent: Agent = None

def onAccountValueUpdate(accountValue: ib_insync.objects.AccountValue):
    # every three minutes
    logger.debug(get_asyncio_running_loop(''))
    logger.debug(f"{accountValue}")
    # pdb.set_trace()
    return # end of onAccountValueUpdate

def onAccountSummaryUpdate(acctValue: ib_insync.objects.AccountValue):
    logger.debug(get_asyncio_running_loop(''))
    logger.info(f"{acctValue}")
    return # end of onAccountSummaryUpdate

def onPnlUpdate(pnl: ib_insync.objects.PnL):
    logger.debug(get_asyncio_running_loop(''))
    logger.info(f"{pnl}")
    # pdb.set_trace()
    return # end of onPnlUpdate

def onPortfolioUpdate(portfolioItem: ib_insync.objects.PortfolioItem) -> None:
    """
    every three minutes, usually following onAccountValueUpdate
    not doing significant function yet, just doing checkings, confirming that we are in sync with IB
    we do the work in onPositionUpdate
    """

    # logger.debug(get_asyncio_running_loop(''))
    # logger.debug(f"{portfolioItem}")
    if agent is None:
        logger.error(f"agent not initialized, expected {portfolioItem}")
        return
    elif portfolioItem.contract.symbol != agent.symbol:
        pass # not our name
        # logger.debug(f"skipping {portfolioItem.contract.symbol} {format_value(portfolioItem.position, True)}")
        return
    elif agent.stkpos is None:
        if portfolioItem.position == 0:
            pass # no position
            return
        else: # portfolioItem.position != 0:
            logger.error(f"agent.stkpos is None, expected {portfolioItem}")
            return
    else: # agent.stkpos is not None and agent is not None
        if agent.stkpos.position == 0 and portfolioItem.position == 0:
            pass # no position, it's fine
            return
        elif agent.stkpos.position == 0 and portfolioItem.position != 0:
            logger.error(f"agent.stkpos.position is zero, expected {portfolioItem}")
            return
    # if portfolioItem.contract.symbol == agent.symbol:
        # ensure we agree with IB on the stock position
        elif portfolioItem.position != agent.stkpos.position:
            logger.warning(f"portfolioItem.position={portfolioItem.position} != agent.stkpos.position={agent.stkpos.position}")
            # could be partially filled
            return
        elif not math.isclose(portfolioItem.averageCost, agent.stkpos.avgCost, abs_tol=.001):
            logger.warning(f"portfolioItem.averageCost={portfolioItem.averageCost:.4f} != agent.stkpos.avgCost={agent.stkpos.avgCost:.4f}")
            return
    # ib.sleep(30) # simulate blocking
    # pdb.set_trace()
    return # end of onPortfolioUpdate

async def onPositionUpdate(newpos: ib_insync.objects.Position):
    def _repr_exec(exec_: Execution):
        return f"({exec_.execId} {exec_.time} {exec_.side})"

    def _repr_exec_lst(execs: list[Execution]):
        return ', '.join([_repr_exec(exec_) for exec_ in execs]) if execs else []

    def _execs_list2tuplst(execs: list[Execution]) -> list[tuple]:
        return [(exec_.execId, exec_.time, exec_.side) for exec_ in execs] if execs else []

    # only care about specific stock positions for now
    # logger.debug(get_asyncio_running_loop(''))
    if agent is None:
        logger.error(f"agent not initialized")
        return
    # if not ((newpos.contract.symbol == agent.symbol) and (newpos.contract.secType == 'STK')):
    if not ((newpos.contract.symbol == agent.symbol) and (newpos.contract.secType == agent.contractType)):
        logger.debug(f"skipping {newpos.contract.secType} {newpos.contract.symbol}")
        # if newpos.contract.secType == 'STK':
        #     logger.debug(f"skipping {newpos.contract.symbol}")
        # else:
        #     logger.warning(f"unexpected secType: {newpos}")
        return
    # check if a trade is triggered outside of the app
    # get all trades so far
    excFilt = ExecutionFilter(symbol=agent.symbol)
    all_fills = await ib.reqExecutionsAsync(excFilt)
    all_execs = [fill.execution for fill in all_fills]

    # ibtrades has all trades for the symbol since app started plus subsequent internal trades but no external trades
    ibtrades = [t for t in ib.trades() if t.contract.symbol == agent.symbol]
    ibfills = [t.fills for t in ibtrades]
    ibexecs = [fill.execution for sublist in ibfills for fill in sublist]

    ext_execs = list(set(_execs_list2tuplst(all_execs)) - set(_execs_list2tuplst(ibexecs)))
    ext_execs_last: Optional[Execution] = None
    if ext_execs:
        # get the most recent external trade
        ext_execs_lst = list(ext_execs)
        # print(f"external execs {ext_execs_lst}")
        ext_execs_last = sorted(ext_execs_lst, key=lambda x: x[1], reverse=True)[0]
        # make sure the timestamp is recent enough, within 1 minute
        if (datetime.datetime.now(local_tz) - ext_execs_last[1]).total_seconds() < 30:
            logger.info(f"external trade: {_execution_repr(ext_execs_last)}")
        else:
            ext_execs_last = None

    # logger.info(f"all_execs={_repr_exec_lst(all_execs)}, ibexecs={_repr_exec_lst(ibexecs)}")
    # logger.info(f"all_execs - ibexecs={set(_execs_list2tuplst(all_execs)) - set(_execs_list2tuplst(ibexecs))}")

    # data = [(o.orderId, o.permId, t) for t, o in [(t, t.order) for t in ibtrades]]
    # # logger.info(f"ib.trades()={data}")
    # want = agent.orderId
    # agent.tradePermId = permId = next((x for orderId, x, _ in data if orderId == want), None)
    # # get the most recent trade (whose permId is highest)
    # most_recent_trade = max(ibtrades, key=lambda t: t.order.permId)
    # # most_recent_trade = max(ibtrades, key=lambda t: t.)
    # if permId is None:
    #     logger.info(f"permId {most_recent_trade.order.permId} is an external trade, action was {most_recent_trade.order.action}")
    #     # if self.lastBuyTime and self.bars[0].date <= self.lastBuyTime and self.lastBuyTime <= self.bars[-1].date:
    #     # in self.bars, filter for the bars after lastBuyTime, then find the max
    #     # if t.order.action == 'BUY':
    #     #     timenow = datetime.datetime.now(local_tz)
    #     #     agent.high_since_buy_bar1m.clear()
    #     #     agent.high_since_buy_bar1m.append(agent.bars[-1])
    #     #     logger.info(f"high_since_buy_bar1m initialized to: {agent.high_since_buy_bar1m}")
    #     # else:
    #     #     pass # SELL order
    # else:
    #     logger.info(f"tradePermId={agent.tradePermId} internal trade")
    logmsg = f"{newpos} id={id(newpos)}"
    if agent:
        logmsg += f" agent.state={agent.state} agent.idxMilestone={agent.idxMilestone}"
        if agent.trade:
            logmsg += f" trade={agent.trade.log}"
            if agent.trade.orderStatus.status == 'Filled' and agent.state == 0:
                logmsg += f" state is zero and last trade is filled, resetting trade status"
                agent.trade = None
                agent.orderId = agent.tradePermId = -1
            if agent.idxMilestone >= 0:
                agent.reset_milestone() # reset milestone
                logmsg += f" resetting strategy1 milestone to -1"
                
    logger.info(logmsg)
    # traceback.print_stack()
    # only care about specific stock positions for now
    if (newpos.contract.symbol == agent.symbol) and (newpos.contract.secType == agent.contractType):
        # sanity check
        if newpos.position != 0 and newpos.avgCost == 0.0:
            p = [p for p in ib.positions() if p.contract.symbol == agent.symbol]
            logger.error(f"ib.positions={p}")
            logger.error(f"position={newpos.position} but avgCost=0.0")
            agent.set_state(99) # bail out of main loop
            return
        # agent.state = 1
        prevstkpos = agent.stkpos
        agent.stkpos = newpos
        agent.useAvgCost = newpos.avgCost
        logger.info(f"updating agent's with stock position: {agent.stkpos} (id={id(newpos)}), prev={prevstkpos}" + (f" (id={id(prevstkpos)})" if prevstkpos else ""))
        # should we change state?
        # let's just warn about possible state change for now
        if (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position != 0 and agent.state == 0:
            logger.info(f"agent state change: 0 -> 1")
            agent.set_state(1)
            # agent.state = 1
            # print stack trace
        elif (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position != 0 and agent.state == 1:
            # nothing's wrong or inconsistent here
            pass
        elif (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position == 0 and agent.state == 0:
            # also nothing's wrong or inconsistent here
            pass
        elif (prevstkpos is not None and (prevstkpos.position != 0)) and newpos.position > prevstkpos.position and agent.state == 1:
            # also nothing's wrong or inconsistent here
            # we are adding to the position
            logger.info(f"adding to the position: {prevstkpos.position} -> {newpos.position}")
            pass
        elif (prevstkpos is not None and (prevstkpos.position != 0)) and newpos.position < prevstkpos.position and agent.state == 0:
            # we are reducing the position, to possibly zero
            logger.info(f"reducing the position: {prevstkpos.position} -> {newpos.position}")
            pass
        elif not (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position == 0 and agent.state == 1:
            logger.info(f"forcing agent state: 1 -> 0")
            agent.set_state(0)
            # agent.state = 0
            if agent.idxMilestone >= 0:
                agent.reset_milestone()
                logger.info(f"resetting strategy1 milestone {agent.idxMilestone} to -1")
        elif not (prevstkpos is None) and (prevstkpos.position == newpos.position) and (prevstkpos.avgCost == newpos.avgCost):
            # why are we getting the same position update?
            logger.warning(f"position and avgCost are the same, why update, prev={prevstkpos} new={newpos}, agent state: {agent.state}")
        elif not (prevstkpos is None) and (prevstkpos.position == newpos.position) and (prevstkpos.avgCost != newpos.avgCost):
            # avgCost changed, no big deal
            pass
            logger.info(f"avgCost changed: {prevstkpos.avgCost} -> {newpos.avgCost}")
        else:
            # why are we getting this?
            logger.warning(f"shouldn't be here: prev={prevstkpos} new={newpos}, agent state: {agent.state}")

        # if prevstkpos is None:
        #     logger.info(f"onPositionUpdate: agent initialized with stock position: {agent.stkpos}, state={agent.state}")
        # logger.info(f"onPositionUpdate: agent initialized with stock position: {agent.stkpos}, state={agent.state}")
    elif (newpos.contract.symbol != agent.symbol) and (newpos.contract.secType == agent.contractType):
        logger.warning(f"not my symbol: {newpos}")
    else:
        logger.warning(f"ignoring new position: {newpos}")
    return # end of onPositionUpdate

def onExecDetailsUpdate(trade: ib_insync.order.Trade, fill: ib_insync.objects.Fill):
    logtext = f"{trade}, {fill}"
    logger.info(logtext)
    if trade.contract.symbol != agent.symbol:
        logger.warning(f"ignoring trade: {trade.contract.symbol}")
        return
    if agent is None:
        logger.error(f"agent not initialized yet")
        return
    # if trade not in agent.execdetailTrade:
    #     agent.execdetailTrade.append(trade)
    # if fill not in agent.execdetailFill:
    #     agent.execdetailFill.append(fill)
    
    logger.info(get_asyncio_running_loop('')) # expect <ProactorEventLoop running=True closed=False debug=False>
    loop = asyncio.get_running_loop()
    # loop = asyncio.get_event_loop()
    task = loop.create_task(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    # future = asyncio.ensure_future(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    # loop.run_until_complete(future)
    # loop.call_soon(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    return # end of onExecDetailsUpdate

def onCancelOrder(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onCancelOrder

def onTradeCancelledEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeCancelledEvent

def onTradeCancelEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeCancelEvent

def onTradeFilledEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeFilledEvent

def onTradeFillEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeFillEvent

def onTradeModifyEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeModifyEvent

def onTradeStatusEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeStatusEvent

def onTradeCommissionReportEvent(trade: ib_insync.order.Trade):
    logger.info(f"{trade}")
    return # end of onTradeCommissionReportEvent

def onOrderStatus(trade: ib_insync.order.Trade):
    if agent is None:
        logger.error(f"agent not initialized yet")
        return
    if trade.contract.symbol != agent.symbol:
        logger.warning(f"not my trade: {trade.contract.symbol}")
        return
    logger.info((f"{trade.order.action} {trade.contract.symbol} orderId={trade.order.orderId} permId={trade.order.permId} "
        f"status={trade.orderStatus.status} "
        f"filled={format_value(trade.orderStatus.filled, True)} "
        f"remaining={format_value(trade.orderStatus.remaining, True)} "
        f"avgFillPrice={trade.orderStatus.avgFillPrice} "
        f"lastFillPrice={trade.orderStatus.lastFillPrice}"))
    if agent.trade is None and trade.orderStatus.status in {'Cancelled', 'Inactive'} and trade.orderStatus.filled == 0:
        pass # it's okay
        return
    elif agent.trade is None:
        logger.error(f"agent's trade is None, shouldn't happen: {trade}")
        return
    if agent.trade.order.orderId != trade.order.orderId:
        logger.error(f"order id mismatch: agent's {agent.trade.order.orderId} != {trade.order.orderId}")
        return
    if trade.orderStatus.status in {'Cancelled', 'Inactive'}:
        if trade.log[-1].errorCode in {451,460}:
            logger.warning(f"Order was {trade.orderStatus.status} due to {trade.log[-1].errorCode}: {trade}")
            logger.warning(f"shutting down agent")
            agent.set_state(99) # bail out of main loop
            return
        if trade.orderStatus.filled == 0:
            logmsg = f"Order was {trade.orderStatus.status}, nothing done, agent state={agent.state}, resetting agent's trade to None"
            if agent.state == 1:
                agent.state = agent.prevstate # undo state change
                logmsg += f", undoing state change"
            agent.trade = None
            agent.orderId = agent.tradePermId = -1
            logger.warning(logmsg)
        else:
            logger.warning(f"Order was {trade.orderStatus.status} but partially filled: {trade}")
    elif trade.orderStatus.status == 'Filled':
        assert trade.orderStatus.remaining == 0, "Expect remaining to be zero"
        sumvalue, sumqty, saleTimestamp = 0.0, 0, datetime.datetime(2024, 1, 1).astimezone()
        for fill in trade.fills:
            sumqty += fill.execution.shares
            sumvalue += fill.execution.shares * fill.execution.price
            saleTimestamp = max(fill.execution.time, saleTimestamp)
        agent.lastSalePrice = sumvalue / sumqty
        agent.lastSellTrade = trade
        agent.lastSaleTime = saleTimestamp
        logger.info(f"Order was filled")
    elif trade.orderStatus.status in {'PreSubmitted','Submitted'} and trade.orderStatus.remaining > 0:
        pass
        # logger.info(f"Order {trade.orderStatus.status}") # already reported above
    else:
        logger.warning(f"Order {trade.orderStatus.status} (not handled)")
    
    return # end of onOrderStatus

def onErrorEvent(reqId, errorCode, errorString, contract):
    # https://interactivebrokers.github.io/tws-api/message_codes.html#system_codes
    if errorCode in [2104, 2106, 2107, 2108, 2158]: # not a real error
        return
    if errorCode == 202:
        # https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
        logger.error("order is subject to price check, too far from current price?")
    logger.info(get_asyncio_running_loop(''))
    logtext = f"reqId={reqId}, errorCode={errorCode}, errorString={errorString}, contract={contract}"
    logger.error(logtext)
    loop = asyncio.get_running_loop()
    task = loop.create_task(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    # future = asyncio.ensure_future(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    # asyncio.run(future)
    return

def onPendingTickers(tickers: set[Ticker]):
    msg = []
    for t in tickers:
        msg.append(f"{t.contract.localSymbol}") # {t.time.astimezone()}
    logger.info(', '.join(msg))
    return

def symbolMktValue(tickerFilter=None):
    # get market value of portfolio

    # Get the current portfolio
    portfolio = ib.portfolio()

    # Get the tickers for the contracts in the portfolio
    tickers = ib.tickers()

    # Create a dictionary to map contract conId to ticker
    conId_to_ticker = {ticker.contract.conId: ticker for ticker in tickers}

    # Calculate market value for each position in the portfolio
    mv = defaultdict(float)
    for position in portfolio:
        contract = position.contract
        if tickerFilter and contract.symbol not in tickerFilter:
            continue
        ticker = conId_to_ticker.get(contract.conId)
        if ticker:
            logger.debug(f"Ticker = {ticker}")
            bid = ticker.close if (ticker.bid == -1.0) or (ticker.bid is None) else ticker.bid
            ask = ticker.close if (ticker.ask == -1.0) or (ticker.ask is None) else ticker.ask
            multiplier = float(contract.multiplier) if contract.multiplier else 1.0
            mktvalue = position.position * multiplier * (bid + ask) / 2
            logger.debug(f"Contract: {contract.localSymbol}, Market Value: {mktvalue}, bid = {bid}, ask = {ask}, multiplier = {multiplier}")
            mv[contract.symbol] += mktvalue
        else:
            logger.warning(f"Ticker not found for contract: {contract.localSymbol}")
            # pass

    return mv

class NoParsingFilter(logging.Filter):
    def filter(self, record):
        return record.getMessage().startswith('ib_insync.wrapper')

def chebyshev_fit(x, y, degree):
    """
    Fit a Chebyshev polynomial of a given degree to the data points (x, y).

    Parameters:
    x (array-like): The x-coordinates of the data points.
    y (array-like): The y-coordinates of the data points.
    degree (int): The degree of the Chebyshev polynomial.

    Returns:
    numpy.polynomial.Chebyshev: The fitted Chebyshev polynomial.
    """
    # Fit the Chebyshev polynomial
    cheb_poly = np.polynomial.Chebyshev.fit(x, y, degree)
    
    return cheb_poly

def resample_bars(bars: BarDataList, resample_interval='2min', use_np_data: bool=False):
    """
    Resample a list of BarData objects into a specified interval.

    Parameters:
    bars (list of BarData): The list of BarData objects to resample.
    resample_interval (str): The resampling interval (e.g., '2min' for 2 minutes).

    Returns:
    pd.DataFrame: The resampled OHLC data.
    """
    # Convert the list of BarData objects to a DataFrame

    if use_np_data:
        data = {
            'date': bars.get_npdate(False),
            'open': bars.get_npopen(False),
            'high': bars.get_nphigh(False),
            'low': bars.get_nplow(False),
            'close': bars.get_npclose(False),
            'volume': bars.get_npvolume(False),
            'barCount': bars.get_npbarCount(False)
        }
    else:
        data = {
            'date': [bar.date for bar in bars],
            'open': [bar.open_ for bar in bars],
            'high': [bar.high for bar in bars],
            'low': [bar.low for bar in bars],
            'close': [bar.close for bar in bars],
            'volume': [bar.volume for bar in bars],
            'barCount': [bar.barCount for bar in bars]
        }
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)

    # Resample the DataFrame
    resampled_df = df.resample(resample_interval).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
        'barCount': 'sum'
    })

    return resampled_df

async def telegram_init(bot):
    # bot = telegram.Bot(TELEGRAM_TOKEN)
    # u = bot.get_me()
    # logger.info(f"Telegram user: {u}")
    # async with bot:
    with contextlib.suppress(telegram.error.NetworkError):
        u = bot.get_me()
        logger.info(f"Telegram user: {await u}")
        # asyncio.Task.set_result(await u)

def load_spec_file(scriptdir: str = os.path.dirname(os.path.realpath(__file__))
    , filename: str = 'spec.json') -> dict:
    # spec file
    
    specfile = os.path.join(scriptdir, filename)
    if not os.path.exists(specfile):
        logger.error(f"Spec file not found: {specfile}")
        sys.exit(1)
    with open(specfile, 'r') as f:
        spec = json.load(f)
    logger.info(f"spec file loaded: {specfile}")
    return spec

import ctypes
import uuid
from ctypes import wintypes

# Constants from the Windows API
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def prevent_sleep() -> None:
    # Prevent Windows from sleeping
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

def restore_sleep() -> None:
    # Restore the default behavior
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

# https://stackoverflow.com/questions/72847468/ctypes-how-to-parser-buffer-content

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_uint32),
        ("Data2", ctypes.c_uint16),
        ("Data3", ctypes.c_uint16),
        ("Data4", ctypes.c_uint8 * 8)
    ]

# class GUID(ctypes.Structure):
#     _fields_ = [
#         ("Data1", wintypes.ULONG),
#         ("Data2", wintypes.USHORT),
#         ("Data3", wintypes.USHORT),
#         ("Data4", wintypes.BYTE * 8)
#     ]

    # def __str__(self):
    #     return f"{{{self.Data1:08X}-{self.Data2:04X}-{self.Data3:04X}-{''.join(f'{x:02X}' for x in self.Data4)}}}"
    # def __repr__(self):
    #     return f"GUID('{self}')"

    def __str__(self):
        return (f"{{{self.Data1:08x}-{self.Data2:04x}-{self.Data3:04x}-"
                f"{bytes(self.Data4[:2]).hex()}-{bytes(self.Data4[2:]).hex()}}}")

    # GUID_ptr = ctypes.POINTER['GUID']
    @staticmethod
    def to_string(guid_ptr) -> str:
        return str(guid_ptr.contents)

    def __init__(self, guid = None):
        if guid is not None:
            data = uuid.UUID(guid)
            self.Data1 = data.time_low
            self.Data2 = data.time_mid
            self.Data3 = data.time_hi_version
            self.Data4[0] = data.clock_seq_hi_variant
            self.Data4[1] = data.clock_seq_low
            self.Data4[2:] = data.node.to_bytes(6, "big")

    def __bytes__(self):
        return bytes(self.Data1.to_bytes(4, "little")
                    + self.Data2.to_bytes(2, "little")
                    + self.Data3.to_bytes(2, "little")
                    + self.Data4)

def GetPowerSetting() -> str:
    # https://learn.microsoft.com/en-us/windows/win32/api/powersetting/nf-powersetting-powergetactivescheme
    # Define necessary constants and types
    PowerGetActiveScheme = ctypes.windll.powrprof.PowerGetActiveScheme
    # [out] A pointer that receives a pointer to a GUID structure. Use the LocalFree function to free this memory.
    PowerGetActiveScheme.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.POINTER(GUID))]
    PowerGetActiveScheme.restype = wintypes.DWORD

    # Initialize variables
    active_scheme_guid_ptr = ctypes.POINTER(GUID)() # Create a pointer to a GUID

    # Call the function
    result = PowerGetActiveScheme(None, ctypes.byref(active_scheme_guid_ptr))
    if result == 0:  # ERROR_SUCCESS
        return GUID.to_string(active_scheme_guid_ptr)
    else:
        raise ctypes.WinError(result)
    # end of GetPowerSetting

def get_friendly_name(scheme_guid: GUID) -> str:
    PowerReadFriendlyName = ctypes.windll.powrprof.PowerReadFriendlyName
    PowerReadFriendlyName.argtypes = [ctypes.c_void_p, ctypes.POINTER(GUID), ctypes.POINTER(GUID), ctypes.POINTER(GUID), ctypes.POINTER(ctypes.c_wchar), ctypes.POINTER(ctypes.c_uint32)]
    PowerReadFriendlyName.restype = ctypes.c_uint32

    buffer_size = ctypes.c_uint32(0)
    PowerReadFriendlyName(None, ctypes.byref(scheme_guid), None, None, None, ctypes.byref(buffer_size))
    # print(buffer_size.value)
    # buffer = (ctypes.c_ubyte * buffer_size.value)()
    buffer = ctypes.create_unicode_buffer(buffer_size.value)
    result = PowerReadFriendlyName(None, ctypes.byref(scheme_guid), None, None, buffer, ctypes.byref(buffer_size))

    if result == 0:  # ERROR_SUCCESS
        return buffer.value
    else:
        raise ctypes.WinError(result)  
    # end of get_friendly_name

# friendly_name = get_friendly_name(active_scheme_guid_ptr.contents)
# print(f"Active Power Scheme Friendly Name: {friendly_name}")

def main():
#if __name__ == "__main__":
    # print(get_asyncio_running_loop('__main__: ')) # expect 'no running event loop'

    # parse command line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbol', type=str, help='Ticker symbol to trade')
    argparser.add_argument('numshares', type=int, nargs='?', help='Number of shares to trade')
    argparser.add_argument('maxloss', type=float, nargs='?', help='Max loss threshold')
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--run_until', type=str, help='Run until this time (HH:MM)')
    argparser.add_argument('--live_trading', action='store_true', help='Live trading')
    argparser.add_argument('--account', type=str, default='paper', help='Account number to use')
    argparser.add_argument('--use5s', action='store_true', help='Use 5s bars')
    argparser.add_argument('--contract_type', type=str, default='STK', help='Contract type (FUT, STK, CASH)')
    argparser.add_argument('--expiry', type=str, help='Contract expiry YYYYMM (for futures)')
    argparser.add_argument('--exchange', type=str, help='Contract exchange')
    argparser.add_argument('--strategy', type=int, default=1, help='Strategy number')
    argparser.add_argument('--avgcost_prevclose', action='store_true', help='Use previous closing level as average cost')
    args = argparser.parse_args()

    # must come before any logging calls
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')
    # moved to top level
    # logging.basicConfig(level=args.loglevel
    #     , format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    # )
    # create handlers
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(args.loglevel)
    # console_handler.setFormatter(formatter)
    if args.account == 'paper':
        account_txt = ''
    else:
        account_txt = f"_{args.account}"

    logfilesuffix = f'{datetime.datetime.now(local_tz):%y%m%d_%H%M}_{computername}{account_txt}_{program_name}'
    datafilesuffixdt = f'{args.symbol}_{datetime.datetime.now(local_tz):%y%m%d}_{computername}{account_txt}'
    logfilename = os.path.join(scriptdir, 'logs', f'{args.symbol}_{logfilesuffix}.log')
    file_handler = logging.FileHandler(logfilename)
    # file_handler.setLevel(args.loglevel)
    file_handler.setFormatter(formatter)

    # # add handlers to logger
    global logger
    logger = logging.getLogger()
    if args.loglevel:
        logger.setLevel(args.loglevel)

    logger.info(f"logging to {logfilename}")
    # # in the meantime, remind user to set power setting to 'full'
    # pwr = GetPowerSetting()
    # if pwr != '{8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c}':
    #     logger.error(f"Expect full power setting, got {pwr}")
    #     sys.exit(1)

    # # logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logging.getLogger('ib_insync').setLevel(logging.WARN)
    logging.getLogger('ib_insync.objects').setLevel(logging.INFO)
    logging.getLogger('ib_insync.Decoder').setLevel(logging.DEBUG)

    # logger.addFilter(NoParsingFilter())

    logger.info(f"module loaded: {inspect.getfile(eventkit)}")
    logger.info(f"module loaded: {inspect.getfile(ib_insync)}")
    logger.info(f"module loaded: {inspect.getfile(telegram)}")
    logger.info(f"module loaded: {inspect.getfile(filterpy)}")

    logger.info(f"TWS API version: {ibapi.__version__}, ib_insync: {ib_insync.__version__}, telegram: {telegram.__version__}")

    logger.info("Script is starting...")

    logger.info(f"args: {args}")

    # args check
    contract_type = args.contract_type
    if args.contract_type == 'FUT':
        all_good = True
        if not args.expiry:
            logger.error(f"Future contract must specify '--expiry'")
            all_good = False
        if not args.exchange:
            logger.error(f"Future contract must specify '--exchange'")
            all_good = False
        if not all_good:
            return -1
    elif args.contract_type == 'FUND':
        pass

    spec = load_spec_file()

    # util.logToConsole(logging.DEBUG) # show network traffic

    # get IB client id from cmd line or spec file
    speckey = args.symbol
    if args.symbol not in spec['root'] and args.numshares and args.maxloss:
        speckey = 'default'
        logger.error(f"Symbol {args.symbol} not found in spec file, using default")
    elif args.symbol not in spec['root']:
        logger.error(f"Symbol {args.symbol} not found in spec file, must provide numshares and maxloss")
        sys.exit(1)
    
    if args.account != 'paper' and args.account in spec and args.symbol in spec[args.account]:
        # account, symbol are in spec file
        spec_a = spec[args.account][args.symbol] # shortcut to account.symbol.*
    else:
        spec_a = {}
    expiry = ''
    exchange = 'SMART'
    if args.symbol in spec['root']:
        spec_p = spec['root'][args.symbol] # shortcut to root.symbol.*
        # get the contract type
        contract_type = spec_p.get('contract_type', '')
        if contract_type in {'FUT'}:
            expiry = spec_p.get('expiry', '')
            exchange = spec_p.get('exchange', '')
            if not expiry or not exchange:
                logger.error(f"Contract type {contract_type} must specify expiry and exchange")
                sys.exit(1)
        elif contract_type in {'STK'}:
            pass
        else:
            logger.error(f"Contract type {contract_type} not valid")
            sys.exit(1)
    else:
        spec_p = {}
    spec_d = spec['root']['default'] # shortcut to root.default.*
    # clientid = args.clientid if args.clientid else spec_p['clientid']
    if args.clientid:
        clientid = args.clientid
    elif 'clientid' in spec_a:
        clientid = spec_a['clientid']
    elif 'clientid' in spec_p:
        clientid = spec_p['clientid']
    elif 'clientid' in spec_d:
        clientid = spec_d['clientid']
    else:
        clientid = np.random.randint(5000, 50000)
        # logger.error(f"TWS Client ID not found in spec file nor in command line")
        # sys.exit(1)
    logger.info(f"Using TWS Client ID: {clientid}")

    h5file = os.path.join(scriptdir, 'data', f'tracker_{datafilesuffixdt}.h5')
    global h5store
    h5store = pd.HDFStore(h5file, 'a')

    # telegram
    TELEGRAM_TOKEN = os.environ.get('TELEGRAMTOKEN', '')
    if TELEGRAM_TOKEN == '':
        logger.error(f"TELEGRAM_TOKEN not found in environment")
        sys.exit(1)

    print(get_asyncio_running_loop('')) # expect 'no running event loop'
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    util.run(telegram_init(bot))
    print(get_asyncio_running_loop('')) # expect '<ProactorEventLoop running=True closed=False debug=False>
    # t = asyncio.create_task(telegram_init(bot))
    # t.add_done_callback(lambda x: logger.info(f"Telegram user: {x.result()}"))

    # IB
    global ib, managedAccounts
    ib = IB()
    if args.account != 'paper':
        ib.connect(args.host, args.port, clientId=clientid, account=args.account)
    else:
        ib.connect(args.host, args.port, clientId=clientid, timeout=60)
    serverVersion = ib.client.serverVersion()
    logger.info(f"Connected to TWS API server version {serverVersion}")
    if serverVersion < 178:
        logger.error(f'TWS version {serverVersion} is too old. Update to latest version.')
        ib.disconnect()
        sys.exit(1)
    # to test connection
    # https://www.interactivebrokers.com/cgi-bin/conn_test.pl

    # get accounts
    managedAccounts = ib.managedAccounts()
    logger.info(f"Managed accounts: {managedAccounts}")
    # get account specific specs
    numshares_a, maxloss_a, account = 0, 0.0, ''
    if args.account == 'paper' and len(managedAccounts) == 1: # only one account
        account = managedAccounts[0]
    elif args.account == 'paper' and len(managedAccounts) > 1:
        logger.error(f"Multiple accounts found, must specify account")
        sys.exit(1)
    elif args.account != 'paper' and args.account in managedAccounts: # specified account
        account = args.account
    else:
        logger.error(f"Account {args.account} not found in managed accounts")
        sys.exit(1)

    logger.info(f"Using account: {account}")
    if spec.get(account):
        spec_a = spec[account]
        if args.symbol in spec_a:
            numshares_a = spec_a[args.symbol].get('numshares', 0)
            maxloss_a = spec_a[args.symbol].get('maxloss', 0.0)

    # print portfolio
    sp_ = [p for p in ib.portfolio(account) if p.contract.symbol in [args.symbol]]
    logger.info(f"Portfolio: {sp_}")

    # find stock position of a given symbol in the portfolio
    sp_ = [p for p in ib.positions(account) if p.contract.symbol in [args.symbol] and p.contract.secType == contract_type]
    # assert len(sp_) == 1
    # if len(sp_) == 0:
    #     logger.warning(f"Stock position not found for {args.symbol}")

    global agent
    milemult = spec_p.get('milestone_multiplier', 1)
    agent = Agent(symbol=args.symbol, liveTrading=args.live_trading
                  , contractType=contract_type, expiry=expiry, exchange=exchange
                  , tradingaccount=account
                  , maxloss=args.maxloss if args.maxloss else maxloss_a if maxloss_a != 0.0 else spec_p['maxloss']
                  , numshares=args.numshares if args.numshares else numshares_a if numshares_a !=0 else spec_p['numshares']
                  , upPctMilestone=np.asarray(spec['root'][speckey]['upPctMilestone']) * milemult
                  , dnPctMilestone=np.asarray(spec_p.get('dnPctMilestone', spec_d['dnPctMilestone'])) * milemult
                  , stopLossPct=np.asarray(spec['root'][speckey]['stopLossPct']) * milemult
                  , mile0_max_retracement_pct=spec_p.get('mile0_max_retracement_pct', spec_d['mile0_max_retracement_pct']) # * milemult
                  , mile0_max_retracement_absolute_min_pct=spec_p.get('mile0_max_retracement_absolute_min_pct', spec_d['mile0_max_retracement_absolute_min_pct']) * milemult
                  , use5s=True if args.use5s else False
                  , avgcost_prevclose=True if args.avgcost_prevclose else False
                  , strategynum=args.strategy
                  , args=args
                  , ib=ib
    )
    if len(sp_) > 0:
        agent.stkpos = sp_[0]
        agent.state = 1
        logger.info(f"Tracked position: {agent.stkpos}")
    else:
        agent.state = 0
        logger.info(f"No position found for {args.symbol}")

    # resume previous session
    pklfile = os.path.join(scriptdir, 'data', f'tracker_{datafilesuffixdt}.pkl')
    global fpkl
    data = None
    if not os.path.exists(pklfile) or os.path.getsize(pklfile) == 0:
        fpkl = open(pklfile, 'wb') # write binary
        pklinit = {
            'symbol': 'init',
            'session_start': [datetime.datetime.now(local_tz)],
            'session_end': [],
            'buyopen_bar1m_idx': [],
            'sellclose_bar1m_idx': [],
            'buyopen_bar1m': [],
            'sellclose_bar1m': [],
            'high_since_buy_bar1m': [],
        }
        pickle.dump(pklinit, fpkl) # initialize it
        logger.info(f"Initialized pkl file: {pklfile}")
    else:
        logger.info(f"Loading pkl file: {pklfile}")
        fpkl = open(pklfile, 'r+b') # read/write binary
        data = pickle.load(fpkl)
        if data['symbol'] == 'init' and data['buyopen_bar1m_idx'] == [] and data['sellclose_bar1m_idx'] == []:
            # TODO why got here
            logger.info(f"Previous session didn't write anything, resetting")
            # data = None # continue as normal, previous session didn't write anything
        elif data['symbol'] != args.symbol:
            logger.error(f"Previous session symbol {data['symbol']} doesn't match {args.symbol}, resetting")
            # continue as normal
        else:
            data['session_start'].append(datetime.datetime.now(local_tz))
            pass # all good
            # logger.info(f"Previous session data: {data}")
    if data:
        agent.resume_session(data)

    logger.info(f"Agent State: {agent}")

    account = ib.managedAccounts()[0]
    # print(ib.managedAccounts())

    # no need to request updates, event fires every 3 minutes automatically
    ib.accountValueEvent += onAccountValueUpdate
    ib.updatePortfolioEvent += onPortfolioUpdate
    ib.execDetailsEvent += onExecDetailsUpdate
    # https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
    ib.cancelOrderEvent += onCancelOrder
    ib.orderStatusEvent += onOrderStatus

    ib.accountSummaryEvent += onAccountSummaryUpdate
    ib.pnlEvent += onPnlUpdate
    ib.errorEvent += onErrorEvent
    
    ib.pnlEvent += onPnlUpdate
    # ib.reqPnL(account)

    ib.positionEvent += onPositionUpdate
    # ib.reqPositions()

    dtnow = datetime.datetime.now(local_tz)
    if args.run_until:
        untilTime = datetime.datetime.combine(dtnow, datetime.datetime.strptime(args.run_until, '%H:%M').time(), tzinfo=local_tz)
    else:           
        if dtnow.weekday() >= 5:  # Saturday or Sunday
            untilTime = dtnow + datetime.timedelta(minutes=1) # run for 10 minutes
        # untilTime = dtnow + datetime.timedelta(hours=2.2)
        elif dateutil.parser.parse('20:00:00').replace(tzinfo=local_tz) < dtnow: # after 8:00 PM, run until 11:59 PM
            untilTime = dateutil.parser.parse('23:59:00').replace(tzinfo=local_tz) # 11:59 PM
        elif dateutil.parser.parse('16:45:00').replace(tzinfo=local_tz) < dtnow: # after 4:45 PM, run until 8:00 PM
            untilTime = dateutil.parser.parse('20:02:00').replace(tzinfo=local_tz) # 8:00 PM
        elif dtnow < dateutil.parser.parse('16:02:00').replace(tzinfo=local_tz): # before 4:02 PM, run until 4:02 PM
            untilTime = datetime.datetime.combine(dtnow, datetime.time(16, 2, 0)) # 4:02 PM
        else:
            untilTime = dtnow + datetime.timedelta(minutes=1)
    doOnce = True

    # run initialization before market open
    status = agent.strategyInitPreOpen()
    # status = agent.simpleLongStrategy1InitPreOpen() # could take 60 seconds to timeout/complete
    if status < 0:
        logger.error(f"Pre-Initialization failed: {status}")
        sys.exit(1)
    else:
        logger.info(f"Pre-Initialization successful")
    idx = agent.ibTradingSessionIdx
    cdliquid: ib_insync.contract.ContractDetails = agent.ibcontractDetails[0].liquidSessions()[idx]
    cdl_full: ib_insync.contract.ContractDetails = agent.ibcontractDetails[0].tradingSessions()[idx]

    if dtnow.weekday() >= 5:  # Saturday or Sunday
        pass
    elif not args.run_until:
        # wait until market open
        # waitUntil = dateutil.parser.parse('09:30:00') - datetime.timedelta(seconds=70) # leave some buffer if initializations take time
        mkt_start, mkt_end = get_market_hours()
        # waitUntil = cdliquid.start - datetime.timedelta(seconds=70) # leave some buffer if initializations take time
        waitUntil = mkt_start - datetime.timedelta(seconds=70) # leave some buffer if initializations take time
        if datetime.datetime.now(local_tz) < waitUntil:
            logger.info(f"Waiting until {waitUntil.astimezone()}")
            util.waitUntil(waitUntil)

        waitUntil2 = dateutil.parser.parse('17:00:00').replace(tzinfo=local_tz) - datetime.timedelta(minutes=1)
        #if dtnow < waitUntil2 and dateutil.parser.parse('16:16:00') < dtnow:
        if dateutil.parser.parse('16:58:00').replace(tzinfo=local_tz) < datetime.datetime.now(local_tz) < waitUntil2:
            logger.info(f"Waiting until {waitUntil2}")
            util.waitUntil(waitUntil2)

    if not args.run_until:
        # logger.info("no --run_until specified, running until market close")
        # untilTime = cdliquid.end + datetime.timedelta(minutes=1) # end of market day
        untilTime = mkt_end + datetime.timedelta(minutes=1) # end of market day
        # if untilTime < datetime.datetime.now(local_tz):
        #     untilTime = cdl_full.end + datetime.timedelta(minutes=1) # end of full trading day
    logger.info(f"Running until {untilTime.astimezone()}")
    # logger.info(f"Running until {untilTime.astimezone().isoformat()}, now is {datetime.datetime.now(local_tz).isoformat()}")
    while datetime.datetime.now(datetime.timezone.utc) < untilTime and agent.get_state() != 99:
        logger.debug(get_asyncio_running_loop('main loop: ')) # expect 'no running event loop'
        # get market data for all positions
        if doOnce:
            # contracts_ = [p.contract for p in ib.positions()]
            # contracts = ib.qualifyContracts(*contracts_)
            # logger.info(f"ib.qualifyContracts: {[x.localSymbol for x in contracts_]}")
            doOnce = False

            # ensure no outstanding trades
            ot = [t for t in ib.reqAllOpenOrders() if t.contract.symbol == agent.symbol]
            if ot:
                logger.warning(f"Outstanding trades: {ot}")
                # for t in ot:
                #     logger.warning(f"Canceling trade: {t}")
                #     ib.cancelOrder(t.order)
                # wait for trades to cancel
                while (ot := [t for t in ib.reqAllOpenOrders() if t.contract.symbol == agent.symbol]):
                    logger.warning(f"Waiting for trades to cancel: {ot}")
                    ib.sleep(np.random.uniform(low=2.0, high=20.0))
            else:
                logger.info(f"ib.reqAllOpenOrders: no outstanding orders")

            # request live market data
            # agent.request_historical_data() # moved to strategyInitPreOpen
            
            # global NPMKTOPENIDX
            # if NPMKTOPENIDX < 0:
            #     results = np.ravel(np.where(agent.bars.npdate_ == NPMKTOPEN))
            #     if len(results) > 0:
            #         # FIXME
            #         NPMKTOPENIDX = results[0]
            #         # logger.info(f"market open idx={NPMKTOPENIDX} date={agent.bars.npdate_[NPMKTOPENIDX:NPMKTOPENIDX+3]}")
            #     else:
            #         NPMKTOPENIDX = -1_000
            #         idx = agent.bars._npidx - 3
            #         logger.warning(f"market is not open: {agent.bars.npdate_[0:3]}..{agent.bars.npdate_[idx:]}")
            #         # should we bail?

            # status = agent.simpleLongStrategy1Init()
            status = agent.strategyInit()
        # for x in contracts:
        #     if x.symbol in agent.symbol:
        #         logger.debug(f"ib.reqMktData(snapshot=True) for {x.localSymbol}...")
        #         ib.reqMktData(x, '', snapshot=True, regulatorySnapshot=False) # gotta request snapshot every time
        # # wait for price updates
        # logger.debug(f"reqId2Ticker: {ib.wrapper.reqId2Ticker.keys()}")
        # while ib.wrapper.reqId2Ticker:
        #     logger.debug(f"Spinning sleep(1) waiting for |ib.wrapper.reqId2Ticker| {len(ib.wrapper.reqId2Ticker)} ...")
        #     ib.sleep(1)

        # # get market value of portfolio
        # logger.debug(f"Getting market value of portfolio...")
        # mv = symbolMktValue(agent.symbol)
        
        # p_dfg = util.df(ib.portfolio()).assign(symbol=lambda _df: _df.contract.apply(lambda c: c.symbol)
        #     , localSymbol=lambda _df: _df.contract.apply(lambda c: c.localSymbol)
        #     , secType=lambda _df: _df.contract.apply(lambda c: c.secType)
        #     , totalPnL=lambda _df: _df.realizedPNL + _df.unrealizedPNL
        #     ).groupby('symbol').agg({'marketValue': 'sum', 'unrealizedPNL': 'sum', 'realizedPNL': 'sum', 'totalPnL': 'sum'})
        # # p_dfg['mv'] = p_dfg.index.map(mv)
        # logger.debug(f"Portfolio:\n{p_dfg}")
        # logger.info(f"Market Value: {mv[agent.symbol]:.2f}")
        if agent.stkpos and agent.stkpos.position != 0:
            logger.info(f"Market Value: {agent.bars[-1].close * agent.stkpos.position:.2f}")
        logger.debug(f"Bars: len={len(agent.bars)} last={agent.bars[-1]}")

        # enforce max loss
        if agent.stkpos and agent.stkpos.position > 0:
            # agent.enforceMaxLoss(agent.bars[-1].close)
            agent.enforceMaxLoss(get_bid_price())

        # resample the bars
        df5m = resample_bars(agent.bars, '5min')
        df15m = resample_bars(agent.bars, '15min')
        df30m = resample_bars(agent.bars, '30min')
        df1h = resample_bars(agent.bars, '1h')
        
        logger.debug(f"5m resampled bars:\n{df5m.tail()}")

        # compute slope of close prices
        s = slice(-10, None) # last N bars
        y = [b.close for b in agent.bars[s]]
        y_high = [b.high for b in agent.bars[s]]
        y_low = [b.low for b in agent.bars[s]]
        y_open = [b.open_ for b in agent.bars[s]]
        x = np.arange(len(y))
        logger.debug(f"x,y: {x}, {y}")

        # PCHIP fit
        price_func = scipy.interpolate.PchipInterpolator(x, y, extrapolate=False)
        price_func_deriv = price_func.derivative()
        price_slopes = price_func_deriv(x)
        logger.debug(f"PCHIP 1m price slopes: {price_slopes}")

        # 5m resampled
        y = [b for b in df5m['close'].iloc[s]]
        y_high = [b for b in df5m['high'].iloc[s]]
        y_low = [b for b in df5m['low'].iloc[s]]
        y_open = [b for b in df5m['open'].iloc[s]]
        x = np.arange(len(y))
        logger.debug(f"x,y: {x}, {y}")
        price_func = scipy.interpolate.PchipInterpolator(x, y, extrapolate=False)
        price_func_deriv = price_func.derivative()
        price_slopes = price_func_deriv(x)
        logger.debug(f"PCHIP 5m price slopes: {price_slopes}")
        # np.log(df5m['close'] / df5m['close'].shift(1))

        # # Chebyshev polynomial fit
        # deg = 7
        # cheb_poly = np.polynomial.Chebyshev.fit(x, y, deg, full=True)
        # logger.debug(f"chebyshev close polyfit: {cheb_poly}")
        # cheb_poly_derivative = cheb_poly[0].deriv()
        # slopes = cheb_poly_derivative(x)
        # logger.info(f"chebyshev close slopes: {slopes}")

        # # optimize the slope of close prices with high/low constraints
        # def objective(coeffs):
        #     cheb = np.polynomial.Chebyshev(coeffs, domain=cheb_poly[0].domain)
        #     return np.sum((cheb(x) - y) ** 2)

        # def constraint(coeffs):
        #     cheb = np.polynomial.Chebyshev(coeffs, domain=cheb_poly[0].domain)
        #     fitted = cheb(x)
        #     high_constraint = y_high - fitted
        #     low_constraint = fitted - y_low
        #     return np.concatenate((high_constraint, low_constraint))

        # initial_guess = cheb_poly[0].coef # fit without constraints
        # cons = {'type': 'ineq', 'fun': constraint}
        # result = scipy.optimize.minimize(objective, initial_guess, constraints=cons)
        # logger.debug(f"cb close polyfit w/ constraints: {result}")
        # cheb_cons = np.polynomial.Chebyshev(result.x, domain=cheb_poly[0].domain)
        # cheb_cons_derivative = cheb_cons.deriv()
        # cons_slopes = cheb_cons_derivative(x)
        # logger.info(f"chebyshev close slopes w/ constraints: {cons_slopes}")

        # # compute slope of open/close prices
        # s = slice(-5, None)
        # y = np.array( [ [b.open, b.close] for b in agent.bars[s] ]).ravel()
        # x = np.arange(len(y))
        # deg = 7
        # cheb_poly = np.polynomial.Chebyshev.fit(x, y, deg, full=True)
        # cheb_poly_derivative = cheb_poly[0].deriv()
        # slopes = cheb_poly_derivative(x)
        # logger.info(f"chebyshev o/c slopes: {slopes}")

        sleepsecs: float = 10
        logger.debug(f"sleeping for {sleepsecs} seconds...")
        ib.sleep(sleepsecs)

    # # dump the bars to a file
    # filesuffix = dtnow.strftime('%Y%m%d_%H%M%S')
    # df = util.df(bars_1)
    # df.to_csv(f'NVDA_{filesuffix}_H.csv')

    # df = util.df(bars_2)
    # df.to_csv(f'META_{filesuffix}_H.csv')

    # df = util.df(bars_3)
    # df.to_csv(f'IWM_{filesuffix}_H.csv')

    if agent.bars and not agent.use5s:
        logger.info(f"cancelHistoricalData: len(bars)={len(agent.bars)} {agent.bars._npidx} {agent.bars._npidx_rth_start} {agent.bars._npidx_rth_end}")
        ib.cancelHistoricalData(agent.bars)
    elif agent.use5s and agent.bars5s and hasattr(agent.bars5s, 'reqId'):
        ib.cancelHistoricalData(agent.bars5s)
        logger.info(f"cancelHistoricalData: len(bars5s)={len(agent.bars5s)}") # , first={agent.bars5s[0] if agent.bars5s else 'N/A'}, last={agent.bars5s[-1] if agent.bars5s else 'N/A'}
        logger.info(f"bars5s: len={len(agent.bars5s)} {agent.bars5s._npidx} {agent.bars5s._npidx_rth_start} {agent.bars5s._npidx_rth_end}")
        logger.info(f"bars1m: len={len(agent.bars)} {agent.bars._npidx} {agent.bars._npidx_rth_start} {agent.bars._npidx_rth_end}")
        # logger.info(f"bars10s: {len(agent.bars10s)} {agent.bars10s._npidx} {agent.bars10s._npidx_rth_start} {agent.bars10s._npidx_rth_end}")
        # logger.info(f"bars15s: {len(agent.bars15s)} {agent.bars15s._npidx} {agent.bars15s._npidx_rth_start} {agent.bars15s._npidx_rth_end}")
        # logger.info(f"bars30s: {len(agent.bars30s)} {agent.bars30s._npidx} {agent.bars30s._npidx_rth_start} {agent.bars30s._npidx_rth_end}")
        # logger.info(f"bars2m: {len(agent.bars2m)} {agent.bars2m._npidx} {agent.bars2m._npidx_rth_start} {agent.bars2m._npidx_rth_end}")
        # logger.info(f"bars5m: {len(agent.bars5m)} {agent.bars5m._npidx} {agent.bars5m._npidx_rth_start} {agent.bars5m._npidx_rth_end}")
        # logger.info(f"bars10m: {len(agent.bars10m)} {agent.bars10m._npidx} {agent.bars10m._npidx_rth_start} {agent.bars10m._npidx_rth_end}")
        # logger.info(f"bars15m: {len(agent.bars15m)} {agent.bars15m._npidx} {agent.bars15m._npidx_rth_start} {agent.bars15m._npidx_rth_end}")
        # logger.info(f"5s: {pd.DataFrame({'date': agent.bars5s.npdate[0:3], 'open': agent.bars5s.npopen[0:3], 'close': agent.bars5s.npclose[0:3], 'high': agent.bars5s.nphigh[0:3], 'low': agent.bars5s.nplow[0:3]})}")
        # logger.info(f"10s: {pd.DataFrame({'date': agent.bars10s.npdate[0:3], 'open': agent.bars10s.npopen[0:3], 'close': agent.bars10s.npclose[0:3], 'high': agent.bars10s.nphigh[0:3], 'low': agent.bars10s.nplow[0:3]})}")
        # logger.info(f"15s: {pd.DataFrame({'date': agent.bars15s.npdate[0:3], 'open': agent.bars15s.npopen[0:3], 'close': agent.bars15s.npclose[0:3], 'high': agent.bars15s.nphigh[0:3], 'low': agent.bars15s.nplow[0:3]})}")
        # logger.info(f"30s: {pd.DataFrame({'date': agent.bars30s.npdate[0:3], 'open': agent.bars30s.npopen[0:3], 'close': agent.bars30s.npclose[0:3], 'high': agent.bars30s.nphigh[0:3], 'low': agent.bars30s.nplow[0:3]})}")
        # logger.info(f"1m: {pd.DataFrame({'date': agent.bars.npdate[0:3], 'open': agent.bars.npopen[0:3], 'close': agent.bars.npclose[0:3], 'high': agent.bars.nphigh[0:3], 'low': agent.bars.nplow[0:3]})}")
        # logger.info(f"2m: {pd.DataFrame({'date': agent.bars2m.npdate[0:3], 'open': agent.bars2m.npopen[0:3], 'close': agent.bars2m.npclose[0:3], 'high': agent.bars2m.nphigh[0:3], 'low': agent.bars2m.nplow[0:3]})}")
        # logger.info(f"5m: {pd.DataFrame({'date': agent.bars5m.npdate[0:3], 'open': agent.bars5m.npopen[0:3], 'close': agent.bars5m.npclose[0:3], 'high': agent.bars5m.nphigh[0:3], 'low': agent.bars5m.nplow[0:3]})}")
        # logger.info(f"10m: {pd.DataFrame({'date': agent.bars10m.npdate[0:3], 'open': agent.bars10m.npopen[0:3], 'close': agent.bars10m.npclose[0:3], 'high': agent.bars10m.nphigh[0:3], 'low': agent.bars10m.nplow[0:3]})}")
        # logger.info(f"15m: {pd.DataFrame({'date': agent.bars15m.npdate[0:3], 'open': agent.bars15m.npopen[0:3], 'close': agent.bars15m.npclose[0:3], 'high': agent.bars15m.nphigh[0:3], 'low': agent.bars15m.nplow[0:3]})}")
        # logger.info(f"len(bars)={len(agent.bars)}, first={agent.bars[0] if agent.bars else 'N/A'}, last={agent.bars[-1] if agent.bars else 'N/A'}")
        # logger.info(f"len(bars2m)={len(agent.bars2m)}, first={agent.bars2m[0] if agent.bars2m else 'N/A'}, last={agent.bars2m[-1] if agent.bars2m else 'N/A'}")
        # logger.info(f"len(bars5m)={len(agent.bars5m)}, first={agent.bars5m[0] if agent.bars5m else 'N/A'}, last={agent.bars5m[-1] if agent.bars5m else 'N/A'}")
        # logger.info(f"len(bars10m)={len(agent.bars10m)}, first={agent.bars10m[0] if agent.bars10m else 'N/A'}, last={agent.bars10m[-1] if agent.bars10m else 'N/A'}")
        # logger.info(f"len(bars15m)={len(agent.bars15m)}, first={agent.bars15m[0] if agent.bars15m else 'N/A'}, last={agent.bars15m[-1] if agent.bars15m else 'N/A'}")
        # h5store.put('bars10s', util.df(agent.bars10s))
        # h5store.put('bars15s', util.df(agent.bars15s))
        # h5store.put('bars30s', util.df(agent.bars30s))
        # h5store.put('bars2m', util.df(agent.bars2m))
        # h5store.put('bars5m', util.df(agent.bars5m))
        # h5store.put('bars10m', util.df(agent.bars10m))
        # h5store.put('bars15m', util.df(agent.bars15m))
    logger.info("Script has finished.")

class ControlCTrap:
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type, value: Exception, traceback: object) -> bool:
        if exc_type is KeyboardInterrupt:
            logger.info(f"Caught KeyboardInterrupt, exiting...")
            return True
        return False

if __name__ == "__main__":
    # prevent system from sleeping
    prevent_sleep()

    #logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.INFO
        , format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting main loop")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Caught KeyboardInterrupt, exiting...")
    except Exception as e:
        logger.exception(f"Caught exception {e}", exc_info=True, stack_info=True)
    finally:
        if agent:
            agent.session_end.append(datetime.datetime.now(local_tz))
            agent.checkpoint('final')
        logger.info("Cleaning up...")
        if ib is not None:
            logger.info(f"{ib}")
            ib.disconnect()
            logger.info("IB disconnected")
        if h5store is not None:
            logger.info(f"{h5store}")
            h5store.close()
            logger.info("HDF5 store closed")
        if fpkl is not None:
            fpkl.close()
        if logger is not None:
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger.removeHandler(handler)
                    logger.info(f"{handler} closed")
        
        logger.info("End of main loop")
        restore_sleep()

# if __name__ == "__main__":
#     main()
#     # with ControlCTrap():
#     #     main()

"""
open issues:
- stop loss is susceptible to gap down
- start getting bars before market open
- sell limit order not filled on the way down, or due to wider bid/ask (META, AMD)
- ib.portfolio and ib.position can they be different?
- trade outside app, especially closing out longs

future work:
- low of the day + two green bars
- trade pnl history
- day cumuloss
- today's price distribution
- drawdown distribution given size of rally from recent low to recent high (rally follow by drawdown)
- distribution of 15 min drawdowns, 30 min drawdowns, 1 hr drawdowns, 1d drawdowns (SPY)
- statistics: filled - order time; time to run strategy;
- heartbeat
- send socket message to this; control-c doesn't work via remote desktop?
"""