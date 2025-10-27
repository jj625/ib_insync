import argparse
import asyncio
import logging
from datetime import datetime
from cli import prompt_ingest_params
from ibkr import IBKRClient
from ingest import insert_ohlcv, update_coverage
from utils import parse_date
from ibkr import IBKRClient
from gaps import find_missing_segments, group_missing_into_ranges, write_backfill_plan
from db import Session, BackfillPlan, BackfillStatus

async def run_backfill(max_tasks: int):
    with Session() as session:
        plans = session.query(BackfillPlan).filter_by(status=BackfillStatus.pending).order_by(
            BackfillPlan.ticker, BackfillPlan.start).all()

    if not plans:
        logging.info("No pending backfill ranges found.")
        return

    sem = asyncio.Semaphore(max_tasks)
    ibkr = IBKRClient()
    await ibkr.connect()

    async def run_range(plan: BackfillPlan):
        async with sem:
            try:
                await ingest_flow(plan.ticker, plan.start, plan.end, ibkr)
                with Session() as session:
                    session.query(BackfillPlan).filter_by(
                        ticker=plan.ticker, start=plan.start, end=plan.end
                    ).update({"status": BackfillStatus.done})
                    session.commit()
            except Exception as e:
                logging.error(f"[{plan.ticker}] Backfill {plan.start} → {plan.end} failed: {e}")
                with Session() as session:
                    session.query(BackfillPlan).filter_by(
                        ticker=plan.ticker, start=plan.start, end=plan.end
                    ).update({"status": BackfillStatus.failed})
                    session.commit()

    await asyncio.gather(*(run_range(p) for p in plans))
    await ibkr.disconnect()

ibkr = IBKRClient()  # Global instance reused across tickers

async def ingest_flow(ticker: str, start: datetime, end: datetime, ibkr: IBKRClient):
    logging.info(f"[{ticker}] Fetching from {start} to {end}")
    df = await ibkr.fetch_ohlcv(ticker, start, end)

    if df.empty:
        logging.warning(f"[{ticker}] No data returned")
        return

    insert_ohlcv(df, ticker)
    update_coverage(ticker, df["time"].min(), df["time"].max())
    logging.info(f"[{ticker}] ✅ Ingested {len(df)} rows")

async def ingest_all(tickers, start, end, max_tasks):
    sem = asyncio.Semaphore(max_tasks)
    ibkr = IBKRClient()
    await ibkr.connect()

    async def wrapped_ingest(ticker):
        async with sem:
            try:
                await ingest_flow(ticker, start, end, ibkr)
            except Exception as e:
                logging.error(f"[{ticker}] Failed: {e}")

    await asyncio.gather(*(wrapped_ingest(t) for t in tickers))
    await ibkr.disconnect()

def validate_args(tickers, start, end):
    if not tickers:
        raise ValueError("At least one ticker must be provided.")
    if start >= end:
        raise ValueError("Start date must be before end date.")

def main():
    parser = argparse.ArgumentParser(description="OHLCV ingestion tool")
    parser.add_argument("--test", action="store_true", help="Run test ingest for AAPL")
    parser.add_argument("--ticker", nargs="+", help="Ticker symbols (e.g. AAPL MSFT TSLA)")
    parser.add_argument("--start", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--max-tasks", type=int, default=2, help="Max concurrent ingestion tasks")
    parser.add_argument("--loglevel", default="INFO", help="Set log level (DEBUG, INFO, WARNING, ERROR)")
    parser.add_argument("--check-gaps", action="store_true", help="Check for missing OHLCV segments")
    parser.add_argument("--backfill-plan", action="store_true", help="Write missing segments to backfill_plan table")
    parser.add_argument("--run-backfill", action="store_true", help="Ingest all ranges from backfill_plan table")
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.loglevel.upper(), logging.INFO),
                        format="%(asctime)s [%(levelname)s] %(message)s")

    if args.test:
        tickers = ["AAPL"]
        start = datetime(2025, 10, 20)
        end = datetime(2025, 10, 22)
    elif args.ticker and args.start and args.end:
        tickers = [t.upper() for t in args.ticker]
        start = parse_date(args.start)
        end = parse_date(args.end)
    else:
        ticker, start, end = prompt_ingest_params()
        tickers = [ticker]

    if args.check_gaps and not args.test:
        tickers = args.ticker or []
        if not tickers:
            logging.error("You must provide at least one --ticker to check gaps.")
            return

        for ticker in [t.upper() for t in tickers]:
            missing = find_missing_segments(ticker)
            if missing.empty:
                print(f"[{ticker}] ✅ No missing segments")
            else:
                print(f"[{ticker}] ❌ Missing {len(missing)} timestamps")
                for start, end in group_missing_into_ranges(missing):
                    print(f"    {start} → {end}")
        return

    if args.backfill_plan and not args.test:
        tickers = args.ticker or []
        if not tickers:
            logging.error("You must provide at least one --ticker to plan backfill.")
            return

        for ticker in [t.upper() for t in tickers]:
            missing = find_missing_segments(ticker)
            if missing.empty:
                print(f"[{ticker}] ✅ No missing segments")
            else:
                ranges = group_missing_into_ranges(missing)
                write_backfill_plan(ticker, ranges)
                print(f"[{ticker}] 📝 Planned {len(ranges)} backfill ranges")
        return

    if args.run_backfill:
        asyncio.run(run_backfill(args.max_tasks))
        return

    try:
        validate_args(tickers, start, end)
    except ValueError as e:
        logging.error(f"Validation error: {e}")
        return

    asyncio.run(ingest_all(tickers, start, end, args.max_tasks))

if __name__ == "__main__":
    main()