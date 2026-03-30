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
from datetime import datetime
port = 7496


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):

        mycontract = Contract()
        mycontract.conId = 265598
        mycontract.exchange = "SMART"

        self.reqTickByTickData(orderId, mycontract, "AllLast", 50, 0)

    # whatToShow=BidAsk
    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float, askPrice: float, bidSize: int, askSize: int, tickAttribBidAsk: TickAttribBidAsk):
        print(f"reqId: {reqId}, time: {datetime.fromtimestamp(time) }, bidPrice: {bidPrice}, askPrice: {askPrice}, bidSize: {bidSize}, askSize: {askSize}, tickAttribBidAsk: {tickAttribBidAsk}")

    # whatToShow=MidPoint
    def tickByTickMidPoint(self, reqId: int, time: int, midPoint: float):
        print(f"reqId: {reqId}, {datetime.fromtimestamp(time)}, {midPoint}")

    # # whatToShow=AllLast
    def tickByTickAllLast(self, reqId: int, tickType: int, time: int, price: float, size: int, tickAttribLast: TickAttribLast, exchange: str, specialConditions: str):
        # Tick type does not correspond to tickType.py
        if tickType == 1:
            print(f"Last. reqId: {reqId}, time: {datetime.fromtimestamp(time)}, price: {price}, size: {size}, tickAttribLast: {tickAttribLast}, exchange: {exchange}, specialConditions: {specialConditions}")
        else:
            print(f"AllLast. reqId: {reqId}, time: {datetime.fromtimestamp(time)}, price: {price}, size: {size}, tickAttribLast: {tickAttribLast}, exchange: {exchange}, specialConditions: {specialConditions}")

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {datetime.fromtimestamp(errorTime)}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")
        

app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
