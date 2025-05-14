import os
import random
import datetime
from app import app, db
from models import Result, Prediction

def main():
    """Generate test predictions for today"""
    print("Generating test predictions...")
    
    with app.app_context():
        # Get today's date
        today = datetime.date.today()
        
        # Get markets from the database
        markets = db.session.query(Result.market).distinct().all()
        print(f"Found {len(markets)} markets: {markets}")
        
        # Generate predictions for each market
        for market_tuple in markets:
            market = market_tuple[0]
            
            # Check if prediction already exists
            existing = Prediction.query.filter_by(date=today, market=market).first()
            if existing:
                print(f"Prediction for {market} on {today} already exists")
                continue
            
            # Generate random predictions
            open_digits = [random.randint(0, 9), random.randint(0, 9)]
            close_digits = [random.randint(0, 9), random.randint(0, 9)]
            jodi_list = [f"{random.randint(0, 9)}{random.randint(0, 9)}" for _ in range(10)]
            
            # Generate patti list
            patti_list = []
            first, last = open_digits
            for middle in range(4):  # Just use 4 random digits for middle
                patti = f"{first}{middle}{last}"
                patti_list.append(patti)
            
            # Create prediction record
            new_prediction = Prediction(
                date=today,
                market=market,
                open_digits=open_digits,
                close_digits=close_digits,
                jodi_list=jodi_list,
                patti_list=patti_list,
                confidence_score=0.6  # Medium confidence
            )
            
            # Save to database
            db.session.add(new_prediction)
            db.session.commit()
            
            print(f"Generated prediction for {market} on {today}:")
            print(f"  Open Digits: {open_digits}")
            print(f"  Close Digits: {close_digits}")
            print(f"  Jodi List: {jodi_list}")
            print(f"  Patti List: {patti_list}")
        
        # Verify
        predictions = Prediction.query.filter_by(date=today).all()
        print(f"Total predictions for today: {len(predictions)}")

if __name__ == "__main__":
    main()