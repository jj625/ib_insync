from contextlib import asynccontextmanager
import logging
import random
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)

import fastapi

import os, sys
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if parent_dir not in sys.path:
    # sys.path.append(parent_dir)
    sys.path.insert(0, parent_dir)
    # parent_dir
from ib_insync import IB, Stock, MarketOrder, Trade
from functools import partial

contract = Stock('SPY', 'SMART', 'USD')

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    # Startup code
    start_ib(ib_host='127.0.0.1', ib_port=7497)
    yield
    # Shutdown code
    ib.disconnect()

fastapp = fastapi.FastAPI(lifespan=lifespan)

@fastapp.get("/status")
async def get_status():
    return {"status": "order server is running"}

def generic_event_handler(event_name: str, *args, **kwargs):
    logger.info(f"Event: {event_name}, args: {args}, kwargs: {kwargs}")
def on_order_filled(trade: Trade):
    logger.info(f"Order filled: {trade}")

@fastapp.get("/")
async def read_root():
    return {"message": "Welcome to the Order Server"}

@fastapp.post("/buy")
async def buy_order(quantity: int):
    action = 'BUY'
    market_order = MarketOrder(action, quantity)
    trade: Trade = ib.placeOrder(contract, market_order)
    trade.filledEvent += partial(generic_event_handler, 'tradeFilledEvent')
    trade.filledEvent += on_order_filled
    return {"status": f"Submitted BUY order for {quantity} shares"}

@fastapp.post("/sell")
async def sell_order(quantity: int):
    action = 'SELL'
    market_order = MarketOrder(action, quantity)
    trade: Trade = ib.placeOrder(contract, market_order)
    trade.filledEvent += partial(generic_event_handler, 'tradeFilledEvent')
    trade.filledEvent += on_order_filled
    return {"status": f"Submitted SELL order for {quantity} shares"}

def start_ib(ib_host: str, ib_port: int):
    global ib
    host_1 = '127.0.0.1'
    host_2 = '192.168.1.90'
    port_1 = 7496
    port_2 = 7497
    port_3 = 4002
    port_ephemeral = random.randrange(49_152, 65_535)
    ib = IB()
    if not ib.isConnected():
        ib.connect(ib_host, ib_port, clientId=random.randrange(5_000, 10_000))
    if ib.client._serverVersion < 178:
        logger.error(f'TWS version {ib.client._serverVersion} is too old. Update to latest version.')
        ib.disconnect()
        sys.exit(1)
    accounts = ib.managedAccounts()
    logger.info(f"account {accounts}")
    assert len(accounts) == 2

def on_button_b_clicked(b):
    # Submit market order
    action = 'BUY'
    market_order = MarketOrder(action, quantity)
    # ib.orderStatusEvent += on_order_status
    trade: Trade = ib.placeOrder(contract, market_order)
    # trade.statusEvent += partial(generic_event_handler, 'tradeStatusEvent')
    # trade.fillEvent += partial(generic_event_handler, 'tradeFillEvent')
    trade.filledEvent += partial(generic_event_handler, 'tradeFilledEvent')
    trade.filledEvent += on_order_filled

def on_button_c_clicked(b):
    # Submit market order
    action = 'SELL'
    market_order = MarketOrder(action, quantity)
    # ib.orderStatusEvent += on_order_status
    trade: Trade = ib.placeOrder(contract, market_order)
    # trade.statusEvent += partial(generic_event_handler, 'tradeStatusEvent')
    # trade.fillEvent += partial(generic_event_handler, 'tradeFillEvent')
    trade.filledEvent += partial(generic_event_handler, 'tradeFilledEvent')
    trade.filledEvent += on_order_filled
