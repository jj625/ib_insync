import pandas as pd
from db import engine

def find_missing_segments(ticker: str, freq="5min") -> pd.DatetimeIndex:
    query = f"SELECT time FROM ohlcv WHERE ticker = '{ticker}'"
    df = pd.read_sql(query, engine, parse_dates=["time"])
    if df.empty:
        return pd.date_range(end=pd.Timestamp.now(), periods=1, freq=freq)

    df = df.sort_values("time")
    full_range = pd.date_range(start=df["time"].min(), end=df["time"].max(), freq=freq)
    return full_range.difference(df["time"])

def group_missing_into_ranges(missing: pd.DatetimeIndex, freq="5min"):
    if missing.empty:
        return []

    df = pd.DataFrame({"time": missing})
    df["gap"] = df["time"].diff() != pd.Timedelta(freq)
    df["group"] = df["gap"].cumsum()
    ranges = df.groupby("group")["time"].agg(["min", "max"])
    return list(ranges.itertuples(index=False, name=None))