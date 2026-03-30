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
import json

port = 7496


class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)

    def nextValidId(self, orderId: OrderId):

        # Either ConID or Filter may be passed, but not both.
        eventData = WshEventData()
        # eventData.conId = 195014116
        eventData.startDate = "20241001"
        # eventData.endDate = ""
        # eventData.fillCompetitors = False
        # eventData.fillPortfolio = False
        # eventData.fillWatchlist = False
        eventData.totalLimit = 0
        eventData.filter = ''
        eventData.filter = '{"country": "All","watchlist":["265598"], "wshe_div":"true"}'

        """
        Filters pulled from wshMetaData. Look for section header in response to find filter name.
        String(Boolean) is only acceptable value to include.

        wshe_bod    ==  Board of Directors
        wshe_ed     ==  Earnings Dates
        wshe_div    ==  Dividend Dates
        wshe_qe     ==  Quarterly Earnings
        """
        # Please note, the third param for self.serverVersion is not necessary for API releases prior to 10.20.
        self.reqWshEventData(orderId, eventData)

    def wshEventData(self, reqId: int, dataJson: str):
        print("eventdata.")
        jsonDict = json.dumps(json.loads(dataJson), indent=4)
        print(jsonDict)
        self.disconnect()


app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
