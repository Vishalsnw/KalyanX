import time
import datetime
import os
import sys
import requests
from bs4 import BeautifulSoup
import pandas as pd
import logging
from app import app, db
from models import Result
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def parse_cell(cell):
    """Parse cell content from HTML"""
    try:
        return cell.text.strip() if cell else None
    except:
        return None

def get_market_results(market_name):
    """
    Scrape results for a specific market from multiple sources
    Returns the latest result for the market
    """
    # Define multiple sources with different URLs to increase chances of getting results
    sources = [
        {
            "name": "dpbossattamatka",
            "url_pattern": "https://dpbossattamatka.com/panel-chart-record/{market}.php",
            "market_transform": lambda m: m.lower().replace(' ', '-')
        },
        {
            "name": "sattamatkaresult",
            "url_pattern": "https://sattamatkaresult.co.in/satta-matka-results-today.php",
            "market_transform": lambda m: m
        },
        {
            "name": "sattamatkamarket",
            "url_pattern": "https://sattamatkamarket.co.in/all-matka-result-today.php",
            "market_transform": lambda m: m
        }
    ]
    
    # Try each source until we get a valid result
    for source in sources:
        try:
            source_name = source["name"]
            market_transform = source["market_transform"]
            url_market_name = market_transform(market_name)
            url = source["url_pattern"].format(market=url_market_name)
            
            logger.info(f"Fetching results for {market_name} from {source_name} ({url})")
            
            response = requests.get(url, timeout=10, 
                                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
            if response.status_code != 200:
                logger.warning(f"Failed to fetch from {source_name}, status: {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find all table rows - different sites have different structures
            if source_name == "dpbossattamatka":
                # DPBoss specific parsing
                rows = soup.select('table tr')
                if not rows or len(rows) < 2:
                    logger.warning(f"No result rows found for {market_name} on {source_name}")
                    continue
                
                # Get the first row with data (index 1 to skip header)
                data_row = rows[1]
                cells = data_row.find_all('td')
                
                if len(cells) < 3:
                    logger.warning(f"Insufficient data in row for {market_name} on {source_name}")
                    continue
                
                # Parse date from the first cell
                date_str = parse_cell(cells[0])
                if not date_str:
                    logger.warning(f"No date found for {market_name} on {source_name}")
                    continue
                
                # Parse date in format DD/MM/YYYY
                try:
                    date_obj = datetime.datetime.strptime(date_str, '%d/%m/%Y').date()
                except:
                    logger.error(f"Error parsing date: {date_str} on {source_name}")
                    continue
                
                # Parse results
                result_text = parse_cell(cells[1])
                if not result_text:
                    logger.warning(f"No result found for {market_name} on {source_name}")
                    continue
                
                # Split the result text to extract open, close, and jodi
                parts = result_text.split('-')
                
                if len(parts) == 2:
                    open_result = parts[0].strip()
                    close_result = parts[1].strip()
                    jodi = f"{open_result[-1]}{close_result[-1]}"
                else:
                    # Handle incomplete results
                    open_result = parts[0].strip() if len(parts) > 0 else None
                    close_result = None
                    jodi = None
            
            else:
                # General parsing for other sites - look for the market name in any element
                # This is a bit more flexible but can be less accurate
                market_elements = soup.find_all(text=lambda text: market_name.lower() in text.lower() if text else False)
                if not market_elements:
                    logger.warning(f"Market {market_name} not found on {source_name}")
                    continue
                
                # Try to find parent elements that might contain results
                result_found = False
                date_obj = datetime.datetime.now().date()  # Default to today
                
                for element in market_elements:
                    parent = element.parent
                    
                    # Search through siblings and parent elements for possible results
                    result_elements = []
                    for sibling in parent.next_siblings:
                        if hasattr(sibling, 'get_text'):
                            text = sibling.get_text().strip()
                            if '-' in text and len(text) <= 10:  # Likely a result
                                result_elements.append(text)
                                
                    # If no results in siblings, try parent's siblings
                    if not result_elements and parent.parent:
                        for sibling in parent.parent.next_siblings:
                            if hasattr(sibling, 'get_text'):
                                text = sibling.get_text().strip()
                                if '-' in text and len(text) <= 10:  # Likely a result
                                    result_elements.append(text)
                    
                    # Process the first likely result
                    if result_elements:
                        result_text = result_elements[0]
                        parts = result_text.split('-')
                        
                        if len(parts) == 2:
                            open_result = parts[0].strip()
                            close_result = parts[1].strip()
                            jodi = f"{open_result[-1]}{close_result[-1]}"
                            result_found = True
                            break
                
                if not result_found:
                    logger.warning(f"Could not parse results for {market_name} from {source_name}")
                    continue
            
            # Create result dictionary
            result = {
                'date': date_obj,
                'market': market_name,
                'open': open_result,
                'close': close_result,
                'jodi': jodi
            }
            
            logger.info(f"Found result for {market_name} on {date_obj} from {source_name}: Open={open_result}, Close={close_result}, Jodi={jodi}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching results for {market_name} from {source_name}: {e}")
            # Continue to next source if one fails
            continue
    
    # If all sources failed, return None
    logger.error(f"All sources failed to get results for {market_name}")
    return None

def update_result_in_db(result):
    """Update or insert result in database"""
    if not result:
        return False
    
    with app.app_context():
        # Check if result already exists
        existing = Result.query.filter_by(
            date=result['date'],
            market=result['market']
        ).first()
        
        if existing:
            # Update existing result
            existing.open = result['open']
            existing.close = result['close']
            existing.jodi = result['jodi']
            existing.updated_at = datetime.datetime.utcnow()
            logger.info(f"Updated existing result for {result['market']} on {result['date']}")
        else:
            # Insert new result
            new_result = Result(
                date=result['date'],
                market=result['market'],
                open=result['open'],
                close=result['close'],
                jodi=result['jodi'],
                day_of_week=result['date'].strftime('%A'),
                is_weekend=result['date'].weekday() >= 5
            )
            db.session.add(new_result)
            logger.info(f"Inserted new result for {result['market']} on {result['date']}")
        
        try:
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            logger.error(f"Database error: {e}")
            return False

def should_check_market(market_name, current_time):
    """Check if a market should be checked based on its operating hours"""
    # Get market configuration
    if market_name not in Config.MARKETS:
        return False
    
    market_config = Config.MARKETS[market_name]
    open_time = market_config['open_time']
    close_time = market_config['close_time']
    
    # Convert time strings to datetime.time objects
    open_time_obj = datetime.datetime.strptime(open_time, '%H:%M').time()
    close_time_obj = datetime.datetime.strptime(close_time, '%H:%M').time()
    
    # Check if current time is within operating hours
    current_day = current_time.weekday()
    
    # Check if market operates on current day
    if current_day not in market_config['days']:
        logger.info(f"{market_name} does not operate on {current_time.strftime('%A')}")
        return False
    
    # Add buffer time (30 minutes after close time)
    close_datetime = datetime.datetime.combine(current_time.date(), close_time_obj)
    buffer_time = close_datetime + datetime.timedelta(minutes=30)
    
    current_time_only = current_time.time()
    
    # Check if current time is between open time and close time + buffer
    if current_time_only >= open_time_obj and current_time < buffer_time:
        return True
    
    # Check if it's past the close time + buffer (don't need to keep checking)
    if current_time_only >= buffer_time.time():
        return False
    
    return False

def continuous_market_check(market_name, interval_seconds=30, max_attempts=240):
    """
    Continuously check a specific market for results with the specified interval
    Will stop checking after max_attempts or if a new result is found
    Reduced interval to 30 seconds (from 60) and increased max attempts to 240 (from 180)
    to check more frequently and for a longer period
    """
    logger.info(f"Starting enhanced continuous check for {market_name} results (every {interval_seconds} seconds)")
    
    # Get the latest result date for this market before we start
    with app.app_context():
        latest_result = Result.query.filter_by(market=market_name).order_by(Result.date.desc()).first()
        latest_date = latest_result.date if latest_result else None
        
    logger.info(f"Latest result for {market_name} is on {latest_date}")
    
    for attempt in range(max_attempts):
        logger.info(f"Checking {market_name} (attempt {attempt+1}/{max_attempts})")
        
        # Get the latest result
        result = get_market_results(market_name)
        
        if result:
            # If we have a new result date or a result with both open and close
            if (latest_date is None or result['date'] > latest_date) or (
                result['date'] == latest_date and 
                result['open'] and result['close'] and 
                latest_result and (not latest_result.open or not latest_result.close)
            ):
                logger.info(f"New or updated result found for {market_name}: {result}")
                
                # Update in database
                if update_result_in_db(result):
                    logger.info(f"Successfully updated {market_name} result in database")
                    
                    # Run prediction script for this market
                    try:
                        from generate_predictions import generate_predictions_for_market
                        with app.app_context():
                            logger.info(f"Generating new predictions for {market_name}")
                            generate_predictions_for_market(market_name)
                    except Exception as e:
                        logger.error(f"Error generating predictions: {e}")
                    
                    # Stop checking if we have a complete result (both open and close)
                    if result['open'] and result['close']:
                        logger.info(f"Complete result found for {market_name}, stopping continuous check")
                        return True
            
        # Sleep for the interval
        time.sleep(interval_seconds)
    
    logger.info(f"Reached maximum attempts for {market_name}, stopping continuous check")
    return False

def check_active_markets():
    """Check markets that should be active now"""
    now = datetime.datetime.now()
    ist_offset = datetime.timedelta(hours=5, minutes=30)  # IST is UTC+5:30
    ist_time = now + ist_offset
    
    logger.info(f"Checking markets at IST time: {ist_time}")
    
    for market_name in Config.MARKETS:
        if should_check_market(market_name, ist_time):
            logger.info(f"{market_name} is operating now, starting continuous check")
            continuous_market_check(market_name)
        else:
            logger.info(f"{market_name} is not operating now, skipping")

if __name__ == "__main__":
    # If market name is provided as argument, check just that market
    if len(sys.argv) > 1:
        market_name = sys.argv[1]
        logger.info(f"Checking specific market: {market_name}")
        continuous_market_check(market_name)
    else:
        # Otherwise check all active markets
        check_active_markets()