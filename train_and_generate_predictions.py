import os
import pandas as pd
import datetime
from app import app, db
from models import Result, Prediction
from ml.predictor import generate_predictions, calculate_confidence_score
from ml.trainer import train_model
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_models_for_all_markets():
    """Train ML models for all markets"""
    logger.info("Starting ML model training for all markets")
    
    # Get distinct markets from database
    markets = db.session.query(Result.market).distinct().all()
    markets = [market[0] for market in markets]
    
    for market in markets:
        logger.info(f"Training model for {market}")
        try:
            # Get results for this market
            results = Result.query.filter_by(market=market).order_by(Result.date).all()
            
            if len(results) < 60:
                logger.warning(f"Not enough data for {market}, need at least 60 days")
                continue
            
            # Convert to dataframe
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
            
            # Train model
            train_model(df, market)
            logger.info(f"Successfully trained model for {market}")
        
        except Exception as e:
            logger.error(f"Error training model for {market}: {e}")
            continue
    
    logger.info("Completed ML model training for all markets")

def generate_predictions_for_market(market):
    """Generate predictions for a specific market"""
    logger.info(f"Generating predictions for {market}")
    
    try:
        # Get latest result date for this market
        latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
        
        if not latest_result:
            logger.warning(f"No results found for {market}")
            return None
        
        # Calculate next day
        next_day = latest_result.date + datetime.timedelta(days=1)
        
        # Check if prediction already exists
        existing = Prediction.query.filter_by(date=next_day, market=market).first()
        if existing:
            logger.info(f"Prediction already exists for {market} on {next_day}")
            return existing
        
        # Get all results for this market
        results = Result.query.filter_by(market=market).order_by(Result.date).all()
        
        # Convert to dataframe
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
        
        # Generate prediction
        prediction_data = generate_predictions(df, market)
        
        # Calculate confidence score
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
        return new_prediction
    
    except Exception as e:
        logger.error(f"Error generating prediction for {market}: {e}")
        db.session.rollback()
        return None

def generate_predictions_for_all_markets():
    """Generate predictions for all markets"""
    logger.info("Generating predictions for all markets")
    
    # Get distinct markets from database
    markets = db.session.query(Result.market).distinct().all()
    markets = [market[0] for market in markets]
    
    predictions = []
    for market in markets:
        prediction = generate_predictions_for_market(market)
        if prediction:
            predictions.append(prediction)
    
    logger.info(f"Generated {len(predictions)} predictions")
    return predictions

def main():
    """Train models and generate predictions"""
    logger.info("Starting to train models and generate predictions")
    
    with app.app_context():
        # First train the models
        train_models_for_all_markets()
        
        # Then generate predictions
        generate_predictions_for_all_markets()
    
    logger.info("Completed training and prediction generation")

if __name__ == "__main__":
    main()