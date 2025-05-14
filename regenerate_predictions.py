#!/usr/bin/env python
"""
Script to regenerate predictions for all markets using the updated prediction algorithm.
This will force a refresh of all predictions, showing more varied open and close digits
and more diverse patti patterns.
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text

from app import app, db
from models import Prediction, Result
from ml.predictor import generate_predictions, calculate_confidence_score
from config import Config

def regenerate_predictions_for_all_markets():
    """Regenerate predictions for all markets with the new algorithm"""
    print("Regenerating predictions for all markets...")
    
    # Get today's date
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    markets = Config.MARKETS.keys()
    
    for market in markets:
        print(f"Processing market: {market}")
        
        # First check if we already have predictions for tomorrow
        existing_prediction = Prediction.query.filter_by(
            date=tomorrow,
            market=market
        ).first()
        
        if existing_prediction:
            print(f"Deleting existing prediction for {market} on {tomorrow}")
            db.session.delete(existing_prediction)
            db.session.commit()
        
        # Get market results for training - use all 60 days data as requested
        results = Result.query.filter_by(market=market).order_by(Result.date.desc()).limit(Config.TRAINING_DAYS).all()
        
        if len(results) < 30:
            print(f"Not enough data for {market}, skipping...")
            continue
        
        # Convert to DataFrame with ALL columns except is_holiday
        data = []
        for r in results:
            data.append({
                'Date': r.date,
                'Market': r.market,
                'Open': r.open,
                'Close': r.close,
                'Jodi': r.jodi,
                'day_of_week': r.day_of_week,
                'is_weekend': r.is_weekend,
                'open_sum': r.open_sum,
                'close_sum': r.close_sum,
                'mirror_open': r.mirror_open,
                'mirror_close': r.mirror_close,
                'reverse_jodi': r.reverse_jodi,
                'prev_jodi_distance': r.prev_jodi_distance
                # Explicitly exclude is_holiday as requested
            })
        
        results_df = pd.DataFrame(data)
        
        # Generate new predictions
        prediction_data = generate_predictions(results_df, market)
        confidence_score = float(calculate_confidence_score(market, results_df))
        
        # Create new prediction
        # Convert all NumPy/Pandas values to native Python types
        new_prediction = Prediction()
        new_prediction.date = tomorrow
        new_prediction.market = market
        new_prediction.open_digits = [str(d) for d in prediction_data['open_digits']]
        new_prediction.close_digits = [str(d) for d in prediction_data['close_digits']]
        new_prediction.jodi_list = [str(j) for j in prediction_data['jodi_list']]
        new_prediction.patti_list = [str(p) for p in prediction_data['patti_list']]
        new_prediction.confidence_score = float(confidence_score)
        
        db.session.add(new_prediction)
        db.session.commit()
        
        print(f"Created new prediction for {market} on {tomorrow}")
        print(f"Open digits: {prediction_data['open_digits']}")
        print(f"Close digits: {prediction_data['close_digits']}")
        print(f"Jodi list: {prediction_data['jodi_list']}")
        print(f"Patti list: {prediction_data['patti_list']}")
        print(f"Confidence: {confidence_score}")
        print("-" * 50)

if __name__ == "__main__":
    with app.app_context():
        regenerate_predictions_for_all_markets()