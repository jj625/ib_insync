import requests
import pandas as pd
import sqlite3
from datetime import datetime
import os

# Define the URL and the local filename
url = 'https://www.ssga.com/us/en/individual/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx'
download_date = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
local_filename = f'spy_holdings_{download_date}.xlsx'

# Download the file
response = requests.get(url)
with open(local_filename, 'wb') as f:
    f.write(response.content)

# Read the Excel file
df = pd.read_excel(local_filename, skiprows=4)

# Parse the date from row 3
xls = pd.ExcelFile(local_filename)
sheet = xls.parse(xls.sheet_names[0], header=None)
holding_date_str = ' '.join(sheet.iloc[2, :].dropna().astype(str).tolist())
holding_date = pd.to_datetime(holding_date_str.split('As of ')[1]).strftime('%Y-%m-%d')
# Close the Excel file
xls.close()
# Rename the file to include the holding date
new_filename = f'spy_holdings_{download_date}_as_of_{holding_date}.xlsx'
os.rename(local_filename, new_filename)

# Save the table into a SQLite database
conn = sqlite3.connect('spy_holdings.db')
c = conn.cursor()

# Create table if it doesn't exist
c.execute('''
CREATE TABLE IF NOT EXISTS holdings (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    name TEXT,
    sector TEXT,
    shares INTEGER,
    market_value REAL,
    weight REAL,
    download_datetime TEXT,
    holding_date TEXT
)
''')

# Insert data into the table
for index, row in df.iterrows():
    if pd.isna(row[0]):
        break
    c.execute('''
    INSERT INTO holdings (ticker, name, sector, shares, market_value, weight, download_datetime, holding_date)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (row[0], row[1], row[2], row[3], row[4], row[5], download_date, holding_date))

# Commit and close the connection
conn.commit()
conn.close()