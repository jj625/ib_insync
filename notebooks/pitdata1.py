# gather point-in-time data and save to database
# from functools import partial
import datetime
import asyncio
import zoneinfo
tz_NY = zoneinfo.ZoneInfo('America/New_York')
import argparse
import logging
logger = None # global
# import pandas as pd
import numpy as np
import re
import pathlib
import json
# import tqdm
# import scipy.stats as stats

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
from ib_insync import Stock, Future, IB, util, ContractDetails, Contract, BarDataList, BarData

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

def last_business_dt() -> datetime.datetime:
    """Return the last business date"""
    today = datetime.datetime.now().date()
    if today.weekday() == 0: # Monday
        return today + datetime.timedelta(days=-3)
    else:
        return today + datetime.timedelta(days=-1)

class PitLogger():
    def __init__(self, ib: IB, contract: Contract, durationStr, barSizeSetting, logfilename):
        self.ib = ib

        self.contract = contract
        self.durationStr = durationStr
        self.barSizeSetting = barSizeSetting

        self.logfile = open(logfilename, 'a')
        self.logfile.write("date,open,high,low,close,average,volume,barCount,hasNewBar,timestamp\n")
        self.logfile.flush()

        self.future = asyncio.ensure_future(self.ib.reqHistoricalDataAsync(
            self.contract,
            endDateTime='', # endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
            durationStr=self.durationStr,
            barSizeSetting=self.barSizeSetting,
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1,
            keepUpToDate=True)
        )
        # self.bars.updateEvent += self.onBarUpdate

    async def onBarUpdate(self, bars, hasNewBar):
        last_bar: BarData = bars[-1]
        self.logfile.write(f"{last_bar.date},{last_bar.open},{last_bar.high},{last_bar.low},{last_bar.close}"
            f",{last_bar.average},{last_bar.volume:n},{last_bar.barCount:n},{hasNewBar},{last_bar.timestamp}\n")
        self.logfile.flush()
        # logger.info(f"{last_bar.timestamp},{last_bar.date},{last_bar.open},{last_bar.high},{last_bar.low},{last_bar.close},{last_bar.volume:n},{last_bar.barCount:n}")

    def run(self):
        self.loop = asyncio.get_event_loop()
        self.loop.run_until_complete(self.future)
        self.bars = self.future.result()
        self.bars.updateEvent += self.onBarUpdate
        # self.future.add_done_callback(self.onBarUpdate)

# def download_bars(contract_: Contract, ib: IB, durationStr, barSizeSetting, endDateTime: datetime.datetime, **kwargs):
#     sym = contract_.symbol
#     logger.info(f"Requesting '{durationStr}' '{barSizeSetting}' historical bars for {sym}...")
#     histbars: BarDataList = ib.reqHistoricalData( # this method is blocking
#         contract_,
#         endDateTime='', # endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
#         durationStr=durationStr,
#         barSizeSetting=barSizeSetting,
#         whatToShow='TRADES',
#         useRTH=False,
#         formatDate=1,
#     )
#     if histbars is None or len(histbars) == 0:
#         logger.error(f"Failed to get historical bars for {sym}")
#     else:
#         # histdf = util.df(histbars)
#         # if 'open_' in histdf.columns: # rename open_ to open
#         #     histdf.rename(columns={'open_':'open'}, inplace=True)
#         # if 'timestamp' in histdf.columns: # drop it
#         #     histdf.drop(columns=['timestamp'], inplace=True)
#         barSizeSetting_ = barSizeSetting.replace(' ','')[:2]
#         filename = pathlib.Path(f'./data/{sym}_pit_{barSizeSetting_}_{endDateTime:%Y%m%d}.csv').resolve()
#         # logger.info(f"Writing to {str(filename)}")
#         # histdf.to_csv(filename, index=False)
#     return histbars

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
    argparser.add_argument('--loglevel', type=str, help='Logging level')
    argparser.add_argument('--dryrun', action='store_true', help='Dry run, don\'t actually download data')
    argparser.add_argument('--date', type=str, help='Date to download data for')
    argparser.add_argument('--contract_type', type=str, default='STK', help='Contract type (FUT, STK, CASH)')
    argparser.add_argument('--expiry', type=str, help='Contract expiry YYYYMM (for futures)')
    argparser.add_argument('--exchange', type=str, help='Contract exchange')
    # argparser.add_argument('--live_trading', action='store_true', help='Live trading')
    args = argparser.parse_args()
    if args.loglevel and args.loglevel.upper() not in ['INFO']:
        logger.setLevel(args.loglevel.upper())
    logger.info(args)
    
    wlogger = logging.getLogger('ib_insync.wrapper')
    wlogger.addFilter(LoggerFilter('ib_insync.wrapper', 
        r'^(connectAck|nextValidId|accountDownloadEnd|execDetailsEnd|updateAccountTime|accountUpdateMulti|execDetails|headTimestamp'
        r'|updateAccountValue|position|updatePortfolio|commissionReport|historicalData|Info 2104|Info 2106|Info 2158)'
    ))

    # Connect to IB Gateway
    ib = IB()
    ib.connect(args.host, args.port, clientId=args.clientid or np.random.randint(1_000, 10_000))

    if args.symbols is None or len(args.symbols) == 0:
        syms = args.symbols or ['SPY']
    else:
        syms = args.symbols
    # dayoffset: int = 0

    # if args.date:
    #     endDateTime = pd.to_datetime(args.date)
    # else:       
    #     if datetime.datetime.now().time() < datetime.time(9, 30):
    #         dayoffset = -1
    #     else:
    #         dayoffset = 0
    #     endDateTime = datetime.datetime.combine(datetime.datetime.now().date() + datetime.timedelta(days=dayoffset), datetime.time(21, 0), tzinfo=tz_NY)
    # endDateTime = datetime.datetime.now() + datetime.timedelta(days=0)
    # endDateTime = pd.to_datetime('2024-11-20 21:00:00-05:00')
    for sym in syms:
        # contract_ = Stock(sym, 'SMART', 'USD')
        contract_ = Future('GC', '202504', 'COMEX')
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

        dtnow = datetime.datetime.now(tz_NY)
        pl1m = PitLogger(ib, contract_, '1 D', '1 min', f'./data/{sym}_pit_1m_{dtnow:%Y%m%d_%H%M}.csv')
        pl1m.run()
        pl15s = PitLogger(ib, contract_, '1 D', '15 secs', f'./data/{sym}_pit_15s_{dtnow:%Y%m%d_%H%M}.csv')
        pl15s.run()

        ib.sleep(60)

        # head = ib.reqHeadTimeStamp(contract_, whatToShow='TRADES', useRTH=True)
        # logger.info(f"Head timestamp: {head}")
        # logger.info(f"Requesting daily historical bars for {sym}... ending {endDateTime}")
        # histbars = ib.reqHistoricalData( # this method is blocking
        #     contract_,
        #     endDateTime=endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
        #     durationStr='1 D',
        #     barSizeSetting='1 day',
        #     whatToShow='TRADES',
        #     useRTH=True,
        #     formatDate=1,
        # )
        # if histbars is None or len(histbars) == 0:
        #     logger.error(f"Failed to get historical bars for {sym}")
        # else:
        #     histdf = util.df(histbars)
        #     if 'open_' in histdf.columns: # rename open_ to open
        #         histdf.rename(columns={'open_':'open'}, inplace=True)
        #     if 'timestamp' in histdf.columns: # drop it
        #         histdf.drop(columns=['timestamp'], inplace=True)
        #     histdf['volume'] = histdf['volume'].astype(int)
        #     filename = pathlib.Path(f'./data/{sym}_1d.csv').resolve()
        #     file_exist = filename.exists()
        #     if file_exist:
        #         existing_histdf = pd.read_csv(filename, parse_dates=['date'])
        #         if True:
        #         # if pd.to_datetime(histdf.date.iloc[-1]) in existing_histdf.date.values:
        #             logger.info(f"Updating {filename}")
        #             # histdf = histdf[~histdf['date'].isin(existing_histdf['date'])]
        #             existing_histdf = existing_histdf.set_index('date')
        #             histdf = histdf.set_index('date')
        #             combined_df = existing_histdf.combine_first(histdf).reset_index().drop_duplicates(keep='last')
        #             logger.info(f"existing_histdf: {existing_histdf.shape}, histdf: {histdf.shape}, combined_df: {combined_df.shape}")
        #             if not combined_df.equals(existing_histdf.reset_index()):
        #                 logger.info("Data has been updated.")
        #                 combined_df.to_csv(filename, index=False)
        #             else:
        #                 logger.info("No changes detected in the data.")
        #         # else:
        #         #     logger.info(f"Appending to {str(filename)}")
        #         #     histdf.to_csv(filename, mode='a', header=not file_exist, index=False)
        #     else:
        #         logger.info(f"Writing to {str(filename)}")
        #         histdf.to_csv(filename, index=False)
        #         # histdf.to_csv(f'./data/{sym}_1d.csv', mode='a', header=not file_exist, index=False)

        # bars1m = download_bars(contract_, ib, '1 D', '1 min', endDateTime)
        # bars15s = download_bars(contract_, ib, '1 D', '15 secs', endDateTime)

    logger.info("Done!")
    return # end of main

if __name__ == '__main__':
    main()