import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import traceback
import time
import logging
import sys

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
CSV_FILE = "attached_assets/enhanced_satta_data.csv"
MARKETS = {
    "Time Bazar": "https://dpbossattamatka.com/panel-chart-record/time-bazar.php",
    "Milan Day": "https://dpbossattamatka.com/panel-chart-record/milan-day.php",
    "Rajdhani Day": "https://dpbossattamatka.com/panel-chart-record/rajdhani-day.php",
    "Kalyan": "https://dpbossattamatka.com/panel-chart-record/kalyan.php",
    "Milan Night": "https://dpbossattamatka.com/panel-chart-record/milan-night.php",
    "Rajdhani Night": "https://dpbossattamatka.com/panel-chart-record/rajdhani-night.php",
    "Main Bazar": "https://dpbossattamatka.com/panel-chart-record/main-bazar.php"
}
HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_cell(cell):
    """Parse cell content from HTML"""
    parts = cell.decode_contents().split('<br>')
    return ''.join(BeautifulSoup(p, 'html.parser').get_text(strip=True) for p in parts)

def calculate_derived_fields(row):
    """
    Calculate derived fields for a result row
    
    Args:
        row: Dictionary with Open, Jodi, Close values
    
    Returns:
        Dictionary with derived fields
    """
    derived = {}
    
    # Calculate open sum (sum of digits)
    if 'Open' in row and row['Open'] and not pd.isna(row['Open']):
        digits = [int(d) for d in str(row['Open']) if d.isdigit()]
        derived['open_sum'] = sum(digits) if digits else None
    
    # Calculate close sum
    if 'Close' in row and row['Close'] and not pd.isna(row['Close']):
        digits = [int(d) for d in str(row['Close']) if d.isdigit()]
        derived['close_sum'] = sum(digits) if digits else None
    
    # Calculate mirror numbers
    if 'Open' in row and row['Open'] and not pd.isna(row['Open']):
        mirror = ''.join(str(9 - int(d)) for d in str(row['Open']) if d.isdigit())
        derived['mirror_open'] = float(mirror) if mirror else None
    
    if 'Close' in row and row['Close'] and not pd.isna(row['Close']):
        mirror = ''.join(str(9 - int(d)) for d in str(row['Close']) if d.isdigit())
        derived['mirror_close'] = float(mirror) if mirror else None
    
    # Calculate reverse jodi
    if 'Jodi' in row and row['Jodi'] and not pd.isna(row['Jodi']):
        jodi = str(row['Jodi']).zfill(2)
        reverse_jodi = jodi[1] + jodi[0]
        derived['reverse_jodi'] = float(reverse_jodi) if reverse_jodi.isdigit() else None
    
    return derived

def get_all_results_from_page(url, market):
    """Get all results from a market page"""
    logger.info(f"Getting all results for {market} from {url}")
    all_results = []
    
    try:
        # Make request with a longer timeout
        response = requests.get(url, headers=HEADERS, timeout=120)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch from {url}: {response.status_code}")
            return all_results
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Process tables
        tables = soup.find_all('table')
        logger.info(f"Found {len(tables)} tables on page")
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                
                # Skip rows without date range
                if len(cols) < 4 or 'to' not in cols[0].text:
                    continue
                
                # Get date range
                date_range = cols[0].text.strip()
                
                try:
                    # Parse date range (only need start date)
                    start_date_str = date_range.split('to')[0].strip()
                    start_date = datetime.datetime.strptime(start_date_str, "%d/%m/%Y").date()
                    
                    # Get result cells (excluding date column)
                    cells = cols[1:]
                    total_days = len(cells) // 3  # Each day has 3 cells: open, jodi, close
                    
                    # Process each day in range
                    for i in range(total_days):
                        date = start_date + datetime.timedelta(days=i)
                        date_str = date.strftime("%d/%m/%Y")
                        
                        # Get cells for this day
                        if i*3+2 < len(cells):  # Make sure we have all 3 cells
                            o, j, c = cells[i*3], cells[i*3+1], cells[i*3+2]
                            
                            # Skip if result not declared
                            if ('*' in o.text or '*' in j.text or '*' in c.text or 
                                'XXX' in o.text or 'XXX' in j.text or 'XXX' in c.text):
                                logger.debug(f"Skipping {date_str} - result not declared")
                                continue
                            
                            # Extract values
                            open_val = parse_cell(o)
                            jodi_val = parse_cell(j)
                            close_val = parse_cell(c)
                            
                            # Skip if any value is empty
                            if not open_val or not jodi_val or not close_val:
                                logger.debug(f"Skipping {date_str} - incomplete values")
                                continue
                            
                            # Create result entry
                            result = {
                                'Date': date_str,
                                'Market': market,
                                'Open': open_val,
                                'Jodi': jodi_val,
                                'Close': close_val,
                                'day_of_week': date.strftime('%A'),
                                'is_weekend': 1 if date.weekday() >= 5 else 0,
                                'is_holiday': 0
                            }
                            
                            # Calculate derived fields
                            derived = calculate_derived_fields(result)
                            result.update(derived)
                            
                            all_results.append(result)
                
                except Exception as e:
                    logger.error(f"Error processing row: {e}")
                    continue
        
        logger.info(f"Extracted {len(all_results)} results for {market}")
        
    except Exception as e:
        logger.error(f"Error fetching data for {market}: {e}")
        traceback.print_exc()
    
    return all_results

def update_csv_with_results(results):
    """Update CSV with new results"""
    logger.info(f"Updating CSV with {len(results)} results")
    
    # Load existing CSV if it exists
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        logger.info(f"Loaded existing CSV with {len(df)} rows")
    else:
        # Create new dataframe
        df = pd.DataFrame(columns=['Date', 'Market', 'Open', 'Jodi', 'Close',
                                  'day_of_week', 'is_weekend', 'open_sum', 'close_sum',
                                  'mirror_open', 'mirror_close', 'reverse_jodi', 'is_holiday'])
        logger.info("Created new CSV file")
    
    # Get existing date-market combinations
    if not df.empty:
        existing = set(zip(df['Date'], df['Market']))
    else:
        existing = set()
    
    # Filter out existing records
    new_results = []
    for result in results:
        if (result['Date'], result['Market']) not in existing:
            new_results.append(result)
    
    logger.info(f"Adding {len(new_results)} new records to CSV")
    
    if new_results:
        # Convert new results to dataframe
        new_df = pd.DataFrame(new_results)
        
        # Append to existing dataframe
        updated_df = pd.concat([df, new_df], ignore_index=True)
        
        # Sort by date and market
        updated_df['Date'] = pd.to_datetime(updated_df['Date'], format='%d/%m/%Y')
        updated_df.sort_values(['Date', 'Market'], inplace=True)
        updated_df['Date'] = updated_df['Date'].dt.strftime('%d/%m/%Y')
        
        # Save updated CSV
        updated_df.to_csv(CSV_FILE, index=False)
        logger.info(f"Updated CSV with {len(new_results)} new records. Total: {len(updated_df)}")
        return len(new_results)
    else:
        logger.info("No new records to add")
        return 0

def update_market(market):
    """Update CSV for a specific market"""
    logger.info(f"Starting CSV update for {market}")
    
    if market not in MARKETS:
        logger.error(f"Market {market} not found in known markets")
        return 0
    
    url = MARKETS[market]
    
    # Get results from market
    results = get_all_results_from_page(url, market)
    
    # Update CSV
    added = 0
    if results:
        added = update_csv_with_results(results)
    
    logger.info(f"CSV update completed for {market}. Added {added} new records.")
    return added

def main():
    """Update CSV for specified market or list markets"""
    if len(sys.argv) < 2:
        print("Usage: python update_market_csv.py <market_name>")
        print("Available markets:")
        for market in MARKETS:
            print(f"  - {market}")
        return
    
    market = sys.argv[1]
    update_market(market)

if __name__ == "__main__":
    main()