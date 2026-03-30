import datetime
import zoneinfo
import argparse
import logging
import pandas as pd
import numpy as np
import re
import pathlib
import tqdm
import os
import sys
import asyncio
from ib_insync import Stock, IB, util

tz_NY = zoneinfo.ZoneInfo('America/New_York')
logger = None  # global

parent_dir = os.path.abspath('..')
if (parent_dir not in sys.path):
    sys.path.insert(0, parent_dir)  # prepend

class LoggerFilter(logging.Filter):
    def __init__(self, logger_name, pattern=r'.*'):
        super().__init__()
        self.logger_name = logger_name
        self.pattern = re.compile(pattern)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not (record.name == self.logger_name and
                    self.pattern.search(msg) and
                    record.levelno >= logging.INFO)

def last_business_dt() -> datetime.datetime:
    """Return the last business date"""
    today = datetime.datetime.now().date()
    if today.weekday() == 0:  # Monday
        return today + datetime.timedelta(days=-3)
    else:
        return today + datetime.timedelta(days=-1)

async def fetch_historical_data(ib, contract, endDateTime, barSizeSetting, filename, timeout=None):
    logger.info(f"Requesting {barSizeSetting} historical bars for {contract.symbol}... ending {endDateTime}")
    try:
        histbars = await asyncio.wait_for(
            ib.reqHistoricalDataAsync(
                contract,
                endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
                durationStr='1 D',
                barSizeSetting=barSizeSetting,
                whatToShow='TRADES',
                useRTH=False,
                formatDate=1,
                timeout=timeout
            ),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        logger.error(f"Timeout while fetching {barSizeSetting} historical bars for {contract.symbol}")
        return

    if histbars is None or len(histbars) == 0:
        logger.error(f"Failed to get historical bars for {contract.symbol}")
    else:
        histdf = util.df(histbars)
        if 'open_' in histdf.columns:  # rename open_ to open
            histdf.rename(columns={'open_': 'open'}, inplace=True)
        if 'timestamp' in histdf.columns:  # drop it
            histdf.drop(columns=['timestamp'], inplace=True)
        logger.info(f"Writing to {str(filename)}")
        histdf.to_csv(filename, index=False)

async def main():
    # Set up logging
    global logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol(s)')
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number')
    argparser.add_argument('--loglevel', type=str, help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
    argparser.add_argument('--date', type=str, help='Date to download data for')
    args = argparser.parse_args()
    if args.loglevel and args.loglevel.upper() not in ['INFO']:
        logger.setLevel(args.loglevel.upper())
    logger.info(args)

    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper',
                                   r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
                                   r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
                                   ))

    # Connect to IB Gateway
    ib = IB()
    await ib.connectAsync(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

    if args.symbols is None or len(args.symbols) == 0:
        syms = args.symbols or ['SPY', 'QQQ', 'IWM', 'TLT', 'NVDA', 'TSLA', 'AMD', 'META', 'MSFT', 'GOOG', 'GOOGL', 'AAPL'
                                , 'PLTR', 'MSTR', 'ANET', 'COIN', 'AVGO', 'PYPL', 'SQ', 'SHOP', 'ROKU', 'ZM', 'AMZN', 'COST'
                                , 'NFLX', 'TMUS', 'ADBE', 'CSCO', 'PEP', 'AMD', 'ISRG', 'INTU', 'QCOM', 'MELI', 'INTC', 'MU'
                                , 'MRVL', 'CRWD', 'CRM', 'ASML', 'SMCI', 'MRNA', 'JD', 'AXON', 'NTES', 'EQIX', 'TCOM', 'UAL'
                                , 'WDAY', 'DELL', 'DKNG', 'BABA', 'CVNA', 'SCCO', 'HOOD', 'JPM', 'LLY', 'V', 'XOM', 'UNH', 'WMT'
                                , 'TGT', 'BAC', 'ORCL', 'ABBV', 'CVX', 'MRK', 'KO', 'NOW', 'MCD', 'IBM', 'DIS', 'AXP']
    else:
        syms = args.symbols
    dayoffset: int = 0

    if args.date:
        endDateTime = pd.to_datetime(args.date)
    else:
        if datetime.datetime.now().time() < datetime.time(9, 30):
            dayoffset = -1
        else:
            dayoffset = 0
        endDateTime = datetime.datetime.combine(datetime.datetime.now().date() + datetime.timedelta(days=dayoffset), datetime.time(21, 0), tzinfo=tz_NY)

    semaphore = asyncio.Semaphore(1)  # Limit to one active request at a time

    async def fetch_with_semaphore(*args, **kwargs):
        async with semaphore:
            await fetch_historical_data(*args, **kwargs)

    tasks = []
    for sym in syms:
        contract_ = Stock(sym, 'SMART', 'USD')
        temp = await ib.reqContractDetailsAsync(contract_)
        if len(temp) == 0:
            logger.error(f"Contract details not found for {sym}")
            continue
        else:
            logger.info(f"Contract details {temp[0].contract}")
            contract_ = temp[0].contract
        if args.dryrun:
            continue

        filename_1d = pathlib.Path(f'./data/{sym}_1d.csv').resolve()
        filename_1m = pathlib.Path(f'./data/{sym}_1m_{endDateTime:%Y%m%d}.csv').resolve()
        filename_5s = pathlib.Path(f'./data/{sym}_5s_{endDateTime:%Y%m%d}.csv').resolve()

        tasks.append(fetch_historical_data(ib, contract_, endDateTime, '1 day', filename_1d))
        tasks.append(fetch_historical_data(ib, contract_, endDateTime, '1 min', filename_1m))
        tasks.append(fetch_with_semaphore(ib, contract_, endDateTime, '5 secs', filename_5s, timeout=180))

    await asyncio.gather(*tasks)
    logger.info("Done!")

if __name__ == '__main__':
    asyncio.run(main())
