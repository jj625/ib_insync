import datetime, traceback, logging, asyncio

# to import local code
# https://stackoverflow.com/questions/61058798/python-relative-import-in-jupyter-notebook
# https://stackoverflow.com/questions/34478398/import-local-function-from-a-module-housed-in-another-directory-with-relative-im

import os, sys
parent_dir = os.path.abspath('..')
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    parent_dir

import ib_insync
from ib_insync import IB, util, Trade, Fill, PortfolioItem, Position, ExecutionFilter, Execution

# util.logToConsole()
def apiStartEvent():
    print("API Start Event")

def apiEndEvent():
    print("API End Event")

def apiErrorEvent(errorMsg: str):
    print(f"API Error {errorMsg}")

def throttleStartEvent():
    print("Throttle Start Event")

def throttleEndEvent():
    print("Throttle End Event")

def onConnectedEvent():
    print("Connected Event")

def onDisconnectedEvent():
    print("Disconnected Event")

def onNewOrderEvent(trade: Trade):
    print(f"New Order Event {trade}")

def onOpenOrderEvent(trade: Trade):
    print(f"Open Order Event {trade}")

def onOrderStatusEvent(trade: Trade):
    print(f"Order Status Event {trade}")

def onExecDetailsEvent(trade: Trade, fill: Fill):
    print(f"Exec Details Event {trade} {fill}")

def onErrorEvent(reqId, errorCode, errorString, contract):
    print(f"Error Event {reqId} {errorCode} {errorString} {contract}")

def onTimeoutEvent(idlePeriod: float):
    print(f"Timeout Event {idlePeriod}")

def _repr_exec(exec_: Execution):
    return f"({exec_.execId} {exec_.time} {exec_.side})"

def _repr_exec_lst(execs: list[Execution]):
    return ', '.join([f"({exec_.execId} {exec_.time} {exec_.side})" for exec_ in execs]) if execs else []

def _execs_list2tuplst(execs: list[Execution]) -> list[tuple]:
    return [(exec_.execId, exec_.time, exec_.side) for exec_ in execs] if execs else []

async def show_fills(symbol):
    excFilt = ExecutionFilter(symbol=symbol)
    all_fills = await ib.reqExecutionsAsync(excFilt)
    all_execs = [fill.execution for fill in all_fills]
    print("all execs", _repr_exec_lst(all_execs))

    fills_lst = [t.fills for t in ib.trades() if t.contract.symbol == symbol]
    int_execs = [fill.execution for sublist in fills_lst for fill in sublist]
    print("internal execs", _repr_exec_lst(int_execs))

def onUpdatePortfolioEvent(pi: PortfolioItem):
    # print(f"Portfolio Update Event {pi}")
    pass

async def onPositionEvent(pos: Position):
    # print(f"Position Event {pos}")
    # await show_fills(pos.contract.symbol)
    symbol = pos.contract.symbol
    excFilt = ExecutionFilter(symbol=symbol)
    all_fills = await ib.reqExecutionsAsync(excFilt)
    all_execs = [fill.execution for fill in all_fills]
    # print("all execs", _repr_exec_lst(all_execs))

    fills_lst = [t.fills for t in ib.trades() if t.contract.symbol == symbol]
    int_execs = [fill.execution for sublist in fills_lst for fill in sublist]
    # print("internal execs", _repr_exec_lst(int_execs))

    ext_execs = set(_execs_list2tuplst(all_execs)) - set(_execs_list2tuplst(int_execs))
    # print(f"external execs {list(ext_execs)}")
    if ext_execs:
        # get the most recent external trade
        ext_execs_lst = list(ext_execs)
        # print(f"external execs {ext_execs_lst}")
        print(sorted(ext_execs_lst, key=lambda x: x[1], reverse=True)[0])

ib = IB()
port_2 = 7497
port_1 = 4002
ib.connect('127.0.0.1', port_2, clientId=13000)
print(ib.managedAccounts())
# util.logToConsole()

ib.newOrderEvent += onNewOrderEvent
ib.openOrderEvent += onOpenOrderEvent
ib.orderStatusEvent += onOrderStatusEvent
# ib.cancelOrderEvent += onCancelOrderEvent
ib.execDetailsEvent += onExecDetailsEvent
ib.updatePortfolioEvent += onUpdatePortfolioEvent
ib.positionEvent += onPositionEvent

# print(set(external_trades) - set(trades))
# print(ib.reqCompletedOrders(False))
# ib.run()
while True:
    ib.sleep(1)
ib.disconnect()
