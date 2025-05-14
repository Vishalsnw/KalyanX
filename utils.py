import random
import string
import datetime
import pandas as pd
import numpy as np
import pytz
from config import Config


def generate_otp(length=6):
    """Generate a numeric OTP of specified length"""
    return ''.join(random.choices(string.digits, k=length))


def generate_referral_code(length=8):
    """Generate an alphanumeric referral code"""
    chars = string.ascii_uppercase + string.digits
    return 'KX' + ''.join(random.choices(chars, k=length-2))


def calculate_expiry_date(days):
    """Calculate expiry date from current date"""
    return datetime.datetime.utcnow() + datetime.timedelta(days=days)


def get_ist_now():
    """Get current datetime in IST timezone"""
    return datetime.datetime.now(pytz.timezone(Config.TIMEZONE))


def get_ist_date():
    """Get current date in IST timezone"""
    return get_ist_now().date()


def utc_to_ist(utc_dt):
    """Convert UTC datetime to IST timezone"""
    if utc_dt.tzinfo is None:
        utc_dt = utc_dt.replace(tzinfo=pytz.UTC)
    return utc_dt.astimezone(pytz.timezone(Config.TIMEZONE))


def format_ist_datetime(dt):
    """Format datetime in IST timezone"""
    ist_dt = utc_to_ist(dt) if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None else dt
    return ist_dt.strftime("%d/%m/%Y %I:%M %p")


def format_date(date_obj):
    """Format date in DD/MM/YYYY format"""
    return date_obj.strftime("%d/%m/%Y")


def parse_date(date_str):
    """Parse date from DD/MM/YYYY format"""
    return datetime.datetime.strptime(date_str, "%d/%m/%Y").date()


def calculate_statistics(results_df):
    """Calculate statistics from results dataframe"""
    stats = {}
    
    # Total records
    stats['total_records'] = len(results_df)
    
    # Market distribution
    stats['market_distribution'] = results_df['Market'].value_counts().to_dict()
    
    # Day of week distribution
    stats['day_distribution'] = results_df['day_of_week'].value_counts().to_dict()
    
    # Open and Close sum distribution
    stats['open_sum_distribution'] = results_df['open_sum'].value_counts().to_dict()
    stats['close_sum_distribution'] = results_df['close_sum'].value_counts().to_dict()
    
    # Most common jodis
    stats['common_jodis'] = results_df['jodi'].value_counts().head(10).to_dict()
    
    # Monthly trends
    results_df['month'] = pd.to_datetime(results_df['Date'], format='%d/%m/%Y').dt.month
    stats['monthly_trends'] = results_df.groupby('month')['jodi'].count().to_dict()
    
    return stats


def calculate_derived_fields(row):
    """Calculate derived fields for a result row"""
    derived = {}
    
    # Skip calculation if the row has 'Off' values
    if row.get('open') == 'Off' or row.get('close') == 'Off' or row.get('jodi') == 'Off':
        return derived
    
    # Calculate open_sum if open is available and is a valid string
    if row.get('open') and isinstance(row.get('open'), str) and row.get('open').isdigit():
        open_val = row.get('open')
        derived['open_sum'] = sum(int(digit) for digit in open_val)
    
    # Calculate close_sum if close is available and is a valid string
    if row.get('close') and isinstance(row.get('close'), str) and row.get('close').isdigit():
        close_val = row.get('close')
        derived['close_sum'] = sum(int(digit) for digit in close_val)
    
    # Calculate mirror values
    if row.get('open') and isinstance(row.get('open'), str) and len(row.get('open')) == 3:
        open_val = row.get('open')
        derived['mirror_open'] = ''.join([str(9-int(digit)) for digit in open_val])
    
    if row.get('close') and isinstance(row.get('close'), str) and len(row.get('close')) == 3:
        close_val = row.get('close')
        derived['mirror_close'] = ''.join([str(9-int(digit)) for digit in close_val])
    
    # Calculate reverse jodi
    if row.get('jodi') and isinstance(row.get('jodi'), str) and len(row.get('jodi')) == 2:
        jodi_val = row.get('jodi')
        derived['reverse_jodi'] = jodi_val[1] + jodi_val[0]
    
    return derived


def is_matching_prediction(prediction, result):
    """Check if prediction matches result"""
    matches = {}
    
    # Check open digits
    if prediction.get('open_digits') and result.get('open'):
        open_str = result.get('open')
        if len(open_str) == 3:
            predicted_open = prediction.get('open_digits')
            actual_open = [int(open_str[0]), int(open_str[2])]
            matches['open'] = predicted_open == actual_open
    
    # Check close digits
    if prediction.get('close_digits') and result.get('close'):
        close_str = result.get('close')
        if len(close_str) == 3:
            predicted_close = prediction.get('close_digits')
            actual_close = [int(close_str[0]), int(close_str[2])]
            matches['close'] = predicted_close == actual_close
    
    # Check jodi
    if prediction.get('jodi_list') and result.get('jodi'):
        jodi_str = result.get('jodi')
        matches['jodi'] = jodi_str in prediction.get('jodi_list')
    
    # Check patti
    if prediction.get('patti_list') and result.get('open') and result.get('close'):
        open_str = result.get('open')
        close_str = result.get('close')
        matches['patti_open'] = open_str in prediction.get('patti_list')
        matches['patti_close'] = close_str in prediction.get('patti_list')
    
    return matches
