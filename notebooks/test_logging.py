import asyncio
import ibapi
#from .. import ib_insync
from ..ib_insync import *
import pandas as pd
import logging
import datetime
import argparse

ib = IB()
util.logToConsole(logging.INFO)
ib.connect('127.0.0.1', 7496, clientId=15)

ib.sleep(60)

ib.disconnect()
