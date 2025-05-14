# Package initialization
from .decorators import trial_or_login_required

# These imports need to be available when importing from utils
import random
import string
import datetime
import pandas as pd
import numpy as np
import pytz
import sys
import os

# Direct implementation of required utility functions to avoid circular import
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

# Import the Config here to avoid circular imports
from config import Config

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

def calculate_statistics(df):
    """Calculate statistics from historical data"""
    stats = {}
    
    # Common digit frequencies
    if 'open_digit1' in df.columns and 'open_digit2' in df.columns:
        open_digits = pd.concat([df['open_digit1'], df['open_digit2']])
        stats['open_digit_freq'] = open_digits.value_counts().to_dict()
    
    if 'close_digit1' in df.columns and 'close_digit2' in df.columns:
        close_digits = pd.concat([df['close_digit1'], df['close_digit2']])
        stats['close_digit_freq'] = close_digits.value_counts().to_dict()
    
    # Jodi frequencies if available
    if 'jodi' in df.columns:
        stats['jodi_freq'] = df['jodi'].value_counts().to_dict()
    
    # Open and close panna frequencies
    if 'open' in df.columns:
        stats['open_freq'] = df['open'].value_counts().to_dict()
    
    if 'close' in df.columns:
        stats['close_freq'] = df['close'].value_counts().to_dict()
    
    return stats

def calculate_derived_fields(df):
    """Calculate derived fields from data for ML model training"""
    # Convert date to datetime if needed
    if 'date' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
        
    # Create day of week, month features
    if 'date' in df.columns:
        df['day_of_week'] = df['date'].dt.dayofweek
        df['month'] = df['date'].dt.month
        df['day'] = df['date'].dt.day
        
    # Extract digits from open and close
    if 'open' in df.columns:
        df['open'] = df['open'].astype(str).str.zfill(3)
        df['open_digit1'] = df['open'].str[0].astype(int)
        df['open_digit2'] = df['open'].str[2].astype(int)
        df['open_sum'] = df['open_digit1'] + df['open_digit2']
        
    if 'close' in df.columns:
        df['close'] = df['close'].astype(str).str.zfill(3)
        df['close_digit1'] = df['close'].str[0].astype(int)
        df['close_digit2'] = df['close'].str[2].astype(int)
        df['close_sum'] = df['close_digit1'] + df['close_digit2']
        
    # Calculate jodi if not already present
    if 'jodi' not in df.columns and 'open_digit1' in df.columns and 'close_digit1' in df.columns:
        df['jodi'] = df['open_digit1'].astype(str) + df['close_digit1'].astype(str)
        
    # Create lag features for time series analysis
    if 'open_digit1' in df.columns:
        for i in range(1, 6):  # 5 days of lags
            df[f'open_digit1_lag{i}'] = df['open_digit1'].shift(i)
            df[f'open_digit2_lag{i}'] = df['open_digit2'].shift(i)
            
    if 'close_digit1' in df.columns:
        for i in range(1, 6):  # 5 days of lags
            df[f'close_digit1_lag{i}'] = df['close_digit1'].shift(i)
            df[f'close_digit2_lag{i}'] = df['close_digit2'].shift(i)
            
    # Rolling statistics
    if 'open_sum' in df.columns:
        df['open_sum_rolling_mean'] = df['open_sum'].rolling(window=7, min_periods=1).mean()
        df['open_sum_rolling_std'] = df['open_sum'].rolling(window=7, min_periods=1).std()
        
    if 'close_sum' in df.columns:
        df['close_sum_rolling_mean'] = df['close_sum'].rolling(window=7, min_periods=1).mean()
        df['close_sum_rolling_std'] = df['close_sum'].rolling(window=7, min_periods=1).std()
        
    # Fill NaN values
    df = df.fillna(-1)  # Replace NaN with -1 for ML models
    
    return df

# Export all our utility functions
__all__ = [
    'trial_or_login_required',
    'generate_otp',
    'generate_referral_code',
    'calculate_expiry_date',
    'get_ist_now',
    'get_ist_date',
    'utc_to_ist',
    'format_ist_datetime',
    'format_date',
    'parse_date',
    'is_matching_prediction',
    'calculate_statistics', 
    'calculate_derived_fields'
]