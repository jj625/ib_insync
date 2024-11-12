import sys
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
import logging
import datetime
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
mpl_dir = pathlib.Path('../eventkit').resolve()
if mpl_dir.exists() and mpl_dir.is_dir() and str(mpl_dir) not in sys.path:
    sys.path.insert(0, str(mpl_dir))
    mpl_dir
elif not mpl_dir.exists():
    print(f"Expected {mpl_dir} does not exist")

import eventkit
import ib_insync
import ib_insync.ib
ib_insync.ib.install_custom_repr_()

from ib_insync import IB, MarketOrder, LimitOrder, BarData, Stock, util

import filterpy
from filterpy.kalman import KalmanFilter as kf

# Global variables
logger = None

bars5s: List[BarData] = []
resampled: List[BarData] = [] # resampled 1m bars
bars1m: List[BarData] = []

def downsample(bars: List[BarData], b, n: int):
    if b.date.minute % n == 0:
        # resample to n minutes
        bars.append(b)
    else:
        bars[-1].close = b.close
        if b.high > bars[-1].high:
            bars[-1].high = b.high
        if b.low < bars[-1].low:
            bars[-1].low = b.low
        bars[-1].volume += b.volume

def onBarUpdate1m(bars: List[BarData], hasNewBar: bool):
    logger.info(f"bars1m[-1]={bars1m[-1]} hasNewBar={hasNewBar}")

def onBarUpdate5s(bars: List[BarData], hasNewBar: bool):
    """
    bars: ohlcv every 5 seconds
    """
    b = bars[-1]
    # logger.info(f"{bars[-1]} hasNewBar={hasNewBar}")

    if b.date.second % 60 == 0 or resampled == []:
        # resample to 60 seconds/1 min
        resampled.append(b)
        logger.info(f"resampled[-1]={b} hasNewBar=True")
    elif resampled:
        sumVolume = resampled[-1].volume + b.volume
        sumValues = resampled[-1].volume * resampled[-1].average + b.volume * b.average
        resampled[-1].close = b.close
        if b.high > resampled[-1].high:
            resampled[-1].high = b.high
        if b.low < resampled[-1].low:
            resampled[-1].low = b.low
        resampled[-1].volume += b.volume
        resampled[-1].barCount += b.barCount
        resampled[-1].average = sumValues / sumVolume if sumVolume > 0 else 0
        logger.info(f"resampled[-1]={resampled[-1]} hasNewBar=False")

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
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    # Connect to IB Gateway
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

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
        bars5s.updateEvent += onBarUpdate5s

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
    
    ib.sleep(5 * 60)
    # ib.waitUntil(datetime.time(16, 2, 0))

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
    
    ib.disconnect()

    filename5s = f"./data/{sym}_5s_{dtnow:%y%m%d_%H%M}.csv"
    filename1m = f"./data/{sym}_1m_{dtnow:%y%m%d_%H%M}.csv"
    filename1m_resampled = f"./data/{sym}_resampled_{dtnow:%y%m%d_%H%M}.csv"
    bars5s_df = util.df(bars5s)
    bars1m_df = util.df(bars1m)
    resampled_df = util.df(resampled)
    bars5s_df.to_csv(filename5s, index=False)
    bars1m_df.to_csv(filename1m, index=False)
    resampled_df.to_csv(filename1m_resampled, index=False)
    logger.info(f"Script done. Files saved to:\n{filename5s}\n{filename1m}\n{filename1m_resampled}")
    return # end of main

if __name__ == '__main__':
    main()
