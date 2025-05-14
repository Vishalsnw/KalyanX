import os
import pandas as pd
import datetime
from app import app, db
from models import Result, Prediction, MLModel
from services.prediction_service import train_models_for_all_markets, update_predictions_for_market
from ml.feature_engineering import engineer_features
from config import Config

def main():
    """Train models and generate predictions"""
    print("Starting model training and prediction generation...")
    
    with app.app_context():
        # Get markets
        markets = set(Result.query.with_entities(Result.market).distinct().all())
        
        print(f"Found {len(markets)} markets: {markets}")
        
        # Train models for all markets
        try:
            print("Training ML models...")
            train_models_for_all_markets()
            print("ML models trained successfully")
        except Exception as e:
            print(f"Error training models: {e}")
        
        # Generate predictions for all markets
        for market_tuple in markets:
            market = market_tuple[0]
            try:
                print(f"Generating predictions for {market}...")
                prediction = update_predictions_for_market(market)
                if prediction:
                    print(f"Predictions for {market} generated successfully")
                else:
                    print(f"Failed to generate predictions for {market}")
            except Exception as e:
                print(f"Error generating predictions for {market}: {e}")
        
        # Verify
        predictions = Prediction.query.all()
        print(f"Total predictions: {len(predictions)}")
        
        models = MLModel.query.all()
        print(f"Total ML models: {len(models)}")

if __name__ == "__main__":
    main()