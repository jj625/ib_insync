import os
# Get the program's file name without the extension 
program_name = os.path.splitext(os.path.basename(__file__))[0] 
program_dir = os.path.dirname(os.path.realpath(__file__))
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

def onUpdateEvent(bars: BarDataList, hasNewBar: bool):
    logger.info(f"len(bars) {len(bars)}, hasNewBar {hasNewBar}")

def main():

    contract = Stock('SPY', 'SMART', 'USD')
    contractDetails = ib.reqContractDetails(contract)
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
        useRTH = True
        barsize = '1 min'
        dur = '1 D'
        bars = ib.reqHistoricalData(
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
        # bars_df = util.df(bars)
    # util.logToConsole(logging.INFO)

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
    filesuffix = f'_{datetime.datetime.now():%y%m%d_%H%M}'
    log_file = os.path.join(program_dir, 'logs', f'{program_name}_{filesuffix}.log')
    # Set up logging
    logging.basicConfig(level=logging.INFO
        #, format=('%(asctime)s:' + logging.BASIC_FORMAT)
        , format='%(asctime)s:%(name)s:%(funcName)s:%(levelname)s:%(message)s'
        , handlers=[
            logging.FileHandler(log_file),
            #RichHandler(markup=True)
            logging.StreamHandler()
        ]
        )
    # global logger
    logger = logging.getLogger(__name__)
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|Info 2104|Info 2106|Info 2158)'
    ))

    argparser = argparse.ArgumentParser()
    # argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol(s)') # nargs='+' means one or more
    # argparser.add_argument('numshares', type=int, nargs='?', help='Number of shares to trade')
    # argparser.add_argument('maxloss', type=float, nargs='?', help='Max loss threshold')
    # argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    args = argparser.parse_args()
    logger.info(f'{args}')

    host_1 = '127.0.0.1'
    host_2 = '192.168.1.90'
    port_1 = 7496
    port_2 = 7497
    port_3 = 4002
    port_ephemeral = np.random.randint(49_152, 65_535)
    ib = IB()
    if not ib.isConnected():
        ib.connect(args.host, args.port, clientId=np.random.randint(5_000, 10_000))
        if ib.client._serverVersion < 178:
            logger.error(f'TWS version {ib.client._serverVersion} is too old. Update to latest version.')
            ib.disconnect()
            sys.exit(1)

    util.logToConsole(logging.DEBUG)
    main()
    ib.sleep(300)
    logger.info('Done')
