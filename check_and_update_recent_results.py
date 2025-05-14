import os
import requests
import datetime
import pandas as pd
from bs4 import BeautifulSoup
from app import app, db
from models import Result
from utils import calculate_derived_fields

# Market URLs - expanded with more markets for better coverage
MARKETS = {
    "Milan Night": "https://dpbossattamatka.com/panel-chart-record/milan-night.php",
    "Milan Day": "https://dpbossattamatka.com/panel-chart-record/milan-day.php",
    "Main Bazar": "https://dpbossattamatka.com/panel-chart-record/main-bazar.php", 
    "Rajdhani Night": "https://dpbossattamatka.com/panel-chart-record/rajdhani-night.php",
    "Kalyan": "https://dpbossattamatka.com/panel-chart-record/kalyan.php",
    "Time Bazar": "https://dpbossattamatka.com/panel-chart-record/time-bazar.php",
    "Madhur Day": "https://dpbossattamatka.com/panel-chart-record/madhur-day.php",
    "Madhur Night": "https://dpbossattamatka.com/panel-chart-record/madhur-night.php",
}

# Set up headers
HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_cell(cell):
    """Parse cell content from HTML"""
    parts = cell.decode_contents().split('<br>')
    return ''.join(BeautifulSoup(p, 'html.parser').get_text(strip=True) for p in parts)

def main():
    """Check and update results for specified dates or recent dates"""
    # If no specific date is provided, check the last 2 days
    # This will ensure we catch recent results that might be missing
    today = datetime.datetime.now().date()
    yesterday = today - datetime.timedelta(days=1)
    
    # Check both yesterday and today to ensure all recent results are captured
    dates_to_check = [
        yesterday.strftime("%d/%m/%Y"),  # Yesterday
        today.strftime("%d/%m/%Y")       # Today
    ]
    
    print(f"Checking for results on multiple dates: {', '.join(dates_to_check)}")
    
    # List to store results found
    all_results = []
    
    # Check each market
    for market, url in MARKETS.items():
        print(f"Checking May 9th results for {market}...")
        
        try:
            # Fetch the data
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.encoding = 'utf-8'
            
            if res.status_code != 200:
                print(f"Failed to fetch from {url}: Status code {res.status_code}")
                continue
            
            # Parse HTML
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Look for results on our target dates
            found_date = False
            
            # Extract results from tables
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 4 and 'to' in cols[0].text:
                        start_date = cols[0].text.split('to')[0].strip()
                        try:
                            base_date = datetime.datetime.strptime(start_date, "%d/%m/%Y").date()
                        except Exception as e:
                            print(f"Error parsing date {start_date}: {e}")
                            continue
                            
                        # Get all cells (excluding the date range cell)
                        cells = cols[1:]
                        total_days = len(cells) // 3
                        
                        # Process each day's results
                        for i in range(total_days):
                            date = (base_date + datetime.timedelta(days=i)).strftime("%d/%m/%Y")
                            # Check if the date is in our dates to check list
                            if date in dates_to_check:
                                date_obj = datetime.datetime.strptime(date, "%d/%m/%Y").date()
                                print(f"Found data for {market} on {date}!")
                                found_date = True
                                
                                o, j, c = cells[i*3:(i+1)*3]
                                
                                # Skip if result not declared
                                if '**' in o.text or '**' in j.text or '**' in c.text:
                                    print(f"Result for {market} on {date} not yet declared")
                                    continue
                                
                                # Extract values
                                try:
                                    open_val = parse_cell(o)
                                    jodi_val = parse_cell(j)
                                    close_val = parse_cell(c)
                                    
                                    # Skip if any value is empty
                                    if not open_val or not jodi_val or not close_val:
                                        print(f"Result for {market} on {date} has empty values")
                                        continue
                                    
                                    # Create and add the result
                                    result = {
                                        'Date': date,
                                        'Market': market,
                                        'Open': open_val,
                                        'Jodi': jodi_val,
                                        'Close': close_val,
                                        'day_of_week': date_obj.strftime('%A'),
                                        'is_weekend': 1 if date_obj.weekday() >= 5 else 0,
                                        'is_holiday': 0
                                    }
                                    
                                    # Calculate derived fields
                                    derived_fields = calculate_derived_fields(result)
                                    for key, value in derived_fields.items():
                                        result[key] = value
                                    
                                    all_results.append(result)
                                    print(f"Found result for {market} on {date}: {open_val}-{jodi_val}-{close_val}")
                                except Exception as e:
                                    print(f"Error processing result for {market} on {date}: {e}")
            
            if not found_date:
                print(f"No results found for {market} on the checked dates")
                
        except Exception as e:
            print(f"Error checking results for {market}: {e}")
    
    # Update database with found results
    if all_results:
        print(f"Found {len(all_results)} results for the checked dates. Updating database...")
        with app.app_context():
            for result in all_results:
                try:
                    date_obj = datetime.datetime.strptime(result['Date'], "%d/%m/%Y").date()
                    
                    # Check if result already exists
                    existing = Result.query.filter_by(date=date_obj, market=result['Market']).first()
                    if existing:
                        print(f"Updating existing result for {result['Market']} on {result['Date']}")
                        existing.open = result['Open']
                        existing.jodi = result['Jodi'] 
                        existing.close = result['Close']
                        
                        # Update other fields
                        for field in ['day_of_week', 'is_weekend', 'open_sum', 'close_sum', 
                                    'mirror_open', 'mirror_close', 'reverse_jodi']:
                            if field in result and result[field] is not None:
                                setattr(existing, field, result[field])
                    else:
                        print(f"Adding new result for {result['Market']} on {result['Date']}")
                        new_result = Result(
                            date=date_obj,
                            market=result['Market'],
                            open=result['Open'],
                            jodi=result['Jodi'],
                            close=result['Close'],
                            day_of_week=result['day_of_week'],
                            is_weekend=bool(result['is_weekend'])
                        )
                        
                        # Add calculated fields
                        for field in ['open_sum', 'close_sum', 'mirror_open', 'mirror_close', 
                                    'reverse_jodi', 'prev_jodi_distance']:
                            if field in result and result[field] is not None:
                                setattr(new_result, field, result[field])
                        
                        db.session.add(new_result)
                    
                    db.session.commit()
                    print(f"Successfully updated/added result for {result['Market']} on {result['Date']}")
                    
                    # Try to update predictions based on new results
                    try:
                        from generate_predictions import generate_predictions_for_market
                        print(f"Generating new predictions for {result['Market']} based on updated results")
                        generate_predictions_for_market(result['Market'])
                    except Exception as pred_err:
                        print(f"Error generating predictions: {pred_err}")
                        
                except Exception as e:
                    print(f"Error updating database with result: {e}")
                    db.session.rollback()
    else:
        print("No results found to update for the checked dates")
    
    print("Results check complete for the specified dates")

if __name__ == "__main__":
    main()