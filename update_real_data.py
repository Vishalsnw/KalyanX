import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import traceback
from app import app, db
from models import Result
from utils import calculate_derived_fields
from sqlalchemy.exc import SQLAlchemyError

CSV_FILE = "attached_assets/enhanced_satta_data.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}

MARKETS = {
    "Time Bazar": "https://dpbossattamatka.com/panel-chart-record/time-bazar.php",
    "Milan Day": "https://dpbossattamatka.com/panel-chart-record/milan-day.php",
    "Rajdhani Day": "https://dpbossattamatka.com/panel-chart-record/rajdhani-day.php",
    "Kalyan": "https://dpbossattamatka.com/panel-chart-record/kalyan.php",
    "Milan Night": "https://dpbossattamatka.com/panel-chart-record/milan-night.php",
    "Rajdhani Night": "https://dpbossattamatka.com/panel-chart-record/rajdhani-night.php",
    "Main Bazar": "https://dpbossattamatka.com/panel-chart-record/main-bazar.php"
}

def parse_cell(cell):
    parts = cell.decode_contents().split('<br>')
    return ''.join(BeautifulSoup(p, 'html.parser').get_text(strip=True) for p in parts)

def get_latest_result(url):
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in reversed(rows):
                cols = row.find_all("td")
                if len(cols) >= 4 and 'to' in cols[0].text:
                    start_date = cols[0].text.split('to')[0].strip()
                    try:
                        base_date = datetime.datetime.strptime(start_date, "%d/%m/%Y")
                    except:
                        continue
                    cells = cols[1:]
                    total_days = len(cells) // 3
                    index = total_days - 1
                    date = (base_date + datetime.timedelta(days=index)).strftime("%d/%m/%Y")
                    o, j, c = cells[index*3: index*3+3]
                    if '**' in o.text or '**' in j.text or '**' in c.text:
                        return {'date': date, 'open': '', 'jodi': '', 'close': '', 'status': 'Not declared'}
                    return {
                        'date': date,
                        'open': parse_cell(o),
                        'jodi': parse_cell(j),
                        'close': parse_cell(c),
                        'status': 'ok'
                    }
    except Exception as e:
        print(f"Error fetching data: {e}")
        traceback.print_exc()
        return {'status': f'error: {e}'}

def get_all_results_from_page(url, market):
    """Get all results from a market page"""
    results = []
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for table in soup.find_all("table"):
            rows = table.find_all("tr")
            for row in rows:
                cols = row.find_all("td")
                if len(cols) >= 4 and 'to' in cols[0].text:
                    date_range = cols[0].text.strip()
                    try:
                        start_date_str = date_range.split('to')[0].strip()
                        start_date = datetime.datetime.strptime(start_date_str, "%d/%m/%Y")
                        
                        # Get all cells (excluding the date range cell)
                        cells = cols[1:]
                        total_days = len(cells) // 3
                        
                        # Process each day's results
                        for i in range(total_days):
                            date = (start_date + datetime.timedelta(days=i)).strftime("%d/%m/%Y")
                            o, j, c = cells[i*3:(i+1)*3]
                            
                            # Skip if result not declared
                            if '**' in o.text or '**' in j.text or '**' in c.text:
                                continue
                                
                            # Extract values
                            open_val = parse_cell(o)
                            jodi_val = parse_cell(j)
                            close_val = parse_cell(c)
                            
                            # Skip if any value is empty
                            if not open_val or not jodi_val or not close_val:
                                continue
                                
                            # Create result record
                            record = {
                                'Date': date,
                                'Market': market,
                                'Open': open_val,
                                'Jodi': jodi_val,
                                'Close': close_val,
                                'day_of_week': (start_date + datetime.timedelta(days=i)).strftime('%A'),
                                'is_weekend': 1 if (start_date + datetime.timedelta(days=i)).weekday() >= 5 else 0,
                                'is_holiday': 0
                            }
                            
                            results.append(record)
                    except Exception as e:
                        print(f"Error parsing row in {market}: {e}")
                        continue
    except Exception as e:
        print(f"Error processing {market}: {e}")
        traceback.print_exc()
    
    return results

def update_csv_with_results(results):
    """Update CSV with new results"""
    if not results:
        print("No results to add to CSV")
        return
    
    try:
        # Load existing CSV or create empty dataframe
        if os.path.exists(CSV_FILE):
            df = pd.read_csv(CSV_FILE)
            existing_dates = set(zip(df['Date'], df['Market']))
        else:
            df = pd.DataFrame(columns=['Date', 'Market', 'Open', 'Jodi', 'Close'])
            existing_dates = set()
        
        # Filter out existing records
        new_results = [r for r in results if (r['Date'], r['Market']) not in existing_dates]
        
        if not new_results:
            print("All results already exist in CSV")
            return df, []
        
        # Calculate derived fields
        for result in new_results:
            derived_fields = calculate_derived_fields(result)
            result.update(derived_fields)
        
        # Create dataframe with new results
        new_df = pd.DataFrame(new_results)
        
        # Append to existing data
        updated_df = pd.concat([df, new_df], ignore_index=True)
        
        # Save updated CSV
        updated_df.to_csv(CSV_FILE, index=False)
        print(f"Added {len(new_results)} new results to CSV")
        
        return updated_df, new_results
    except Exception as e:
        print(f"Error updating CSV: {e}")
        traceback.print_exc()
        return None, []

def update_database_with_results(results):
    """Update database with new results"""
    if not results:
        print("No results to add to database")
        return 0
    
    with app.app_context():
        count = 0
        for result in results:
            try:
                # Parse date
                date_parts = result['Date'].split('/')
                date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                
                # Check if result already exists
                existing = Result.query.filter_by(date=date_obj, market=result['Market']).first()
                if existing:
                    # Update existing record
                    existing.open = result['Open']
                    existing.jodi = result['Jodi']
                    existing.close = result['Close']
                    if 'open_sum' in result:
                        existing.open_sum = result['open_sum']
                    if 'close_sum' in result:
                        existing.close_sum = result['close_sum']
                    if 'mirror_open' in result:
                        existing.mirror_open = result['mirror_open']
                    if 'mirror_close' in result:
                        existing.mirror_close = result['mirror_close']
                    if 'reverse_jodi' in result:
                        existing.reverse_jodi = result['reverse_jodi']
                else:
                    # Create new result
                    new_result = Result(
                        date=date_obj,
                        market=result['Market'],
                        open=result['Open'],
                        jodi=result['Jodi'],
                        close=result['Close'],
                        day_of_week=result['day_of_week'],
                        is_weekend=bool(result['is_weekend']),
                        is_holiday=bool(result['is_holiday'])
                    )
                    
                    # Add derived fields
                    if 'open_sum' in result:
                        new_result.open_sum = result['open_sum']
                    if 'close_sum' in result:
                        new_result.close_sum = result['close_sum']
                    if 'mirror_open' in result:
                        new_result.mirror_open = result['mirror_open']
                    if 'mirror_close' in result:
                        new_result.mirror_close = result['mirror_close']
                    if 'reverse_jodi' in result:
                        new_result.reverse_jodi = result['reverse_jodi']
                    
                    db.session.add(new_result)
                
                # Commit after each record
                db.session.commit()
                count += 1
                
            except Exception as e:
                print(f"Error adding result for {result['Market']} on {result['Date']}: {e}")
                db.session.rollback()
        
        print(f"Added/updated {count} records in the database")
        return count

def generate_predictions():
    """Generate predictions for markets with new results"""
    print("Generating predictions for latest data...")
    try:
        # Import needed here to avoid circular imports
        from services.prediction_service import update_predictions_for_all_markets
        
        with app.app_context():
            # Generate predictions for all markets
            update_predictions_for_all_markets()
            print("Predictions generated successfully")
    except Exception as e:
        print(f"Error generating predictions: {e}")
        traceback.print_exc()

def main():
    """Update data with real results from websites"""
    print("Starting to update data with real results...")
    
    all_results = []
    
    # Get results for each market
    for market, url in MARKETS.items():
        print(f"Getting results for {market}...")
        market_results = get_all_results_from_page(url, market)
        print(f"Found {len(market_results)} results for {market}")
        all_results.extend(market_results)
    
    # Update CSV with new results
    _, new_results = update_csv_with_results(all_results)
    
    # Update database with new results
    if new_results:
        count = update_database_with_results(new_results)
        if count > 0:
            # Generate predictions for the updated data
            generate_predictions()
    
    print("Data update completed")

if __name__ == "__main__":
    main()