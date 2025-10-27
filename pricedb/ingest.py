import pandas as pd
from db import engine, Session, Coverage
from sqlalchemy.orm import sessionmaker

def insert_ohlcv(df: pd.DataFrame, ticker: str):
    df = df.copy()
    df["ticker"] = ticker
    df["time"] = pd.to_datetime(df["time"])
    df.to_sql("ohlcv", engine, if_exists="append", index=False, method="multi")

def update_coverage(ticker: str, start, end, is_backfill=False):
    session = Session()
    existing = session.query(Coverage).filter_by(ticker=ticker).first()
    if existing:
        existing.start = min(existing.start, start)
        existing.end = max(existing.end, end)
        existing.is_backfill = existing.is_backfill or is_backfill
    else:
        session.add(Coverage(ticker=ticker, start=start, end=end, is_backfill=is_backfill))
    session.commit()