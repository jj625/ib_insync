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
import inspect
# import tqdm
# import scipy.stats as stats

import gizmo

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
print(inspect.getfile(ib_insync))
from ib_insync import Stock, Future, IB, util, ContractDetails, Contract, BarDataList, BarData

from gizmo import LoggerFilter

def last_business_dt() -> datetime.datetime:
    """Return the last business date"""
    today = datetime.datetime.now().date()
    if today.weekday() == 0: # Monday
        return today + datetime.timedelta(days=-3)
    else:
        return today + datetime.timedelta(days=-1)

class PitLogger():
    """
    Log pit (point-in-time) data to a file
    """
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
        # only log the live updates
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
def main():

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

    # args check
    contract_type = args.contract_type
    exchange = args.exchange or ''
    expiry = args.expiry or ''

    if args.contract_type == 'FUT':
        all_good = True
        if not args.expiry:
            logger.error(f"Future contract must specify '--expiry'")
            all_good = False
        if not args.exchange:
            logger.error(f"Future contract must specify '--exchange'")
            all_good = False
        if not all_good:
            return -1
    elif args.contract_type == 'STK':
        pass
    elif args.contract_type == 'FUND':
        pass

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
        match contract_type:
            case 'FUT':
                contract_ = Future(sym, expiry, exchange)
                # contract_ = Future('GC', '202504', 'COMEX')
            case 'STK':
                if exchange == '':
                    exchange = 'SMART'
                contract_ = Stock(sym, exchange, 'USD')
        temp: list[ContractDetails] = ib.reqContractDetails(contract_)
        if len(temp) == 0:
            logger.error(f"Contract details not found for {sym}")
            continue
        elif len(temp) > 1:
            logger.info(f"Multiple contract details found for {contract_}")
            continue
            # contract_ = temp[0].contract
        else:
            cdl: ContractDetails = temp[0]
            contract_ = cdl.contract
            logger.info(f"Contract details {cdl}")

        dtnow = datetime.datetime.now(tz_NY)
        pl1m = PitLogger(ib, contract_, '1 D', '1 min', f'./data/{sym}_pit_1m_{dtnow:%Y%m%d_%H%M}.csv')
        pl1m.run()
        pl15s = PitLogger(ib, contract_, '1 D', '15 secs', f'./data/{sym}_pit_15s_{dtnow:%Y%m%d_%H%M}.csv')
        pl15s.run()
        pl5m = PitLogger(ib, contract_, '1 D', '5 mins', f'./data/{sym}_pit_5m_{dtnow:%Y%m%d_%H%M}.csv')
        pl5m.run()
        pl30m = PitLogger(ib, contract_, '1 D', '30 mins', f'./data/{sym}_pit_30m_{dtnow:%Y%m%d_%H%M}.csv')
        pl30m.run()
        # pl1d = PitLogger(ib, contract_, '1 D', '1 day', f'./data/{sym}_pit_1d_{dtnow:%Y%m%d_%H%M}.csv')
        # pl1d.run()
        untilTime = cdl.tradingSessions()[0].end+datetime.timedelta(minutes=1)
        logger.info(f"running until {untilTime}")
        ib.waitUntil(untilTime)

    logger.info("Done!")
    return # end of main

if __name__ == '__main__':
    gizmo.prevent_sleep()

    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    logger.info("Starting main loop")
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Caught KeyboardInterrupt, exiting...")
    except Exception as e:
        logger.exception(f"Caught exception {e}", exc_info=True, stack_info=True)
    finally:
        # if ib is not None:
        #     logger.info(f"{ib}")
        #     ib.disconnect()
        #     logger.info("IB disconnected")
        if logger is not None:
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    handler.close()
                    logger.removeHandler(handler)
                    logger.info(f"{handler} closed")
        
        logger.info("End of main loop")
        gizmo.restore_sleep()
