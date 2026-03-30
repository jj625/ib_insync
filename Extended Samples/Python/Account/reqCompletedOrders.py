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
        self.reqCompletedOrders(apiOnly=False)

    def completedOrder(self, contract: Contract, order: Order, orderState: OrderState):
        print("Contract:", contract)
    
        print(order)
        attrs = vars(orderState)
        print("OrderState Details.\n",
            "\n".join(f"{name}: {value}" for name, value in attrs.items())
            )

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")


app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
