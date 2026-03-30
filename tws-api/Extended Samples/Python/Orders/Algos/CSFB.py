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
        contract = Contract()
        contract.symbol = "AAPL"
        contract.secType = "STK"
        contract.exchange = "CSFBALGO"
        contract.currency = "USD"


        myorder = Order()
        myorder.orderId = orderId
        myorder.action = "BUY"
        myorder.orderType = "MKT"
        # myorder.lmtPrice = 167.00
        myorder.totalQuantity = 1
        myorder.tif = "GTC"
        # myorder.whatIf = True

        # must be direct-routed to "CSFBALGO"
        myorder.algoStrategy = "GUERRILLA"
        myorder.algoParams = []
        myorder.algoParams.append(TagValue("StartTime", "12:30:00 US/Eastern"))
        myorder.algoParams.append(TagValue("EndTime", "16:00:00 US/Eastern"))
        myorder.algoParams.append(TagValue("ExecStyle", "Normal"))
        myorder.algoParams.append(TagValue("MinPercent", 10))
        myorder.algoParams.append(TagValue("MaxPercent", 20))
        myorder.algoParams.append(TagValue("DisplaySize", 100))
        # myorder.algoParams.append(TagValue("Auction", "Default"))
        myorder.algoParams.append(TagValue("BlockFinder", 0))
        myorder.algoParams.append(TagValue("BlockPrice", "388"))
        myorder.algoParams.append(TagValue("MinBlockSize", "150"))
        myorder.algoParams.append(TagValue("MaxBlockSize", "180"))
        myorder.algoParams.append(TagValue("IWouldPrice", "170"))
        
        self.placeOrder(myorder.orderId, contract, myorder)

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

