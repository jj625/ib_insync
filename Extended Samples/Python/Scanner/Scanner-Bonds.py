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

        sub = ScannerSubscription()
        sub.instrument = "BOND"
        sub.locationCode = "BOND.US"
        sub.scanCode = "BOND_CUSIP_AZ"

        # Both are lists of TagValue objects: TagValue(tag, value)
        scan_options = []
        filter_options = [
            TagValue("marketCapAbove1e6","100000"),
            TagValue("priceAbove", 100),
            TagValue("priceBelow", 109),
            TagValue("esgWorkforceScoreAbove", 7),
            TagValue("changePercAbove", 0.9),
            TagValue("changePercBelow", -1),
            TagValue("usdVolumeAbove", 500000),
            TagValue("avgUsdVolumeAbove", 1000000),
            TagValue("priceBelow", 1000),
            TagValue("avgOptVolumeAbove", 0),
            TagValue("excludeConvertible", 0)
        ]
        self.reqScannerSubscription(orderId, sub, scan_options, filter_options)

    def scannerData(self, reqId: int, rank: int, contractDetails: ContractDetails, distance: str, benchmark: str, projection: str, legsStr: str):
        print(rank, contractDetails, distance, benchmark, projection, legsStr)


    def scannerDataEnd(self, reqId: int):
        print(f"scannerDataEnd. reqId:{reqId}")
        self.cancelScannerSubscription(reqId)
        self.disconnect()

    def error(self, reqId: TickerId, errorTime: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(f"Error., Time of Error: {errorTime}, Error Code: {errorCode}, Error Message: {errorString}")
        if advancedOrderRejectJson != "":
            print(f"AdvancedOrderRejectJson: {advancedOrderRejectJson}")

app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
