from cli import prompt_ingest_params
from ibkr import IBKRClient
from ingest import insert_ohlcv, update_coverage
import asyncio
import logging

logger = None

async def ingest_flow(ticker, start, end):
    ibkr = IBKRClient()
    df = await ibkr.fetch_ohlcv(ticker, start, end)

    if df.empty:
        print(f"No data returned for {ticker} between {start} and {end}")
        return

    insert_ohlcv(df, ticker)
    update_coverage(ticker, df["time"].min(), df["time"].max())
    print(f"✅ Ingested {len(df)} rows for {ticker}")

def main():
    logging.basicConfig(level=logging.INFO)
    global logger
    logger = logging.getLogger(__name__)

    ticker, start, end = prompt_ingest_params()  # ← sync prompt
    asyncio.run(ingest_flow(ticker, start, end))  # ← async fetch

if __name__ == "__main__":
    main()