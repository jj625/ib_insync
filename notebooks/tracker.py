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
np_pct = {'float_kind': lambda x: f"{x:.2%}"}
import scipy.optimize
np.set_printoptions(linewidth=150, precision=2, suppress=True)
import scipy
from scipy.ndimage import gaussian_filter1d, minimum_filter1d, maximum_filter1d
import math
import logging
import datetime
NYMKTOPEN = datetime.datetime.combine(datetime.datetime.today(), datetime.time(9, 30)).astimezone()
MKTOPEN = NYMKTOPEN
PDMKTOPEN = pd.to_datetime(MKTOPEN)
NPMKTOPEN = np.datetime64(MKTOPEN.replace(tzinfo=None), 's')
# NPMKTOPENIDX = -1
NYMKTCLOSE = datetime.datetime.combine(datetime.datetime.today(), datetime.time(16, 0)).astimezone()
MKTCLOSE = NYMKTCLOSE
PDMKTCLOSE = pd.to_datetime(MKTCLOSE)
NPMKTCLOSE = np.datetime64(MKTCLOSE.replace(tzinfo=None), 's')
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
import zoneinfo
local_tz = zoneinfo.ZoneInfo('US/Eastern')  # Adjust for your local timezone, America/New_York
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

from ib_insync import IB, MarketOrder, LimitOrder, Trade, Fill, CommissionReport, BarData, BarDataList, Stock, util, PortfolioItem
# probe for numpy support
probe = BarDataList()
if not hasattr(probe, '_init_npdata'):
    print("ib_insync.BarDataList does not have numpy extension")
    sys.exit(1)

# import filterpy
# from filterpy.kalman import KalmanFilter as kf

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

def extract_field_as_array(group: Iterable, field_name: str) -> NDArray:
    return np.asarray([getattr(item, field_name) for item in group])

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
        if value.date() == datetime.datetime.now().date():
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
    today = datetime.datetime.now().date() + datetime.timedelta(days=0)
    # before 9:30am, use previous business day
    if datetime.datetime.now().time() < datetime.time(16, 0):
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

class KalmanFilter:
    def __init__(self, A, B, H, Q, R, P, x0):
        self.A = A  # State transition matrix
        self.B = B  # Control input matrix
        self.H = H  # Observation matrix
        self.Q = Q  # Process noise covariance
        self.R = R  # Measurement noise covariance
        self.P = P  # Estimate error covariance
        self.x = x0  # Initial state estimate

    def predict(self, u=0):
        # Predict the next state
        self.x = np.dot(self.A, self.x) + np.dot(self.B, u)
        self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q

    def update(self, z):
        # Update the state with a new measurement
        y = z - np.dot(self.H, self.x)  # Measurement residual
        S = np.dot(self.H, np.dot(self.P, self.H.T)) + self.R  # Residual covariance
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))  # Kalman gain
        self.x = self.x + np.dot(K, y)
        self.P = self.P - np.dot(np.dot(K, self.H), self.P)

# Example usage
    bars15s: BarDataList = field(default_factory=BarDataList)
    bars30s: BarDataList = field(default_factory=BarDataList)
    bars1m: BarDataList = field(default_factory=BarDataList)
    bars2m: BarDataList = field(default_factory=BarDataList)
    bars5m: BarDataList = field(default_factory=BarDataList)
    bars10m: BarDataList = field(default_factory=BarDataList)
    bars15m: BarDataList = field(default_factory=BarDataList)

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
    symbol: str
    tradingaccount: str
    # position: ib_insync.objects.Position = None
    stkpos: ib_insync.objects.Position = None
    rput: float = 0.0 # if we have position, earning rate = return per unit time (rput)
    volatility_per_min: deque = field(default_factory=deque) # volatility every minute
    volatility_pm_running: deque = field(default_factory=deque) # running per minute volatility since open
    ibcontract: ib_insync.contract.Contract = None
    ibcontractDetails: ib_insync.contract.ContractDetails = None
    prevclose: float = 0.0
    begintime: datetime.datetime = datetime.datetime.now()
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
    bars15s: BarDataList = field(default_factory=BarDataList)
    bars30s: BarDataList = field(default_factory=BarDataList)
    bars1m: BarDataList = field(default_factory=BarDataList)
    bars2m: BarDataList = field(default_factory=BarDataList)
    bars5m: BarDataList = field(default_factory=BarDataList)
    bars10m: BarDataList = field(default_factory=BarDataList)
    bars15m: BarDataList = field(default_factory=BarDataList)

    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    lastPrice: float = 0.0 # cache bars[-1].close
    maxloss: float = 0.0
    trade: ib_insync.order.Trade = None # trade that we placed
    tradeMgr: TradeManager = None
    # order: ib_insync.objects.Order = None
    liveTrading: bool = False
    strategy_tasks: set[asyncio.Task] = field(default_factory=set) # keep separate references for strategy tasks

    # state variables and methods for simpleLongStrategy1
    strategy1initstatus: int = -10 # -1 = failed, 0 = success, -10 = not initialized
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
 
    def reset(self):
        pass

    async def initial_resample_hook(self, start: str, end: str, bars: BarDataList):
        logger.info(f"start={start}, end={end}, len(bars)={len(bars)}")
        for b in bars:
            await self.resample_from_5s_core(b, False)
        logger.info(f"len(self.bars)={len(self.bars)} {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
        logger.info(f"len(self.bars)={len(self.bars)}")
        logger.info(f"len(self.bars2m)={len(self.bars2m)}")
        logger.info(f"len(self.bars5m)={len(self.bars5m)}")
        logger.info(f"len(self.bars10m)={len(self.bars10m)}")
        logger.info(f"len(self.bars15m)={len(self.bars15m)}")
        logger.info(f"len(self.bars)={len(self.bars)} {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
        # logger.info(f"len(self.bars10s)={len(self.bars10s)}")

    async def resample_from_5s(self, inBars: BarDataList, inBarHasNewBar: bool):
        """
        Resample 5s bars to 1m, 2m, 5m, 10m, and 15m bars.
        """
        await self.resample_from_5s_core(inBars[-1], inBarHasNewBar)
        hasNewBar1m = inBars[-1].date.second == 0
        await self.onBarUpdate(self.bars, hasNewBar1m) # every 5 secs

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
                outBars._set_last_npdata(newcopy)

        z = inBar
        b = BarData(z.date, z.open, z.high, z.low, z.close, z.volume, z.average, z.barCount, z.timestamp)
        atTopMinute = b.date.second % 60 == 0
        hasNewBar10s = b.date.second % 10 == 0
        hasNewBar15s = b.date.second % 15 == 0
        hasNewBar30s = b.date.second % 30 == 0
        hasNewBar1m = b.date.second == 0
        hasNewBar2m = hasNewBar1m and b.date.minute % 2 == 0
        hasNewBar5m = hasNewBar1m and b.date.minute % 5 == 0
        hasNewBar10m = hasNewBar1m and b.date.minute % 10 == 0
        hasNewBar15m = hasNewBar1m and b.date.minute % 15 == 0

        handle_new_bar(self.bars, b, hasNewBar1m)
        handle_new_bar(self.bars10s, b, hasNewBar10s)
        handle_new_bar(self.bars15s, b, hasNewBar15s)
        handle_new_bar(self.bars30s, b, hasNewBar30s)
        handle_new_bar(self.bars10s, b, hasNewBar10s)
        handle_new_bar(self.bars15s, b, hasNewBar15s)
        handle_new_bar(self.bars30s, b, hasNewBar30s)
        handle_new_bar(self.bars2m, b, hasNewBar2m)
        handle_new_bar(self.bars5m, b, hasNewBar5m)
        handle_new_bar(self.bars10m, b, hasNewBar10m)
        handle_new_bar(self.bars15m, b, hasNewBar15m)

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
        self.session_start = data.get('session_start', []).append(datetime.datetime.now(datetime.timezone.utc).astimezone()) or data['session_start']
        self.session_end = data.get('session_end', []) or data['session_end']
        self.buyopen_bar1m_idx = data.get('buyopen_bar1m_idx', []) or data['buyopen_bar1m_idx']
        self.buyopen_bar1m = data.get('buyopen_bar1m', []) or data['buyopen_bar1m'] # the bar1m where buy was recorded, valid across days
        self.sellclose_bar1m_idx = data.get('sellclose_bar1m_idx', []) or data['sellclose_bar1m_idx']
        self.sellclose_bar1m = data.get('sellclose_bar1m', []) or data['sellclose_bar1m'] # the bar1m where sell was recorded, valid across days
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

    def simpleLongStrategy1InitPreMarket(self) -> int:
        logger.info(f"Pre-market initialization for {self.symbol}")
        # # get historical bars for the last 6 months
        # contract_ = Stock(self.symbol, 'SMART', 'USD')
        # self.histbars = ib.reqHistoricalData( # this method is blocking
        #     contract_,
        #     endDateTime=(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
        #     durationStr='3 M',
        #     barSizeSetting='15 mins',
        #     whatToShow='TRADES',
        #     useRTH=True,
        #     formatDate=1,
        #     timeout=120) # 2 minutes timeout
        # # and may timeout
        # if self.histbars is None or len(self.histbars) == 0:
        #     logger.error(f"Failed to get historical bars for {self.symbol}")
        #     # self.strategy1initstatus = -1
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
        else:
            logger.warning(f"{filename} not found")

        agent.ibcontract = contract_1 = Stock(agent.symbol, 'SMART', 'USD')
        ib.qualifyContracts(contract_1)
        agent.ibcontractDetails = contractDetails = ib.reqContractDetails(contract_1)
        if len(contractDetails) != 1:
            logger.error(f"Contract must be unique, expected 1 contractDetails, got {len(contractDetails)}")
            logger.error(f"{contractDetails}")
            return -1
        cdl = contractDetails[0].liquidSessions()[0]
        logger.info(f"trading hours: {cdl.start} to {cdl.end}")

        # request market data
        ib.reqMarketDataType(1)
        t = ib.reqMktData(contract_1, '', False, False, None)
        if len(ib.tickers()) != 1:
            logger.error(f"{ib.tickers()}: expected 1 ticker")
            return -1
        t = ib.tickers()[0]
        for i in range(10):
            if hasattr(t, 'time') and t.time is not None:
                break
            logger.info(f"waiting for ticker to be fully populated")
            ib.sleep(1)
        else: # no break
            logger.error(f"ticker is not populating")
            return -1
        tdiff = (t.time - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds()
        if abs(tdiff) > 2.0:
            # report clock skew
            logger.warning(f"Tick time is {tdiff:.2f} seconds" + (" ahead" if tdiff > 0 else " behind") + " of current time")
        if np.isnan(t.bid) or np.isnan(t.ask) or np.isnan(t.last) or np.isnan(t.close) or np.isnan(t.open_):
            bidasklast = f"bid {t.bid} ask {t.ask} last {t.last} close {t.close} open {t.open_}"
        else:
            bidasklast = f"bid {t.bid} ask {t.ask} last {t.last} chg {(t.ask+t.bid)/2.0/t.close-1.0:+.2%} open {t.open_} close {t.close} volume {t.volume:n}"
        logger.info(f"{t.contract.localSymbol}: {t.time.astimezone():%H:%M:%S} {bidasklast}")

        if t.close > 0:
            self.prevclose = t.close
        elif dailyclose_df.empty or prevclose_fromfile == 0.0:
            logger.error(f"closing price is not available from ticker or file")
            return -1
        elif t.close != prevclose_fromfile:
            logger.warning(f"ticker.close={t.close} != dailyclose.close={self.prevclose}")
            if datetime.datetime.now(datetime.timezone.utc).weekday() >= 5:  # Saturday or Sunday
                logger.warning(f"Weekend using dailyclose.close as ticker.close is not reliable")
                self.prevclose = prevclose_fromfile
            else: # weekday
                logger.warning(f"Using ticker.close={t.close} as prevclose")
                self.prevclose = t.close
            # not fatal, just a warning
        # self.recenthigh = (-1, self.dailyclose[-1]) # initialize to last bar data from prev day
        # self.recentlow = (-1, self.dailyclose[-1]) # initialize to last bar data from prev day

        # logger.info(f"dailyclose len={len(self.dailyclose)}, dailyclose[0]={self.dailyclose[0]}, dailyclose[-1]={self.dailyclose[-1]}")
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
                    # self.high_since_buy_bar1m.append(self.bars[-1])
                    self.high_since_buy_bar1m.append(max(self.bars, key=lambda bar: bar.average))
                    logger.info(f"high_since_buy_bar1m initialized to: {self.high_since_buy_bar1m}")
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
        #     endDateTime=(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
        #     durationStr='6 M',
        #     barSizeSetting='15 mins',
        #     whatToShow='TRADES',
        #     useRTH=True,
        #     formatDate=1)
        # # and may timeout
        # if self.histbars is None or len(self.histbars) == 0:
        #     logger.error(f"Failed to get historical bars for {self.symbol}")
        #     self.strategy1initstatus = -1
        #     return -1
        # self.prevclose = self.histbars[-1].close
        # # self.recenthigh = (-1, self.histbars[-1]) # initialize to last bar data from prev day
        # # self.recentlow = (-1, self.histbars[-1]) # initialize to last bar data from prev day

        # logger.info(f"SimpleLongStrategy1Init: histbars len={len(self.histbars)}")
        self.strategy1initstatus = 0
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
            'session_end': self.session_end, # .append(datetime.datetime.now(datetime.timezone.utc).astimezone()) or self.session_end,
            'buyopen_bar1m_idx': self.buyopen_bar1m_idx, # current day only, not valid the next day
            'buyopen_bar1m': self.buyopen_bar1m, # the bar1m where buy was recorded, valid across days
            'sellclose_bar1m_idx': self.sellclose_bar1m_idx, # current day only, not valid the next day
            'sellclose_bar1m': self.sellclose_bar1m, # the bar1m where sell was recorded, valid across days
            'high_since_buy_bar1m': self.high_since_buy_bar1m, # the bar1m where the high since buy was recorded, valid across days
        }
        fpkl.seek(0)
        pickle.dump(pkldump, fpkl)
        fpkl.flush()

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
        logger.info(f"hasNewBar={hasNewBar}, {_repr_barlist(reversed(bars[-3:]))}")
        # util.barplot(bars)
        currentBar = bars[-1] # bar that is being built, never full
        currentFullBar = bars[-2] # the most recent fully formed bar
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
            if self.use5s:
                logger.info(f"bars: {self.bars._npidx} {self.bars._npidx_rth_start} {self.bars._npidx_rth_end}")
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

        if currentBar.date >= MKTOPEN:
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
            b = self.high_since_buy_bar1m[-1]
            if self.high_since_buy_bar1m[-1].average <= currentBar.average:
                # prev = self.high_since_buy_bar1m[-1].copy()
                prev = BarData(b.date, b.open_, b.high, b.low, b.close, b.volume, b.average)
                self.high_since_buy_bar1m[-1] = currentBar
                needCheckpoint = True
                logger.info(f"high_since_buy_bar1m from {prev} to {currentBar}")
            if self.high_since_buy_bar1m[-1].average <= currentFullBar.average:
                # prev = self.high_since_buy_bar1m[-1].copy()
                prev = BarData(b.date, b.open_, b.high, b.low, b.close, b.volume, b.average)
                self.high_since_buy_bar1m[-1] = currentFullBar
                needCheckpoint = True
                logger.info(f"high_since_buy_bar1m from {prev} to {currentFullBar}")
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
            # check if strategy initialization is complete
            if self.strategy1initstatus == -10:
                logger.info(f"waiting for strategy initialization to complete")
                return
            elif self.strategy1initstatus == -1:
                logger.error(f"Failed to initialize strategy, exiting...")
                self.set_state(99) # bail out of main loop               
                return
            elif datetime.datetime.now(datetime.timezone.utc) > MKTCLOSE + datetime.timedelta(seconds=15):
                logger.info(f"Market closed, exiting...")
                self.set_state(99) # bail out of main loop
            assert self.strategy1initstatus == 0, "Strategy initialization should return success"
            logger.info(f"scheduling strategy execution")
            task = asyncio.create_task(self.simpleLongStrategy1())
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
            return (lastPrice_ / self.stkpos.avgCost) - 1.0 # life-to-date return

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
            if currentBar.date < MKTOPEN:
                logging.warning(f"{currentBar.date} before market open")
                return retval
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
                logger.info(f"tbg={tbg} tbg1y={tbg1y} cnh ({cnhratio_actual2:.3},{cnhratio_actual3:.3})={cnh} bars[-2]={self.bars[-2]} bars[-3]={self.bars[-3]}")
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
            # nplows = bars.nplow[-n:]
            # if not np.isclose(lows, nplows, atol=1e-6).all():
            #     logger.warning(f"lows != nplows: {lows} != {nplows}")
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
            self.gf1 = gf1 = self.direction_s3 == 'positive' and self.direction_s16 == 'positive' and self.direction_s24 == 'positive' # gaussian filter 1
            if self.direction_s3 or self.direction_s16 or self.direction_s24:
                logger.info(f"gf1: direction_s3={self.direction_s3}, direction_s16={self.direction_s16}, direction_s24={self.direction_s24}")
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
            lkbk = -3
            nbr_actual: int = mn_bars_red(self.bars[lkbk-20:], lkbk, lkbk-20, relax=True, consecutive=True)
            nbr4 = nbr_actual >= 4 # looking for strings of 4+ red bars, starting from -3
            pbonl_threshold = 0.2
            pbhml_ = prevBar.high - prevBar.low
            pbonl_realized: float = (prevBar.open_ - prevBar.low) / pbhml_ if pbhml_ != 0.0 else 0.0 # previous bar open near low
            pbonl = pbonl_realized <= pbonl_threshold # previous bar open near low
            pbcnh_threshold = 0.8
            pbcnh_real = (prevBar.close - prevBar.low) / pbhml_ if pbhml_ != 0.0 else 0.0 # previous bar close near high
            pbcnh = pbcnh_real >= pbcnh_threshold # previous bar close near high
            pbg = prevBar.close > prevBar.open_ # previous bar green
            cbah = currentBar.average > prevBar.average # current bar average higher (than previous bar average)
            at30s = datetime.datetime.now(datetime.timezone.utc).second >= 30 # at 30 seconds (or later)
            dl0m = dl1m = dl2m = dl3m = 0.0
            dl0mb = dl1mb = dl2mb = dl3mb = False
            if agent.dayhilopct:
                dl_arr = extract_field_as_array(slice_deque(agent.dayhilopct, -4, -1), 'low')
                dlmb_arr = dl_arr <= 0.05
                # dl0m = agent.dayhilopct[-1][2] # day low pct below 5%, current bar
                # dl1m = agent.dayhilopct[-2][2] # day low pct below 5%, 1 bar ago
                # dl2m = agent.dayhilopct[-3][2] # 2 bars ago
                # dl3m = agent.dayhilopct[-4][2] # 3 bars ago
                # dl0mb = dl0m <= 0.05
                # dl1mb = dl1m <= 0.05
                # dl2mb = dl2m <= 0.05
                # dl3mb = dl3m <= 0.05
            if orig_cond or isFollowThrough or gf1: # must add additional check when isFollowThrough
                if isFollowThrough:
                    # fyi
                    ft1 = nbr4 and pbonl and pbg and cbah and at30s
                    logger.info(f"ft1: nbr4({nbr_actual:n})={nbr4}, pbonl({pbonl_realized:.3})={pbonl}, pbg={pbg}, cbah={cbah}, at30s={at30s}")
                    ft2 = False
                    if agent.dayhilopct:
                        # ft2 = (dl0mb or dl1mb or dl2mb or dl3mb) and pbg and cbah
                        ft2 = dlmb_arr.any() and pbg and cbah
                    # logger.info(f"ft2: dl0m({dl0m:.1%})={dl0mb}, dl1m({dl1m:.1%})={dl1mb}, dl2m({dl2m:.1%})={dl2mb}, dl3m({dl3m:.1%})={dl3mb}, pbcnh({pbcnh_real:.3})={pbcnh}")
                    logger.info(f"ft2: dlmb={dlmb_arr}, pbg={pbg}, cbah={cbah}")
                    if not blw_lsp and not gf1:
                        logger.info(f"blw_lsp: {blw_lsp}, gf1: {gf1}, no action")
                        return
                    elif blw_lsp and gf1: # AND gf1 (19-Dec-2024)
                        # we are below last sold price OR gauss filter indic are all positives, we can buy
                        # but only if ...
                        if (ft1 and gf1) or (ft2 and gf1) or gf1:
                            # using limit order
                            t = ib.tickers()[0]
                            mintick = self.ibcontractDetails[0].minTick  # Assuming the minimum tick size is 0.01, adjust as necessary
                            mktPrice = round(t.marketPrice() / mintick) * mintick
                            self.order = LimitOrder('BUY', agent.numshares, mktPrice, discretionaryAmt=round(0.0002 * self.milestone_multiplier * t.ask, 2))
                            self.order.account = self.tradingaccount
                        else:
                            logger.info(f"blw_lsp: {blw_lsp}, ft1: {ft1}, ft2: {ft2}, gf1: {gf1}, no action")
                            return
                    else:
                        logger.info(f"blw_lsp: {blw_lsp}, gf1: {gf1}, no action")
                        return
                elif not isFollowThrough and gf1: # original condition, AND gf1 (19-Dec-2024)
                    # ok using market order
                    self.order = MarketOrder('BUY', agent.numshares)
                    self.order.account = self.tradingaccount
                else:
                    logger.info(f"orig_cond: {orig_cond}, isFollowThrough: {isFollowThrough}, gf1: {gf1}, no action")
                    return

                # logger.info(f"seekEntry: Two bars green with one close near it's high, seeking entry...")
                # last_5m_hml_ = last_5m_hml(self.bars)
                # logger.info(f"trailing 5m hml {last_5m_hml_} ({np.array2string(last_5m_hml_ / self.lastPrice, formatter=np_pct)})")
                # check if these two are the same

                # self.order = MarketOrder('BUY', agent.numshares) # see elaboration above
                contract_ = Stock(self.symbol, 'SMART', 'USD')
                logger.info(f"Buying shares of {contract_} as {self.order}")
                # before we place the order, make sure no outstanding trades
                if self.trade and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"clearing old trade {self.trade.log}")
                    self.trade = None
                if self.trade is None:
                    if self.liveTrading:
                        self.set_state(1) # because this is market order, we can change state immediately
                        self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                        self.tradeMgr = TradeManager(self.trade)
                        if self.order.action == 'BUY':
                            self.lastBuyTrade = self.trade
                        logger.info(f"Trade placed: {self.trade}")
                        self.buyopen_bar1m_idx.append(len(agent.bars) - 1) # remember the bar index when we placed the trade
                        self.buyopen_bar1m.append(agent.bars[-1]) # remember the bar when we placed the trade
                        self.high_since_buy_bar1m.append(agent.bars[-1]) # initialize high since buy
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
        tdiff = (t.time - datetime.datetime.now(tz=datetime.timezone.utc)).total_seconds()
        if abs(tdiff) > 1.0:
            logger.warning(f"Tick time is {tdiff:.2f} seconds" + (f" ahead" if tdiff > 0 else " behind") + f" current time")
        basprd = t.ask - t.bid
        logger.info(f"{t.contract.localSymbol} bid {t.bid} ask {t.ask} last {t.last} chg {chg:+.2%} b/a spread {basprd:.2f} ({basprd/lastPrice_:.3%}) volume {t.volume:n}")
        # lastPrice_ = get_market_price() # move to the top

        # volatility
        last_5m_hml_ = last_5m_hml(self.bars)
        logger.info(f"last 5m hml {last_5m_hml_} ({np.array2string(last_5m_hml_ / lastPrice_, formatter=np_pct)})")
        logger.info(f"hml {np.asarray(self.hml[-5:])} hml_pct {np.array2string(np.asarray(self.hml_pct[-5:]), formatter=np_pct)}")

       # calculate trapdoor index
        trdrIdx_ = 0
        # find the highest (down) milestone crossed, i.e. dnPctMilestone[trdrIdx_] > lastPrice_ > dnPctMilestone[trdrIdx_+1]
        # chg = (lastPrice_/self.prevclose-1.)
        # logger.info(f"lastPrice_={lastPrice_:.2f}, prevclose={self.prevclose:.2f}, chg={chg:.2%}")
        while trdrIdx_ < len(self.dnPctMilestone) and chg < self.dnPctMilestone[trdrIdx_]:
            trdrIdx_ += 1
            ret = (lastPrice_/self.prevclose-1.)
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
                logger.info(f"portfolio: {p.position:n} {p.contract.symbol}, avgcost {p.averageCost:,.2f}, mktprc {p.marketPrice:.2f} mv {p.marketValue:,.2f}, dailypnl {p.unrealizedPNL+p.realizedPNL:,.2f} ({(p.unrealizedPNL+p.realizedPNL)/self.prevclose/p.position:+.2%}), unrlzd {p.unrealizedPNL:,.2f} rlzd {p.realizedPNL:,.2f}")
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
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                    self.high_since_buy_bar1m = [] # reset high since buy
                    # allow to proceed
                elif self.trade.orderStatus.status == 'Cancelled':
                    logger.error(f"Trade was cancelled: {self.trade}, undoing state change ({self.state} -> {self.prevstate}), resetting trade to None")
                    self.state = self.prevstate # undo state change
                    self.trade = None
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
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logmsg = f"Trade not filled: {self.trade.log}"
                    self.trade = None
                    self.tradeMgr.clear()
                    logger.error(logmsg + f", resetting trade to None")
                    return # proceed or not?
        elif self.get_state() == 99:
            logger.warning(f"Exiting strategy...")
            return
        
        # if we have no position, just return
        if (self.stkpos is None) or (self.stkpos.position == 0):
            logger.warning(f"No position, returning...")
            return
        
        # update milestone index
        newIdx_ = 0
        # lastPrice_ = get_market_price()
        avgCost_ = self.stkpos.avgCost
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
            T = (datetime.datetime.now(datetime.timezone.utc).astimezone() - max_exec_time(self.lastBuyTrade)).total_seconds() / 60.0 / nrpm # in minutes
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

        if self.high_since_buy_bar1m:
            highest_since_buy = self.high_since_buy_bar1m[-1].average # using average is more realistic
        else:
            logger.warning(f"high_since_buy_bar1m is not set")
            highest_since_buy = lastPrice_
        hwm = max(highest_since_buy, lastPrice_)
        logger.info(f"highest_since_buy={highest_since_buy:.2f} vs hwm={hwm:.2f}")
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
        if cond1 or cond2 or gfe2: # (disabled for now)
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
            contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
            logger.warning(f"Selling shares of {contract_} as {self.order}")
            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
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
                            , text=f"Selling shares of {contract_} as {self.order} {self.trade.log}"))
                    background_tasks.add(task) # keep a reference to the task
                    task.add_done_callback(background_tasks.discard)
                else:
                    logger.error(f"No live trading, trade not placed: {self.order}")
            elif self.trade in ib.openTrades():
                logger.info(f"Trade is still open: {ib.openTrades()}")
            else: # self.trade is not in ib.openTrades()
                logmsg = f"Impossible state: trade {self.trade} not in {ib.openTrades()}"
                self.trade = None
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
        maxlossPct_ = maxloss_ / self.stkpos.avgCost / self.stkpos.position
        currentPnl = (lastPrice - self.stkpos.avgCost) * self.stkpos.position
        currentPnlPct = lastPrice / self.stkpos.avgCost - 1.
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
                contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
                logger.warning(f"Selling shares of {contract_} as {self.order} ...")
            if self.stkpos.position < 0 and self.trade is None:
                logger.warning(f"Buying {-self.stkpos.position} shares of {self.symbol}...")
                # ib.placeOrder(self.stkpos.contract, MarketOrder('BUY', -self.stkpos.position))

            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
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
                            , text=f"Selling shares of {contract_} as {self.order} {self.trade.log}"))
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
                    self.tradeMgr.clear()
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logger.error(f"Trade was not filled: {self.trade}")
                    self.set_state(99) # bail out of main loop
                    # assert False, "Please close out manually."
            else:
                logmsg = f"Impossible state: trade {self.trade} not in {ib.openTrades()}"
                self.trade = None
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

def onPositionUpdate(newpos: ib_insync.objects.Position):
    # only care about specific stock positions for now
    # logger.debug(get_asyncio_running_loop(''))
    if agent is None:
        logger.error(f"agent not initialized")
        return
    if not ((newpos.contract.symbol == agent.symbol) and (newpos.contract.secType == 'STK')):
        if newpos.contract.secType == 'STK':
            logger.debug(f"skipping {newpos.contract.symbol}")
        else:
            logger.warning(f"unexpected secType: {newpos}")
        return
    logmsg = f"{newpos} id={id(newpos)}"
    if agent:
        logmsg += f" agent.state={agent.state} agent.idxMilestone={agent.idxMilestone}"
        if agent.trade:
            logmsg += f" trade={agent.trade.log}"
            if agent.trade.orderStatus.status == 'Filled' and agent.state == 0:
                logmsg += f" state is zero and last trade is filled, resetting trade status"
                agent.trade = None
            if agent.idxMilestone >= 0:
                agent.reset_milestone() # reset milestone
                logmsg += f" resetting strategy1 milestone to -1"
                
    logger.info(logmsg)
    # traceback.print_stack()
    # only care about specific stock positions for now
    if (newpos.contract.symbol == agent.symbol) and (newpos.contract.secType == 'STK'):
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
        logger.info(f"updating agent's with stock position: {agent.stkpos} (id={id(newpos)}), prev={prevstkpos} (id={id(prevstkpos)})")
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
    elif (newpos.contract.symbol != agent.symbol) and (newpos.contract.secType == 'STK'):
        logger.warning(f"ignoring stock position: {newpos}")
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
        if trade.orderStatus.filled == 0:
            logmsg = f"Order was {trade.orderStatus.status}, nothing done, agent state={agent.state}, resetting agent's trade to None"
            if agent.state == 1:
                agent.state = agent.prevstate # undo state change
                logmsg += f", undoing state change"
            agent.trade = None
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

def resample_bars(bars, resample_interval='2min'):
    """
    Resample a list of BarData objects into a specified interval.

    Parameters:
    bars (list of BarData): The list of BarData objects to resample.
    resample_interval (str): The resampling interval (e.g., '2min' for 2 minutes).

    Returns:
    pd.DataFrame: The resampled OHLC data.
    """
    # Convert the list of BarData objects to a DataFrame
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
    if args.account == 'default':
        account_txt = ''
    else:
        account_txt = f"_{args.account}"

    logfilesuffix = f'{datetime.datetime.now(datetime.timezone.utc):%y%m%d_%H%M}_{computername}{account_txt}_{program_name}'
    datafilesuffixdt = f'{args.symbol}_{datetime.datetime.now(datetime.timezone.utc):%y%m%d}_{computername}{account_txt}'
    logfilename = os.path.join(scriptdir, 'logs', f'{args.symbol}_{logfilesuffix}.log')
    file_handler = logging.FileHandler(logfilename)
    file_handler.setLevel(args.loglevel)
    file_handler.setFormatter(formatter)

    # # add handlers to logger
    global logger
    logger = logging.getLogger()

    logger.info(f"logging to {logfilename}")
    # # in the meantime, remind user to set power setting to 'full'
    # pwr = GetPowerSetting()
    # if pwr != '{8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c}':
    #     logger.error(f"Expect full power setting, got {pwr}")
    #     sys.exit(1)

    # # logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logging.getLogger('ib_insync').setLevel(logging.WARN)

    # logger.addFilter(NoParsingFilter())

    logger.info(f"module loaded: {inspect.getfile(eventkit)}")
    logger.info(f"module loaded: {inspect.getfile(ib_insync)}")
    logger.info(f"module loaded: {inspect.getfile(telegram)}")

    logger.info(f"TWS API version: {ibapi.__version__}, ib_insync: {ib_insync.__version__}, telegram: {telegram.__version__}")

    logger.info("Script is starting...")

    logger.info(f"args: {args}")

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
    
    if args.account != 'default' and args.account in spec and args.symbol in spec[args.account]:
        spec_a = spec[args.account][args.symbol]
    else:
        spec_a = {}
    spec_p = spec['root'][args.symbol]
    spec_d = spec['root']['default']
    clientid = args.clientid if args.clientid else spec_p['clientid']
    if args.clientid:
        clientid = args.clientid
    elif 'clientid' in spec_a:
        clientid = spec_a['clientid']
    elif 'clientid' in spec_p:
        clientid = spec_p['clientid']
    elif 'clientid' in spec_d:
        clientid = spec_d['clientid']
    else:
        logger.error(f"TWS Client ID not found in spec file nor in command line")
        sys.exit(1)
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
    if ib.client._serverVersion < 178:
        logger.error(f'TWS version {ib.client._serverVersion} is too old. Update to latest version.')
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
    sp_ = [p for p in ib.positions(account) if p.contract.symbol in [args.symbol] and p.contract.secType == 'STK']
    # assert len(sp_) == 1
    # if len(sp_) == 0:
    #     logger.warning(f"Stock position not found for {args.symbol}")

    global agent
    agent = Agent(symbol=args.symbol, liveTrading=args.live_trading
                  , tradingaccount=account
                  , maxloss=args.maxloss if args.maxloss else maxloss_a if maxloss_a != 0.0 else spec_p['maxloss']
                  , numshares=args.numshares if args.numshares else numshares_a if numshares_a !=0 else spec_p['numshares']
                  , upPctMilestone=np.asarray(spec['root'][speckey]['upPctMilestone']) * spec_p['milestone_multiplier']
                  , dnPctMilestone=np.asarray(spec_p.get('dnPctMilestone', spec_d['dnPctMilestone'])) * spec_p['milestone_multiplier']
                  , stopLossPct=np.asarray(spec['root'][speckey]['stopLossPct']) * spec_p['milestone_multiplier']
                  , mile0_max_retracement_pct=spec_p.get('mile0_max_retracement_pct', spec_d['mile0_max_retracement_pct']) # * spec_p['milestone_multiplier']
                  , mile0_max_retracement_absolute_min_pct=spec_p.get('mile0_max_retracement_absolute_min_pct', spec_d['mile0_max_retracement_absolute_min_pct']) * spec_p['milestone_multiplier']
                  , use5s=True if args.use5s else False
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
            'session_start': [datetime.datetime.now(datetime.timezone.utc).astimezone()],
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
            data['session_start'].append(datetime.datetime.now(datetime.timezone.utc).astimezone())
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

    # contract_1 = Stock('NVDA', 'SMART', 'USD')
    # bars_1 = ib.reqHistoricalData(
    #     contract_1,
    #     endDateTime='',
    #     durationStr='1 D', # 900 S
    #     barSizeSetting='5 secs',
    #     whatToShow='TRADES',
    #     useRTH=True,
    #     formatDate=1,
    #     keepUpToDate=True)
    # # bars_1.updateEvent += onBarUpdate

    dtnow = datetime.datetime.now(datetime.timezone.utc)
    if args.run_until:
        untilTime = datetime.datetime.combine(dtnow, datetime.datetime.strptime(args.run_until, '%H:%M').time()).astimezone()
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
    status = agent.simpleLongStrategy1InitPreMarket() # could take 60 seconds to timeout/complete
    if status < 0:
        logger.error(f"Pre-Initialization failed: {status}")
        sys.exit(1)
    else:
        logger.info(f"Pre-Initialization successful")
    cdl: ib_insync.contract.ContractDetails = agent.ibcontractDetails[0].liquidSessions()[0]

    if dtnow.weekday() >= 5:  # Saturday or Sunday
        pass
    elif not args.run_until:
        # wait until market open
        # waitUntil = dateutil.parser.parse('09:30:00') - datetime.timedelta(seconds=70) # leave some buffer if initializations take time
        waitUntil = cdl.start - datetime.timedelta(seconds=70) # leave some buffer if initializations take time
        if datetime.datetime.now(datetime.timezone.utc) < waitUntil:
            logger.info(f"Waiting until {waitUntil}")
            util.waitUntil(waitUntil)

        waitUntil2 = dateutil.parser.parse('17:00:00').replace(tzinfo=local_tz) - datetime.timedelta(minutes=1)
        #if dtnow < waitUntil2 and dateutil.parser.parse('16:16:00') < dtnow:
        if dateutil.parser.parse('16:58:00').replace(tzinfo=local_tz) < datetime.datetime.now(datetime.timezone.utc) < waitUntil2:
            logger.info(f"Waiting until {waitUntil2}")
            util.waitUntil(waitUntil2)

    if not args.run_until:   
        untilTime = cdl.end + datetime.timedelta(minutes=1) # end of market day
    logger.info(f"Running until {untilTime:%H:%M:%S}")
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
            # agent.ibcontract = contract_1 = Stock(agent.symbol, 'SMART', 'USD')
            contract_1 = agent.ibcontract
            ib.qualifyContracts(contract_1)
            if agent.use5s:
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
                    bars._init_npdata('', '')

                # must init before initial_resample_hook
                initialize_bars(agent.bars10s, '10 secs')
                initialize_bars(agent.bars15s, '15 secs')
                initialize_bars(agent.bars30s, '30 secs')
                initialize_bars(agent.bars, '1 min')
                initialize_bars(agent.bars2m, '2 mins')
                initialize_bars(agent.bars5m, '5 mins')
                initialize_bars(agent.bars10m, '10 mins')
                initialize_bars(agent.bars15m, '15 mins')
                agent.bars5s = ib.reqHistoricalDataExt(
                    contract_1,
                    endDateTime='',
                    durationStr='1 D',
                    barSizeSetting='5 secs',
                    whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                    useRTH=False, # start from ~4:00 AM
                    formatDate=1,
                    keepUpToDate=True,
                    _historicalDataEndHook=agent.initial_resample_hook,
                    # tradingHours=cdl
                    )
                # agent.bars = BarDataList()

                procname = 'ib.reqHistoricalDataExt'
            else:
                agent.bars = ib.reqHistoricalData(
                    contract_1,
                    endDateTime='',
                    durationStr='1 D',
                    barSizeSetting='1 min', # '5 secs', # always ticks every 5 secs
                    whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                    useRTH=False, # start from ~4:00 AM
                    formatDate=1,
                    keepUpToDate=True
                    )
                procname = 'ib.reqHistoricalData'
            # agent.bars5m.initialize(agent.bars)
            if len(agent.bars) > 0:
                dtnow = datetime.datetime.now(datetime.timezone.utc)
                if dtnow.weekday() >= 5:  # Saturday or Sunday
                    logging.warning(f"{dtnow.strftime('%A')} is not trading today")
                else:
                    assert agent.bars[0].date.date() == dtnow.date(), f"Expect first bar {agent.bars[0]} to be today"
            else:
                assert False, "Expect at least one bar"
            agent.barsstartidx = len(agent.bars) - 1
            agent.beginprice = agent.bars[agent.barsstartidx].close
            logger.info(f"{procname}: len(bars)={len(agent.bars)}, bar[0]={agent.bars[0]}, bar[-1]={agent.bars[-1]}")
            # agent.bars.updateEvent += lambda x, y: agent.onBarUpdate(x, y) # are these two equivalent?
            if agent.use5s:
                logger.info(f'{agent.bars.buffer_size} {agent.bars._npidx} {len(agent.bars.open_prices)}')
                agent.bars5s.updateEvent += agent.resample_from_5s
            else:
                agent.bars.updateEvent += agent.onBarUpdate
            # agent.bars.updateEvent += agent.bars5m.__call__ # 1m to 5m resampling
            # agent.bars5m.updateEvent += agent.on5mBarUpdate
            # agent.bars5m.updateEvent += agent.bars10m.__call__ # 1m to 10m resampling
            # agent.bars10m.updateEvent += agent.on10mBarUpdate
            # # agent.bars.updateEvent += agent.bars15m.__call__ # 1m to 15m resampling

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

            status = agent.simpleLongStrategy1Init()

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

        # # if no position, we just quit
        # if agent.stkpos.position == 0:
        #     logger.warning(f"No position, quitting...")
        #     break

        # enforce max loss
        if agent.stkpos and agent.stkpos.position > 0:
            # agent.enforceMaxLoss(agent.bars[-1].close)
            agent.enforceMaxLoss(get_bid_price())

        # # try simple strategy
        # if (agent.stkpos.position > 0) and agent.trade is None:
        #     agent.simpleLongStrategy1()

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
    elif agent.use5s and agent.bars5s and hasattr(agent.bar5s, 'reqId'):
        ib.cancelHistoricalData(agent.bars5s)
        logger.info(f"cancelHistoricalData: len(bars5s)={len(agent.bars5s)}") # , first={agent.bars5s[0] if agent.bars5s else 'N/A'}, last={agent.bars5s[-1] if agent.bars5s else 'N/A'}
        logger.info(f"bars5s: {len(agent.bars5s)} {agent.bars5s._npidx} {agent.bars5s._npidx_rth_start} {agent.bars5s._npidx_rth_end}")
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
            agent.session_end.append(datetime.datetime.now(datetime.timezone.utc).astimezone())
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