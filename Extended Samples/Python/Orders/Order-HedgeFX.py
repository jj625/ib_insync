'''
2002-2025: Use is subject to Interactive Brokers TWS API Non-Commercial License ("License") terms. 
This License is NOT for anybody who is developing software applications that they wish to: (a) sell to third 
party users for a fee, or (b) give to third party users to generate an indirect financial benefit (e.g., 
commissions). If You wish to make a software application for the purposes described in the preceding 
sentence then please contact Interactive Brokers
'''

from ibapi.client import *
from ibapi.wrapper import *
from decimal import Decimal
import time


port = 7496


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):
        # Stock Hedge
        parent = Contract()
        parent.conId = 272093 # AAPL STK
        parent.exchange = "SMART"

        # FX Pair
        hedgeChild = Contract()
        hedgeChild.conId = 12087820 # USD.CHF fx pair
        hedgeChild.exchange = "IDEALPRO"

        ###################################### Parent Order ###################################################
        parentOrder = Order()
        parentOrder.account = "DU5240685"
        parentOrder.orderId = orderId
        parentOrder.action = "BUY"
        parentOrder.orderType = "LMT"
        parentOrder.lmtPrice = 100
        parentOrder.tif = "GTC"
        parentOrder.totalQuantity = 1
        parentOrder.transmit = False

        self.placeOrder(parentOrder.orderId, parent, parentOrder)
        time.sleep(1)
        ###################################### Hedged Child Order ###################################################
        hedgeChildOrder = Order()
        hedgeChildOrder.account = "DU5240685"
        hedgeChildOrder.parentId = parentOrder.orderId
        hedgeChildOrder.orderId = parentOrder.orderId + 1
        hedgeChildOrder.action = "SELL"
        hedgeChildOrder.orderType = "MKT"
        hedgeChildOrder.hedgeType = "F"
        hedgeChildOrder.totalQuantity = 0
        # hedgeChildOrder.dontUseAutoPriceForHedge = False
        hedgeChildOrder.transmit = True

        self.placeOrder(hedgeChildOrder.orderId, hedgeChild, hedgeChildOrder)

    def openOrder(self, orderId: OrderId, contract: Contract, order: Order, orderState: OrderState):
        print(f"openOrder. orderId: {orderId}, contract: {contract}, order: {order}, orderState: {orderState.status}, submitter: {order.submitter}") 

    def orderStatus(self, orderId: TickerId, status: str, filled: Decimal, remaining: Decimal, avgFillPrice: float, permId: TickerId, parentId: TickerId, lastFillPrice: float, clientId: TickerId, whyHeld: str, mktCapPrice: float):
        print(orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld, mktCapPrice)

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")
            
app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
