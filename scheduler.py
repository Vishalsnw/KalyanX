import os
import logging
import datetime
import pandas as pd
import pytz
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import current_app

from models import User, Result, Prediction
from services.notification_service import send_trial_expiry_notification, send_prediction_match_notification
from services.prediction_service import update_predictions_for_market, train_models_for_all_markets
from services.data_service import import_csv_data
from config import Config
from utils import is_matching_prediction, get_ist_now, get_ist_date

# Configure logging
logger = logging.getLogger(__name__)

def setup_scheduler(scheduler):
    """
    Set up all scheduled tasks
    """
    # Run import_results more frequently (every 5 minutes) to check for new results
    # This helps ensure we get results as soon as they're declared
    scheduler.add_job(
        import_results,
        IntervalTrigger(minutes=5),  # More frequent checks (was 15 minutes)
        id='import_results',
        replace_existing=True
    )
    
    # Also run import_results immediately to get the latest data right away
    scheduler.add_job(
        import_results,
        'date',
        run_date=datetime.datetime.now() + datetime.timedelta(seconds=10),
        id='import_results_now',
        replace_existing=True
    )
    
    # Train ML models only on Sundays at 1:00 AM IST
    ist_timezone = pytz.timezone(Config.TIMEZONE)
    scheduler.add_job(
        train_ml_models,
        CronTrigger(day_of_week='sun', hour=1, minute=0, timezone=ist_timezone),
        id='train_ml_models_weekly',
        replace_existing=True
    )
    
    # Add continuous monitoring jobs for each market
    for market_name, market_config in Config.MARKETS.items():
        # Get market timing
        open_time = market_config['open_time']
        close_time = market_config['close_time']
        days_of_week = ",".join(str(day) for day in market_config['days'])
        
        # Convert close time to datetime.time
        close_time_obj = datetime.datetime.strptime(close_time, '%H:%M').time()
        
        # Add job to start continuous checking 15 minutes before market closes
        check_start_time = datetime.datetime.combine(datetime.date.today(), close_time_obj) - datetime.timedelta(minutes=15)
        check_start_time = check_start_time.time().strftime('%H:%M')
        
        # Schedule to check results more frequently starting 15 min before close time
        scheduler.add_job(
            check_market_results,
            CronTrigger(day_of_week=days_of_week, hour=check_start_time.split(':')[0], minute=check_start_time.split(':')[1]),
            args=[market_name],
            id=f'check_results_{market_name}',
            replace_existing=True
        )
    
    # Run update_predictions for each market based on their schedules
    for market, settings in Config.MARKETS.items():
        # Schedule for open predictions - 30 minutes before open time
        open_time = datetime.datetime.strptime(settings['open_time'], '%H:%M').time()
        open_hour, open_minute = open_time.hour, open_time.minute
        
        # Adjust time to 30 minutes before
        open_predict_minute = (open_minute - 30) % 60
        open_predict_hour = (open_hour - 1) if open_minute < 30 else open_hour
        
        # Schedule open prediction update
        scheduler.add_job(
            update_market_predictions,
            CronTrigger(
                hour=open_predict_hour,
                minute=open_predict_minute,
                day_of_week=','.join(str(day) for day in settings['days'])
            ),
            args=[market],
            id=f'update_predictions_{market}_open',
            replace_existing=True
        )
        
        # Schedule for checking results and sending notifications
        scheduler.add_job(
            check_results_and_notify,
            CronTrigger(
                hour='*',
                minute='15,45',  # Check every 30 minutes at :15 and :45
                day_of_week=','.join(str(day) for day in settings['days'])
            ),
            args=[market],
            id=f'check_results_{market}',
            replace_existing=True
        )
    
    # We've already set up ML model training on Sundays at 1:00 AM IST above
    
    # Send trial expiry notifications daily at 10 AM
    scheduler.add_job(
        send_trial_expiry_notifications,
        CronTrigger(hour=10, minute=0),
        id='trial_expiry_notifications',
        replace_existing=True
    )
    
    # Clean up old data monthly
    scheduler.add_job(
        cleanup_old_data,
        CronTrigger(day=1, hour=2, minute=0),
        id='cleanup_old_data',
        replace_existing=True
    )
    
    logger.info("Scheduler initialized with all jobs")


def import_results():
    """
    Run the fetch_results.py script to import latest results
    """
    try:
        logger.info("Running fetch_results.py to import latest results")
        
        # Improved process check to avoid multiple instances
        import subprocess
        import os
        import time
        
        # Create a PID file-based lock to prevent multiple instances
        pid_file = '/tmp/fetch_results.pid'
        
        # Check if PID file exists and if process is still running
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process is still running
                if subprocess.run(['ps', '-p', str(old_pid)], capture_output=True).returncode == 0:
                    current_time = time.time()
                    file_modified_time = os.path.getmtime(pid_file)
                    
                    # If the file is older than 10 minutes, the process might be stuck
                    if current_time - file_modified_time > 600:  # 10 minutes in seconds
                        logger.warning(f"Process {old_pid} appears to be stuck (PID file is > 10 minutes old). Killing it.")
                        try:
                            os.kill(old_pid, 9)  # SIGKILL
                            logger.info(f"Successfully killed process {old_pid}")
                            time.sleep(1)  # Give it a moment to clean up
                        except Exception as e:
                            logger.error(f"Failed to kill process {old_pid}: {e}")
                    else:
                        logger.warning("fetch_results.py is already running. Skipping this run.")
                        return
                else:
                    logger.info("PID file exists but process is not running. Will override lock.")
            except Exception as e:
                logger.error(f"Error checking process: {e}")
        
        # Create PID file with current process ID
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
            
        # Run fetch_results.py as a subprocess instead of importing it
        # This avoids any potential blocking or memory issues
        try:
            fetch_process = subprocess.run(
                ['python3', 'fetch_results.py'],
                capture_output=True,
                text=True,
                timeout=180  # Increased timeout to 3 minutes to ensure completion
            )
            logger.info("Successfully ran fetch_results.py as subprocess")
            
            # Now also run the more comprehensive check_and_update_recent_results.py
            # to ensure we get results from multiple sources and for recent days
            logger.info("Running enhanced recent results check for more thorough updates")
            recent_process = subprocess.run(
                ['python3', 'check_and_update_recent_results.py'],
                capture_output=True,
                text=True,
                timeout=240  # 4 minutes timeout due to checking multiple sources
            )
            
            if recent_process.returncode == 0:
                logger.info("Successfully ran comprehensive recent results check")
            else:
                logger.error(f"Error in recent results check: {recent_process.stderr}")
                
        except subprocess.TimeoutExpired:
            logger.error("Timeout running results update scripts")
        except Exception as e:
            logger.error(f"Error running results update scripts: {str(e)}")
        finally:
            # Release lock by removing PID file
            try:
                if os.path.exists(pid_file):
                    os.remove(pid_file)
                    logger.debug(f"Successfully removed PID file {pid_file}")
            except Exception as e:
                logger.error(f"Error removing PID file {pid_file}: {str(e)}")
            
        # After importing results, update predictions for markets that have new results
        # Use app context to avoid Working outside of application context error
        try:
            from app import app
            with app.app_context():
                update_predictions_for_new_results()
        except Exception as e:
            logger.error(f"Error updating predictions: {str(e)}")
        
        logger.info("Completed import_results job")
    except Exception as e:
        logger.error(f"Error in import_results job: {str(e)}")


def update_market_predictions(market):
    """
    Update predictions for a specific market
    """
    try:
        logger.info(f"Updating predictions for market: {market}")
        
        # Use app context to avoid Working outside of application context error
        from app import app
        with app.app_context():
            prediction = update_predictions_for_market(market)
            
            if prediction:
                logger.info(f"Successfully updated predictions for {market}")
            else:
                logger.warning(f"Failed to update predictions for {market}")
    except Exception as e:
        logger.error(f"Error updating predictions for {market}: {str(e)}")


def check_results_and_notify(market):
    """
    Check for new results and send notifications for prediction matches
    """
    try:
        logger.info(f"Checking results for market: {market}")
        
        # Use app context to avoid Working outside of application context error
        from app import app
        with app.app_context():
            # Get today's date in IST
            today = get_ist_date()
            
            # Get prediction and result for this market and date
            prediction = Prediction.query.filter_by(date=today, market=market).first()
            result = Result.query.filter_by(date=today, market=market).first()
        
        if not prediction or not result:
            logger.info(f"No prediction or result found for {market} on {today}")
            return
        
        # Check if result has been updated since last check
        if not result.open and not result.close:
            logger.info(f"No open or close result available yet for {market}")
            return
        
        # Convert prediction to dictionary format for matching
        prediction_data = {
            'open_digits': prediction.open_digits,
            'close_digits': prediction.close_digits,
            'jodi_list': prediction.jodi_list,
            'patti_list': prediction.patti_list
        }
        
        # Convert result to dictionary format for matching
        result_data = {
            'open': result.open,
            'close': result.close,
            'jodi': result.jodi
        }
        
        # Check for matches
        matches = is_matching_prediction(prediction_data, result_data)
        
        if any(matches.values()):
            logger.info(f"Found matching prediction for {market}: {matches}")
            
            # Get users who viewed this prediction
            from models import PredictionView
            views = PredictionView.query.filter_by(prediction_id=prediction.id).all()
            
            # Send notifications to users
            for view in views:
                user = User.query.get(view.user_id)
                
                # Check if user has notification preferences for this market
                if user and user.notification_preferences:
                    preferences = user.notification_preferences
                    markets = preferences.get('markets', [])
                    
                    if preferences.get('push_enabled') and (not markets or market in markets):
                        # Send notification
                        send_prediction_match_notification(user.id, prediction, result)
                        logger.info(f"Sent match notification to user {user.id} for {market}")
        
        logger.info(f"Completed checking results for {market}")
    except Exception as e:
        logger.error(f"Error checking results for {market}: {str(e)}")


def check_market_results(market_name):
    """
    Run a continuous check on a specific market close to its result time
    This function will run the update_market_results.py script for the specific market
    """
    try:
        logger.info(f"Starting continuous result check for market: {market_name}")
        
        # Improved process check with PID file-based locking
        import subprocess
        import os
        import time
        
        # Create a market-specific PID file
        pid_file = f'/tmp/update_market_{market_name}.pid'
        
        # Check if PID file exists and if process is still running
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r') as f:
                    old_pid = int(f.read().strip())
                
                # Check if process is still running
                if subprocess.run(['ps', '-p', str(old_pid)], capture_output=True).returncode == 0:
                    current_time = time.time()
                    file_modified_time = os.path.getmtime(pid_file)
                    
                    # If the file is older than 5 minutes, the process might be stuck
                    if current_time - file_modified_time > 300:  # 5 minutes in seconds
                        logger.warning(f"Process {old_pid} for {market_name} appears to be stuck. Killing it.")
                        try:
                            os.kill(old_pid, 9)  # SIGKILL
                            logger.info(f"Successfully killed process {old_pid}")
                            time.sleep(1)  # Give it a moment to clean up
                        except Exception as e:
                            logger.error(f"Failed to kill process {old_pid}: {e}")
                    else:
                        logger.warning(f"Update for {market_name} is already running. Skipping this run.")
                        return
                else:
                    logger.info(f"PID file for {market_name} exists but process is not running. Will override lock.")
            except Exception as e:
                logger.error(f"Error checking process for {market_name}: {e}")
        
        # Create PID file with current process ID
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Execute the update_market_results.py script for the specific market
        # with a timeout to prevent hanging
        try:
            result = subprocess.run(
                ['python3', 'update_market_results.py', market_name],
                capture_output=True,
                text=True,
                timeout=60  # Add a timeout of 60 seconds
            )
            
            if result.returncode == 0:
                logger.info(f"Successfully ran update_market_results.py for {market_name}")
                logger.debug(f"Output: {result.stdout}")
            else:
                logger.error(f"Error running update_market_results.py for {market_name}")
                logger.error(f"Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout running update_market_results.py for {market_name}")
        except Exception as e:
            logger.error(f"Error executing update_market_results.py for {market_name}: {str(e)}")
        finally:
            # Release lock by removing PID file
            try:
                if os.path.exists(pid_file):
                    os.remove(pid_file)
                    logger.debug(f"Successfully removed PID file {pid_file}")
            except Exception as e:
                logger.error(f"Error removing PID file {pid_file}: {str(e)}")
    except Exception as e:
        logger.error(f"Error in check_market_results for {market_name}: {str(e)}")
        # Make sure to remove PID file even if outer exception occurs
        try:
            import os  # Import here to ensure it's always available
            pid_file = f'/tmp/update_market_{market_name}.pid'
            if os.path.exists(pid_file):
                os.remove(pid_file)
                logger.debug(f"Successfully removed PID file {pid_file} after error")
        except Exception as e:
            logger.error(f"Error removing PID file after outer exception: {str(e)}")

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
    import datetime  # Import here to ensure it's always available
    
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

def update_predictions_for_new_results():
    """
    Update predictions for markets that have new results
    """
    try:
        # Get all markets
        markets = set(Result.query.with_entities(Result.market).distinct().all())
        logger.info(f"Found {len(markets)} markets to process")
        
        for market_tuple in markets:
            try:
                market = market_tuple[0]
                logger.info(f"Processing market: {market}")
                
                # Get the latest result for this market
                latest_result = Result.query.filter_by(market=market).order_by(Result.date.desc()).first()
                
                if not latest_result:
                    logger.warning(f"No results found for market {market}, skipping prediction update")
                    continue
                
                logger.info(f"Latest result for {market} is from {latest_result.date}")
                
                # Find the next valid day when the market operates
                next_valid_day = find_next_valid_day(market, latest_result.date)
                logger.info(f"Next valid day for {market} is {next_valid_day}")
                
                # Check if we already have a prediction for this market for the next valid day
                existing_prediction = Prediction.query.filter_by(date=next_valid_day, market=market).first()
                
                if not existing_prediction:
                    # Update predictions for this market
                    logger.info(f"Creating new prediction for {market} for {next_valid_day}")
                    try:
                        update_predictions_for_market(market)
                        logger.info(f"Successfully created prediction for {market}")
                    except Exception as market_err:
                        logger.error(f"Error creating prediction for {market}: {str(market_err)}")
                else:
                    logger.info(f"Prediction already exists for {market} on {next_valid_day}")
            except Exception as market_err:
                logger.error(f"Error processing market {market_tuple}: {str(market_err)}")
                # Continue with next market rather than failing everything
                continue
                
        logger.info("Completed updating predictions for all markets")
    except Exception as e:
        logger.error(f"Error updating predictions for new results: {str(e)}")


def train_ml_models():
    """
    Train all ML models
    """
    try:
        logger.info("Starting ML model training")
        # Use app context to avoid Working outside of application context error
        from app import app
        with app.app_context():
            train_models_for_all_markets()
        logger.info("Completed ML model training")
    except Exception as e:
        logger.error(f"Error training ML models: {str(e)}")


def send_trial_expiry_notifications():
    """
    Send notifications to users whose trial is about to expire
    """
    try:
        logger.info("Sending trial expiry notifications")
        
        # Use app context to avoid Working outside of application context error
        from app import app
        with app.app_context():
            # Get current date in IST
            now = get_ist_now()
            
            # Find users whose trial is ending in 1, 2, or 3 days
            for days in [1, 2, 3]:
                target_date = now + datetime.timedelta(days=days)
                
                # Find users with trial ending on that date
                users = User.query.filter(
                    User.is_premium == False,
                    User.trial_end_date >= target_date.replace(hour=0, minute=0, second=0, microsecond=0),
                    User.trial_end_date < target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                ).all()
                
                for user in users:
                    # Send notification
                    send_trial_expiry_notification(user.id, days)
                    logger.info(f"Sent trial expiry notification to user {user.id} ({days} days remaining)")
        
        logger.info("Completed sending trial expiry notifications")
    except Exception as e:
        logger.error(f"Error sending trial expiry notifications: {str(e)}")


def cleanup_old_data():
    """
    Clean up old notifications and other temporary data
    """
    try:
        logger.info("Starting old data cleanup")
        
        # Use app context to avoid Working outside of application context error
        from app import app, db
        with app.app_context():
            # Get current date in IST
            now = get_ist_now()
            
            # Delete notifications older than 30 days
            from models import Notification
            old_date = now - datetime.timedelta(days=30)
            
            deleted_count = Notification.query.filter(
                Notification.created_at < old_date,
                Notification.is_read == True
            ).delete()
            
            db.session.commit()
            logger.info(f"Deleted {deleted_count} old read notifications")
            
            # Delete old OTPs
            from models import OTP
            deleted_count = OTP.query.filter(
                OTP.expiry < now
            ).delete()
            
            db.session.commit()
            logger.info(f"Deleted {deleted_count} expired OTPs")
        
        logger.info("Completed old data cleanup")
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")
