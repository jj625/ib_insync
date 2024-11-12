import sys
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
from typing import List
# import pdb
import telegram
if telegram.__version__ < '20.0':
    print("Requires python-telegram-bot library version 20.0 or higher")
    sys.exit(1)

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

from ib_insync import IB, MarketOrder, LimitOrder, BarData, Stock, Forex, util

import filterpy
from filterpy.kalman import KalmanFilter as kf

background_tasks: set[asyncio.Task] = set()

# globals
ib = None
logger = None
h5store = None

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

async def telegram_init(bot):
    # bot = telegram.Bot(TELEGRAM_TOKEN)
    # u = bot.get_me()
    # logger.info(f"Telegram user: {u}")
    # async with bot:
    u = bot.get_me()
    logger.info(f"Telegram user: {await u}")

logger: logging.Logger = None

class ControlCTrap:
    def __enter__(self):
        return self

    def __exit__(self, exc_type: type, value: Exception, traceback: object) -> bool:
        if exc_type is KeyboardInterrupt:
            logger.info(f"Caught KeyboardInterrupt, exiting...")
            return True
        return False

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

def onBarUpdate_es(bars: BarData, hasNewBar: bool):
    logger.info(f"{bars[-1]} {hasNewBar}")

def onBarUpdate_eur(bars: BarData, hasNewBar: bool):
    logger.info(f"{bars[-1]} {hasNewBar}")

def onIBBarUpdate(bars: BarData, hasNewBar: bool):
    logger.info(f"{bars[-1]} {hasNewBar}")

def main_2():
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
    # create handlers
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(args.loglevel)
    # console_handler.setFormatter(formatter)
    scriptdir = os.path.dirname(os.path.realpath(__file__))
    filesuffix = f'{args.symbol}_{datetime.datetime.now():%Y%m%d_%H%M}'
    logfilename = os.path.join(scriptdir, 'logs', f'controlc_{filesuffix}.log')
    file_handler = logging.FileHandler(f'controlc_{filesuffix}.log')
    file_handler.setLevel(args.loglevel)
    file_handler.setFormatter(formatter)

    # # add handlers to logger
    global logger
    logger = logging.getLogger()

    # in the meantime, remind user to set power setting to 'full'
    pwr = GetPowerSetting()
    if pwr != '{8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c}':
        logger.error(f"Expect full power setting, got {pwr}")
        sys.exit(1)

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
    clientid = args.clientid if args.clientid else spec['root'][args.symbol]['clientid']

    h5file = os.path.join(scriptdir, 'data', f'ibdata_{filesuffix}.h5')
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
    logger.info(f"Portfolio: {ib.portfolio()}")

    # no need to request updates, event fires every 3 minutes automatically
    ib.accountValueEvent += logger.info
    ib.updatePortfolioEvent += logger.info
    ib.execDetailsEvent += logger.info
    # https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
    ib.cancelOrderEvent += logger.info
    ib.orderStatusEvent += logger.info

    ib.accountSummaryEvent += logger.info
    ib.pnlEvent += logger.info
    ib.errorEvent += logger.info
    
    ib.pnlEvent += logger.info
    # ib.reqPnL(account)

    ib.positionEvent += logger.info
    ib.barUpdateEvent += onIBBarUpdate

    doOnce = False

    untilTime = datetime.datetime.now() + datetime.timedelta(minutes=5) # run for 10 minutes
    while datetime.datetime.now() < untilTime:

        if not doOnce:
            # request live market data
            forex_eur = Forex('EURUSD')
            fut_es = ib_insync.Future('ES', '202412', 'CME')
            bars_es = ib.reqHistoricalData(
                fut_es,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='5 secs', # '5 secs', # always ticks every 5 secs
                whatToShow='TRADES', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                useRTH=False, # start from ~4:00 AM
                formatDate=1,
                keepUpToDate=True)
            bars_es.updateEvent += onBarUpdate_es
            doOnce = True
        
            bars_eur = ib.reqHistoricalData(
                forex_eur,
                endDateTime='',
                durationStr='1 D',
                barSizeSetting='5 secs', # '5 secs', # always ticks every 5 secs
                whatToShow='MIDPOINT', # https://interactivebrokers.github.io/tws-api/historical_bars.html#hd_what_to_show
                useRTH=False, # start from ~4:00 AM
                formatDate=1,
                keepUpToDate=True)
            bars_eur.updateEvent += onBarUpdate_eur
        
        ib.sleep(10)

    return # end of main_2

def main():
    global logger
    #logging.basicConfig(level=logging.INFO)
    logging.basicConfig(level=logging.INFO
        , format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s'
    )
    logger = logging.getLogger(__name__)

    logger.info("Starting main loop")
    try:
        main_2()
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
        if logger is not None:
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger.removeHandler(handler)
                    logger.info(f"{handler} closed")
        
        logger.info("End of main loop")
    return # end of main

if __name__ == "__main__":
    main()
    # with ControlCTrap():
    #     main()
