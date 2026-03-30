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
from ibapi.tag_value import TagValue

port = 7496

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):

        mycontract = Contract()
        # mycontract.symbol = "AAPL"
        # mycontract.secType = "STK"
        # mycontract.currency = "USD"
        mycontract.conId = 533620665
        mycontract.exchange = "QBALGO"
        # mycontract.primaryExchange = "ISLAND"
        
        baseOrder = Order()
        baseOrder.action = "BUY"
        baseOrder.totalQuantity = 10
        baseOrder.orderType = "MKT"
        # baseOrder.lmtPrice = 180
        baseOrder.outsideRth = True

        baseOrder.algoStrategy = "Octane"
        baseOrder.algoParams = []
        baseOrder.algoParams.append(TagValue("StartTime", "13:00:00 America/Chicago"))
        baseOrder.algoParams.append(TagValue("EndTime", "15:00:00 America/Chicago"))
        baseOrder.algoParams.append(TagValue("Duration", "-99"))
        baseOrder.algoParams.append(TagValue("Urgency", "High"))

        self.placeOrder(orderId, mycontract, baseOrder)

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
