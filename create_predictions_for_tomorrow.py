import datetime
from app import app, db
from models import Result, Prediction
import random
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def create_predictions_for_tomorrow():
    """Create predictions for all markets for tomorrow"""
    print("Creating predictions for tomorrow...")
    
    # Get tomorrow's date
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    
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
            # Check if prediction exists
            existing = Prediction.query.filter_by(date=tomorrow, market=market).first()
            
            if existing:
                print(f"Prediction already exists for {market} on {tomorrow}")
                continue
            
            # Generate prediction
            prediction_data = generate_random_predictions(market, tomorrow)
            
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
            
            print(f"Created prediction for {market} on {tomorrow}")
        except Exception as e:
            print(f"Error creating prediction for {market}: {e}")
            db.session.rollback()
    
    # Commit all changes
    if count > 0:
        db.session.commit()
        print(f"Created {count} predictions for tomorrow")
    else:
        print("No new predictions created")

def main():
    """Run the script"""
    logger.info("Starting to create predictions for tomorrow...")
    
    with app.app_context():
        create_predictions_for_tomorrow()
    
    logger.info("Completed creating predictions")

if __name__ == "__main__":
    main()