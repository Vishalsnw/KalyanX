import pandas as pd
import numpy as np
import datetime
import json
import joblib
import os
from app import db
from models import Result, Prediction, MLModel
from config import Config
from ml.predictor import generate_predictions
from ml.trainer import train_model
from utils import calculate_derived_fields


def get_latest_results(market=None, limit=50):
    """Get the latest results from the database"""
    query = Result.query.order_by(Result.date.desc())
    
    if market:
        query = query.filter_by(market=market)
    
    return query.limit(limit).all()


def get_predictions_for_date(date, market=None):
    """Get predictions for a specific date"""
    query = Prediction.query.filter_by(date=date)
    
    if market:
        query = query.filter_by(market=market)
    
    return query.all()


def update_result(result_data):
    """Update or insert result in the database"""
    date = result_data.get('date')
    market = result_data.get('market')
    
    # Check if result already exists
    existing_result = Result.query.filter_by(date=date, market=market).first()
    
    if existing_result:
        # Update existing result
        for key, value in result_data.items():
            if hasattr(existing_result, key) and key != 'id':
                setattr(existing_result, key, value)
        
        # Calculate derived fields
        derived_fields = calculate_derived_fields(result_data)
        for key, value in derived_fields.items():
            setattr(existing_result, key, value)
        
        existing_result.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        return existing_result
    else:
        # Create new result
        new_result = Result(**result_data)
        
        # Calculate derived fields
        derived_fields = calculate_derived_fields(result_data)
        for key, value in derived_fields.items():
            setattr(new_result, key, value)
        
        db.session.add(new_result)
        db.session.commit()
        return new_result


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

def update_predictions_for_market(market):
    """Update predictions for a specific market"""
    try:
        # Find the latest date with results for this market
        latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
        
        if not latest_result:
            print(f"No results found for {market}, cannot generate prediction")
            return None
        
        # Find the next valid day when the market will operate
        next_valid_day = find_next_valid_day(market, latest_result.date)
        print(f"Generating predictions for {market} on {next_valid_day} (next valid operating day)")
        
        # Check if predictions already exist for the target date
        existing_prediction = Prediction.query.filter_by(date=next_valid_day, market=market).first()
        
        if existing_prediction:
            print(f"Predictions already exist for {market} on {next_valid_day}")
            return existing_prediction
        
        # Get training data (last 60 days before latest result)
        end_date = latest_result.date
        start_date = end_date - datetime.timedelta(days=Config.TRAINING_DAYS)
        training_data = Result.query.filter(
            Result.market == market,
            Result.date >= start_date,
            Result.date <= end_date
        ).order_by(Result.date).all()
        
        print(f"Found {len(training_data)} training records for {market}")
        
        # Convert to DataFrame for ML processing
        training_df = pd.DataFrame([{
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
        } for r in training_data])
        
        # Skip if not enough data
        if len(training_df) < 30:
            print(f"Not enough training data for {market}, need at least 30 records")
            # For testing, let's relax this constraint
            if len(training_df) < 10:
                print(f"Less than 10 records, skipping prediction for {market}")
                return None
            else:
                print(f"Using limited data ({len(training_df)} records) for testing purposes")
        
        # Generate predictions using ML model
        print(f"Generating predictions for {market} using {len(training_df)} records")
        predictions = generate_predictions(training_df, market)
        
        if not predictions:
            print(f"Failed to generate predictions for {market}")
            return None
            
        print(f"Prediction results: {predictions}")
        
        # Create new prediction record
        new_prediction = Prediction(
            date=next_valid_day,
            market=market,
            open_digits=predictions.get('open_digits'),
            close_digits=predictions.get('close_digits'),
            jodi_list=predictions.get('jodi_list'),
            patti_list=predictions.get('patti_list'),
            confidence_score=predictions.get('confidence_score')
        )
        
        db.session.add(new_prediction)
        db.session.commit()
        
        print(f"Successfully saved prediction for {market}")
        return new_prediction
    except Exception as e:
        print(f"Error generating predictions for {market}: {str(e)}")
        return None


def train_models_for_all_markets():
    """Train ML models for all markets"""
    # Get list of all markets
    markets = set(Result.query.with_entities(Result.market).distinct().all())
    
    for market_tuple in markets:
        market = market_tuple[0]
        
        try:
            print(f"Training models for market: {market}")
            
            # Get training data for this market (last 60 days)
            end_date = datetime.date.today()
            start_date = end_date - datetime.timedelta(days=Config.TRAINING_DAYS)
            
            training_data = Result.query.filter(
                Result.market == market,
                Result.date >= start_date,
                Result.date <= end_date
            ).order_by(Result.date).all()
            
            print(f"Found {len(training_data)} records for {market}")
            
            # Skip if not enough data
            if len(training_data) < 30:
                print(f"Not enough data for {market}, need at least 30 records")
                # For testing, let's relax this constraint
                if len(training_data) < 10:
                    continue
            
            # Convert to DataFrame for ML processing
            training_df = pd.DataFrame([{
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
            } for r in training_data])
            
            # Train models for this market
            print(f"Training ML models for {market} with {len(training_df)} records")
            models = train_model(training_df, market)
            
            # Save model info in database
            for model_type, model_info in models.items():
                # Check if model already exists
                existing_model = MLModel.query.filter_by(
                    market=market, model_type=model_type
                ).first()
                
                if existing_model:
                    # Update existing model
                    existing_model.model_path = model_info['path']
                    existing_model.accuracy = model_info['accuracy']
                    existing_model.training_date = datetime.datetime.utcnow()
                else:
                    # Create new model record
                    new_model = MLModel(
                        market=market,
                        model_type=model_type,
                        model_path=model_info['path'],
                        accuracy=model_info['accuracy'],
                        training_date=datetime.datetime.utcnow()
                    )
                    db.session.add(new_model)
            
            db.session.commit()
            print(f"Successfully trained models for {market}")
        except Exception as e:
            print(f"Error training models for {market}: {str(e)}")
    
    return True


def get_prediction_accuracy():
    """Calculate prediction accuracy across all markets"""
    # Get predictions from the last 30 days
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    predictions = Prediction.query.filter(
        Prediction.date >= start_date,
        Prediction.date < end_date
    ).all()
    
    accuracy_stats = {
        'total': len(predictions),
        'open_matches': 0,
        'close_matches': 0,
        'jodi_matches': 0,
        'markets': {}
    }
    
    for prediction in predictions:
        # Get corresponding result
        result = Result.query.filter_by(
            date=prediction.date, market=prediction.market
        ).first()
        
        if not result or not result.jodi:
            continue
        
        # Initialize market stats if needed
        if prediction.market not in accuracy_stats['markets']:
            accuracy_stats['markets'][prediction.market] = {
                'total': 0,
                'open_matches': 0,
                'close_matches': 0,
                'jodi_matches': 0
            }
        
        # Update market total
        accuracy_stats['markets'][prediction.market]['total'] += 1
        
        # Check open prediction
        if result.open and prediction.open_digits:
            open_str = result.open
            if len(open_str) == 3:
                predicted_open = prediction.open_digits
                actual_open = [int(open_str[0]), int(open_str[2])]
                if predicted_open == actual_open:
                    accuracy_stats['open_matches'] += 1
                    accuracy_stats['markets'][prediction.market]['open_matches'] += 1
        
        # Check close prediction
        if result.close and prediction.close_digits:
            close_str = result.close
            if len(close_str) == 3:
                predicted_close = prediction.close_digits
                actual_close = [int(close_str[0]), int(close_str[2])]
                if predicted_close == actual_close:
                    accuracy_stats['close_matches'] += 1
                    accuracy_stats['markets'][prediction.market]['close_matches'] += 1
        
        # Check jodi prediction
        if result.jodi and prediction.jodi_list:
            if result.jodi in prediction.jodi_list:
                accuracy_stats['jodi_matches'] += 1
                accuracy_stats['markets'][prediction.market]['jodi_matches'] += 1
    
    # Calculate overall percentages
    if accuracy_stats['total'] > 0:
        accuracy_stats['open_accuracy'] = round(100 * accuracy_stats['open_matches'] / accuracy_stats['total'], 2)
        accuracy_stats['close_accuracy'] = round(100 * accuracy_stats['close_matches'] / accuracy_stats['total'], 2)
        accuracy_stats['jodi_accuracy'] = round(100 * accuracy_stats['jodi_matches'] / accuracy_stats['total'], 2)
    
    # Calculate market percentages
    for market, stats in accuracy_stats['markets'].items():
        if stats['total'] > 0:
            stats['open_accuracy'] = round(100 * stats['open_matches'] / stats['total'], 2)
            stats['close_accuracy'] = round(100 * stats['close_matches'] / stats['total'], 2)
            stats['jodi_accuracy'] = round(100 * stats['jodi_matches'] / stats['total'], 2)
    
    return accuracy_stats
