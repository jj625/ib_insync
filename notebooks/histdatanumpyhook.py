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

import matplotlib as mpl
mpl.use('Qt5Agg')
if mpl.get_backend() != 'Qt5Agg':
    print(f"Warning: matplotlib backend is {mpl.get_backend()}")

import matplotlib.pyplot as plt
if not plt.isinteractive():
    plt.ion()

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

logger = None
ib = None

def onhistoricalDataHook(reqId: int, bar: BarData):
    logger.info(f"reqId: {reqId}, bar: {bar}")

def onhistoricalDataEndHook(start_: str, end_: str, bars: BarDataList):
    logger.info(f"start: {start_}, end: {end_}, len(bars): {len(bars)}")

def onhistoricalDataUpdateHook(reqId: int, bar: BarData):
    logger.info(f"reqId: {reqId}, bar: {bar}")

def onUpdateEvent(bars: BarDataList, hasNewBar: bool):
    logger.info(f"bars: {len(bars)}, hasNewBar: {hasNewBar}, idx: {bars.idx}")

async def test1():

    contract = Stock('NVDA', 'SMART', 'USD')
    contractDetails = await ib.reqContractDetailsAsync(contract)
    # ib.reqHeadTimeStamp(contract, whatToShow='TRADES', useRTH=True)

    # util.logToConsole(logging.INFO)
    load_from_csv = False
    if load_from_csv:
        bars_df = pd.read_csv('TSLA_1min.csv', parse_dates=['date'])
    else:
        endDateTime = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d 21:00:00 US/Eastern')
        endDateTime = ''
        # endDateTime = '20241109 16:20:00 US/Eastern'
        keepUpToDate = True
        useRTH = False
        barsize = '1 min'
        dur = '1 D'
        bars = await ib.reqHistoricalDataAsync(
            contract,
            endDateTime=endDateTime,
            durationStr=dur,
            #barSizeSetting='5 secs',
            barSizeSetting=barsize,
            whatToShow='TRADES',
            useRTH=useRTH,
            keepUpToDate=keepUpToDate,
            formatDate=1)
        bars.updateEvent += onUpdateEvent
        # if hasattr(bars, 'historicalDataHook'):
        #     bars.historicalDataHook += onhistoricalDataHook
        # else:
        #     logger.info('No historicalDataHook')
        # if hasattr(bars, 'historicalDataEndHook'):
        #     bars.historicalDataEndHook += onhistoricalDataEndHook
        # else:
        #     logger.info('No historicalDataEndEvent')
        # if hasattr(bars, 'historicalDataUpdateHook'):
        #     bars.historicalDataUpdateHook += onhistoricalDataUpdateHook
        # else:
        #     logger.info('No historicalDataUpdateHook')
        # await bars
        # bars_df = util.df(bars)
    # util.logToConsole(logging.INFO)
        logger.info(f"bars: {len(bars)}, bars.idx: {bars.idx}")
        logger.info(f"bars.date: {bars.date[0:]}..{bars.date[-1]}")
        # find the index of the market open time
        mktopentime = np.datetime64(MKTOPEN.astimezone(datetime.timezone.utc).replace(tzinfo=None), 's')
        results = np.where(bars.date == mktopentime)
        idx_start = results[0][0] if results[0].size > 0 else -999
        logger.info(f"mktopentime: {mktopentime}, results: {results}")
        if idx_start != -999:
            logger.info(f"bars.close_prices: {bars.close_prices[idx_start:]} log_high_low={bars.log_high_low[idx_start:]}")

async def test2():
    contract = Stock('NVDA', 'SMART', 'USD')
    # contractDetails = await ib.reqContractDetailsAsync(contract)
    # ib.reqHeadTimeStamp(contract, whatToShow='TRADES', useRTH=True)

    # util.logToConsole(logging.INFO)
    endDateTime = (datetime.datetime.now() + datetime.timedelta(days=0)).strftime('%Y%m%d 21:00:00 US/Eastern')
    endDateTime = ''
    # endDateTime = '20241109 16:20:00 US/Eastern'
    keepUpToDate = True
    useRTH = True
    barsize = '1 min'
    dur = '3000 S'
    if hasattr(ib, 'reqHistoricalDataExtAsync'):
        bars = await ib.reqHistoricalDataExtAsync(
            contract,
            endDateTime=endDateTime,
            durationStr=dur,
            #barSizeSetting='5 secs',
            barSizeSetting=barsize,
            whatToShow='TRADES',
            useRTH=useRTH,
            keepUpToDate=keepUpToDate,
            formatDate=1,
            _historicalDataEndHook=onhistoricalDataEndHook,
            )
        bars.updateEvent += onUpdateEvent
    # if hasattr(bars, '_historicalDataEndHook'):
    #     bars.historicalDataHook += onhistoricalDataHook
        # else:
        #     logger.info('No historicalDataHook')
        # if hasattr(bars, 'historicalDataEndHook'):
        #     bars.historicalDataEndHook += onhistoricalDataEndHook
        # else:
        #     logger.info('No historicalDataEndEvent')
        # if hasattr(bars, 'historicalDataUpdateHook'):
        #     bars.historicalDataUpdateHook += onhistoricalDataUpdateHook
        # else:
        #     logger.info('No historicalDataUpdateHook')
        # await bars
        # bars_df = util.df(bars)
    # util.logToConsole(logging.INFO)
        mktopentime = np.datetime64(MKTOPEN.astimezone(datetime.timezone.utc).replace(tzinfo=None), 's')
        results = np.where(bars.date == mktopentime)
        idx = results[0][0] if results[0].size > 0 else -1
        logger.info(f"mktopentime: {mktopentime}, results: {results}, bars.date: {bars.date[idx:]}")
        logger.info(f"bars: {len(bars)}, bars.idx: {bars.idx}, bars.close_prices: {bars.close_prices[idx:]}")
        logger.info(f"{bars.log_high_low[idx:]}")

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

if __name__ == '__main__':
    # Set up logging
    logging.basicConfig(level=logging.INFO
        #, format=('%(asctime)s:' + logging.BASIC_FORMAT)
        , format='%(asctime)s:%(name)s:%(funcName)s:%(levelname)s:%(message)s'
        )
    # global logger
    logger = logging.getLogger(__name__)
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|Info 2104|Info 2106|Info 2158)'
    ))

    host_1 = '127.0.0.1'
    host_2 = '192.168.1.90'
    port_1 = 7496
    port_2 = 7497
    port_3 = 4002
    port_ephemeral = np.random.randint(49_152, 65_535)
    ib = IB()
    if not ib.isConnected():
        ib.connect(host_1, port_1, clientId=np.random.randint(5_000, 10_000))

    util.logToConsole(logging.INFO)
    util.run(test2())
    ib.sleep(30)
    logger.info('Done')
