import requests
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import os
import traceback
from app import app, db
from models import Result, Prediction
from utils import calculate_derived_fields
from ml.predictor import generate_predictions, calculate_confidence_score

# Market URLs
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
CSV_FILE = "attached_assets/enhanced_satta_data.csv"

def parse_cell(cell):
    """Parse cell content from HTML"""
    parts = cell.decode_contents().split('<br>')
    return ''.join(BeautifulSoup(p, 'html.parser').get_text(strip=True) for p in parts)

def get_latest_results():
    """Get latest results for all markets"""
    print("Fetching latest results...")
    all_results = []
    
    for market, url in MARKETS.items():
        try:
            print(f"Checking {market}...")
            
            response = requests.get(url, headers=HEADERS, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                print(f"Failed to fetch from {url}: {response.status_code}")
                continue
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for table in soup.find_all('table'):
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4 and 'to' in cols[0].text:
                        try:
                            # Get date range
                            date_range = cols[0].text.strip()
                            start_date_str = date_range.split('to')[0].strip()
                            start_date = datetime.datetime.strptime(start_date_str, "%d/%m/%Y").date()
                            
                            # Get cells
                            cells = cols[1:]
                            total_days = len(cells) // 3
                            
                            # Get most recent result (last day in range)
                            date = start_date + datetime.timedelta(days=total_days-1)
                            date_str = date.strftime("%d/%m/%Y")
                            
                            o, j, c = cells[-3], cells[-2], cells[-1]
                            
                            # Skip if result not declared
                            if '**' in o.text or '**' in j.text or '**' in c.text:
                                print(f"Result not declared for {market} on {date_str}")
                                continue
                            
                            # Extract values
                            open_val = parse_cell(o)
                            jodi_val = parse_cell(j)
                            close_val = parse_cell(c)
                            
                            # Skip if any value is empty
                            if not open_val or not jodi_val or not close_val:
                                print(f"Incomplete result for {market} on {date_str}")
                                continue
                            
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
                            
                            all_results.append(result)
                            print(f"Found result for {market} on {date_str}")
                            
                            # After finding most recent result, break
                            break
                        except Exception as e:
                            print(f"Error processing {market}: {e}")
                        break
                break
        except Exception as e:
            print(f"Error fetching data for {market}: {e}")
    
    print(f"Found {len(all_results)} latest results")
    return all_results

def update_csv(results):
    """Update CSV with new results"""
    if not results:
        print("No results to add to CSV")
        return
    
    # Load existing CSV
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        print(f"Loaded existing CSV with {len(df)} rows")
    else:
        df = pd.DataFrame(columns=['Date', 'Market', 'Open', 'Jodi', 'Close'])
        print("Created new CSV file")
    
    # Get existing date-market combinations
    existing = set(zip(df['Date'], df['Market']))
    
    # Filter out existing records
    new_results = []
    for result in results:
        if (result['Date'], result['Market']) not in existing:
            derived_fields = calculate_derived_fields(result)
            result.update(derived_fields)
            new_results.append(result)
    
    if not new_results:
        print("All results already exist in CSV")
        return
    
    # Add new results to dataframe
    new_df = pd.DataFrame(new_results)
    updated_df = pd.concat([df, new_df], ignore_index=True)
    
    # Save updated CSV
    updated_df.to_csv(CSV_FILE, index=False)
    print(f"Added {len(new_results)} new results to CSV")

def update_database(results):
    """Update database with results"""
    if not results:
        print("No results to add to database")
        return 0
    
    count = 0
    for result in results:
        try:
            # Parse date
            date_parts = result['Date'].split('/')
            date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            
            # Calculate derived fields if not already done
            if 'open_sum' not in result:
                derived_fields = calculate_derived_fields(result)
                result.update(derived_fields)
            
            # Check if result exists
            existing = Result.query.filter_by(date=date_obj, market=result['Market']).first()
            
            if existing:
                # Update existing result
                existing.open = result['Open']
                existing.jodi = result['Jodi']
                existing.close = result['Close']
                
                # Update derived fields
                for field in ['open_sum', 'close_sum', 'mirror_open', 'mirror_close', 'reverse_jodi']:
                    if field in result:
                        setattr(existing, field, result[field])
                
                print(f"Updated existing result: {result['Market']} on {result['Date']}")
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
                    is_holiday=bool(result['is_holiday']) if 'is_holiday' in result else False
                )
                
                # Add derived fields
                for field in ['open_sum', 'close_sum', 'mirror_open', 'mirror_close', 'reverse_jodi']:
                    if field in result:
                        setattr(new_result, field, result[field])
                
                db.session.add(new_result)
                print(f"Added new result: {result['Market']} on {result['Date']}")
            
            db.session.commit()
            count += 1
        except Exception as e:
            print(f"Error updating database: {e}")
            db.session.rollback()
    
    print(f"Updated {count} records in database")
    return count

def generate_predictions():
    """Generate predictions for next day after latest results"""
    print("Generating predictions...")
    
    # Get markets
    markets = Result.query.with_entities(Result.market).distinct().all()
    markets = [m[0] for m in markets]
    
    for market in markets:
        try:
            # Get latest result
            latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
            
            if not latest_result:
                print(f"No results found for {market}")
                continue
            
            # Calculate prediction date (next day after latest result)
            prediction_date = latest_result.date + datetime.timedelta(days=1)
            
            # Check if prediction already exists
            existing = Prediction.query.filter_by(market=market, date=prediction_date).first()
            if existing:
                print(f"Prediction already exists for {market} on {prediction_date}")
                continue
            
            # Get all results for this market
            results = Result.query.filter_by(market=market).all()
            
            # Convert to dataframe
            data = []
            for r in results:
                row = {
                    'Date': r.date.strftime('%d/%m/%Y'),
                    'Market': r.market,
                    'Open': r.open,
                    'Jodi': r.jodi,
                    'Close': r.close,
                    'day_of_week': r.day_of_week,
                    'is_weekend': r.is_weekend,
                    'open_sum': r.open_sum,
                    'close_sum': r.close_sum,
                    'mirror_open': r.mirror_open,
                    'mirror_close': r.mirror_close,
                    'reverse_jodi': r.reverse_jodi,
                    'is_holiday': r.is_holiday,
                    'prev_jodi_distance': r.prev_jodi_distance
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            
            # Generate prediction
            print(f"Generating prediction for {market} on {prediction_date}")
            prediction_data = generate_predictions(df, market)
            
            # Calculate confidence score
            confidence_score = calculate_confidence_score(market)
            
            # Create new prediction
            new_prediction = Prediction(
                date=prediction_date,
                market=market,
                open_digits=prediction_data.get('open_digits'),
                close_digits=prediction_data.get('close_digits'),
                jodi_list=prediction_data.get('jodi_list'),
                patti_list=prediction_data.get('patti_list'),
                confidence_score=confidence_score
            )
            
            db.session.add(new_prediction)
            db.session.commit()
            
            print(f"Created prediction for {market} on {prediction_date}")
        except Exception as e:
            print(f"Error generating prediction for {market}: {e}")
            db.session.rollback()
    
    print("Prediction generation complete")

def main():
    """Update data and generate predictions"""
    print("Starting quick update process...")
    
    # Get latest results
    results = get_latest_results()
    
    # Update CSV
    update_csv(results)
    
    with app.app_context():
        # Update database
        update_database(results)
        
        # Generate predictions
        generate_predictions()
    
    print("Quick update process completed")

if __name__ == "__main__":
    main()