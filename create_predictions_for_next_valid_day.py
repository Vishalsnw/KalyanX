import datetime
from app import app, db
from models import Result, Prediction
import random
import logging
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_market_operating(market_name, check_date):
    """Check if a market is operating on a given date"""
    if market_name not in Config.MARKETS:
        return False
    
    # Convert date to day of week (0 is Monday, 6 is Sunday)
    day_of_week = check_date.weekday()
    
    # Check if the day is in the market's operating days
    return day_of_week in Config.MARKETS[market_name]['days']

def find_next_valid_day(market, start_date):
    """Find the next valid day for a market"""
    next_date = start_date
    
    # Keep incrementing the date until we find a day when the market is operating
    max_attempts = 10  # Avoid infinite loop
    attempts = 0
    
    while attempts < max_attempts:
        next_date = next_date + datetime.timedelta(days=1)
        if is_market_operating(market, next_date):
            return next_date
        attempts += 1
    
    # Fallback to next day if no valid day found within max_attempts
    return start_date + datetime.timedelta(days=1)

def generate_random_predictions(market, date):
    """Generate random predictions for a market on a specific date"""
    # Generate 2 random digits for open
    open_digits = [str(random.randint(0, 9)) for _ in range(2)]
    
    # Generate 2 random digits for close
    close_digits = [str(random.randint(0, 9)) for _ in range(2)]
    
    # Generate 10 random jodis
    jodi_list = []
    while len(jodi_list) < 10:
        jodi = f"{random.randint(0, 9)}{random.randint(0, 9)}"
        if jodi not in jodi_list:
            jodi_list.append(jodi)
    
    # Generate 4 random pattis
    patti_list = [str(random.randint(100, 999)) for _ in range(4)]
    
    # Calculate confidence score
    confidence_score = round(random.uniform(0.7, 0.9), 2)
    
    return {
        'date': date,
        'market': market,
        'open_digits': open_digits,
        'close_digits': close_digits,
        'jodi_list': jodi_list,
        'patti_list': patti_list,
        'confidence_score': confidence_score
    }

def create_predictions_for_next_valid_day():
    """Create predictions for all markets for the next valid day when they operate"""
    print("Creating predictions for the next valid day for each market...")
    
    # Get today's date
    today = datetime.date.today()
    
    # Markets list
    markets = [
        "Time Bazar",
        "Milan Day",
        "Rajdhani Day",
        "Kalyan",
        "Milan Night",
        "Rajdhani Night",
        "Main Bazar"
    ]
    
    count = 0
    for market in markets:
        try:
            # Find the next valid day for this market
            next_valid_day = find_next_valid_day(market, today)
            print(f"Next valid day for {market} is {next_valid_day}")
            
            # Check if prediction exists
            existing = Prediction.query.filter_by(date=next_valid_day, market=market).first()
            
            if existing:
                print(f"Prediction already exists for {market} on {next_valid_day}")
                continue
            
            # Generate prediction
            prediction_data = generate_random_predictions(market, next_valid_day)
            
            # Create new prediction
            prediction = Prediction(
                date=prediction_data['date'],
                market=prediction_data['market'],
                open_digits=prediction_data['open_digits'],
                close_digits=prediction_data['close_digits'],
                jodi_list=prediction_data['jodi_list'],
                patti_list=prediction_data['patti_list'],
                confidence_score=prediction_data['confidence_score']
            )
            
            db.session.add(prediction)
            count += 1
            
            print(f"Created prediction for {market} on {next_valid_day}")
        except Exception as e:
            print(f"Error creating prediction for {market}: {e}")
            db.session.rollback()
    
    # Commit all changes
    if count > 0:
        db.session.commit()
        print(f"Created {count} predictions for next valid days")
    else:
        print("No new predictions created")

def main():
    """Run the script"""
    logger.info("Starting to create predictions for next valid days...")
    
    with app.app_context():
        create_predictions_for_next_valid_day()
    
    logger.info("Completed creating predictions")

if __name__ == "__main__":
    main()