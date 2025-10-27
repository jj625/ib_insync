from ib_insync import IB, Stock, util
import pandas as pd
from datetime import datetime
import asyncio
import logging

class IBKRClient:
    def __init__(self, host='127.0.0.1', port=7497, client_id=1234):
        self.ib = IB()
        self.host = host
        self.port = port
        self.client_id = client_id
        self._logger = logging.getLogger(__name__)

    async def connect(self):
        if not self.ib.isConnected():
            await self.ib.connectAsync(self.host, self.port, self.client_id)

    async def disconnect(self):
        if self.ib.isConnected():
            self.ib.disconnect()

    async def fetch_ohlcv(self, ticker: str, start: datetime, end: datetime, bar_size='5 mins') -> pd.DataFrame:
        await self.connect()

        contract = Stock(ticker, 'SMART', 'USD')
        await self.ib.qualifyContractsAsync(contract)

        # IBKR only allows requesting one day at a time for 5-min bars
        df_list = []
        current = start
        while current < end:
            duration = '1 D'
            end_str = current.strftime('%Y%m%d %H:%M:%S')
            bars = await self.ib.reqHistoricalDataAsync(
                contract,
                endDateTime=end_str,
                durationStr=duration,
                barSizeSetting=bar_size,
                whatToShow='TRADES',
                useRTH=True,
                formatDate=1
            )
            self._logger.debug(f"Fetched {len(bars)} bars for {ticker} ending {end_str}")
            df = util.df(bars)
            self._logger.info(df.columns)
            # if df.empty:
            #     current += pd.Timedelta(days=1)
            #     continue

            df = df.rename(columns={
                'date': 'time',
                'open_': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })[['time', 'open', 'high', 'low', 'close', 'volume']]
            df_list.append(df)
            current += pd.Timedelta(days=1)

        await self.disconnect()
        return pd.concat(df_list).drop_duplicates().reset_index(drop=True)