import datetime
import zoneinfo
tz_NY = zoneinfo.ZoneInfo('America/New_York')
import argparse
import logging
logger = None # global
import pandas as pd
import numpy as np
import re
import pathlib
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
from ib_insync import Stock, IB, util, ContractDetails

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
    # Set up logging
    global logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    argparser = argparse.ArgumentParser()
    argparser.add_argument('symbols', nargs='*', type=str, help='Just run for this symbol(s)') # nargs='+' means one or more
    # argparser.add_argument('numshares', type=int, nargs='?', help='Number of shares to trade')
    # argparser.add_argument('maxloss', type=float, nargs='?', help='Max loss threshold')
    argparser.add_argument('--clientid', type=int, help='IBKR API Client ID')
    argparser.add_argument('--host', type=str, default='127.0.0.1', help='Host name')
    argparser.add_argument('--port', type=int, default=7497, help='Port number') # IB Gateway 4001, TWS 7496
    argparser.add_argument('--loglevel', type=str, default='INFO', help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
    argparser.add_argument('--date', type=str, help='Date to download data for')
    # argparser.add_argument('--live_trading', action='store_true', help='Live trading')
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
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

    if args.symbols is None or len(args.symbols) == 0:
        syms = args.symbols or ['SPY','QQQ','IWM','TLT','NVDA','TSLA','AMD','META','MSFT','GOOG','GOOGL','AAPL'
                                ,'PLTR','MSTR','ANET','COIN','AVGO','PYPL','SQ','SHOP','ROKU','ZM','AMZN','COST'
                                ,'NFLX','TMUS','ADBE','CSCO','PEP','AMD','ISRG','INTU','QCOM','MELI','INTC','MU'
                                ,'MRVL','CRWD','CRM','ASML','SMCI','MRNA','JD','AXON','NTES','EQIX','TCOM','UAL'
                                ,'WDAY','DELL','DKNG','BABA','CVNA','SCCO','HOOD','JPM','LLY','V','XOM','UNH','WMT'
                                ,'TGT','BAC','ORCL','ABBV','CVX','MRK','KO','NOW','MCD','IBM','DIS','AXP']
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
    # endDateTime = datetime.datetime.now() + datetime.timedelta(days=0)
    # endDateTime = pd.to_datetime('2024-11-20 21:00:00-05:00')
    for sym in syms:
        contract_ = Stock(sym, 'SMART', 'USD')
        temp: ContractDetails = ib.reqContractDetails(contract_)
        if len(temp) == 0:
            logger.error(f"Contract details not found for {sym}")
            continue
        elif len(temp) > 1:
            logger.info(f"Multiple contract details found for {contract_}")
            continue
            # contract_ = temp[0].contract
        else:
            logger.info(f"Contract details {temp[0].contract}")
            contract_ = temp[0].contract
        if args.dryrun:
            continue
        head = ib.reqHeadTimeStamp(contract_, whatToShow='TRADES', useRTH=True)
        logger.info(f"Head timestamp: {head}")
        logger.info(f"Requesting daily historical bars for {sym}... ending {endDateTime}")
        histbars = ib.reqHistoricalData( # this method is blocking
            contract_,
            endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
            durationStr='1 D',
            barSizeSetting='1 day',
            whatToShow='TRADES',
            useRTH=True,
            formatDate=1,
        )
        if histbars is None or len(histbars) == 0:
            logger.error(f"Failed to get historical bars for {sym}")
        else:
            histdf = util.df(histbars)
            if 'open_' in histdf.columns: # rename open_ to open
                histdf.rename(columns={'open_':'open'}, inplace=True)
            if 'timestamp' in histdf.columns: # drop it
                histdf.drop(columns=['timestamp'], inplace=True)
            histdf['volume'] = histdf['volume'].astype(int)
            filename = pathlib.Path(f'./data/{sym}_1d.csv').resolve()
            file_exist = filename.exists()
            if file_exist:
                existing_histdf = pd.read_csv(filename, parse_dates=['date'])
                if True:
                # if pd.to_datetime(histdf.date.iloc[-1]) in existing_histdf.date.values:
                    logger.info(f"Updating {filename}")
                    # histdf = histdf[~histdf['date'].isin(existing_histdf['date'])]
                    existing_histdf = existing_histdf.set_index('date')
                    histdf = histdf.set_index('date')
                    combined_df = existing_histdf.combine_first(histdf).reset_index().drop_duplicates(keep='last')
                    logger.info(f"existing_histdf: {existing_histdf.shape}, histdf: {histdf.shape}, combined_df: {combined_df.shape}")
                    combined_df.to_csv(filename, index=False)
                # else:
                #     logger.info(f"Appending to {str(filename)}")
                #     histdf.to_csv(filename, mode='a', header=not file_exist, index=False)
            else:
                logger.info(f"Writing to {str(filename)}")
                histdf.to_csv(filename, index=False)
                # histdf.to_csv(f'./data/{sym}_1d.csv', mode='a', header=not file_exist, index=False)

        logger.info(f"Requesting 1m historical bars for {sym}...")
        histbars = ib.reqHistoricalData( # this method is blocking
            contract_,
            endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
            durationStr='1 D',
            barSizeSetting='1 min',
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1,
        )
        if histbars is None or len(histbars) == 0:
            logger.error(f"Failed to get historical bars for {sym}")
        else:
            histdf = util.df(histbars)
            if 'open_' in histdf.columns: # rename open_ to open
                histdf.rename(columns={'open_':'open'}, inplace=True)
            if 'timestamp' in histdf.columns: # drop it
                histdf.drop(columns=['timestamp'], inplace=True)
            filename = pathlib.Path(f'./data/{sym}_1m_{endDateTime:%Y%m%d}.csv').resolve()
            logger.info(f"Writing to {str(filename)}")
            histdf.to_csv(filename, index=False)

        logger.info(f"Requesting 5s historical bars for {sym}...")
        histbars = ib.reqHistoricalData( # this method is blocking
            contract_,
            endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
            durationStr='1 D',
            barSizeSetting='5 secs',
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1,
        )
        if histbars is None or len(histbars) == 0:
            logger.error(f"Failed to get historical bars for {sym}")
        else:
            histdf = util.df(histbars)
            if 'open_' in histdf.columns: # rename open_ to open
                histdf.rename(columns={'open_':'open'}, inplace=True)
            if 'timestamp' in histdf.columns: # drop it
                histdf.drop(columns=['timestamp'], inplace=True)
            filename = pathlib.Path(f'./data/{sym}_5s_{endDateTime:%Y%m%d}.csv').resolve()
            logger.info(f"Writing to {str(filename)}")
            histdf.to_csv(filename, index=False)

    logger.info("Done!")
    return # end of main

if __name__ == '__main__':
    main()