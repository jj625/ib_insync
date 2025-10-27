import argparse
import asyncio
import logging
from datetime import datetime
from cli import prompt_ingest_params
from ibkr import IBKRClient
from ingest import insert_ohlcv, update_coverage

async def ingest_flow(ticker: str, start: datetime, end: datetime):
    logging.info(f"Fetching {ticker} from {start} to {end}")
    ibkr = IBKRClient()
    df = await ibkr.fetch_ohlcv(ticker, start, end)

    if df.empty:
        logging.warning(f"No data returned for {ticker} between {start} and {end}")
        return

    insert_ohlcv(df, ticker)
    update_coverage(ticker, df["time"].min(), df["time"].max())
    logging.info(f"✅ Ingested {len(df)} rows for {ticker}")

def main():
    parser = argparse.ArgumentParser(description="OHLCV ingestion tool")
    parser.add_argument("--test", action="store_true", help="Run test ingest for AAPL")
    parser.add_argument("--loglevel", default="INFO", help="Set log level (DEBUG, INFO, WARNING, ERROR)")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.loglevel.upper(), logging.INFO),
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if args.test:
        ticker = "AAPL"
        start = datetime(2025, 10, 20)
        end = datetime(2025, 10, 22)
    else:
        ticker, start, end = prompt_ingest_params()

    asyncio.run(ingest_flow(ticker, start, end))

if __name__ == "__main__":
    main()