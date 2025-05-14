import os
import pandas as pd
import datetime
import traceback
from app import app, db
from models import Result
from utils import calculate_derived_fields
from sqlalchemy.exc import SQLAlchemyError

def main():
    """
    Import the most recent data for each market to get started
    """
    print("Starting to import recent data for each market...")
    
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
    
    # Get a list of unique markets
    markets = data['Market'].unique()
    print(f"Found {len(markets)} unique markets: {markets}")
    
    # Process the most recent 60 days of data for each market
    with app.app_context():
        total_count = 0
        
        for market in markets:
            print(f"Processing market: {market}")
            market_data = data[data['Market'] == market]
            
            # Sort by date (assuming DD/MM/YYYY format)
            market_data['DateObj'] = pd.to_datetime(market_data['Date'], format='%d/%m/%Y')
            market_data = market_data.sort_values('DateObj', ascending=False)
            
            # Take last 60 days (or less if not available)
            days_to_import = min(60, len(market_data))
            recent_data = market_data.head(days_to_import)
            
            print(f"Importing {len(recent_data)} recent days for {market}")
            
            market_count = 0
            for _, row in recent_data.iterrows():
                try:
                    # Parse the date
                    date_parts = row['Date'].split('/')
                    date_obj = datetime.date(int(date_parts[2]), int(date_parts[1]), int(date_parts[0]))
                    
                    # Skip 'Off' days
                    if row['Open'] == 'Off' or row['Close'] == 'Off':
                        continue
                    
                    # Check if result already exists
                    existing = Result.query.filter_by(date=date_obj, market=market).first()
                    if existing:
                        continue
                    
                    # Create new result record
                    new_result = Result(
                        date=date_obj,
                        market=market,
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
                    market_count += 1
                    
                except Exception as e:
                    print(f"Error processing row for {market}: {str(e)}")
                    continue
            
            try:
                # Commit for this market
                db.session.commit()
                print(f"Imported {market_count} records for {market}")
                total_count += market_count
            except SQLAlchemyError as e:
                db.session.rollback()
                print(f"Database error when importing {market} data: {str(e)}")
        
        print(f"Successfully imported {total_count} records across all markets")
        return True

if __name__ == "__main__":
    main()