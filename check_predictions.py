from app import app, db
from models import Prediction
import pandas as pd
import datetime

def check_predictions():
    """Check the predictions in the database"""
    with app.app_context():
        # Get all predictions
        predictions = Prediction.query.all()
        print(f'Found {len(predictions)} predictions in the database')
        
        # Get distinct markets
        markets = db.session.query(Prediction.market).distinct().all()
        markets = [m[0] for m in markets]
        print('Markets with predictions:')
        for market in markets:
            print(f'- {market}')
        
        # Get latest prediction for each market
        print('\nLatest prediction for each market:')
        for market in markets:
            latest = Prediction.query.filter_by(market=market).order_by(Prediction.date.desc()).first()
            if latest:
                confidence = f"{latest.confidence_score:.2f}" if latest.confidence_score else "N/A"
                print(f'- {market}: {latest.date} (Confidence: {confidence})')
                
                # Display prediction details
                open_digits = ', '.join(latest.open_digits) if latest.open_digits else 'N/A'
                close_digits = ', '.join(latest.close_digits) if latest.close_digits else 'N/A'
                jodi_list = ', '.join(latest.jodi_list[:3]) + '...' if latest.jodi_list and len(latest.jodi_list) > 3 else ', '.join(latest.jodi_list) if latest.jodi_list else 'N/A'
                
                print(f'  Open Digits: {open_digits}')
                print(f'  Close Digits: {close_digits}')
                print(f'  Top Jodis: {jodi_list}')
            else:
                print(f'- {market}: No predictions found')

if __name__ == "__main__":
    check_predictions()