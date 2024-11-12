import datetime
import ctypes
import uuid
from ctypes import wintypes
import numpy as np

# Constants from the Windows API
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

def prevent_sleep() -> None:
    # Prevent Windows from sleeping
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)

def restore_sleep() -> None:
    # Restore the default behavior
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    print(parent_dir)

import ib_insync
from ib_insync import IB, Stock, util
ib_insync.ib.install_custom_repr_()

def onBarUpdate(bars, hasNewBar):
    print(bars[-1])

if __name__ == '__main__':
    host_1 = '127.0.0.1'
    # host_2 = '192.168.1.90'
    # port_1 = 7496
    port_2 = 7497
    # port_3 = 4002
    ib = IB()
    ib.connect(host_1, port_2, clientId=np.random.randint(100, 10000))
    # Prevent the computer from sleeping
    prevent_sleep()
    try:
        # Do something that takes a long time
        contract = Stock('SPY', 'SMART', 'USD')
        keepUpToDate = True
        bars = ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr='1 D',
            barSizeSetting='5 secs',
            whatToShow='TRADES',
            useRTH=False,
            keepUpToDate=keepUpToDate,
            formatDate=1)
        bars.updateEvent += onBarUpdate

        untilTime = datetime.datetime.now() + datetime.timedelta(minutes=3)
        while datetime.datetime.now() < untilTime:
            ib.sleep(5) # sleep for 5 seconds
    finally:
        # Restore the default behavior
        restore_sleep()
        ib.disconnect()