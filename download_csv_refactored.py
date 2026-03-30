"""
Refactored CSV download script using the cookie_manager module.

This script demonstrates how to use the separated cookie management functionality
for downloading CSV files from web sources.
"""

import os
import requests
import tempfile
import csv
import filecmp
from datetime import datetime

# Import our cookie management module
from cookie_manager import CookieManager, filter_necessary_cookies


def download_csv_with_cookies(url):
    """
    Download CSV file from URL with proper cookie handling and file management.
    
    Args:
        url (str): URL to download the CSV from
    """
    print(f"Downloading from: {url}")
    
    # Create a session and cookie manager
    session = requests.Session()
    cookie_manager = CookieManager(verbose=True)
    
    # Set headers to mimic a real browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/csv,application/csv,text/plain,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.invesco.com/',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
    }
    
    try:
        # Set up initial cookies using the cookie manager
        initial_url = 'https://www.invesco.com/us/financial-products/etfs/holdings/main/holdings/0?audienceType=Investor&ticker=QQQ'
        session = cookie_manager.setup_session_cookies(session, initial_url, headers)
        
        # Get a summary of cookies for logging
        cookie_summary = cookie_manager.get_cookie_summary(session)
        print(f"\nUsing {cookie_summary['necessary']} necessary cookies for download")
        
        # Now try the download with filtered cookies
        print("\nAttempting download with necessary cookies only...")
        response = session.get(url, headers=headers, allow_redirects=True, timeout=30)
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code != 200:
            print(f"Server returned status code: {response.status_code}")
            print(f"Response text: {response.text[:500]}...")  # First 500 chars
            return
        
        response.raise_for_status()  # Raise an exception for bad status codes
        
        print(f"Content type: {response.headers.get('content-type', 'Unknown')}")
        print(f"Content length: {len(response.content)} bytes")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=".csv") as temp_file:
            temp_file.write(response.content)
            temp_filename = temp_file.name
        
        print(f"Downloaded to temporary file: {temp_filename}")
        
        # Process the CSV file to extract date and manage file naming
        date_str = _process_csv_file(temp_filename)
        _manage_file_storage(temp_filename, date_str)
        
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def _process_csv_file(temp_filename):
    """
    Process the CSV file to extract information and return a date string.
    
    Args:
        temp_filename (str): Path to the temporary CSV file
        
    Returns:
        str: Date string for file naming
    """
    try:
        with open(temp_filename, 'r', encoding='utf-8') as csvfile:
            # Read first few lines to see the structure
            sample_lines = []
            for i, line in enumerate(csvfile):
                sample_lines.append(line.strip())
                if i >= 10:  # Read first 11 lines
                    break
            
            print("First few lines of the file:")
            for i, line in enumerate(sample_lines):
                print(f"Line {i}: {line}")
        
        # Reset file pointer and try to parse as CSV
        with open(temp_filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            first_row = next(reader)
            
            print(f"CSV columns: {reader.fieldnames}")
            print(f"First row: {first_row}")
            
            # Extract date
            if 'Date' in first_row:
                date_str = first_row['Date'].replace('/', '-').replace(' ', '_')
                print(f"Extracted date: {date_str}")
                return date_str
            else:
                # Use current date if no Date column found
                date_str = datetime.now().strftime('%Y-%m-%d')
                print(f"No Date column found, using current date: {date_str}")
                return date_str
                
    except Exception as e:
        print(f"Error reading CSV: {e}")
        # Use current date as fallback
        date_str = datetime.now().strftime('%Y-%m-%d')
        print(f"Using current date as fallback: {date_str}")
        return date_str


def _manage_file_storage(temp_filename, date_str):
    """
    Manage the storage of the downloaded file with proper naming and versioning.
    
    Args:
        temp_filename (str): Path to the temporary file
        date_str (str): Date string for file naming
    """
    # Generate destination filename
    destination_filename = f"QQQ_holdings_{date_str}.csv"
    
    # Check if destination file exists
    if os.path.exists(destination_filename):
        print(f"Destination file {destination_filename} already exists")
        
        # Compare files
        if filecmp.cmp(temp_filename, destination_filename, shallow=False):
            print(f"File {destination_filename} already exists and is identical.")
            os.remove(temp_filename)
            print("Temporary file removed.")
        else:
            print("Files are different. Creating versioned file...")
            version = 1
            while os.path.exists(f"QQQ_holdings_{date_str}_v{version}.csv"):
                version += 1
            
            versioned_filename = f"QQQ_holdings_{date_str}_v{version}.csv"
            os.rename(temp_filename, versioned_filename)
            print(f"File saved as: {versioned_filename}")
    else:
        # Rename temp file to permanent name
        os.rename(temp_filename, destination_filename)
        print(f"File saved as: {destination_filename}")


def main():
    """Main function to run the download."""
    url = "https://www.invesco.com/us/financial-products/etfs/holdings/main/holdings/0?audienceType=Investor&action=download&ticker=QQQ"
    download_csv_with_cookies(url)


if __name__ == "__main__":
    main()
