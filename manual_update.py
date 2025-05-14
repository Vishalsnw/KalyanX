import os
import pandas as pd
import datetime
import traceback
import requests
from bs4 import BeautifulSoup
from app import app, db
from models import Result, Prediction
import logging
from utils import calculate_derived_fields
from ml.predictor import generate_predictions, calculate_confidence_score

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

# Headers
HEADERS = {"User-Agent": "Mozilla/5.0"}

def parse_cell(cell):
    """Parse cell content from HTML"""
    parts = cell.decode_contents().split('<br>')
    return ''.join(BeautifulSoup(p, 'html.parser').get_text(strip=True) for p in parts)

def get_recent_results(market, url, days=30):
    """Get recent results for a specific market"""
    logger.info(f"Fetching recent results for {market}")
    results = []
    
    try:
        # Make request
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch data for {market}: {response.status_code}")
            return results
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Process tables
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4 and 'to' in cols[0].text:
                    date_range = cols[0].text.strip()
                    try:
                        start_date_str = date_range.split('to')[0].strip()
                        start_date = datetime.datetime.strptime(start_date_str, "%d/%m/%Y").date()
                        
                        # Get cells
                        cells = cols[1:]
                        total_days = len(cells) // 3
                        
                        # Process each day
                        for i in range(total_days):
                            date = start_date + datetime.timedelta(days=i)
                            o, j, c = cells[i*3:(i+1)*3]
                            
                            # Skip if results not declared
                            if '**' in o.text or '**' in j.text or '**' in c.text:
                                continue
                            
                            # Extract values
                            open_val = parse_cell(o)
                            jodi_val = parse_cell(j)
                            close_val = parse_cell(c)
                            
                            # Skip if any value is empty
                            if not open_val or not jodi_val or not close_val:
                                continue
                            
                            # Add result
                            result = {
                                'Date': date.strftime("%d/%m/%Y"),
                                'Market': market,
                                'Open': open_val,
                                'Jodi': jodi_val,
                                'Close': close_val,
                                'day_of_week': date.strftime('%A'),
                                'is_weekend': 1 if date.weekday() >= 5 else 0,
                                'is_holiday': 0
                            }
                            results.append(result)
                            
            # Only need most recent data
            break
    except Exception as e:
        logger.error(f"Error fetching data for {market}: {e}")
        traceback.print_exc()
    
    logger.info(f"Found {len(results)} results for {market}")
    return results

def update_database(results):
    """Update database with results"""
    logger.info(f"Updating database with {len(results)} results")
    count = 0
    
    for result in results:
        try:
            # Parse date
            date_parts = result['Date'].split('/')
            date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            
            # Check if result exists
            existing = Result.query.filter_by(date=date_obj, market=result['Market']).first()
            
            # Calculate derived fields
            derived_fields = calculate_derived_fields(result)
            result.update(derived_fields)
            
            if existing:
                # Update existing
                existing.open = result['Open']
                existing.jodi = result['Jodi']
                existing.close = result['Close']
                
                # Update derived fields
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
                
                logger.info(f"Updated result for {result['Market']} on {date_obj}")
            else:
                # Create new
                new_result = Result(
                    date=date_obj,
                    market=result['Market'],
                    open=result['Open'],
                    jodi=result['Jodi'],
                    close=result['Close'],
                    day_of_week=result['day_of_week'],
                    is_weekend=bool(result['is_weekend'])
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
                if 'prev_jodi_distance' in result:
                    new_result.prev_jodi_distance = result['prev_jodi_distance']
                
                db.session.add(new_result)
                logger.info(f"Added new result for {result['Market']} on {date_obj}")
            
            # Commit
            db.session.commit()
            count += 1
        except Exception as e:
            logger.error(f"Error updating result for {result['Market']} on {result['Date']}: {e}")
            db.session.rollback()
    
    logger.info(f"Added/updated {count} results in database")
    return count

def generate_predictions_for_all_markets():
    """Generate predictions for all markets"""
    logger.info("Generating predictions for all markets")
    
    # Get unique markets
    markets = Result.query.with_entities(Result.market).distinct().all()
    markets = [m[0] for m in markets]
    
    predictions = []
    for market in markets:
        try:
            # Get latest result
            latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
            
            if not latest_result:
                logger.warning(f"No results found for {market}")
                continue
            
            # Calculate next day
            next_day = latest_result.date + datetime.timedelta(days=1)
            
            # Check if prediction exists
            existing = Prediction.query.filter_by(date=next_day, market=market).first()
            if existing:
                logger.info(f"Prediction already exists for {market} on {next_day}")
                predictions.append(existing)
                continue
            
            # Get market data
            results = Result.query.filter_by(market=market).order_by(Result.date).all()
            
            # Convert to DataFrame
            data = []
            for result in results:
                row = {
                    'Date': result.date.strftime('%d/%m/%Y'),
                    'Market': result.market,
                    'Open': result.open,
                    'Jodi': result.jodi,
                    'Close': result.close,
                    'day_of_week': result.day_of_week,
                    'is_weekend': result.is_weekend,
                    'open_sum': result.open_sum,
                    'close_sum': result.close_sum,
                    'mirror_open': result.mirror_open,
                    'mirror_close': result.mirror_close,
                    'reverse_jodi': result.reverse_jodi,
                    'is_holiday': result.is_holiday,
                    'prev_jodi_distance': result.prev_jodi_distance
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            
            if len(df) < 30:
                logger.warning(f"Not enough data for {market}, need at least 30 days")
                continue
            
            # Generate prediction
            prediction_data = generate_predictions(df, market)
            
            # Calculate confidence
            confidence_score = calculate_confidence_score(market)
            
            # Create new prediction
            new_prediction = Prediction(
                date=next_day,
                market=market,
                open_digits=prediction_data.get('open_digits'),
                close_digits=prediction_data.get('close_digits'),
                jodi_list=prediction_data.get('jodi_list'),
                patti_list=prediction_data.get('patti_list'),
                confidence_score=confidence_score
            )
            
            db.session.add(new_prediction)
            db.session.commit()
            
            logger.info(f"Generated prediction for {market} on {next_day}")
            predictions.append(new_prediction)
        except Exception as e:
            logger.error(f"Error generating prediction for {market}: {e}")
            db.session.rollback()
    
    logger.info(f"Generated {len(predictions)} predictions")
    return predictions

def main():
    """Update data and generate predictions"""
    logger.info("Starting manual update process")
    
    with app.app_context():
        # Get results for all markets
        all_results = []
        for market, url in MARKETS.items():
            results = get_recent_results(market, url)
            all_results.extend(results)
        
        # Update database
        if all_results:
            update_database(all_results)
            
            # Generate predictions
            generate_predictions_for_all_markets()
    
    logger.info("Manual update completed")

if __name__ == "__main__":
    main()