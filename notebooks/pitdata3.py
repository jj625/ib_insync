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
from ib_insync.util import waitUntilAsync

from gizmo import LoggerFilter

def last_business_dt() -> datetime.datetime:
    """Return the last business date"""
    today = datetime.datetime.now().date()
    if today.weekday() == 0: # Monday
        return today + datetime.timedelta(days=-3)
    else:
        return today + datetime.timedelta(days=-1)

class IBInstrument():
    logger = logging.getLogger(__name__)
    def __init__(self, ib: IB, contract: Contract):
        self.ib = ib
        self.contract = contract

    async def get_contract_details(self):
        temp: list[ContractDetails] = self.ib.reqContractDetails(self.contract)
        if len(temp) == 0:
            logger.error(f"Contract details not found for {sym}")
            # continue
        elif len(temp) > 1:
            logger.info(f"Multiple contract details found for {contract_}")
            # continue
            # contract_ = temp[0].contract
        else:
            cdl: ContractDetails = temp[0]
            contract_ = cdl.contract
            logger.info(f"Contract details {cdl}")

    async def get_historical_data(self, durationStr, barSizeSetting):
        bars = await self.ib.reqHistoricalDataAsync(
            self.contract,
            endDateTime='', # endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
            durationStr=durationStr,
            barSizeSetting=barSizeSetting,
            whatToShow='TRADES',
            useRTH=False,
            formatDate=1,
            keepUpToDate=True)
        return bars
    
class PitLogger():
    """
    Log pit (point-in-time) data to a file
    """
    def __init__(self, ib: IB, contract: Contract, durationStr, barSizeSetting, logfilename, useRTH=False, keepUpToDate=True):
        self.ib = ib

        self.contract = contract
        self.durationStr = durationStr
        self.barSizeSetting = barSizeSetting
        self.useRTH = useRTH
        self.keepUpToDate = keepUpToDate

        self.logfile = open(logfilename, 'a')
        self.logfile.write("date,open,high,low,close,average,volume,barCount,hasNewBar,timestamp\n")
        self.logfile.flush()

        # # self.ib.waitUntil(datetime.time(17, 59, 57, tzinfo=tz_NY))
        # self.future = asyncio.ensure_future(self.ib.reqHistoricalDataAsync(
        #     self.contract,
        #     endDateTime='', # endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
        #     durationStr=self.durationStr,
        #     barSizeSetting=self.barSizeSetting,
        #     whatToShow='TRADES',
        #     useRTH=False,
        #     formatDate=1,
        #     keepUpToDate=True)
        # )
        # # self.bars.updateEvent += self.onBarUpdate

    async def onBarUpdate(self, bars, hasNewBar):
        # only log the live updates
        last_bar: BarData = bars[-1]
        self.logfile.write(f"{last_bar.date.astimezone(tz=None)},{last_bar.open},{last_bar.high},{last_bar.low},{last_bar.close}"
            f",{last_bar.average},{last_bar.volume:n},{last_bar.barCount:n},{hasNewBar},{last_bar.timestamp.astimezone(tz=None)}\n")
        self.logfile.flush()
        # logger.info(f"{last_bar.timestamp},{last_bar.date},{last_bar.open},{last_bar.high},{last_bar.low},{last_bar.close},{last_bar.volume:n},{last_bar.barCount:n}")

    async def run(self, startTime: datetime.datetime):
        dtnow = datetime.datetime.now(tz_NY)
        if dtnow < startTime:
            logger.info(f"Waiting until {startTime}")
            delay_secs = (startTime - dtnow).total_seconds()
            await asyncio.sleep(delay_secs)

        self.bars = await self.ib.reqHistoricalDataAsync(
            self.contract,
            endDateTime='', # endDateTime.strftime(r'%Y%m%d 21:00:00 US/Eastern'),
            durationStr=self.durationStr,
            barSizeSetting=self.barSizeSetting,
            whatToShow='TRADES',
            useRTH=self.useRTH,
            formatDate=1,
            keepUpToDate=self.keepUpToDate) 
        if self.keepUpToDate:
            self.bars.updateEvent += self.onBarUpdate
        else:
            logger.info(f"bars={len(self.bars)}")
            for bar in self.bars:
                self.logfile.write(f"{bar.date.astimezone(tz=None)},{bar.open},{bar.high},{bar.low},{bar.close}"
                    f",{bar.average},{bar.volume:n},{bar.barCount:n},{bar.hasNewBar},{bar.timestamp.astimezone(tz=None)}\n")
                self.logfile.flush()
            logger.info(f"Finished writing {self.logfile.name}")
            self.logfile.close()
        return

def onErrorEvent(reqId, errorCode, errorString, contract):
    # https://interactivebrokers.github.io/tws-api/message_codes.html#system_codes
    if errorCode in [2104, 2106, 2107, 2108, 2158]: # not a real error
        return
    # if errorCode == 202:
    #     # https://interactivebrokers.github.io/tws-api/automated_considerations.html#order_placement
    #     logger.error("order is subject to price check, too far from current price?")
    # logger.info(get_asyncio_running_loop(''))
    logtext = f"reqId={reqId}, errorCode={errorCode}, errorString={errorString}, contract={contract}"
    logger.error(logtext)
    # loop = asyncio.get_running_loop()
    # task = loop.create_task(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    # background_tasks.add(task)
    # task.add_done_callback(background_tasks.discard)
    # future = asyncio.ensure_future(telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=logtext))
    # asyncio.run(future)
    return

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
    ib.errorEvent += onErrorEvent

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
        _idx = 0
        if cdl.tradingSessions()[_idx].end < dtnow:
            _idx += 1
        startTime = cdl.tradingSessions()[_idx].start
        pl5s = PitLogger(ib, contract_, '2 D', '5 secs', f'./data/{sym}_pit_5s_{dtnow:%Y%m%d_%H%M}.csv', useRTH=True, keepUpToDate=False)
        # pl1m = PitLogger(ib, contract_, '1 D', '1 min', f'./data/{sym}_pit_1m_{dtnow:%Y%m%d_%H%M}.csv')
        # # pl1m.run(startTime)
        # pl15s = PitLogger(ib, contract_, '1 D', '15 secs', f'./data/{sym}_pit_15s_{dtnow:%Y%m%d_%H%M}.csv')
        # # pl15s.run(startTime)
        # pl5m = PitLogger(ib, contract_, '1 D', '5 mins', f'./data/{sym}_pit_5m_{dtnow:%Y%m%d_%H%M}.csv')
        # # pl5m.run(startTime)
        # pl30m = PitLogger(ib, contract_, '1 D', '30 mins', f'./data/{sym}_pit_30m_{dtnow:%Y%m%d_%H%M}.csv')
        # pl30m.run(startTime)
        # pl1d = PitLogger(ib, contract_, '1 D', '1 day', f'./data/{sym}_pit_1d_{dtnow:%Y%m%d_%H%M}.csv')
        # pl1d.run()
        results = asyncio.gather(
            pl5s.run(startTime),
            # pl1m.run(startTime),
            # pl15s.run(startTime),
            # pl5m.run(startTime),
            # pl30m.run(startTime),
            return_exceptions=True
        )
        # logger.info(f"{type(results)}")
        # done_tasks, pending_tasks = asyncio.wait(pl1m.run(startTime),
        #     pl15s.run(startTime),
        #     pl5m.run(startTime),
        #     pl30m.run(startTime))

        # for i, result in enumerate(results):
        #     done = result.done()
        #     logger.info(f"{i}: {done}")
        #     if isinstance(result, Exception):
        #         logger.error(f"{i}: {result}")
        #     elif done:
        #         logger.info(f"{i}: {result.result()}")

        # wait until results are done
        logger.info(f"Waiting for results to finish")
        for result in results:
            if not result.done():
                logger.info(f"Waiting for {result}")
            else:
                logger.info(f"{result} is done")
        logger.info(f"Waiting for {len(results)} results")

        # untilTime = cdl.tradingSessions()[_idx].end + datetime.timedelta(minutes=1, days=0)
        # logger.info(f"running until {untilTime.astimezone()}")
        # ib.waitUntil(untilTime)
        for i, result in enumerate(results):
            logger.info(f"{i}: {result.done()}")
    ib.disconnect()
    logger.info("Done!")
    return # end of main

if __name__ == '__main__':
    gizmo.prevent_sleep()

    # Set up logging
    FMT=r'%(asctime)s:%(levelname)s:%(name)s:%(message)s' # :%(funcName)s
    logging.basicConfig(level=logging.INFO, format=FMT)
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
