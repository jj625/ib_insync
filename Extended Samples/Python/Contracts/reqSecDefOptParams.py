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

port = 7496


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):

        self.reqSecDefOptParams(  
            reqId=123,
            underlyingSymbol="AAPL",
            futFopExchange="",  
            underlyingSecType="STK",
            underlyingConId="265598",
        )

    def securityDefinitionOptionParameter(
        self,
        reqId: int,
        exchange: str,
        underlyingConId: int,
        tradingClass: str,
        multiplier: str,
        expirations: SetOfString,
        strikes: SetOfFloat,
    ):
        print(
            "securityDefinitionOptionParameter.",
            f"reqId:{reqId}",
            f"exchange:{exchange}",
            f"underlyingConId:{underlyingConId}",
            f"tradingClass:{tradingClass}",
            f"multiplier:{multiplier}",
            f"expirations:{expirations}",
            f"strikes:{strikes}",
        )

    def securityDefinitionOptionParameterEnd(self, reqId: int):
        print(f"securityDefinitionOptionParameterEnd. reqId:{reqId}")

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")

app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
