import os
import pandas as pd
import datetime
import traceback
import requests
from bs4 import BeautifulSoup
import time
import random
import csv
from app import app, db
from models import Result
from utils import calculate_derived_fields, parse_date
from sqlalchemy.exc import SQLAlchemyError
from config import Config

def parse_cell(cell):
    """Parse cell content from HTML"""
    parts = cell.decode_contents().split('<br>')
    return ''.join(BeautifulSoup(p, 'html.parser').get_text(strip=True) for p in parts)

def scrape_satta_results():
    """
    Scrape latest Satta Matka results from websites
    Returns a DataFrame with the latest results
    """
    print("Scraping latest Satta Matka results from websites with enhanced multi-day collection...")
    
    # Better source URLs from dpbossattamatka.com
    MARKETS = {
        "Time Bazar": "https://dpbossattamatka.com/panel-chart-record/time-bazar.php",
        "Milan Day": "https://dpbossattamatka.com/panel-chart-record/milan-day.php",
        "Rajdhani Day": "https://dpbossattamatka.com/panel-chart-record/rajdhani-day.php",
        "Kalyan": "https://dpbossattamatka.com/panel-chart-record/kalyan.php",
        "Milan Night": "https://dpbossattamatka.com/panel-chart-record/milan-night.php",
        "Rajdhani Night": "https://dpbossattamatka.com/panel-chart-record/rajdhani-night.php",
        "Main Bazar": "https://dpbossattamatka.com/panel-chart-record/main-bazar.php"
    }
    
    # Using multiple sources can help with redundancy
    BACKUP_URLS = {
        "Time Bazar": "https://sattamatkaresult.co.in/satta-matka-results-today.php",
        "Milan Day": "https://sattamatkaresult.co.in/satta-matka-results-today.php",
        "Kalyan": "https://sattamatkaresult.co.in/satta-matka-results-today.php",
        "Milan Night": "https://sattamatkaresult.co.in/satta-matka-results-today.php",
        "Main Bazar": "https://sattamatkaresult.co.in/satta-matka-results-today.php"
    }
    
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    
    # List to store all results
    all_results = []
    
    # Try each market with primary and backup URLs
    for market, url in MARKETS.items():
        print(f"Checking {market} (primary source)...")
        primary_success = False
        
        try:
            # Add random delay to avoid too many requests
            time.sleep(random.uniform(1, 2))
            
            # Get the data from the primary website
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.encoding = 'utf-8'
            
            if res.status_code != 200:
                print(f"Failed to fetch from primary URL {url}: Status code {res.status_code}")
            else:
                primary_success = True
                # Process the primary source
                print(f"Successfully fetched data from primary source for {market}")
        except Exception as e:
            print(f"Error fetching from primary source for {market}: {e}")
            
        # If primary source failed and we have a backup URL, try it
        if not primary_success and market in BACKUP_URLS:
            print(f"Trying backup source for {market}...")
            try:
                time.sleep(random.uniform(1, 2))
                backup_url = BACKUP_URLS[market]
                res = requests.get(backup_url, headers=HEADERS, timeout=10)
                res.encoding = 'utf-8'
                
                if res.status_code != 200:
                    print(f"Failed to fetch from backup URL {backup_url}: Status code {res.status_code}")
                    continue
                
                print(f"Successfully fetched data from backup source for {market}")
            except Exception as e:
                print(f"Error fetching from backup source for {market}: {e}")
                continue
        elif not primary_success:
            # If primary failed and no backup, skip this market
            continue
            
        # Parse the HTML - only reached if either primary or backup was successful
        try:
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Extract results from tables
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in reversed(rows):  # Start from most recent (bottom of table)
                    cols = row.find_all("td")
                    if len(cols) >= 4 and 'to' in cols[0].text:
                        start_date = cols[0].text.split('to')[0].strip()
                        try:
                            base_date = datetime.datetime.strptime(start_date, "%d/%m/%Y").date()
                        except Exception as e:
                            print(f"Error parsing date {start_date}: {e}")
                            continue
        except Exception as e:
            print(f"Error parsing HTML for {market}: {e}")
            continue
                            
                        # Get all cells (excluding the date range cell)
                        cells = cols[1:]
                        total_days = len(cells) // 3
                        
                        # Process each day's results, starting from most recent
                        for i in reversed(range(total_days)):
                            date = (base_date + datetime.timedelta(days=i)).strftime("%d/%m/%Y")
                            o, j, c = cells[i*3:(i+1)*3]
                            
                            # Skip if result not declared
                            if '**' in o.text or '**' in j.text or '**' in c.text:
                                continue
                            
                            # Extract values
                            try:
                                open_val = parse_cell(o)
                                jodi_val = parse_cell(j)
                                close_val = parse_cell(c)
                                
                                # Skip if any value is empty
                                if not open_val or not jodi_val or not close_val:
                                    continue
                                
                                # Create and add the result
                                result_date = base_date + datetime.timedelta(days=i)
                                result = {
                                    'Date': date,
                                    'Market': market,
                                    'Open': open_val,
                                    'Jodi': jodi_val,
                                    'Close': close_val,
                                    'day_of_week': result_date.strftime('%A'),
                                    'is_weekend': 1 if result_date.weekday() >= 5 else 0,
                                    'is_holiday': 0
                                }
                                
                                all_results.append(result)
                                print(f"Found result for {market} on {date}")
                                
                                # Collect all recent results instead of just the most recent
                                # Continue processing the row to find more results
                                # We won't break here anymore to collect multiple days of results
                            except Exception as e:
                                print(f"Error processing result for {market} on {date}: {e}")
                                continue
                        
                        # Break after processing the first date range row
                        break
        except Exception as e:
            print(f"Error fetching data for {market}: {e}")
            traceback.print_exc()
    
    # Convert results to DataFrame
    if all_results:
        df = pd.DataFrame(all_results)
        print(f"Successfully scraped {len(df)} results")
        return df
    else:
        print("No results scraped from any website")
        return pd.DataFrame()

def update_csv_with_new_results(new_results_df):
    """
    Update the CSV file with new results
    
    Args:
        new_results_df: DataFrame containing new results
    """
    if new_results_df.empty:
        print("No new results to add to CSV")
        return False
        
    # Path to the CSV file
    csv_path = 'attached_assets/enhanced_satta_data.csv'
    
    # Check if CSV exists
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False
    
    try:
        # Load the existing CSV
        existing_data = pd.read_csv(csv_path)
        print(f"Loaded existing CSV with {len(existing_data)} rows")
        
        # Calculate derived fields for new results
        for index, row in new_results_df.iterrows():
            derived_fields = calculate_derived_fields(row)
            for key, value in derived_fields.items():
                new_results_df.at[index, key] = value
        
        # Add new results to existing data, avoiding duplicates
        # Create a key for comparison (Date + Market)
        existing_data['key'] = existing_data['Date'] + existing_data['Market']
        new_results_df['key'] = new_results_df['Date'] + new_results_df['Market']
        
        # Filter out rows that already exist in the CSV
        new_rows = new_results_df[~new_results_df['key'].isin(existing_data['key'])]
        
        if new_rows.empty:
            print("All results already exist in CSV, no updates needed")
            return False
        
        # Remove the temporary key column
        new_rows = new_rows.drop(columns=['key'])
        existing_data = existing_data.drop(columns=['key'])
        
        # Append new rows to existing data
        updated_data = pd.concat([existing_data, new_rows], ignore_index=True)
        
        # Save the updated data
        updated_data.to_csv(csv_path, index=False)
        print(f"Successfully updated CSV with {len(new_rows)} new results, total {len(updated_data)} rows")
        return True
    except Exception as e:
        print(f"Error updating CSV: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """
    Fetch and process results from web and CSV data
    """
    print("Starting to import results...")
    
    # First try to scrape the latest results from websites
    new_results_df = scrape_satta_results()
    
    # Update the CSV with new results if any
    if not new_results_df.empty:
        update_csv_with_new_results(new_results_df)
        
        # If we have new results, add them directly to the database as well
        with app.app_context():
            try:
                for _, row in new_results_df.iterrows():
                    try:
                        # Parse the date
                        date_parts = row['Date'].split('/')
                        date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                        
                        # Check if result already exists
                        existing = Result.query.filter_by(date=date_obj, market=row['Market']).first()
                        if existing:
                            # Update existing result if needed
                            if existing.open == 'Off' or existing.open is None:
                                existing.open = row['Open']
                            if existing.close == 'Off' or existing.close is None:
                                existing.close = row['Close']
                            if existing.jodi == 'Off' or existing.jodi is None:
                                existing.jodi = row['Jodi']
                            # Update other fields
                            for field in ['day_of_week', 'is_weekend', 'open_sum', 'close_sum', 
                                          'mirror_open', 'mirror_close', 'reverse_jodi']:
                                if field in row and not pd.isna(row[field]):
                                    setattr(existing, field, row[field])
                            db.session.commit()
                            print(f"Updated existing result for {row['Market']} on {row['Date']}")
                        else:
                            # Create new result
                            new_result = Result(
                                date=date_obj,
                                market=row['Market'],
                                open=row['Open'],
                                jodi=row['Jodi'],
                                close=row['Close'],
                                day_of_week=row['day_of_week'],
                                is_weekend=bool(row['is_weekend']) if 'is_weekend' in row else False
                            )
                            
                            # Add calculated fields if they exist
                            for field in ['open_sum', 'close_sum', 'mirror_open', 'mirror_close', 
                                          'reverse_jodi', 'prev_jodi_distance']:
                                if field in row and not pd.isna(row[field]):
                                    setattr(new_result, field, row[field])
                            
                            db.session.add(new_result)
                            db.session.commit()
                            print(f"Added new result for {row['Market']} on {row['Date']}")
                    except Exception as e:
                        print(f"Error processing scraped row: {str(e)}")
                        db.session.rollback()
                        continue
                
                print("Successfully processed scraped results")
                # After adding new results, return True to indicate success
                return True
            except Exception as e:
                print(f"Error processing scraped results: {str(e)}")
                db.session.rollback()
    
    # Path to the CSV file
    csv_path = 'attached_assets/enhanced_satta_data.csv'
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False
    
    # Load the CSV data (now potentially updated with scraped results)
    try:
        data = pd.read_csv(csv_path)
        print(f"Successfully loaded {len(data)} rows from CSV")
    except Exception as e:
        print(f"Error loading CSV data: {str(e)}")
        return False
    
    # Process data in batches to avoid memory issues
    print(f"Importing all {len(data)} rows in batches")
    
    # Define batch size
    BATCH_SIZE = 1000
    total_rows = len(data)
    
    # Set up application context for database operations
    with app.app_context():
        count = 0
        for market in data['Market'].unique():
            print(f"Processing market: {market}")
            market_data = data[data['Market'] == market]
            
            try:
                # Process each row for this market
                market_count = 0
                for _, row in market_data.iterrows():
                    try:
                        # Parse the date (assuming DD/MM/YYYY format in CSV)
                        date_parts = row['Date'].split('/')
                        date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                        
                        # Skip 'Off' days
                        if row['Open'] == 'Off' or row['Close'] == 'Off':
                            continue
                        
                        # Check if result already exists
                        existing = Result.query.filter_by(date=date_obj, market=row['Market']).first()
                        if existing:
                            # Skip if already exists
                            continue
                        
                        # Create new result record
                        new_result = Result(
                            date=date_obj,
                            market=row['Market'],
                            open=row['Open'],
                            jodi=row['Jodi'],
                            close=row['Close'],
                            day_of_week=row['day_of_week'],
                            is_weekend=bool(row['is_weekend']),
                            open_sum=row['open_sum'] if not pd.isna(row['open_sum']) else None,
                            close_sum=row['close_sum'] if not pd.isna(row['close_sum']) else None,
                            mirror_open=row['mirror_open'] if not pd.isna(row['mirror_open']) else None,
                            mirror_close=row['mirror_close'] if not pd.isna(row['mirror_close']) else None,
                            reverse_jodi=row['reverse_jodi'] if not pd.isna(row['reverse_jodi']) else None,
                            is_holiday=bool(row['is_holiday'])
                        )
                        
                        # Check if prev_jodi_distance exists in the row
                        if 'prev_jodi_distance' in row and not pd.isna(row['prev_jodi_distance']):
                            new_result.prev_jodi_distance = row['prev_jodi_distance']
                        
                        # Add to database
                        db.session.add(new_result)
                        count += 1
                        market_count += 1
                        
                        # Commit in smaller batches
                        if market_count % 200 == 0:
                            db.session.commit()
                            print(f"Processed {market_count} rows for {market}, total {count}/{total_rows}")
                        
                    except Exception as e:
                        print(f"Error processing row for {market}: {str(e)}")
                        traceback.print_exc()
                        # Continue with next row
                        continue
                
                # Commit remaining rows for this market
                try:
                    db.session.commit()
                    print(f"Completed market {market}: {market_count} records imported")
                except SQLAlchemyError as e:
                    db.session.rollback()
                    print(f"Database error when committing {market} data: {str(e)}")
                
            except Exception as e:
                print(f"Error processing market {market}: {str(e)}")
                traceback.print_exc()
                db.session.rollback()
        
        print(f"Successfully processed {count} results across all markets")
        return True

if __name__ == "__main__":
    main()