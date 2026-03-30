import asyncio
import os
import pprint
from supabase import create_client, Client

url: str = os.environ.get("SUPABASE_URL", '')
key: str = os.environ.get("SUPABASE_KEY", '')
supabase: Client = create_client(url, key)

response = (
    supabase.table("users")
    .select("*")
    .execute()
)

from collections import defaultdict

async def fetch_all_rows(supabase, table_name, page_size=1000):
    all_rows = []
    start = 0

    while True:
        end = start + page_size - 1
        res = (
            supabase.table(table_name)
            .select("holding_date, download_datetime")
            .order("holding_date")
            .range(start, end)
            .execute()
        )

        rows = res.data
        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        start += page_size

    return all_rows


def group_rows(rows):
    grouped = defaultdict(int)
    for row in rows:
        key = (row["holding_date"], row["download_datetime"])
        grouped[key] += 1

    return [
        {
            "cnt": cnt,
            "holding_date": holding_date,
            "download_datetime": download_datetime,
        }
        for (holding_date, download_datetime), cnt in grouped.items()
    ]


async def main():
    rows = await fetch_all_rows(supabase, "spy_holdings")
    grouped = group_rows(rows)
    print(grouped)
    print(len(grouped))

# async def main():
#     res = supabase.table("users").select("*").execute()
#     print(res)

    # # execute sql without using rpc
    # _sql = 'select count(*), holding_date, download_datetime from public.spy_holdings group by holding_date, download_datetime order by holding_date'
    # res = supabase.table("spy_holdings").select("holding_date, download_datetime").execute()
    # print(len(res.data))
    # # # print everything in `res` but the data itself
    # # print({k: v for k, v in res.items() if k != "data"})
    # # print histogram of holding_date
    # holding_dates = [row["holding_date"] for row in res.data]
    # histogram = {}
    # for date in holding_dates:
    #     histogram[date] = histogram.get(date, 0) + 1
    # print(histogram)


asyncio.run(main())
