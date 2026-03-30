import asyncio
import ibapi
import pandas as pd
import logging
import datetime
import argparse
import re

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    print(f"{parent_dir} added to sys.path")

import ib_insync
from ib_insync import *

ib_insync.ib.install_custom_repr_()

print(f"TWS API version: {ibapi.__version__}, ib_insync version: {ib_insync.__version__}")

def onBarUpdate(bars, hasNewBar):
    print(hasNewBar, bars[-1])

class LoggerNameFilter(logging.Filter):
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

if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Request historical bars from IB')
    parser.add_argument('--host', type=str, help='Host of the IB Gateway or TWS instance', default='127.0.0.1')
    parser.add_argument('--port', type=int, help='Port of the IB Gateway or TWS instance', default=7496) # 4002
    parser.add_argument('--loglevel', type=str, help='Log level', default='INFO')
    parser.add_argument('symbol', type=str, help='Symbol of the stock')
    parser.add_argument('duration', type=str, help='Duration of the bars', default='1 D')
    parser.add_argument('barsize', type=str, help='Size of the bars', default='1 min')
    args = parser.parse_args()

    logger = logging.getLogger()
    logging.basicConfig(level=args.loglevel) # must come before any logging calls

    # class ExcludeFilter(logging.Filter):
    #     def filter(self, record):
    #         return not record.name.startswith("ib_insync.wrapper")

    # logger.addFilter(ExcludeFilter())

    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.setLevel(logging.INFO)
    wlogger.addFilter(LoggerNameFilter('ib_insync.wrapper', r'^(updateAccountTime|accountUpdateMulti'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    logger.info("Script is starting...")
    ib = IB()
    # util.logToConsole(logging.DEBUG) # show network traffic
    ib.connect(args.host, args.port, clientId=8) # IB Gateway 4001, TWS 7496

    logger.info(f"Requesting historical bars for {args.symbol}...")
    contract_1 = Stock(args.symbol, 'SMART', 'USD')
    headts = ib.reqHeadTimeStamp(contract_1, whatToShow='TRADES', useRTH=True)
    logger.info(f"Head timestamp: {headts}")
    bars_1 = ib.reqHistoricalData(
        contract_1,
        endDateTime='',
        durationStr=args.duration, # '1 D', # 900 S
        barSizeSetting=args.barsize, #'5 secs',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1,
        keepUpToDate=False)
    # bars_1.updateEvent += onBarUpdate

    ib.sleep(0)
    
    # dump the bars to a file
    filesuffix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    logger.info(f"Writing bars to {args.symbol}_{filesuffix}_H.csv")
    df = util.df(bars_1)
    df.to_csv(f'{args.symbol}_{filesuffix}_H.csv', index=False)

    ib.cancelHistoricalData(bars_1)

    logger.info("Script has finished.")
