import os
import sys
import pandas as pd
import datetime
import traceback
from app import app, db
from models import Result
from utils import calculate_derived_fields
from sqlalchemy.exc import SQLAlchemyError

def main(market_name):
    """
    Import data for a specific market
    """
    print(f"Starting to import data for {market_name}...")
    
    # Path to the CSV file
    csv_path = 'attached_assets/enhanced_satta_data.csv'
    
    if not os.path.exists(csv_path):
        print(f"Error: CSV file not found at {csv_path}")
        return False
    
    # Load the CSV data
    try:
        data = pd.read_csv(csv_path)
        print(f"Successfully loaded {len(data)} rows from CSV")
    except Exception as e:
        print(f"Error loading CSV data: {str(e)}")
        return False
    
    # Filter for the specified market
    market_data = data[data['Market'] == market_name]
    if len(market_data) == 0:
        print(f"Error: No data found for market {market_name}")
        return False
    
    print(f"Found {len(market_data)} rows for {market_name}")
    
    # Sort by date (assuming DD/MM/YYYY format)
    market_data['DateObj'] = pd.to_datetime(market_data['Date'], format='%d/%m/%Y')
    market_data = market_data.sort_values('DateObj')
    
    # Take the most recent 60 days for ML training
    days_to_import = min(60, len(market_data))
    recent_data = market_data.tail(days_to_import)
    
    print(f"Importing {len(recent_data)} days for {market_name}")
    
    # Import the data
    with app.app_context():
        count = 0
        for _, row in recent_data.iterrows():
            try:
                # Parse the date
                date_parts = row['Date'].split('/')
                date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                
                # Skip 'Off' days
                if row['Open'] == 'Off' or row['Close'] == 'Off':
                    continue
                
                # Check if result already exists
                existing = Result.query.filter_by(date=date_obj, market=market_name).first()
                if existing:
                    continue
                
                # Create new result record
                new_result = Result(
                    date=date_obj,
                    market=market_name,
                    open=row['Open'],
                    jodi=row['Jodi'],
                    close=row['Close'],
                    day_of_week=row['day_of_week'],
                    is_weekend=bool(row['is_weekend']),
                    open_sum=row['open_sum'] if not pd.isna(row['open_sum']) else None,
                    close_sum=row['close_sum'] if not pd.isna(row['close_sum']) else None,
                    mirror_open=row['mirror_open'] if not pd.isna(row['mirror_open']) else None,
                    mirror_close=row['mirror_close'] if not pd.isna(row['mirror_close']) else None,
                    reverse_jodi=row['reverse_jodi'] if not pd.isna(row['reverse_jodi']) else None,
                    is_holiday=bool(row['is_holiday'])
                )
                
                # Check if prev_jodi_distance exists in the row
                if 'prev_jodi_distance' in row and not pd.isna(row['prev_jodi_distance']):
                    new_result.prev_jodi_distance = row['prev_jodi_distance']
                
                # Add to database
                db.session.add(new_result)
                count += 1
                
            except Exception as e:
                print(f"Error processing row: {str(e)}")
                continue
        
        try:
            # Commit changes
            db.session.commit()
            print(f"Successfully imported {count} rows for {market_name}")
        except SQLAlchemyError as e:
            db.session.rollback()
            print(f"Database error: {str(e)}")
            return False
        
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python import_one_market.py <market_name>")
        sys.exit(1)
    
    market_name = sys.argv[1]
    main(market_name)