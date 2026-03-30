import asyncio
import ibapi
import ib_insync
from ib_insync import *
import pandas as pd
import logging
import datetime
import argparse

# globals
ib = None


print(f"TWS API version: {ibapi.__version__}, ib_insync version: {ib_insync.__version__}")

def onBarUpdate(bars, hasNewBar):
    print(hasNewBar, bars[-1])

if __name__ == "__main__":
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Request real-time bars from IB')
    parser.add_argument('--run_until', type=str, help='Run until this time (HH:MM:SS)')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO) # must come before any logging calls
    logging.info("Script is starting...")
    ib = IB()
    # util.logToConsole(logging.DEBUG) # show network traffic
    ib.connect('127.0.0.1', 7496, clientId=8) # IB Gateway 4001, TWS 7496

    contract_1 = Stock('NVDA', 'SMART', 'USD')
    bars_1 = ib.reqHistoricalData(
        contract_1,
        endDateTime='',
        durationStr='1 D', # 900 S
        barSizeSetting='5 secs',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1,
        keepUpToDate=True)
    # bars_1.updateEvent += onBarUpdate

    contract_2 = Stock('META', 'SMART', 'USD')
    bars_2 = ib.reqHistoricalData(
        contract_2,
        endDateTime='',
        durationStr='1 D', # 900 S
        barSizeSetting='5 secs',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1,
        keepUpToDate=True)
    # bars_2.updateEvent += onBarUpdate

    contract_3 = Stock('IWM', 'SMART', 'USD')
    bars_3 = ib.reqHistoricalData(
        contract_3,
        endDateTime='',
        durationStr='1 D', # 900 S
        barSizeSetting='5 secs',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1,
        keepUpToDate=True)
    # bars_3.updateEvent += onBarUpdate

    # ib.sleep(60) # sleep for 60 seconds
    ib.waitUntil(datetime.time(16,2,0)) # wait until 4:05 PM
    
    # dump the bars to a file
    filesuffix = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    df = util.df(bars_1)
    df.to_csv(f'NVDA_{filesuffix}_H.csv')

    df = util.df(bars_2)
    df.to_csv(f'META_{filesuffix}_H.csv')

    df = util.df(bars_3)
    df.to_csv(f'IWM_{filesuffix}_H.csv')

    ib.cancelHistoricalData(bars_1)
    ib.cancelHistoricalData(bars_2)
    ib.cancelHistoricalData(bars_3)

    logging.info("Script has finished.")
