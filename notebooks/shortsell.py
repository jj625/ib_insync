import datetime, traceback, logging, re

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    parent_dir

import ib_insync.ib
ib_insync.ib.install_custom_repr_()

# import pytz
# local_tz = pytz.timezone('US/Eastern')  # Adjust for your local timezone, America/New_York

from ib_insync import *

class LoggerNameFilter(logging.Filter):
    def __init__(self, logger_name, pattern=r'.*'):
        super().__init__()
        self.logger_name = logger_name
        self.pattern = re.compile(pattern)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not (record.name == self.logger_name and \
            self.pattern.search(msg)
        )

logging.basicConfig(level=logging.DEBUG
    , format='%(asctime)s %(name)s %(levelname)s %(funcName)s %(message)s'
)
formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(funcName)s %(message)s')

file_handler = logging.FileHandler(f'shortsell_{datetime.datetime.now():%Y%m%d_%H%M}.log')
# file_handler.setLevel(args.loglevel)
file_handler.setFormatter(formatter)

# add handlers to logger
logger = logging.getLogger()
# logger.addHandler(console_handler)
logger.addHandler(file_handler)

wlogger = logging.getLogger('ib_insync.wrapper')
wlogger.setLevel(logging.DEBUG)
wlogger.addFilter(LoggerNameFilter('ib_insync.wrapper', r'^(updateAccountTime|accountUpdateMulti|updateAccountValue|position|updatePortfolio|commissionReport)'))

clogger = logging.getLogger('ib_insync.client')
clogger.setLevel(logging.DEBUG)

ib = IB()

util.logToConsole()
# def apiStartEvent():
#     print("API Start Event")

# def apiEndEvent():
#     print("API End Event")

# def apiErrorEvent(errorMsg: str):
#     print(f"API Error {errorMsg}")

# def throttleStartEvent():
#     print("Throttle Start Event")

# def throttleEndEvent():
#     print("Throttle End Event")

# def onConnectedEvent():
#     print("Connected Event")

# def onDisconnectedEvent():
#     print("Disconnected Event")

# def onNewOrderEvent(trade: Trade):
#     print(f"New Order Event {trade}")

# def onOpenOrderEvent(trade: Trade):
#     print(f"Open Order Event {trade}")

# def onOrderStatusEvent(trade: Trade):
#     print(f"Order Status Event {trade}")

# def onExecDetailsEvent(trade: Trade, fill: Fill):
#     print(f"Exec Details Event __repr__orig\n{fill.__repr__orig}")
#     print(f"Exec Details Event __repr__\n{trade} {fill}")

# def onErrorEvent(reqId, errorCode, errorString, contract):
#     print(f"Error Event {reqId} {errorCode} {errorString} {contract}")

# def onTimeoutEvent(idlePeriod: float):
#     print(f"Timeout Event {idlePeriod}")

# ib.connectedEvent += print # onConnectedEvent
# ib.disconnectedEvent += print # onDisconnectedEvent
# ib.newOrderEvent += print # onNewOrderEvent
# ib.openOrderEvent += print # onOpenOrderEvent
# ib.orderStatusEvent += print # onOrderStatusEvent
ib.execDetailsEvent += print # onExecDetailsEvent
# ib.errorEvent += print # onErrorEvent
# ib.timeoutEvent += print # onTimeoutEvent

# ib.client.apiStart.connect(apiStartEvent)
# ib.client.apiEnd.connect(apiEndEvent)
# ib.client.apiError.connect(apiErrorEvent)
# ib.client.throttleStart.connect(throttleStartEvent)
# ib.client.throttleEnd.connect(throttleEndEvent)

# ib = IB()
port_2 = 7497
port_1 = 4002
ib.connect('127.0.0.1', port_2, clientId=13)
# util.logToConsole()

# exchange = 'OVERNIGHT'
exchange = 'SMART'
primaryExchange = 'ARCA'
contract = Stock('PFE', exchange, 'USD')
discretionaryAmt = 1.0
buysell = 'SELL'
# mktOrder = MarketOrder(buysell, 100, outsideRth=True)
mktOrder = MarketOrder(buysell, 100)
lmtOrder = LimitOrder(buysell, 100, 570.02, discretionaryAmt=discretionaryAmt)

util.logToConsole(logging.DEBUG)

trade = ib.placeOrder(contract, mktOrder)

while trade in ib.openTrades():
    ib.sleep(1)

ib.sleep(1)
ib.disconnect()

