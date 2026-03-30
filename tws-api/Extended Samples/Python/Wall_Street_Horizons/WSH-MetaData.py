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
        self.reqWshMetaData(orderId)

    def wshMetaData(self, reqId: TickerId, data: str):
        jsonDict = json.dumps(json.loads(data), indent=2)
        open('./wshMetaData.xml', 'w').write(jsonDict)
        
        print("WSH Meta Data received.")
        jcon = json.loads(data)
        for jobj in jcon["meta_data"]["event_types"]:
            print(f'{jobj["name"]}: {jobj["tag"]}')
        self.disconnect()

app = TestApp()
app.connect("127.0.0.1", port, 0)
app.run()
