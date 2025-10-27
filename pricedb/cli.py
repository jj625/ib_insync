import questionary
from ingest import insert_ohlcv, update_coverage
from gaps import find_missing_segments, group_missing_into_ranges

def main_menu():
    action = questionary.select(
        "📈 OHLCV Data Manager — What would you like to do?",
        choices=["Ingest recent data", "Backfill older data", "Check missing segments", "Exit"]
    ).ask()

    if action == "Ingest recent data":
        # prompt for ticker, start/end, ingest
        pass
    elif action == "Check missing segments":
        ticker = questionary.text("Enter ticker:").ask()
        missing = find_missing_segments(ticker)
        ranges = group_missing_into_ranges(missing)
        for start, end in ranges:
            print(f"Missing: {start} → {end}")
    elif action == "Exit":
        print("Goodbye!")

from utils import parse_date

def prompt_ingest_params():
    ticker = questionary.text("Enter ticker symbol (e.g. AAPL):").ask()
    start_str = questionary.text("Start date (YYYY-MM-DD):").ask()
    end_str = questionary.text("End date (YYYY-MM-DD):").ask()

    start = parse_date(start_str)
    end = parse_date(end_str)
    return ticker.upper(), start, end