import datetime
import argparse
import logging
import pandas as pd
import numpy as np
import re
import tqdm

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir) # prepend
    # print(f"{parent_dir} added to sys.path")

import ib_insync
from ib_insync import Stock, IB, util
import asyncio

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

def last_business_dt() -> datetime.datetime:
    """Return the last business date"""
    today = datetime.datetime.now().date()
    if today.weekday() == 0: # Monday
        return today + datetime.timedelta(days=-3)
    else:
        return today + datetime.timedelta(days=-1)

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
    logging.basicConfig(level=args.loglevel)
    logger = logging.getLogger(__name__)
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    # Connect to IB Gateway
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

    syms = args.symbols or ['SPY','QQQ','IWM','TLT','NVDA','TSLA','AMD','META','MSFT','GOOG','GOOGL','AAPL'
                            ,'PLTR','MSTR','ANET','COIN','AVGO','PYPL','SQ','SHOP','ROKU','ZM','AMZN','COST'
                            ,'NFLX','TMUS','ADBE','CSCO','PEP','AMD','ISRG','INTU','QCOM','MELI','INTC','MU'
                            ,'MRVL','CRWD','CRM','ASML','SMCI','MRNA','JD','AXON','NTES','EQIX','TCOM','UAL'
                            ,'WDAY','DELL','DKNG','BABA','CVNA','SCCO','HOOD','JPM','LLY','V','XOM','UNH','WMT'
                            ,'TGT','BAC','ORCL','ABBV','CVX','MRK','KO','NOW','MCD','IBM','DIS','AXP']
    dayoffset: int = 0
    if datetime.datetime.now().time() < datetime.time(9, 30):
        dayoffset = -1
    else:
        dayoffset = 0
    endDateTime = datetime.datetime.combine(datetime.datetime.now().date() + datetime.timedelta(days=dayoffset), datetime.time(21, 0))
    # endDateTime = datetime.datetime.now() + datetime.timedelta(days=0)
    # endDateTime = pd.to_datetime('2024-11-20 21:00:00-05:00')
    async def fetch_data(sym, contract_, endDateTime, logger, args):
        try:
            logger.info(f"Requesting historical bars for {sym}...")
            if args.dryrun:
                return

            tasks = [
                ib.reqHistoricalDataAsync(
                    contract_,
                    endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
                    durationStr='1 D',
                    barSizeSetting='1 min',
                    whatToShow='TRADES',
                    useRTH=False,
                    formatDate=1,
                ),
                ib.reqHistoricalDataAsync(
                    contract_,
                    endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
                    durationStr='1 D',
                    barSizeSetting='5 secs',
                    whatToShow='TRADES',
                    useRTH=False,
                    formatDate=1,
                )
            ]

            results = await asyncio.gather(*tasks)

            for idx, histbars in enumerate(results):
                if histbars is None or len(histbars) == 0:
                    logger.error(f"Failed to get historical bars for {sym}")
                else:
                    histdf = util.df(histbars)
                    if idx == 0:
                        histdf.to_csv(f'./data/{sym}_1m_{endDateTime:%Y%m%d}.csv', index=False)
                    else:
                        histdf.to_csv(f'./data/{sym}_5s_{endDateTime:%Y%m%d}.csv', index=False)

        except Exception as e:
            logger.error(f"Error fetching data for {sym}: {e}")

    async def main_async():
        tasks = []
        contract_tasks = [ib.reqContractDetailsAsync(Stock(sym, 'SMART', 'USD')) for sym in syms]
        contract_details = await asyncio.gather(*contract_tasks)

        for sym, details in zip(syms, contract_details):
            if len(details) == 0:
                logger.error(f"Contract details not found for {sym}")
                continue
            else:
                logger.info(f"Contract details {details[0].contract}")
                contract_ = details[0].contract

            tasks.append(fetch_data(sym, contract_, endDateTime, logger, args))

        await asyncio.gather(*tasks)

    ib.run(main_async())

    return # end of main

if __name__ == '__main__':
    main()