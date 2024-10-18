import inspect
import asyncio
import ibapi
import pandas as pd
import numpy as np
import scipy.optimize
np.set_printoptions(precision=2, suppress=True)
import scipy
import logging
import datetime
import time
import dateutil
import argparse
import json
import email.utils
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List
import pdb
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
from ib_insync import IB, MarketOrder, LimitOrder, BarData, Stock, util, objects

def install_custom_repr_():
    # monkey patch ib_insync.objects.TradeLogEntry.__repr__ to use friendlier time format
    def trade_log_entry_repr(self):
        return f"TradeLogEntry(time={self.time.astimezone(local_tz).strftime('%H:%M:%S.%f')}" \
            + (f", status='{self.status}'") \
            + (f", message='{self.message}'" if self.message else '') \
            + (f", errorCode={self.errorCode})" if self.errorCode else '')
    ib_insync.objects.TradeLogEntry.__repr__ = trade_log_entry_repr

    def bar_data_repr(self):
        if isinstance(self.date, datetime.datetime):
            dstr = self.date.astimezone(local_tz).strftime('%H:%M:%S')
        else:
            dstr = self.date.__repr__()
        return f"BarData(date={dstr}, open={self.open}, high={self.high}, low={self.low}, close={self.close}, volume={self.volume:.0f}, average={self.average:.2f}, barCount={self.barCount})"
    ib_insync.objects.BarData.__repr__ = bar_data_repr
    # ib_insync.objects.BarData.__str__ = bar_data_repr

install_custom_repr_()

# globals
ib = None
logger = None

import pytz
import traceback
local_tz = pytz.timezone('US/Eastern')  # Adjust for your local timezone, America/New_York

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
    background_tasks: set[asyncio.Task] = field(default_factory=set)

    # state variables and methods for simpleLongStrategy1
    upPctMilestone: List[float] = field(default_factory=list)
    # upPriceMilestone: List[float] = field(default_factory=list)
    stopLossPct: List[float] = field(default_factory=list)
    # stopLossPrice: List[float] = field(default_factory=list)
    idxMilestone: int = -1 # initialize to an impossible value
    # avgCost: float = 0.0
    state: int = 0 # state machine: 0 = seek entry, 1 = maintain position, keep ratchet up until stop loss

    def reset(self):
        pass

    def simpleLongStrategy1Init(self):
        self.upPctMilestone = [0, .0025, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.045, 0.05,
            0.055, 0.06, 0.065, 0.07, 0.075, 0.08, 0.09, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 1.0,
            2.0, 3.0]
        # self.upPriceMilestone = [0.0] * len(self.upPctMilestone)
        self.stopLossPct = [-0.001] * len(self.upPctMilestone) # uniform -10bps for now. This is the stop loss for each milestone as we cross it, we want small buffer from previous milestone as stop loss so we don't bump into it immediately
        self.stopLossPct[0] = -0.0025 # -25bps initial stop loss
        self.idxMilestone = -1 # initialize to an impossible value
        logger.info(f"SimpleLongStrategy1Init: upPctMilestone={self.upPctMilestone}, stopLossPct={self.stopLossPct}")
        
        # stockpos = [p for p in ib.positions() if p.contract.symbol in [self.symbol] and p.contract.secType == 'STK']
        # assert len(stockpos) == 1, 'Stock position not found'
        # self.avgCost = stockpos[0].avgCost
        # self.position = stockpos[0].position

        # get historical bars for the last 6 months
        contract_ = Stock(self.symbol, 'SMART', 'USD')
        self.histbars = ib.reqHistoricalData(
            contract_,
            endDateTime=(datetime.datetime.now() + datetime.timedelta(days=-1)).strftime('%Y%m%d 16:20:00 US/Eastern'),
            durationStr='6 M',
            barSizeSetting='15 mins',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1)
        self.prevclose = self.histbars[-1].close
        logger.info(f"SimpleLongStrategy1Init: histbars len={len(self.histbars)}")

    def __str__(self):
        return f"Symbol: {self.symbol}, stock position: {self.stkpos}"
    #, Avg Cost: {self.avg_cost}, Last Price: {self.last_price}, Realized PnL: {self.realized_pnl}, Unrealized PnL: {self.unrealized_pnl}, Daily PnL: {self.daily_pnl}"

    def onBarUpdate(self, bars, hasNewBar):
        # reqHistoricalData with keepUpToDate=True always ticks every 5s
        self.lastPrice = bars[-1].close
        logger.debug(f"onBarUpdate: {datetime.datetime.now().isoformat(' ')} {hasNewBar}, {bars[-1]}")
        if (self.highsincestart == 0.0) or (self.highsincestart < bars[-1].high):
            self.highsincestart = bars[-1].high
        if (self.lowsincestart == 0.0) or (self.lowsincestart > bars[-1].low):
            self.lowsincestart = bars[-1].low
        self.testpnl = bars[-1].close - self.beginprice
        logger.info(f"High since start: {self.highsincestart}, Low since start: {self.lowsincestart}, test pnl = {self.testpnl:.2f}")

        # schedule strategy execution
        if self.background_tasks == set():
            task = asyncio.create_task(self.simpleLongStrategy1())
            self.background_tasks.add(task)
            task.add_done_callback(self.background_tasks.discard)

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

        def two_bars_green_with_one_close_near_high_2():
            """
            Check if the last two bars are green and at least one of them close near the high.
            Last two bars don't include the current bar.
            """
            if len(self.bars) < 3:
                return False
            if (self.bars[-2].close > self.bars[-2].open) and (self.bars[-3].close > self.bars[-3].open):
                if (self.bars[-2].close > self.bars[-2].low + 0.8 * (self.bars[-2].high - self.bars[-2].low)):
                    return True
                if (self.bars[-3].close > self.bars[-3].low + 0.8 * (self.bars[-3].high - self.bars[-3].low)):
                    return True

        def low_to_high_inflection_point(n=15, m=5):
            """check if there is a low to high inflection point in the last n bars.
            This is a sign of reversal. We want to catch the reversal early.
            Define inflection point as any of the last m bars lows is lower than any of the previous n-m bars lows
            """
            if len(self.bars) < n:
                return False
            lows = [b.low for b in self.bars[-n:]]
            if min(lows[-m:]) < min(lows[:-m]):
                return True
            return False
        
        def seekEntry():
            if two_bars_green_with_one_close_near_high_2() and low_to_high_inflection_point(10, 5):
                logger.info(f"seekEntry: Two bars green with one close near it's high, seeking entry...")
                self.order = MarketOrder('BUY', 100)
                contract_ = Stock(self.symbol, 'SMART', 'USD')
                logger.info(f"Buying shares of {contract_} as {self.order}")
                # before we place the order, make sure no outstanding trades
                if self.trade and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"clearing old trade {self.trade.log}")
                    self.trade = None
                if self.trade is None:
                    if self.liveTrading:
                        self.state = 1 # because this is market order, we can change state immediately
                        self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                        logger.info(f"Trade placed: {self.trade.log}")
                        # asyncio.sleep(0.2)
                    else:
                        logger.error(f"No live trading, trade not placed: {self.order}")
                else:
                    assert False, f"Impossible state: trade outstanding: {self.trade}"
                if self.trade and self.trade in ib.openTrades():
                    logger.info(f"Trade is still open: {ib.openTrades()}")
                if self.trade and self.trade not in ib.openTrades() and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"Trade is filled: {self.trade.log}")
                    self.state = 1
                    self.trade = None
                # else:
                #     assert False, f"Impossible state: trade {self.trade} not in {ib.openTrades() and }"

        logger.info(f"SimpleLongStrategy1: {datetime.datetime.now().isoformat(' ')} state={self.state}")
        if self.state == 0:
            # no position
            if ((self.stkpos is None) or (self.stkpos.position == 0)) and self.idxMilestone == -1:
                logger.info(f"No position, seeking entry...")
                seekEntry()
                return
            else:
                logger.error(f"Impossible state: state=0 but position={self.stkpos} and idxMilestone={self.idxMilestone}")
        elif self.state == 1:
            # we have a position
            if self.stkpos is None:
                logger.error(f"Waiting for position update to complete...")
                return
            if self.stkpos.position == 0:
                logger.error(f"Impossible state: state=1 but position={self.stkpos}")
                return
            # ensure no outstanding trades
            if self.trade:
                if self.trade in ib.openTrades():
                    logger.info(f"Trade is still open: {ib.openTrades()}")
                if self.trade not in ib.openTrades() and self.trade.orderStatus.status == 'Filled':
                    logger.info(f"Trade is filled: {self.trade.log}")
                    # self.state = 1
                    self.trade = None
            
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
            self.idxMilestone = newIdx_
            logger.info(f"Crossed milestone {self.idxMilestone} {self.upPctMilestone[self.idxMilestone]:.2%}: {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
        else:
            logger.info(f"Milestone unch: {self.idxMilestone} {self.upPctMilestone[self.idxMilestone]:.2%}: {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
        assert self.idxMilestone >= 0, "idxMilestone should be greater than zero"
        
        # is the price below the upPctMilestone[i-1]+stopLossPct[i] for the current milestone?
        if self.idxMilestone > 0:
            stoplossPrice_ = avgCost_ * (1 + self.stopLossPct[self.idxMilestone] + self.upPctMilestone[self.idxMilestone-1])
        else:
            stoplossPrice_ = avgCost_ * (1 + self.stopLossPct[self.idxMilestone])
        if lastPrice_ < stoplossPrice_:
            # crossed below milestone, we should liquidate
            logger.warning(f"Crossed below stopLoss {stoplossPrice_:.2f}, last {lastPrice_:.2f} (return = {lastPctReturn():.2%})")
            self.order = LimitOrder('SELL', self.stkpos.position, lastPrice_)
            contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
            logger.warning(f"Selling shares of {contract_} as {self.order}")
            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                    self.state = 0 # reset state
                    logger.info(f"Trade placed: {self.trade.log}, state reset to 0")
                else:
                    logger.error(f"No live trading, trade not placed: {self.order}")
            elif self.trade in ib.openTrades():
                logger.info(f"Trade is still open: {ib.openTrades()}")
            else:
                logger.error(f"Impossible state: trade {self.trade} not in {ib.openTrades()}")
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
        if lastPrice is None:
            lastPrice = self.lastPrice
        if maxloss_ is None:
            maxloss_ = self.maxloss
        currentPnl = (lastPrice - self.stkpos.avgCost) * self.stkpos.position
        if currentPnl < maxloss_:
            logger.warning(f"Current loss: {currentPnl:.2f}, max loss: {maxloss_:.2f}")
            if self.stkpos.position > 0:
                # self.order = MarketOrder('SELL', self.stkpos.position)
                self.order = LimitOrder('SELL', self.stkpos.position, lastPrice)
                contract_ = Stock(self.stkpos.contract.symbol, 'SMART', self.stkpos.contract.currency)
                logger.warning(f"Selling shares of {contract_} as {self.order} ...")
            if self.stkpos.position < 0:
                logger.warning(f"Buying {-self.stkpos.position} shares of {self.symbol}...")
                # ib.placeOrder(self.stkpos.contract, MarketOrder('BUY', -self.stkpos.position))

            # before we place the order, make sure no outstanding trades
            if self.trade is None:
                if self.liveTrading:
                    self.trade = ib.placeOrder(contract_, self.order) # non-blocking
                    self.state = 0 # reset state
                    logger.info(f"Trade placed: {self.trade.log}, state reset to 0")
                else:
                    logger.error(f"No live trading, trade not placed: {self.order}")
            elif self.trade in ib.openTrades():
                logger.info(f"Trade is still open: {ib.openTrades()}")
            else:
                assert False, f"Impossible state: trade {self.trade} not in {ib.openTrades()}"

agent = None

print(f"TWS API version: {ibapi.__version__}, ib_insync version: {ib_insync.__version__}")

def onAccountValueUpdate(*args, **kwargs):
    # every three minutes
    logger.debug(f"onAccountValueUpdate: {datetime.datetime.now().isoformat(' ')} {args} {kwargs}")
    # pdb.set_trace()

def onPnlUpdate(pnl):
    logger.debug(f"pnl update: {datetime.datetime.now().isoformat(' ')} {pnl}")
    # pdb.set_trace()

def onPortfolioUpdate(portfolio):
    # every three minutes, usually following onAccountValueUpdate
    logger.debug(f"portfolio update: {datetime.datetime.now().isoformat(' ')} {portfolio}")
    # pdb.set_trace()

def onPositionUpdate(newpos):
    logmsg = f"onPositionUpdate: {datetime.datetime.now().isoformat(' ')} {newpos} id={id(newpos)}"
    if agent:
        logmsg += f" agent.state={agent.state} agent.idxMilestone={agent.idxMilestone}"
        if agent.trade:
            logmsg += f" trade={agent.trade.log}"
            if agent.trade.orderStatus.status == 'Filled' and agent.state == 0:
                logmsg += f" state is zero and last trade is filled, resetting trade status"
                agent.trade = None
                if agent.idxMilestone >= 0:
                    agent.idxMilestone = -1 # reset milestone
                    logmsg += f" also resetting strategy1 milestone to -1"
                
    logger.info(logmsg)
    traceback.print_stack()
    if agent is None:
        logger.error(f"onPositionUpdate: agent not initialized yet")
        # just move on
        return
    # only care about specific stock positions for now
    if (newpos.contract.symbol == agent.symbol) and (newpos.contract.secType == 'STK'):
        # agent.state = 1
        prevstkpos = agent.stkpos
        agent.stkpos = newpos
        logger.info(f"onPositionUpdate: updating agent's with stock position: {agent.stkpos} (id={id(newpos)}), prev={prevstkpos} (id={id(prevstkpos)})")
        # should we change state?
        # let's just warn about possible state change for now
        if (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position != 0 and agent.state == 0:
            logger.info(f"onPositionUpdate: agent state change: 0 -> 1")
            agent.state = 1
            # print stack trace
        elif not (prevstkpos is None or (prevstkpos.position == 0)) and newpos.position == 0 and agent.state == 1:
            logger.info(f"onPositionUpdate: agent state should change: 1 -> 0")
            agent.state = 0
        elif not (prevstkpos is None) and (prevstkpos.position == newpos.position):
            logger.warning(f"onPositionUpdate: newpos.position == prevpos.position, agent state: {agent.state}")

        # if prevstkpos is None:
        #     logger.info(f"onPositionUpdate: agent initialized with stock position: {agent.stkpos}, state={agent.state}")
        # logger.info(f"onPositionUpdate: agent initialized with stock position: {agent.stkpos}, state={agent.state}")
    elif (newpos.contract.symbol != agent.symbol) and (newpos.contract.secType == 'STK'):
        logger.warning(f"onPositionUpdate: ignoring stock position: {newpos}")
    else:
        logger.warning(f"onPositionUpdate: ignoring new position: {newpos}")

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

if __name__ == "__main__":
    # parse command line arguments
    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbol', type=str, help='Ticker symbol to trade')
    argparser.add_argument('maxloss', type=float, help='Max loss threshold')
    argparser.add_argument('--clientid', type=int, default=9, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=4002, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--run_until', type=str, help='Run until this time (HH:MM)')
    argparser.add_argument('--live_trading', action='store_true', help='Live trading')
    args = argparser.parse_args()

    logging.basicConfig(level=args.loglevel) # must come before any logging calls
    logger = logging.getLogger()
    logging.getLogger('ib_insync').setLevel(logging.WARN)

    # logger.addFilter(NoParsingFilter())

    logger.info("Script is starting...")
    logger.info(f"args: {args}")
    ib = IB()
    # util.logToConsole(logging.DEBUG) # show network traffic
    ib.connect(args.host, args.port, clientId=args.clientid)
    # print portfolio
    logger.info(f"Portfolio: {ib.portfolio()}")

    # find stock position of a given symbol in the portfolio
    sp_ = [p for p in ib.positions() if p.contract.symbol in [args.symbol] and p.contract.secType == 'STK']
    # assert len(sp_) == 1
    # if len(sp_) == 0:
    #     logger.warning(f"Stock position not found for {args.symbol}")

    agent = Agent(symbol=args.symbol, liveTrading=args.live_trading, maxloss=args.maxloss)
    if len(sp_) > 0:
        agent.stkpos = sp_[0]
        agent.state = 1
        logger.info(f"Tracked position: {agent.stkpos}")
    else:
        agent.state = 0
        logger.info(f"Tracked position not found for {args.symbol}")

    logger.info(f"Agent State: {agent}")

    account = ib.managedAccounts()[0]
    # print(ib.managedAccounts())

    # no need to request updates, event fires every 3 minutes automatically
    ib.accountValueEvent += onAccountValueUpdate
    ib.updatePortfolioEvent += onPortfolioUpdate
    
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
        # untilTime = datetime.datetime.now() + datetime.timedelta(hours=2.2)
        untilTime = datetime.datetime.combine(datetime.datetime.now(), datetime.time(16, 2, 0)) # 4:02 PM
    doOnce = True
    logger.info(f"Running until {untilTime}")
    while datetime.datetime.now() < untilTime:
        # get market data for all positions
        if doOnce:
            # contracts_ = [p.contract for p in ib.positions()]
            # contracts = ib.qualifyContracts(*contracts_)
            # logger.info(f"ib.qualifyContracts: {[x.localSymbol for x in contracts_]}")
            doOnce = False

            # request market data
            contract_1 = Stock(agent.symbol, 'SMART', 'USD')
            agent.bars = ib.reqHistoricalData(
                contract_1,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='1 min', # '5 secs', # always ticks every 5 secs
                whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                useRTH=False,
                formatDate=1,
                keepUpToDate=True)
            agent.barsstartidx = len(agent.bars) - 1
            agent.beginprice = agent.bars[agent.barsstartidx].close
            logger.info(f"ib.reqHistoricalData: {contract_1}, len(bars)={len(agent.bars)}, bar start={agent.bars[agent.barsstartidx]}")
            agent.bars.updateEvent += lambda x, y: agent.onBarUpdate(x, y)

            agent.simpleLongStrategy1Init()

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
        if agent.stkpos:
            logger.info(f"Market Value: {agent.bars[-1].close * agent.stkpos.position:.2f}")
        logger.debug(f"Bars: {len(agent.bars)} {agent.bars[-1]}")

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
        logger.info(f"PCHIP 1m price slopes: {price_slopes}")

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
        logger.info(f"PCHIP 5m price slopes: {price_slopes}")
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

        logger.debug("sleeping for 10 seconds...")
        ib.sleep(10)

    # ib.sleep(60*10) # sleep for 60 seconds
    # ib.waitUntil(datetime.time(16,2,0)) # wait until 4:05 PM
    
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
