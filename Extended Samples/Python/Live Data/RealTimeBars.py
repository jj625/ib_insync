'''
2002-2025: Use is subject to Interactive Brokers TWS API Non-Commercial License ("License") terms. 
This License is NOT for anybody who is developing software applications that they wish to: (a) sell to third 
party users for a fee, or (b) give to third party users to generate an indirect financial benefit (e.g., 
commissions). If You wish to make a software application for the purposes described in the preceding 
sentence then please contact Interactive Brokers
'''

from ibapi.client import *
from ibapi.common import TickerId
from ibapi.wrapper import *
from decimal import Decimal
from ibapi.tag_value import *


port = 7496


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):

        mycontract = Contract()
        mycontract.conId = 265598
        mycontract.exchange = "SMART"

        self.reqRealTimeBars(orderId, mycontract, 5, "TRADES", True, [])

    def realtimeBar(self, reqId: int, time: int, open_: float, high: float, low: float, close: float, volume: Decimal, wap: Decimal, count: int):
        print(f"reqId: {reqId}, Bar Time: {time}, Open: {open_}, High: {high}, Low: {low}, Close: {close}, Volume: {volume}, Weighted Average Price: {wap}, Count: {count}")

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")

app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
