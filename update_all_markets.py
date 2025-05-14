import subprocess
import time
import sys
from app import app, db
from services.prediction_service import update_predictions_for_market

# List of markets to import
MARKETS = [
    "Time Bazar",
    "Milan Day",
    "Rajdhani Day",
    "Kalyan",
    "Milan Night",
    "Rajdhani Night",
    "Main Bazar"
]

def import_markets():
    """Import data for each market one by one"""
    print("Starting market import process...")
    
    for market in MARKETS:
        print(f"\n=== Importing {market} ===")
        
        # Run the import_one_market.py script with the market name
        try:
            result = subprocess.run(
                ["python", "import_one_market.py", market],
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error importing {market}:")
            print(e.stdout)
            print(e.stderr)
        
        # Add a delay to avoid database contention
        time.sleep(1)
    
    print("\nAll markets imported successfully")

def generate_predictions():
    """Generate predictions for each market"""
    print("\nStarting prediction generation...")
    
    with app.app_context():
        for market in MARKETS:
            print(f"\n=== Generating predictions for {market} ===")
            
            try:
                prediction = update_predictions_for_market(market)
                if prediction:
                    print(f"Successfully generated prediction for {market} on {prediction.date}")
                else:
                    print(f"No new prediction generated for {market}")
            except Exception as e:
                print(f"Error generating prediction for {market}: {str(e)}")
                db.session.rollback()
            
            # Add a delay to avoid database contention
            time.sleep(1)
    
    print("\nAll predictions generated successfully")

def main():
    """Main function to run the import and prediction generation"""
    print("=== Starting full data update process ===")
    
    # Import data for each market
    import_markets()
    
    # Generate predictions for each market
    generate_predictions()
    
    print("\n=== Process completed successfully ===")

if __name__ == "__main__":
    main()