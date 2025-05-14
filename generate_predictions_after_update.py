import os
import pandas as pd
import datetime
from app import app, db
from models import Result, Prediction
from ml.predictor import generate_predictions, calculate_confidence_score
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_FILE = "attached_assets/enhanced_satta_data.csv"
MARKETS = [
    "Time Bazar", 
    "Milan Day", 
    "Rajdhani Day", 
    "Kalyan", 
    "Milan Night", 
    "Rajdhani Night", 
    "Main Bazar"
]

def import_recent_data_to_database():
    """Import recent CSV data to database"""
    logger.info(f"Importing recent data from {CSV_FILE}")
    
    # Load CSV
    df = pd.read_csv(CSV_FILE)
    logger.info(f"Loaded {len(df)} rows from CSV")
    
    # Sort by date (most recent first)
    df['Date'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    df = df.sort_values('Date', ascending=False)
    
    # Get most recent 60 days of data for each market
    recent_data = []
    for market in MARKETS:
        market_data = df[df['Market'] == market].head(60)
        recent_data.append(market_data)
    
    # Combine all recent data
    recent_df = pd.concat(recent_data)
    logger.info(f"Selected {len(recent_df)} recent records for processing")
    
    # Convert back to string format
    recent_df['Date'] = recent_df['Date'].dt.strftime('%d/%m/%Y')
    
    # Process each row
    count = 0
    for _, row in recent_df.iterrows():
        try:
            # Parse date
            date_parts = row['Date'].split('/')
            date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
            
            # Check if result exists
            existing = Result.query.filter_by(date=date_obj, market=row['Market']).first()
            
            if existing:
                # Update existing
                existing.open = row['Open']
                existing.jodi = row['Jodi']
                existing.close = row['Close']
                existing.day_of_week = row['day_of_week']
                existing.is_weekend = bool(row['is_weekend'])
                
                # Update derived fields
                for field in ['open_sum', 'close_sum', 'mirror_open', 'mirror_close', 'reverse_jodi']:
                    if field in row and not pd.isna(row[field]):
                        setattr(existing, field, row[field])
            else:
                # Create new result
                new_result = Result(
                    date=date_obj,
                    market=row['Market'],
                    open=row['Open'],
                    jodi=row['Jodi'],
                    close=row['Close'],
                    day_of_week=row['day_of_week'],
                    is_weekend=bool(row['is_weekend']),
                    is_holiday=bool(row['is_holiday']) if 'is_holiday' in row else False
                )
                
                # Add derived fields
                for field in ['open_sum', 'close_sum', 'mirror_open', 'mirror_close', 'reverse_jodi', 'prev_jodi_distance']:
                    if field in row and not pd.isna(row[field]):
                        setattr(new_result, field, row[field])
                
                db.session.add(new_result)
                count += 1
                
                # Commit in batches
                if count % 100 == 0:
                    db.session.commit()
                    logger.info(f"Imported {count} records")
        
        except Exception as e:
            logger.error(f"Error importing {row['Date']}, {row['Market']}: {e}")
            db.session.rollback()
            continue
    
    # Final commit
    db.session.commit()
    logger.info(f"Successfully imported/updated {count} records")
    return count

def generate_predictions_for_all_markets():
    """Generate predictions for all markets"""
    logger.info("Generating predictions for all markets")
    
    predictions_count = 0
    for market in MARKETS:
        try:
            # Get latest result date
            latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
            
            if not latest_result:
                logger.warning(f"No results found for {market}")
                continue
            
            # Generate prediction for next day
            next_day = latest_result.date + datetime.timedelta(days=1)
            today = datetime.date.today()
            
            # Skip if next_day is more than 1 day ahead of today
            if (next_day - today).days > 1:
                logger.warning(f"Next day {next_day} is too far ahead of today {today} for {market}")
                continue
            
            # Check if prediction exists
            existing = Prediction.query.filter_by(date=next_day, market=market).first()
            if existing:
                logger.info(f"Prediction already exists for {market} on {next_day}")
                continue
            
            # Get all results for this market
            results = Result.query.filter_by(market=market).order_by(Result.date).all()
            
            # Convert to DataFrame
            data = []
            for r in results:
                row = {
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
                }
                data.append(row)
            
            df = pd.DataFrame(data)
            
            if len(df) < 30:
                logger.warning(f"Not enough data for {market}, need at least 30 days. Got {len(df)} days.")
                continue
            
            # Generate prediction
            logger.info(f"Generating prediction for {market} on {next_day}")
            prediction_data = generate_predictions(df, market)
            
            # Calculate confidence
            confidence_score = calculate_confidence_score(market)
            
            # Create prediction
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
            
            logger.info(f"Created prediction for {market} on {next_day}")
            predictions_count += 1
            
        except Exception as e:
            logger.error(f"Error generating prediction for {market}: {e}")
            db.session.rollback()
    
    logger.info(f"Generated {predictions_count} predictions")
    return predictions_count

def main():
    """Import data and generate predictions"""
    logger.info("Starting data import and prediction generation")
    
    with app.app_context():
        # Import recent data
        import_recent_data_to_database()
        
        # Generate predictions
        generate_predictions_for_all_markets()
    
    logger.info("Process completed")

if __name__ == "__main__":
    main()