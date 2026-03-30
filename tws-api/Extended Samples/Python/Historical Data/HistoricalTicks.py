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
import datetime

port = 7496


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):

        mycontract = Contract()
        mycontract.conId = 265598
        mycontract.exchange = "SMART"

        self.reqHistoricalTicks(
            reqId=orderId,
            contract=mycontract,
            startDateTime="",
            endDateTime="20240927 10:18:00 US/Eastern",
            numberOfTicks=1000,
            whatToShow="TRADES",
            useRth=0,
            ignoreSize=False,
            miscOptions=[],
        )

    def historicalTicksLast(
        self, 
        reqId: int, 
        ticks: ListOfHistoricalTickLast, 
        done: bool,
    ):
        for tick in ticks:
            if tick.price <= 108.93:
                print(
                    "historicalTicksLast.", 
                    f"reqId:{reqId}", 
                    datetime.datetime.fromtimestamp(tick.time),
                    f"ticks:{tick.price}"
                )
        self.disconnect()

    def historicalTicksBidAsk(
        self, 
        reqId: int, 
        ticks: ListOfHistoricalTickBidAsk, 
        done: bool,
    ):
        for tick in ticks:
            print(
                "historicalTicksBidAsk.", 
                f"reqId:{reqId}", 
                datetime.datetime.fromtimestamp(tick.time),
                f"ticks:{tick}"
            )

    def historicalTicks(
        self, 
        reqId: int, 
        ticks: ListOfHistoricalTick, 
        done: bool,
    ):
        for tick in ticks:
            print(
                "historicalTicks.", 
                f"reqId:{reqId}", 
                datetime.datetime.fromtimestamp(tick.time,datetime.timezone.tzname("US/Central")),
                f"ticks:{tick.price}"
            )

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {datetime.datetime.fromtimestamp(errorTime)}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")


app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
