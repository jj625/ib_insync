'''
2002-2025: Use is subject to Interactive Brokers TWS API Non-Commercial License ("License") terms. 
This License is NOT for anybody who is developing software applications that they wish to: (a) sell to third 
party users for a fee, or (b) give to third party users to generate an indirect financial benefit (e.g., 
commissions). If You wish to make a software application for the purposes described in the preceding 
sentence then please contact Interactive Brokers
'''

from ibapi.client import *
from ibapi.common import TickerId
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.order_state import OrderState
from ibapi.wrapper import *
from decimal import Decimal


import threading
import time
port=7496

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.oid = 0

    def nextValidId(self, orderId: OrderId):
        self.oid = orderId

    def nextOid(self):
        self.oid += 1
        return self.oid


    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        print(f"openOrder. orderId: {orderId}, contract: {contract}, order: {order}, orderState: {orderState.status}, submitter: {order.submitter}") 

    def orderStatus(self, orderId: TickerId, status: str, filled: Decimal, remaining: Decimal, avgFillPrice: float, permId: TickerId, parentId: TickerId, lastFillPrice: float, clientId: TickerId, whyHeld: str, mktCapPrice: float):
        print(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)

    # def completedOrder(self, contract: Contract, order: Order, orderState: OrderState):
    #     print(f"CompletedOrder. submitter: {order.submitter}")

    def execDetails(self, reqId: int, contract: Contract, execution: Execution):
        print(f"reqId: {reqId}, contract: {contract}, execution: {execution}, submitter: {execution.submitter}")

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")
        
if __name__ == "__main__":
    c= Contract()
    c.symbol = "RSM"
    c.secType = "OPT"
    c.exchange = "FORECASTX"
    c.currency = "USD"
    c.lastTradeDateOrContractMonth = "202504"
    c.strike = -0.5
    c.right = "C"
    
    o = Order()
    o.action = "BUY"
    o.totalQuantity = 10
    o.orderType = "LMT"
    o.lmtPrice = 0.18
    o.orderId = 27

    app = TestApp()
    app.connect("127.0.0.1", port, 0)
    time.sleep(1)
    threading.Thread(target=app.run).start()
    time.sleep(1)

    app.placeOrder(o.orderId, c, o)

    time.sleep(3)
    # c.secType = "EC"
    o.lmtPrice = 0.20
    app.placeOrder(o.orderId, c, o)