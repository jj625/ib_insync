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


import time

port = 7496

class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):
        self.reqAccountUpdatesMulti(orderId, "DU74649", "")

    def accountUpdateMulti(self, reqId: TickerId, account: str, modelCode: str, key: str, value: str, currency: str):
        print("updateAccountValue.", key, value, currency, account)
    
    def accountUpdateMultiEnd(self, reqId: TickerId):
        print("End of "+str(reqId))

    def updateAccountTime(self, timeStamp: str):
        print("updateAccountTime.", timeStamp)

    def updatePortfolio(self, contract: Contract, position: Decimal, marketPrice: float, marketValue: float, averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S US/Central', time.localtime())}updatePortfolio. contract: {contract.symbol}@{contract.exchange}:{contract.secType}, position: {position}, marketPrice: {marketPrice}, marketValue: {marketValue}, averageCost: {averageCost}, unrealizedPNL: {unrealizedPNL}, realizedPNL: {realizedPNL}")
    
    def accountDownloadEnd(self, accountName: str):
        print("accountDownloadEnd.", accountName)
        self.disconnect()

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")

if __name__ == "__main__":
    app = TestApp()
    app.connect("127.0.0.1", port, 0)
    app.run()