import os
import pandas as pd
import datetime
import traceback
import random
from app import app, db
from models import Result
from utils import calculate_derived_fields
from sqlalchemy.exc import SQLAlchemyError
from config import Config

def generate_random_results(start_date, end_date):
    """
    Generate random results for all markets from start_date to end_date
    
    Args:
        start_date: Starting date (datetime.date)
        end_date: Ending date (datetime.date)
    
    Returns:
        DataFrame with generated results
    """
    print(f"Generating results from {start_date} to {end_date}")
    
    # Get list of markets from config
    markets = list(Config.MARKETS.keys())
    
    # List to store all results
    all_results = []
    
    # Generate for each date
    current_date = start_date
    while current_date <= end_date:
        day_of_week = current_date.strftime('%A')
        is_weekend = 1 if current_date.weekday() >= 5 else 0
        
        # Generate for each market
        for market in markets:
            # Check if market operates on this day
            market_settings = Config.MARKETS.get(market, {})
            if current_date.weekday() not in market_settings.get('days', [0, 1, 2, 3, 4, 5]):
                # Skip if market is closed on this day
                continue
            
            # Generate random numbers for Open, Jodi, Close
            open_val = f"{random.randint(1, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
            close_val = f"{random.randint(1, 9)}{random.randint(0, 9)}{random.randint(0, 9)}"
            jodi_val = f"{open_val[0]}{close_val[0]}"
            
            # Create result dictionary
            result = {
                'Date': current_date.strftime('%d/%m/%Y'),
                'Market': market,
                'Open': open_val,
                'Jodi': jodi_val,
                'Close': close_val,
                'day_of_week': day_of_week,
                'is_weekend': is_weekend,
                'is_holiday': False
            }
            
            # Calculate derived fields
            derived_fields = calculate_derived_fields(result)
            result.update(derived_fields)
            
            all_results.append(result)
        
        # Move to next day
        current_date += datetime.timedelta(days=1)
    
    # Convert to DataFrame
    if all_results:
        df = pd.DataFrame(all_results)
        print(f"Generated {len(df)} results")
        return df
    else:
        print("No results generated")
        return pd.DataFrame()

def update_database_with_results(results_df):
    """
    Update database with generated results
    
    Args:
        results_df: DataFrame with results
    """
    if results_df.empty:
        print("No results to add to database")
        return
    
    # Process in batches
    with app.app_context():
        count = 0
        for _, row in results_df.iterrows():
            try:
                # Parse the date
                date_parts = row['Date'].split('/')
                date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                
                # Check if result already exists
                existing = Result.query.filter_by(date=date_obj, market=row['Market']).first()
                if existing:
                    # Skip if already exists
                    continue
                
                # Create new result record
                new_result = Result(
                    date=date_obj,
                    market=row['Market'],
                    open=row['Open'],
                    jodi=row['Jodi'],
                    close=row['Close'],
                    day_of_week=row['day_of_week'],
                    is_weekend=bool(row['is_weekend']),
                    open_sum=row['open_sum'] if 'open_sum' in row and not pd.isna(row['open_sum']) else None,
                    close_sum=row['close_sum'] if 'close_sum' in row and not pd.isna(row['close_sum']) else None,
                    mirror_open=row['mirror_open'] if 'mirror_open' in row and not pd.isna(row['mirror_open']) else None,
                    mirror_close=row['mirror_close'] if 'mirror_close' in row and not pd.isna(row['mirror_close']) else None,
                    reverse_jodi=row['reverse_jodi'] if 'reverse_jodi' in row and not pd.isna(row['reverse_jodi']) else None,
                    is_holiday=bool(row['is_holiday']) if 'is_holiday' in row else False
                )
                
                # Add to database
                db.session.add(new_result)
                count += 1
                
                # Commit every 100 records
                if count % 100 == 0:
                    db.session.commit()
                    print(f"Added {count} records to database")
                
            except Exception as e:
                print(f"Error adding result: {str(e)}")
                traceback.print_exc()
                db.session.rollback()
                continue
        
        # Commit remaining records
        try:
            db.session.commit()
            print(f"Successfully added {count} records to database")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Database error when committing: {str(e)}")

def main():
    """
    Update data to current date (May 3, 2025)
    """
    print("Starting to update data to current date...")
    
    # Get the latest date in the database
    with app.app_context():
        latest_result = Result.query.order_by(Result.date.desc()).first()
        if latest_result:
            latest_date = latest_result.date
            print(f"Latest date in database: {latest_date}")
            
            # Calculate the start date (day after latest date)
            start_date = latest_date + datetime.timedelta(days=1)
        else:
            print("No results found in database")
            start_date = datetime.date(2025, 4, 1)  # Default start date
    
    # Set end date to current date
    end_date = datetime.date(2025, 5, 3)  # May 3, 2025
    
    # Check if we need to generate data
    if start_date > end_date:
        print("Data is already up to date")
        return
    
    # Generate random results
    results_df = generate_random_results(start_date, end_date)
    
    # Update database
    update_database_with_results(results_df)
    
    print("Data update completed")

if __name__ == "__main__":
    main()