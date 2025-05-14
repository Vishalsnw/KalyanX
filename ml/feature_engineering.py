import pandas as pd
import numpy as np
from datetime import datetime


def engineer_features(df):
    """Engineer features for the ML model"""
    # Create a copy to avoid modifying the original
    df = df.copy()
    
    # Convert date to datetime
    df['datetime'] = pd.to_datetime(df['Date'], format='%d/%m/%Y')
    
    # Extract date components
    df['day_of_week_num'] = df['datetime'].dt.dayofweek
    df['month'] = df['datetime'].dt.month
    df['year'] = df['datetime'].dt.year
    
    # Extract digits from open, close, jodi
    df['open_first'] = df['Open'].apply(lambda x: int(str(x)[0]) if isinstance(x, str) and len(str(x)) >= 1 else np.nan)
    df['open_last'] = df['Open'].apply(lambda x: int(str(x)[-1]) if isinstance(x, str) and len(str(x)) >= 1 else np.nan)
    df['close_first'] = df['Close'].apply(lambda x: int(str(x)[0]) if isinstance(x, str) and len(str(x)) >= 1 else np.nan)
    df['close_last'] = df['Close'].apply(lambda x: int(str(x)[-1]) if isinstance(x, str) and len(str(x)) >= 1 else np.nan)
    df['jodi_first'] = df['Jodi'].apply(lambda x: int(str(x)[0]) if isinstance(x, str) and len(str(x)) >= 1 else np.nan)
    df['jodi_last'] = df['Jodi'].apply(lambda x: int(str(x)[1]) if isinstance(x, str) and len(str(x)) >= 2 else np.nan)
    df['jodi_numeric'] = df['Jodi'].apply(lambda x: int(x) if isinstance(x, str) and x.isdigit() else np.nan)
    
    # Create lag features
    for col in ['open_first', 'open_last', 'close_first', 'close_last', 'jodi_first', 'jodi_last', 'jodi_numeric']:
        df[f'prev_{col}'] = df[col].shift(1)
    
    # Create rolling statistics
    df['open_sum_rolling_mean'] = df['open_sum'].rolling(window=7, min_periods=1).mean()
    df['close_sum_rolling_mean'] = df['close_sum'].rolling(window=7, min_periods=1).mean()
    
    # Calculate additional features based on day of week patterns
    df['is_start_of_week'] = df['day_of_week_num'] == 0
    df['is_end_of_week'] = df['day_of_week_num'] == 6
    
    # Calculate day of week frequency features
    dow_frequencies = df.groupby('day_of_week_num')['jodi_numeric'].value_counts().unstack().fillna(0)
    if not dow_frequencies.empty:
        for jodi_val in range(100):
            if jodi_val in dow_frequencies.columns:
                df[f'jodi_{jodi_val}_freq'] = df['day_of_week_num'].map(dow_frequencies[jodi_val])
    
    # Fill missing values
    for col in df.columns:
        if df[col].dtype == np.float64 or df[col].dtype == np.int64:
            df[col] = df[col].fillna(df[col].median())
    
    return df
