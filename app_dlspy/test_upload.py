# python code to download SPY holdings from SSGA website
# download using requests, parse the Excel file using pandas,
# and save the data to a SQLite database
import httpx
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timezone
import os
import logging

from httpx import Cookies

def print_cookie_details(cookies, title="Cookies"):
    """
    Print detailed information about cookies
    """
    print(f"\n=== {title} ===")
    print(f"Total cookies: {len(cookies)}")
    
    for cookie in cookies:
        print(f"\nCookie: {cookie.name}")
        print(f"  Value: {cookie.value[:50]}{'...' if len(cookie.value) > 50 else ''}")
        print(f"  Domain: {cookie.domain}")
        print(f"  Path: {cookie.path}")
        print(f"  Secure: {cookie.secure}")
        print(f"  HttpOnly: {hasattr(cookie, 'has_nonstandard_attr') and cookie.has_nonstandard_attr('HttpOnly')}")
        print(f"  Expires: {cookie.expires}")
        print(f"  SameSite: {getattr(cookie, 'same_site', 'Not set')}")
        
        # Try to determine if cookie is necessary or optional
        cookie_type = classify_cookie(cookie.name, cookie.value)
        print(f"  Classification: {cookie_type}")

def classify_cookie(name, value):
    """
    Classify cookies as necessary, functional, analytics, or marketing
    """
    name_lower = name.lower()
    
    # Necessary cookies (required for basic functionality)
    necessary_patterns = [
        'session', 'csrf', 'xsrf', 'auth', 'login', 'security',
        'audience', 'jsessionid', 'phpsessid', 'asp.net_sessionid',
        'cookieconsent', 'gdpr', 'ccpa', 'necessary'
    ]
    
    # Analytics/tracking cookies (optional)
    analytics_patterns = [
        'ga', 'gtm', 'gtag', '_gid', '_gat', 'analytics', 'tracking',
        'omniture', 'adobe', 'mixpanel', 'hotjar', 'mouseflow'
    ]
    
    # Marketing/advertising cookies (optional)
    marketing_patterns = [
        'doubleclick', 'facebook', 'twitter', 'linkedin', 'youtube',
        'advertising', 'ads', 'marketing', 'retargeting', 'conversion'
    ]
    
    for pattern in necessary_patterns:
        if pattern in name_lower:
            return "NECESSARY"
    
    for pattern in analytics_patterns:
        if pattern in name_lower:
            return "ANALYTICS (Optional)"
    
    for pattern in marketing_patterns:
        if pattern in name_lower:
            return "MARKETING (Optional)"
    
    # Default classification based on common patterns
    if len(value) > 100 or 'tracking' in value.lower():
        return "LIKELY TRACKING (Optional)"
    
    return "UNKNOWN (Treating as Optional)"

def filter_necessary_cookies(client):
    """
    Filter cookies to keep only necessary ones
    """
    print("\n=== Filtering Cookies ===")
    original_cookies = list(client.cookies.jar)
    print_cookie_details(original_cookies, "All Received Cookies")
    
    # Create new cookie jar with only necessary cookies
    necessary_jar = Cookies()
    
    for cookie in original_cookies:
        classification = classify_cookie(cookie.name, cookie.value)
        if "NECESSARY" in classification:
            necessary_jar.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
            print(f"\n✓ KEEPING: {cookie.name} - {classification}")
        else:
            print(f"\n✗ REJECTING: {cookie.name} - {classification}")
    
    # Replace client cookies with filtered ones
    client.cookies = necessary_jar
    
    print(f"\nCookie filtering complete:")
    print(f"  Original: {len(original_cookies)} cookies")
    print(f"  Kept: {len(list(client.cookies.jar))} necessary cookies")
    print(f"  Rejected: {len(original_cookies) - len(list(client.cookies.jar))} optional cookies")
    
    print_cookie_details(list(client.cookies.jar), "Final Necessary Cookies")
    return client

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(message)s')
logger = logging.getLogger(__name__)

# Define the URL and the local filename
url = 'https://www.ssga.com/us/en/individual/library-content/products/fund-data/etfs/us/holdings-daily-us-en-spy.xlsx'
download_date = datetime.now().strftime(r'%Y-%m-%d')
download_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
local_filename = f'spy_holdings_{download_date}.xlsx' # no holding date in the name yet

# # Download the file
# client = httpx.Client()


# main_page_response = client.get(url)
# logger.info(f'Main page status: {main_page_response.status_code}')
# logger.info(f'Initial cookies received: {len(client.cookies)}')
# client = filter_necessary_cookies(client)
# # attempt download with filtered cookies
# logger.info(f'Attempting download with necessary cookies only...')

# response = client.get(url, follow_redirects=True, timeout=5)
# if response.status_code != 200:
#     logger.error(f'Failed to download {url}')
#     exit(1)
# # get the file size and modified time
# file_size: int = len(response.content)
# file_modified: str = response.headers['Last-Modified']
# file_mod_dt = datetime.strptime(file_modified, r'%a, %d %b %Y %H:%M:%S %Z')
# # if the timezone is either UTC or GMT, set the timezone to UTC
# if file_mod_dt.tzinfo is None or file_mod_dt.tzinfo.utcoffset(file_mod_dt) is None:
#     if file_modified.endswith('GMT') or file_modified.endswith('UTC'):
#         file_mod_dt = file_mod_dt.replace(tzinfo=timezone.utc)
#     else:
#         logger.error(f'Failed to parse the timezone from the Last-Modified header: {file_modified}')
#         exit(1)
# logger.info(f'Downloading {url} to {local_filename}, {file_size} bytes, last modified at {file_mod_dt.astimezone()}')
# with open(local_filename, 'wb') as f:
#     f.write(response.content)

local_filename = 'spy_holdings_2025-10-25_as_of_2025-10-23.xlsx'  # for testing purposes
# Read the Excel file
df = pd.read_excel(local_filename, skiprows=4)

# Parse the date from row 3
xls = pd.ExcelFile(local_filename)
sheet = xls.parse(xls.sheet_names[0], header=None)
# Read the top three rows
top_rows = sheet.head(3)

# Turn each row into a python string, join each cell in a row with a comma
top_rows_str = [' '.join(row.dropna().astype(str).tolist()) for _, row in top_rows.iterrows()]

# confirm that the first row is the fund name
if 'SPDR® S&P 500® ETF Trust' not in top_rows_str[0]:
    logger.error(f'Failed to find the fund name in the first three rows: {top_rows_str}')
    exit(1)
# second line is the ticker symbol
if 'SPY' not in top_rows_str[1]:
    logger.error(f'Failed to find the ticker symbol in the first three rows: {top_rows_str}')
    exit(1)
# third line is the holding date
holding_date_str = top_rows_str[2]
# holding_date_str = ' '.join(sheet.iloc[2, :].dropna().astype(str).tolist())
holding_date = pd.to_datetime(holding_date_str.split('As of ')[1]).strftime('%Y-%m-%d')
logger.info(f'Holding date: {holding_date}')

# find blank rows in sheet
blank_rows = sheet[sheet.isnull().all(axis=1)]
# read into dataframe the rows after the first blank row until the next blank row
# this is the table of holdings
df = xls.parse(xls.sheet_names[0], skiprows=blank_rows.index[0] + 1, nrows=blank_rows.index[1] - blank_rows.index[0] - 1)
# the dataframe should have about between 500 and 506 rows
if len(df) < 500 or len(df) > 506:
    logger.error(f'Unexpected number of rows in the holdings table: {len(df)}')
    exit(1)
# Close the Excel file
xls.close()

# rename columns to supabase table columns
expected_columns = {
    'Name': 'name',
    'Ticker': 'ticker',
    'Identifier': 'identifier',
    'SEDOL': 'sedol',
    'Weight': 'weight',
    'Sector': 'sector',
    'Shares Held': 'shares_held',
    'Local Currency': 'local_currency',
}
df = df.rename(columns=expected_columns)
logger.info(f'Parsed {len(df)} rows from the holdings table:\n{df.head()}')
# # Rename the file to include the holding date
# new_filename = f'spy_holdings_{download_date}_as_of_{holding_date}.xlsx'
# if os.path.exists(new_filename):
#     with open(local_filename, 'rb') as f1, open(new_filename, 'rb') as f2:
#         if f1.read() == f2.read():
#             logger.info(f'{new_filename} already exists and is identical to the downloaded file. Exiting.')
#             exit(0)
# os.rename(local_filename, new_filename)
# logger.info(f'Renamed {local_filename} to {new_filename}')

# Get Supabase credentials from environment variables
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_KEY')

if not supabase_url or not supabase_key:
    logger.error('SUPABASE_URL and SUPABASE_KEY environment variables must be set')
    exit(1)

# Initialize Supabase client
supabase: Client = create_client(supabase_url, supabase_key)

# Check if data already exists for the download date
response = supabase.table('holdings').select('*', count='exact').eq('download_datetime', download_date).execute()
count = response.count if hasattr(response, 'count') else len(response.data)

if count > 0:
    logger.info(f'Data already downloaded on {download_date}, rowcount {count}')
    exit()

# Add download_datetime and holding_date columns to the DataFrame
df['download_datetime'] = download_date
df['holding_date'] = holding_date

# Drop the rows with missing Ticker, Identifier, or SEDOL
df_nona = df.dropna(subset=['ticker', 'identifier', 'sedol'])
if len(df) != len(df_nona):
    logger.warning(f'Dropped {len(df) - len(df_nona)} rows with missing Ticker, Identifier, or SEDOL')
    # print the dropped rows
    logger.warning(df.loc[~df.index.isin(df_nona.index), ['name', 'ticker', 'identifier', 'sedol']])

# Convert DataFrame to list of dictionaries for Supabase insert
records = df_nona.to_dict('records')

# Insert data into Supabase in batches (Supabase has limits on batch size)
batch_size = 1000
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    supabase.table('holdings').insert(batch).execute()
    logger.info(f'Inserted batch {i//batch_size + 1}: {len(batch)} rows')

logger.info(f'Inserted total {len(df_nona)} rows into the holdings table')
