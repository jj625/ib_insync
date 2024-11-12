import sys
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
import scipy.optimize
np.set_printoptions(precision=2, suppress=True)
import scipy
import logging
import datetime
import dateutil
import argparse
import json
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

from concurrent.futures import ThreadPoolExecutor
import pytz
local_tz = pytz.timezone('US/Eastern')  # Adjust for your local timezone, America/New_York

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
mpl_dir = pathlib.Path('../eventkit').resolve()
if mpl_dir.exists() and mpl_dir.is_dir() and str(mpl_dir) not in sys.path:
    sys.path.insert(0, str(mpl_dir))
    mpl_dir
elif not mpl_dir.exists():
    print(f"Expected {mpl_dir} does not exist")

import eventkit
import ib_insync
import ib_insync.ib
from ib_insync import IB, MarketOrder, LimitOrder, BarData, Stock, util

ib_insync.ib.install_custom_repr_()

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

async def send_telegram_message_async(text):
    # bot = Bot(token='YOUR_BOT_TOKEN')
    return await telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)

def send_telegram_message(text):
    util.run(send_telegram_message_async(text))
    # task = asyncio.create_task(send_telegram_message_async(text))
    # telegram_tasks.add(task)
    # task.add_done_callback(telegram_tasks.discard)

# def run_async_task(chat_id, text):
#     loop = asyncio.get_event_loop()
#     asyncio.run_coroutine_threadsafe(send_telegram_message(chat_id, text), loop)

# # Example usage
# if __name__ == "__main__":
#     chat_id = 'YOUR_CHAT_ID'
#     text = 'Hello, this is an asynchronous message!'
#     executor = ThreadPoolExecutor()
#     executor.submit(run_async_task, chat_id, text)

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
    # position: ib_insync.objects.Position = None
    stkpos: ib_insync.objects.Position = None
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
    bars: List[BarData] = field(default_factory=list)
    highs: List[float] = field(default_factory=list)
    lows: List[float] = field(default_factory=list)
    lastPrice: float = 0.0 # cache bars[-1].close
    maxloss: float = 0.0
    trade: ib_insync.order.Trade = None # trade that we placed
    # order: ib_insync.objects.Order = None
    liveTrading: bool = False
    strategy_tasks: set[asyncio.Task] = field(default_factory=set) # keep separate references for strategy tasks

    # state variables and methods for simpleLongStrategy1
    strategy1initstatus: int = -10 # -1 = failed, 0 = success, -10 = not initialized
    numshares: int = 0
    upPctMilestone: List[float] = field(default_factory=list)
    # upPriceMilestone: List[float] = field(default_factory=list)
    stopLossPct: List[float] = field(default_factory=list)
    # stopLossPrice: List[float] = field(default_factory=list)
    idxMilestone: int = -1 # initialize to an impossible value
    # avgCost: float = 0.0
    state: int = 0 # state machine: 0 = seek entry, 1 = maintain position, keep ratchet up until stop loss
    prevstate: int = 0 # previous state
    recenthigh: tuple[int, BarData] = None
    recentlow: tuple[int, BarData] = None
    # execdetailTrade: list[ib_insync.order.Trade] = field(default_factory=list)
    # execdetailFill: list[ib_insync.objects.Fill] = field(default_factory=list)
    buyopen_bar1m_idx: list[int] = field(default_factory=list)
    sellclose_bar1m_idx: list[int] = field(default_factory=list)
    mile0_max_retracement_pct: float = 0.0
    mile0_max_retracement_absolute_min_pct: float = 0.0
    lastSalePrice: float = 0.0
    buyagainbuffer: float = 0.0 # buffer to buy again after selling
    lastSellTrade: Optional[ib_insync.order.Trade] = None
    lastSaleTime: Optional[datetime.datetime] = None
 
    def reset(self):
        pass

    def resume_session(self, data: dict):
        if not data:
            logger.warning(f"previous session data is empty")
            return
        _ = data.pop('trade_list', None) # no need for this anymore
        logger.info(f"Resuming session {data}")
        self.buyopen_bar1m_idx = data['buyopen_bar1m_idx']
        self.sellclose_bar1m_idx = data['sellclose_bar1m_idx']

        # get all trades so far
        t = sorted([t for t in ib.trades() if t.contract.symbol == self.symbol], key=lambda trade: max(fill.execution.time for fill in trade.fills))
        if t:
            if t[-1].order.action == 'SELL':
                lt = t[-1]
            elif t[-1].order.action == 'BUY' and (len(t) > 1 and t[-2].order.action == 'SELL'):
                lt = t[-2]
            else:
                lt = None
                logger.warning(f"no sell trade found")
                return
            self.lastSellTrade = lt
            self.lastSaleTime = max(fill.execution.time for fill in lt.fills)
            self.lastSalePrice = sum(fill.execution.price * fill.execution.shares for fill in lt.fills) / sum(fill.execution.shares for fill in lt.fills)
            logger.info(f"last sell trade: {lt}, last sale time: {self.lastSaleTime}, last sale price: {self.lastSalePrice}")

    def simpleLongStrategy1InitPreMarket(self) -> int:
        logger.info(f"Pre-market initialization for {self.symbol}")
        # # get historical bars for the last 6 months
        # contract_ = Stock(self.symbol, 'SMART', 'USD')
        # self.histbars = ib.reqHistoricalData( # this method is blocking
        #     contract_,
        #     endDateTime=(datetime.datetime.now() + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
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

        histbars = pd.read_csv(f'./data/{self.symbol}_1d.csv', parse_dates=['date'])
        yestdate = pd.to_datetime(datetime.datetime.now().date() + datetime.timedelta(days=-1))
        if yestdate not in histbars['date'].values:
            logger.error(f"Yesterday's date not found in historical bars")
            return -1
        # at the moment, this is all we care about
        self.prevclose = histbars[ histbars['date'] == yestdate ].close
        # self.recenthigh = (-1, self.histbars[-1]) # initialize to last bar data from prev day
        # self.recentlow = (-1, self.histbars[-1]) # initialize to last bar data from prev day

        # logger.info(f"histbars len={len(self.histbars)}, histbars[0]={self.histbars[0]}, histbars[-1]={self.histbars[-1]}")
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
        logger.info(f"SimpleLongStrategy1Init: upPctMilestone={self.upPctMilestone}, stopLossPct={self.stopLossPct}")
        
        # stockpos = [p for p in ib.positions() if p.contract.symbol in [self.symbol] and p.contract.secType == 'STK']
        # assert len(stockpos) == 1, 'Stock position not found'
        # self.avgCost = stockpos[0].avgCost
        # self.position = stockpos[0].position

        # # get historical bars for the last 6 months
        # contract_ = Stock(self.symbol, 'SMART', 'USD')
        # self.histbars = ib.reqHistoricalData( # this method is blocking
        #     contract_,
        #     endDateTime=(datetime.datetime.now() + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
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
        return f"Symbol: {self.symbol}, stock position: {self.stkpos}"
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
        logger.info(f"{typ}, {self.symbol}, {self.buyopen_bar1m_idx}, {self.sellclose_bar1m_idx}")
        pkldump = {
            'symbol': self.symbol,
            'buyopen_bar1m_idx': self.buyopen_bar1m_idx,
            'sellclose_bar1m_idx': self.sellclose_bar1m_idx
        }
        fpkl.seek(0)
        pickle.dump(pkldump, fpkl)
        fpkl.flush()

    async def onBarUpdate(self, bars: List[BarData], hasNewBar: bool):
        logger.debug(get_asyncio_running_loop('')) # expect '<ProactorEventLoop running=True closed=False debug=False>
        # reqHistoricalData with keepUpToDate=True always ticks every 5s
        self.lastPrice = bars[-1].close
        logger.info(f"hasNewBar={hasNewBar}, {bars[-1]}")
        if (self.highsincestart == 0.0) or (self.highsincestart < bars[-1].high):
            self.highsincestart = bars[-1].high
        if (self.lowsincestart == 0.0) or (self.lowsincestart > bars[-1].low):
            self.lowsincestart = bars[-1].low
        self.testpnl = bars[-1].close - self.beginprice
        logger.info(f"since start: hi/lo {self.highsincestart} {self.lowsincestart} ({self.highsincestart/self.lowsincestart:.2%})")

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
            assert self.strategy1initstatus == 0, "Strategy initialization should return success"
            logger.info(f"scheduling strategy execution")
            task = asyncio.create_task(self.simpleLongStrategy1())
            self.strategy_tasks.add(task)
            task.add_done_callback(self.strategy_tasks.discard)
            await task
            task = None
        
        return

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
            return (lastPrice_ - self.stkpos.avgCost) / self.stkpos.avgCost

        def two_bars_green_with_one_close_near_high():
            """Check if the last two bars are green and at least one of them close near the high"""
            if len(self.bars) < 2:
                return False
            if (self.bars[-1].close > self.bars[-1].open) and (self.bars[-2].close > self.bars[-2].open):
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
            # check if the last two bars are green
            tbg = self.bars[-2].close > self.bars[-2].open and self.bars[-3].close > self.bars[-3].open
            # if one of them is yellow it's ok too
            # case in point: AMD 10/29/2024 9:35 and 9:36 bars
            tbg1y = (self.bars[-2].close > self.bars[-2].open and self.bars[-3].close == self.bars[-3].open or
                self.bars[-2].close == self.bars[-2].open and self.bars[-3].close > self.bars[-3].open)
            if tbg or tbg1y:
                if tbg1y:
                    logger.warning(f"tbg1y={tbg1y}")
                # check if at least one of them close near the high
                cnh = (self.bars[-2].close >= self.bars[-2].low + 0.8 * (self.bars[-2].high - self.bars[-2].low) or
                    self.bars[-3].close >= self.bars[-3].low + 0.8 * (self.bars[-3].high - self.bars[-3].low))
                if cnh:
                    retval = True # (tbg or tbg1y) and cnh
            
            logger.warning(f"tbg={tbg} tbg1y={tbg1y} cnh={cnh} bars[-2]={self.bars[-2]} bars[-3]={self.bars[-3]}")
            return retval

        def low_to_high_inflection_point(n=15, m=5) -> bool:
            """check if there is a low to high inflection point in the last n bars.
            This is a sign of reversal. We want to catch the reversal early.
            Define inflection point as any of the last m bars lows is lower than any of the previous n-m bars lows
            """
            if len(self.bars) < n:
                # the first n bars ...
                # case in point: AMD 10/29/2024 9:35 and 9:36 bars
                if len(self.bars) > 3:
                    lows = [b.low for b in self.bars] # low so far
                    lastn_lows = lows[-3:] # last 3 lows
                    if min(lastn_lows) == min(lows):
                        logger.info(f"low_to_high_inflection_point: last 3 lows are the same: {lows} {lastn_lows}")
                        # return True
                return False
            lows = [b.low for b in self.bars[-n:]]
            if min(lows[-m:]) < min(lows[:-m]):
                logger.info(f"low_to_high_inflection_point: {lows[-m:]} < {lows[:-m]}")
                return True
            return False # no inflection point
        
        def five_bars_green():
            """Check if the last five bars are green"""
            if len(self.bars) < 5:
                return False
            return all([bar.close > bar.open for bar in self.bars[-5:]])
        
        def lastn_bars_green(n=10, relax: bool=False) -> int:
            """
            examine the last n bars, count the longest string of successive green bars from the last
            relax: if True, allow for a yellow bar in between green bars
            """
            if len(self.bars) < n:
                return 0
            count = 0
            for bar in self.bars[-n:]:
                if bar.close > bar.open:
                    count += 1
                elif relax and bar.close == bar.open:
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
                if bar.close < bar.open:
                    count += 1
                elif relax and bar.close == bar.open:
                    count += 1
                else:
                    break
            return count

        def seekEntry(isFollowThrough: bool = False):
            """
            pre-condition: no position, no outstanding trades, milestone has been reset
            """
            assert self.trade is None, "Expect no outstanding trades"
            isInflection_15_5 = low_to_high_inflection_point(15, 5)
            isInflection_10_5 = low_to_high_inflection_point(10, 5)
            isInflection_5_3 = low_to_high_inflection_point(5, 3)
            cond1 = two_bars_green_with_one_close_near_high_2() and isInflection_10_5 # original condition 
            cond2 = isFollowThrough and lastn_bars_green(3) >= 2 # don't need to check for inflection point
            logger.info(f"cond1={cond1}, cond2={cond2}, isInflection_15_5={isInflection_15_5}, isInflection_10_5={isInflection_10_5}, isInflection_5_3={isInflection_5_3}")
            if cond1 or cond2:
                # logger.info(f"seekEntry: Two bars green with one close near it's high, seeking entry...")
                self.order = MarketOrder('BUY', agent.numshares)
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
                        logger.info(f"Trade placed: {self.trade}")
                        self.buyopen_bar1m_idx.append(len(agent.bars) - 1) # record the bar index when we placed the trade
                        self.checkpoint('buyopen')
                        loop = asyncio.get_running_loop()
                        task = loop.create_task(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"Buying shares of {contract_} as {self.order} {self.trade.log}"))
                        background_tasks.add(task) # keep a reference to the task
                        task.add_done_callback(background_tasks.discard)
                        # asyncio.sleep(0.2)
                    else:
                        logger.error(f"No live trading, trade not placed: {self.order}")
                else:
                    assert False, f"Impossible state: trade outstanding: {self.trade}"
                if self.trade and self.trade in ib.openTrades():
                    logger.info(f"Trade is still open: {ib.openTrades()}")
                if self.trade and self.trade not in ib.openTrades() and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"Trade is filled: {self.trade.log}")
                    self.set_state(1)
                    self.trade = None
                # else:
                #     assert False, f"Impossible state: trade {self.trade} not in {ib.openTrades() and }"
            return # end of seekEntry

        logger.debug(get_asyncio_running_loop('')) # expect '<ProactorEventLoop running=True closed=False debug=False>
        logger.info(f"state={self.get_state()}")
        if self.get_state() in [0, 2]:
            # no position, no outstanding trades and milestone has been reset
            if ((self.stkpos is None) or (self.stkpos.position == 0)) and self.idxMilestone == -1 and self.trade is None:
                isFollowThrough = (self.lastSaleTime is not None)
                logger.info(f"No position, seeking {'follow through ' if isFollowThrough else ''}entry ...")
                seekEntry(isFollowThrough=isFollowThrough)
                return
            elif self.trade and self.trade in ib.openTrades():
                logger.info(f"Trade is still open: {ib.openTrades()}") # wait for trade to complete
                return
            elif self.trade and not (self.trade in ib.openTrades()):
                if self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade status: {self.trade}"
                    self.trade = None
                    logger.info(logmsg + f", resetting trade to None")
                    # allow to proceed
                elif self.trade.orderStatus.status == 'Cancelled':
                    logger.error(f"Trade was cancelled: {self.trade}, undoing state change")
                    self.state = self.prevstate # undo state change
                    return
            else:
                logger.error(f"Impossible state: state=0 but position={self.stkpos} and idxMilestone={self.idxMilestone}")
                return # don't allow to proceed
            
        elif self.get_state() == 1:
            # we have a position
            if self.stkpos is None and self.trade and self.trade in ib.openTrades():
                logger.info(f"Waiting for position update to complete...")
                return
            elif self.stkpos is None:
                logger.error(f"Impossible state: state=1 waiting for position update to complete but no outstanding trade")
                return
            if self.stkpos.position == 0:
                logger.error(f"Impossible state: state=1 but position={self.stkpos}")
                return
            # ensure no outstanding trades
            if self.trade:
                if self.trade in ib.openTrades():
                    logger.info(f"Trade is still open: {ib.openTrades()}")
                elif self.trade not in ib.openTrades() and self.trade.orderStatus.status == 'Filled':
                    logmsg = f"Trade is filled: {self.trade.log}"
                    logger.info(logmsg)
                    # self.state = 1
                    self.trade = None
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logmsg = f"Trade not filled: {self.trade.log}"
                    self.trade = None
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
        lastPrice_ = self.lastPrice
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
        logger.info(f"{logmsg}={self.idxMilestone} ({self.upPctMilestone[self.idxMilestone]:.2%}) last {lastPrice_:.2f}, return {lastPctReturn():.2%}, stoploss {stoplossPrice_:.2f} ({stoplossPrice_/lastPrice_-1:.2%})")
        
        # calculate drawdown
        # get the highest 1m close since we last buy. get the higher of that and current price. drawdownpct = min(0, (lastprice - highest)/highest)
        # if we are below the highest, we are in drawdown
        if not self.buyopen_bar1m_idx:
            logger.warning(f"buyopen_bar1m_idx is not set")
            j = None
            j_timestamp = None
            highest_since_buy = max([bar.close for bar in self.bars])
        else:
            j = self.buyopen_bar1m_idx[-1]
            highest_since_buy = max([bar.close for bar in self.bars[j:]])
            j_timestamp = self.bars[j].date
            logger.info(f"highest_since_buy bar[{j}]={self.bars[j]}")
        hwm = max(highest_since_buy, lastPrice_)
        drawdown = min(0, lastPrice_ - hwm)
        drawdown_pct = drawdown / hwm
        pnl_hwm = hwm - avgCost_
        pnl_hwm_pct = pnl_hwm / avgCost_
        logger.info(f"drawdown {drawdown:.2f} {drawdown_pct:.2%}, pnl_hwm {pnl_hwm:.2f} {pnl_hwm_pct:.2%}")
        logger.info(f"px_hwm {hwm}, px_highest_since_buy {highest_since_buy}")
        # report if we are in drawdown
        if drawdown_pct < 0:
            logger.warning(f"Drawdown: {drawdown_pct:.2%}")
        
        # this is the original exit condition
        # but this results in negative expected pnl because we are exiting at a loss
        cond1 = lastPrice_ < stoplossPrice_

        # to avoid negative expected pnl, we introduce drawdown condition from pnl high water mark
        # allow some retracement from pnl high water mark
        max_retracement_pct = -1.0 * self.mile0_max_retracement_pct * pnl_hwm_pct
        # sometimes max_retracement_pct is too small (when pnl high water mark is close to zero), so we use the absolute min
        cond2 = drawdown_pct < min(-1.0 * self.mile0_max_retracement_absolute_min_pct, max_retracement_pct) and self.idxMilestone == 0
        if self.idxMilestone == 0:
            logger.info(f"{max_retracement_pct:.3%} {min(-1.0 * self.mile0_max_retracement_absolute_min_pct, max_retracement_pct):.3%}")
        logger.info(f"cond1={cond1}, cond2={cond2}, idxMilestone={self.idxMilestone}")
        
        if cond1 or cond2:
            # crossed below milestone, we should liquidate
            if cond1: 
                logger.warning(f"Crossed below stopLoss {stoplossPrice_:.2f}, last {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
            elif cond2:
                logger.warning(f"Crossed below max retracement {drawdown_pct:.2%}, last {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
            self.order = LimitOrder('SELL', self.stkpos.position, lastPrice_)
            contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
            logger.warning(f"Selling shares of {contract_} as {self.order}")
            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                    self.set_state(0) # reset state
                    logger.info(f"Trade placed: {self.trade}, state reset to 0")
                    self.sellclose_bar1m_idx.append(len(self.bars) - 1)
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
            lastPrice = self.lastPrice
        if maxloss_ is None:
            maxloss_ = self.maxloss
        currentPnl = (lastPrice - self.stkpos.avgCost) * self.stkpos.position
        logging.info(f"last {lastPrice}, pnl: {currentPnl:.2f}, max loss: {maxloss_:.2f}")
        if currentPnl < maxloss_:
            logger.warning(f"Current loss: {currentPnl:.2f}, max loss: {maxloss_:.2f}")
            if self.stkpos.position > 0 and self.trade is None:
                # self.order = MarketOrder('SELL', self.stkpos.position)
                # watch out, with limit order we may not get filled
                self.order = LimitOrder('SELL', self.stkpos.position, lastPrice)
                contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
                logger.warning(f"Selling shares of {contract_} as {self.order} ...")
            if self.stkpos.position < 0 and self.trade is None:
                logger.warning(f"Buying {-self.stkpos.position} shares of {self.symbol}...")
                # ib.placeOrder(self.stkpos.contract, MarketOrder('BUY', -self.stkpos.position))

            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                    self.set_state(0) # reset state
                    logger.info(f"Trade placed: {self.trade}, state reset to 0")
                    self.sellclose_bar1m_idx.append(len(self.bars) - 1) # record the bar index when we placed the trade
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
                    logger.info(logmsg + f", resetting trade to None")
                else:
                    logger.error(f"Trade was not filled: {self.trade}")
                    self.set_state(99) # bail out of main loop
                    # assert False, "Please close out manually."
            else:
                logmsg = f"Impossible state: trade {self.trade} not in {ib.openTrades()}"
                self.trade = None
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

def onPortfolioUpdate(portfolio: ib_insync.objects.PortfolioItem) -> None:
    """
    every three minutes, usually following onAccountValueUpdate
    not doing significant function yet, just doing checkings, confirming that we are in sync with IB
    we do the work in onPositionUpdate
    """

    # logger.debug(get_asyncio_running_loop(''))
    # logger.debug(f"{portfolio}")
    if agent is None:
        logger.error(f"agent not initialized, expected {portfolio}")
        return
    if portfolio.contract.symbol == agent.symbol:
        # ensure we agree with IB on the stock position
        if agent.stkpos is None:
            logger.error(f"agent.stkpos is None, expected {portfolio}")
            return
        if portfolio.position != agent.stkpos.position:
            logger.error(f"portfolio.position={portfolio.position} != agent.stkpos.position={agent.stkpos.position}")
            agent.set_state(99) # bail out of main loop
            return
        if portfolio.averageCost != agent.stkpos.avgCost:
            logger.warning(f"portfolio.averageCost={portfolio.averageCost} != agent.stkpos.avgCost={agent.stkpos.avgCost}")
            # agent.set_state(99) # bail out of main loop
            return
    else:
        logger.debug(f"skipping {portfolio.contract.symbol} {format_value(portfolio.position, True)}")
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
            agent.state = 1
            # print stack trace
        elif not (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position == 0 and agent.state == 1:
            logger.info(f"agent state should change: 1 -> 0")
            agent.state = 0
        elif not (prevstkpos is None) and (prevstkpos.position == newpos.position):
            logger.warning(f"newpos.position == prevpos.position, agent state: {agent.state}")

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
    if agent.trade is None:
        logger.error(f"agent's trade is None, shouldn't happen: {trade}")
        return
    if agent.trade.order.orderId != trade.order.orderId:
        logger.error(f"order id mismatch: agent's {agent.trade.order.orderId} != {trade.order.orderId}")
        return
    if trade.orderStatus.status == 'Cancelled':
        if trade.orderStatus.filled == 0:
            logmsg = f"Order was cancelled, nothing done, agent state={agent.state}, resetting agent's trade to None"
            if agent.state == 1:
                agent.state = agent.prevstate # undo state change
                logmsg += f", undoing state change"
            agent.trade = None
            logger.warning(logmsg)
        else:
            logger.warning(f"Order was cancelled but partially filled: {trade}")
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
        'open': [bar.open for bar in bars],
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
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    filesuffix = f'{args.symbol}_{datetime.datetime.now():%Y%m%d_%H%M}'
    filesuffixdt = f'{args.symbol}_{datetime.datetime.now():%Y%m%d}'
    logfilename = os.path.join(scriptdir, 'logs', f'tracker_{filesuffix}.log')
    file_handler = logging.FileHandler(logfilename)
    file_handler.setLevel(args.loglevel)
    file_handler.setFormatter(formatter)

    # # add handlers to logger
    global logger
    logger = logging.getLogger()

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
    spec_p = spec['root'][args.symbol]
    spec_d = spec['root']['default']
    clientid = args.clientid if args.clientid else spec_p['clientid']

    h5file = os.path.join(scriptdir, 'data', f'tracker_{filesuffixdt}.h5')
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
    global ib
    ib = IB()
    ib.connect(args.host, args.port, clientId=clientid)
    # to test connection
    # https://www.interactivebrokers.com/cgi-bin/conn_test.pl

    # print portfolio
    sp_ = [p for p in ib.portfolio() if p.contract.symbol in [args.symbol]]
    logger.info(f"Portfolio: {sp_}")

    # find stock position of a given symbol in the portfolio
    sp_ = [p for p in ib.positions() if p.contract.symbol in [args.symbol] and p.contract.secType == 'STK']
    # assert len(sp_) == 1
    # if len(sp_) == 0:
    #     logger.warning(f"Stock position not found for {args.symbol}")

    global agent
    agent = Agent(symbol=args.symbol, liveTrading=args.live_trading
                  , maxloss=args.maxloss if args.maxloss else spec_p['maxloss']
                  , numshares=args.numshares if args.numshares else spec_p['numshares']
                  , upPctMilestone=spec['root'][speckey]['upPctMilestone']
                  , stopLossPct=spec['root'][speckey]['stopLossPct']
                  , mile0_max_retracement_pct=spec_p.get('mile0_max_retracement_pct', spec_d['mile0_max_retracement_pct'])
                  , mile0_max_retracement_absolute_min_pct=spec_p.get('mile0_max_retracement_absolute_min_pct', spec_d['mile0_max_retracement_absolute_min_pct'])
    )
    if len(sp_) > 0:
        agent.stkpos = sp_[0]
        agent.state = 1
        logger.info(f"Tracked position: {agent.stkpos}")
    else:
        agent.state = 0
        logger.info(f"No position found for {args.symbol}")

    # resume previous session
    pklfile = os.path.join(scriptdir, 'data', f'tracker_{filesuffixdt}.pkl')
    global fpkl
    data = None
    if not os.path.exists(pklfile) or os.path.getsize(pklfile) == 0:
        fpkl = open(pklfile, 'wb') # write binary
        pklinit = {
            'symbol': 'init',
            'buyopen_bar1m_idx': [],
            'sellclose_bar1m_idx': []
        }
        pickle.dump(pklinit, fpkl) # initialize it
    else:
        fpkl = open(pklfile, 'r+b') # read/write binary
        data = pickle.load(fpkl)
        if data['symbol'] == 'init' and data['buyopen_bar1m_idx'] == [] and data['sellclose_bar1m_idx'] == []:
            logger.info(f"Previous session didn't write anything, resetting")
            data = None # continue as normal, previous session didn't write anything
        elif data['symbol'] != args.symbol:
            logger.error(f"Previous session symbol {data['symbol']} doesn't match {args.symbol}, resetting")
        else:
            logger.info(f"Previous session data: {data}")
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

    if args.run_until:
        untilTime = datetime.datetime.combine(datetime.datetime.now(), datetime.datetime.strptime(args.run_until, '%H:%M').time())
    else:           
        if datetime.datetime.now().weekday() >= 5:  # Saturday or Sunday
            untilTime = datetime.datetime.now() + datetime.timedelta(minutes=1) # run for 10 minutes
        # untilTime = datetime.datetime.now() + datetime.timedelta(hours=2.2)
        elif dateutil.parser.parse('20:00:00') < datetime.datetime.now(): # after 8:00 PM, run until 11:59 PM
            untilTime = dateutil.parser.parse('23:59:00') # 11:59 PM
        elif dateutil.parser.parse('16:16:00') < datetime.datetime.now(): # after 4:16 PM, run until 8:00 PM
            untilTime = dateutil.parser.parse('20:02:00') # 8:00 PM
        elif datetime.datetime.now() < dateutil.parser.parse('16:02:00'): # before 4:02 PM, run until 4:02 PM
            untilTime = datetime.datetime.combine(datetime.datetime.now(), datetime.time(16, 2, 0)) # 4:02 PM
    doOnce = True

    # run initialization before market open
    status = agent.simpleLongStrategy1InitPreMarket() # could take 60 seconds to timeout/complete
    if status < 0:
        logger.error(f"Pre-Initialization failed: {status}")
        sys.exit(1)
    else:
        logger.info(f"Pre-Initialization successful")

    if datetime.datetime.now().weekday() >= 5:  # Saturday or Sunday
        pass
    else:
        # wait until market open
        waitUntil = dateutil.parser.parse('09:30:00') - datetime.timedelta(seconds=70) # leave some buffer if initializations take time
        if datetime.datetime.now() < waitUntil:
            logger.info(f"Waiting until {waitUntil}")
            util.waitUntil(waitUntil)

        waitUntil2 = dateutil.parser.parse('17:00:00') - datetime.timedelta(minutes=1)
        #if datetime.datetime.now() < waitUntil2 and dateutil.parser.parse('16:16:00') < datetime.datetime.now():
        if dateutil.parser.parse('16:16:00') < datetime.datetime.now() < waitUntil2:
            logger.info(f"Waiting until {waitUntil2}")
            util.waitUntil(waitUntil2)

    logger.info(f"Running until {untilTime:%H:%M:%S}")
    while datetime.datetime.now() < untilTime and agent.get_state() != 99:
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

            # request live market data
            contract_1 = Stock(agent.symbol, 'SMART', 'USD')
            agent.bars = ib.reqHistoricalData(
                contract_1,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='1 min', # '5 secs', # always ticks every 5 secs
                whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                useRTH=False, # start from ~4:00 AM
                formatDate=1,
                keepUpToDate=True)

            if len(agent.bars) > 0:
                if datetime.datetime.now().weekday() >= 5:  # Saturday or Sunday
                    logging.warning(f"{datetime.datetime.now().weekday()} is not trading today")
                else:
                    assert agent.bars[0].date.date() == datetime.datetime.now().date(), f"Expect first bar {agent.bars[0]} to be today"
            else:
                assert False, "Expect at least one bar"
            agent.barsstartidx = len(agent.bars) - 1
            agent.beginprice = agent.bars[agent.barsstartidx].close
            logger.info(f"ib.reqHistoricalData: {contract_1}, len(bars)={len(agent.bars)}, bar[0]={agent.bars[0]}, bar[-1]={agent.bars[-1]}")
            # agent.bars.updateEvent += lambda x, y: agent.onBarUpdate(x, y) # are these two equivalent?
            agent.bars.updateEvent += agent.onBarUpdate

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
            agent.enforceMaxLoss(agent.bars[-1].close)

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
        y_open = [b.open for b in agent.bars[s]]
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
    # filesuffix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    # df = util.df(bars_1)
    # df.to_csv(f'NVDA_{filesuffix}_H.csv')

    # df = util.df(bars_2)
    # df.to_csv(f'META_{filesuffix}_H.csv')

    # df = util.df(bars_3)
    # df.to_csv(f'IWM_{filesuffix}_H.csv')

    if agent.bars:
        logger.info(f"cancelHistoricalData: len(bars)={len(agent.bars)}")
        ib.cancelHistoricalData(agent.bars)

    logger.info("Script has finished.")

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
    finally:
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
"""
open issues:
- stop loss is susceptible to gap down
- start getting bars before market open

"""