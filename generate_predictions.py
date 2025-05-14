import os
import random
import datetime
from app import app, db
from models import Result, Prediction

def main():
    """Generate predictions for the next day after last available results"""
    print("Generating predictions for all markets with data...")
    
    with app.app_context():
        # Get markets from the database
        markets = db.session.query(Result.market).distinct().all()
        print(f"Found {len(markets)} markets with data: {markets}")
        
        # Generate predictions for each market
        for market_tuple in markets:
            market = market_tuple[0]
            
            # Find the latest date with results for this market
            latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
            
            if not latest_result:
                print(f"No results found for {market}, skipping")
                continue
                
            # Set target date to the day after the latest result
            target_date = latest_result.date + datetime.timedelta(days=1)
            print(f"Latest result for {market} is on {latest_result.date}, generating prediction for {target_date}")
            
            # Check if prediction already exists
            existing = Prediction.query.filter_by(date=target_date, market=market).first()
            if existing:
                print(f"Prediction for {market} on {target_date} already exists")
                continue
            
            # Get recent results for this market
            recent_results = Result.query.filter_by(market=market).order_by(Result.date.desc()).limit(10).all()
            
            if len(recent_results) < 5:
                print(f"Not enough data for {market}, need at least 5 records")
                continue
            
            # Generate "smart" predictions based on most common values in recent results
            open_values = [result.open for result in recent_results if result.open != 'Off']
            close_values = [result.close for result in recent_results if result.close != 'Off']
            
            # Extract first and last digits from recent open/close values
            open_first_digits = [int(val[0]) if len(val) >= 3 else random.randint(0, 9) for val in open_values]
            open_last_digits = [int(val[2]) if len(val) >= 3 else random.randint(0, 9) for val in open_values]
            close_first_digits = [int(val[0]) if len(val) >= 3 else random.randint(0, 9) for val in close_values]
            close_last_digits = [int(val[2]) if len(val) >= 3 else random.randint(0, 9) for val in close_values]
            
            # Choose most common digits
            open_first = max(set(open_first_digits), key=open_first_digits.count)
            open_last = max(set(open_last_digits), key=open_last_digits.count)
            close_first = max(set(close_first_digits), key=close_first_digits.count)
            close_last = max(set(close_last_digits), key=close_last_digits.count)
            
            open_digits = [open_first, open_last]
            close_digits = [close_first, close_last]
            
            # Generate jodi list - 10 most likely pairs
            jodi_list = []
            for i in range(10):
                # Randomly select digits but make them more likely to be similar to our predicted digits
                if random.random() < 0.3:  # 30% chance to use our prediction
                    first = str(open_first) if random.random() < 0.7 else str(random.randint(0, 9))
                    second = str(close_last) if random.random() < 0.7 else str(random.randint(0, 9))
                else:
                    first = str(random.randint(0, 9))
                    second = str(random.randint(0, 9))
                jodi = first + second
                if jodi not in jodi_list:
                    jodi_list.append(jodi)
                else:
                    # Ensure we get 10 unique jodis
                    while len(jodi_list) < 10:
                        jodi = f"{random.randint(0, 9)}{random.randint(0, 9)}"
                        if jodi not in jodi_list:
                            jodi_list.append(jodi)
                            break
            
            # Generate patti list
            patti_list = []
            first, last = open_digits
            for middle in range(4):  # Just use 4 random digits for middle
                patti = f"{first}{middle}{last}"
                patti_list.append(patti)
            
            # Create prediction record
            confidence_score = min(len(recent_results) / 10.0, 0.85)  # Base confidence on amount of data
            new_prediction = Prediction(
                date=target_date,
                market=market,
                open_digits=open_digits,
                close_digits=close_digits,
                jodi_list=jodi_list,
                patti_list=patti_list,
                confidence_score=confidence_score
            )
            
            # Save to database
            db.session.add(new_prediction)
            db.session.commit()
            
            print(f"Generated prediction for {market} on {target_date}:")
            print(f"  Open Digits: {open_digits}")
            print(f"  Close Digits: {close_digits}")
            print(f"  Jodi List: {jodi_list}")
            print(f"  Patti List: {patti_list}")
            print(f"  Confidence: {confidence_score:.2f}")
        
        # Verify all predictions
        today = datetime.date.today()
        predictions = Prediction.query.filter(Prediction.date >= (today - datetime.timedelta(days=7))).all()
        print(f"Total predictions for the past week: {len(predictions)}")

if __name__ == "__main__":
    main()