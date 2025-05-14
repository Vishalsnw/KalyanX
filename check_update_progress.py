import os
import pandas as pd
import time

# Constants
CSV_FILE = "attached_assets/enhanced_satta_data.csv"
LOG_FILE = "csv_update.log"

def check_csv_size():
    """Check the size of the CSV file"""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return len(df)
    return 0

def get_last_log_lines(n=20):
    """Get the last n lines from the log file"""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            return "".join(lines[-n:]) if lines else "Log file is empty"
    return "Log file not found"

def is_process_running():
    """Check if the update process is still running"""
    result = os.popen("ps aux | grep '[u]pdate_csv_to_current.py'").read()
    return bool(result.strip())

def main():
    """Monitor the update process"""
    print("\n===== CSV Update Progress =====\n")
    
    # Check if process is running
    if is_process_running():
        print("Status: RUNNING")
    else:
        print("Status: STOPPED")
    
    # Check CSV size
    csv_size = check_csv_size()
    print(f"Current CSV size: {csv_size} records")
    
    # Print last log entries
    print("\nRecent log entries:")
    print("-" * 50)
    print(get_last_log_lines())
    print("-" * 50)
    
    print("\nNote: Run this script again to check the latest progress.")

if __name__ == "__main__":
    main()