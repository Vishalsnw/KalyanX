import os
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_squared_error
import xgboost as xgb
import logging
from datetime import datetime
from config import Config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Path to save ML models
MODEL_DIR = "ml_models"
os.makedirs(MODEL_DIR, exist_ok=True)

def train_model(df, market):
    """
    Train ML models for a specific market with enhanced features
    
    Args:
        df: DataFrame with historical data
        market: Market name
    
    Returns:
        Dictionary with model paths and accuracy
    """
    logger.info(f"Training model for {market}")
    
    # Prepare data for training
    recent_df = df.tail(Config.TRAINING_DAYS).copy()  # Last 60 days
    
    if len(recent_df) < 30:
        logger.warning(f"Not enough data for {market}, need at least 30 days")
        return None
    
    # For this implementation, we'll create models that predict:
    # 1. Open digits based on first digit of jodis
    # 2. Close digits based on second digit of jodis
    # 3. Full jodi based on patterns in last 60 days
    # 4. Pattis based on actual historical pattis
    
    # Prepare features and targets
    try:
        # Use all columns except 'is_holiday' as features
        feature_columns = [col for col in recent_df.columns if col != 'is_holiday']
        
        # Prepare datasets for our specific targets
        jodi_first_digits = []  # For open prediction
        jodi_second_digits = [] # For close prediction
        full_jodis = []         # For jodi prediction
        
        # Create enhanced feature dataframe
        feature_df = recent_df[feature_columns].copy()
        
        # Fill NAs with appropriate values
        for col in feature_df.columns:
            if feature_df[col].dtype == np.float64 or feature_df[col].dtype == np.int64:
                feature_df[col] = feature_df[col].fillna(0)
            else:
                feature_df[col] = feature_df[col].fillna('')
                
        # Extract jodi digits and patterns
        for i in range(len(feature_df)):
            if feature_df.iloc[i]['Jodi'] and not pd.isna(feature_df.iloc[i]['Jodi']):
                jodi = str(feature_df.iloc[i]['Jodi']).zfill(2)
                
                # Extract first digit (for open) and second digit (for close)
                jodi_first_digits.append(int(jodi[0]))
                jodi_second_digits.append(int(jodi[1]))
                full_jodis.append(jodi)
        
        # Create additional features for pattern analysis
        
        # 1. Add distance between consecutive jodis
        feature_df['jodi_numeric'] = feature_df['Jodi'].apply(
            lambda x: int(str(x).zfill(2)) if x and not pd.isna(x) else 0
        )
        feature_df['prev_jodi'] = feature_df['jodi_numeric'].shift(1)
        feature_df['jodi_distance'] = abs(feature_df['jodi_numeric'] - feature_df['prev_jodi'])
        
        # 2. Add flip pattern detection
        feature_df['jodi_first_digit'] = feature_df['Jodi'].apply(
            lambda x: int(str(x).zfill(2)[0]) if x and not pd.isna(x) else 0
        )
        feature_df['jodi_second_digit'] = feature_df['Jodi'].apply(
            lambda x: int(str(x).zfill(2)[1]) if x and not pd.isna(x) else 0
        )
        feature_df['prev_jodi_first'] = feature_df['jodi_first_digit'].shift(1)
        feature_df['prev_jodi_second'] = feature_df['jodi_second_digit'].shift(1)
        
        # Check if current jodi is flipped compared to previous
        feature_df['is_flip'] = (
            (feature_df['jodi_first_digit'] == feature_df['prev_jodi_second']) & 
            (feature_df['jodi_second_digit'] == feature_df['prev_jodi_first'])
        ).astype(int)
        
        # 3. Add near-miss pattern detection
        feature_df['near_miss_first'] = abs(feature_df['jodi_first_digit'] - feature_df['prev_jodi_first'])
        feature_df['near_miss_second'] = abs(feature_df['jodi_second_digit'] - feature_df['prev_jodi_second'])
        feature_df['is_near_miss'] = (
            (feature_df['near_miss_first'] <= 1) & 
            (feature_df['near_miss_second'] <= 1) &
            ((feature_df['near_miss_first'] > 0) | (feature_df['near_miss_second'] > 0))  # Not exact match
        ).astype(int)
        
        # 4. Add rolling statistics on jodi frequencies
        for digit in range(10):
            # Count occurrences of each digit in first position (rolling window)
            feature_df[f'first_digit_{digit}_freq'] = feature_df['jodi_first_digit'].rolling(
                window=7, min_periods=1
            ).apply(lambda x: (x == digit).sum())
            
            # Count occurrences of each digit in second position (rolling window)
            feature_df[f'second_digit_{digit}_freq'] = feature_df['jodi_second_digit'].rolling(
                window=7, min_periods=1
            ).apply(lambda x: (x == digit).sum())
        
        # 5. Add moving averages and trends
        feature_df['jodi_7day_avg'] = feature_df['jodi_numeric'].rolling(window=7, min_periods=1).mean()
        feature_df['jodi_7day_std'] = feature_df['jodi_numeric'].rolling(window=7, min_periods=1).std()
        feature_df['jodi_trend'] = feature_df['jodi_numeric'].diff()
        
        # Fill NAs in derived features
        for col in feature_df.columns:
            if feature_df[col].dtype == np.float64 or feature_df[col].dtype == np.int64:
                feature_df[col] = feature_df[col].fillna(0)
                
        # Convert categorical data to numeric
        # For 'day_of_week' column, convert to one-hot encoding
        if 'day_of_week' in feature_df.columns and feature_df['day_of_week'].dtype == object:
            # Get unique values
            days = feature_df['day_of_week'].unique()
            for day in days:
                feature_df[f'day_{day}'] = (feature_df['day_of_week'] == day).astype(int)
            
            # Drop original column
            feature_df = feature_df.drop('day_of_week', axis=1)
            
        # Remove non-numeric columns that can't be used for training
        non_numeric_cols = []
        for col in feature_df.columns:
            if feature_df[col].dtype == object:
                non_numeric_cols.append(col)
                
        feature_df = feature_df.drop(non_numeric_cols, axis=1)
        
        # Ensure we have enough data for all targets
        if len(jodi_first_digits) < 30 or len(jodi_second_digits) < 30 or len(full_jodis) < 30:
            logger.warning(f"Not enough target data for {market}")
            return None
            
        # Prepare feature and target arrays
        X = feature_df.iloc[:-1].values  # All rows except last (which has no next day)
        
        # Use appropriate target arrays (offset by 1 to predict next day)
        y_open = np.array(jodi_first_digits[1:])   # First digit of next day's jodi
        y_close = np.array(jodi_second_digits[1:]) # Second digit of next day's jodi
        y_jodi = np.array(full_jodis[1:])          # Full jodi of next day
        
        # Split data
        X_train, X_test, y_open_train, y_open_test = train_test_split(X, y_open, test_size=0.2, random_state=42)
        _, _, y_close_train, y_close_test = train_test_split(X, y_close, test_size=0.2, random_state=42)
        _, _, y_jodi_train, y_jodi_test = train_test_split(X, y_jodi, test_size=0.2, random_state=42)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Use XGBoost for better performance
        # Train open model (classification)
        open_model = xgb.XGBClassifier(
            n_estimators=100, 
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        open_model.fit(X_train_scaled, y_open_train)
        
        # Train close model (classification)
        close_model = xgb.XGBClassifier(
            n_estimators=100, 
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )
        close_model.fit(X_train_scaled, y_close_train)
        
        # Train jodi model (classification)
        jodi_model = RandomForestClassifier(
            n_estimators=100, 
            max_depth=10,
            random_state=42
        )
        jodi_model.fit(X_train_scaled, y_jodi_train)
        
        # Evaluate models
        open_accuracy = accuracy_score(y_open_test, open_model.predict(X_test_scaled))
        close_accuracy = accuracy_score(y_close_test, close_model.predict(X_test_scaled))
        jodi_accuracy = accuracy_score(y_jodi_test, jodi_model.predict(X_test_scaled))
        
        # Save models
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        open_model_path = os.path.join(MODEL_DIR, f"{market}_open_{timestamp}.pkl")
        close_model_path = os.path.join(MODEL_DIR, f"{market}_close_{timestamp}.pkl")
        jodi_model_path = os.path.join(MODEL_DIR, f"{market}_jodi_{timestamp}.pkl")
        scaler_path = os.path.join(MODEL_DIR, f"{market}_scaler_{timestamp}.pkl")
        
        # Also save feature columns for future prediction
        feature_columns_path = os.path.join(MODEL_DIR, f"{market}_feature_columns_{timestamp}.pkl")
        
        joblib.dump(open_model, open_model_path)
        joblib.dump(close_model, close_model_path)
        joblib.dump(jodi_model, jodi_model_path)
        joblib.dump(scaler, scaler_path)
        joblib.dump(feature_df.columns.tolist(), feature_columns_path)
        
        # Save model info
        model_info = {
            'market': market,
            'open_model_path': open_model_path,
            'close_model_path': close_model_path,
            'jodi_model_path': jodi_model_path,
            'scaler_path': scaler_path,
            'feature_columns_path': feature_columns_path,
            'open_accuracy': open_accuracy,
            'close_accuracy': close_accuracy,
            'jodi_accuracy': jodi_accuracy,
            'timestamp': timestamp,
            'data_size': len(recent_df)
        }
        
        # Save model info
        model_info_path = os.path.join(MODEL_DIR, f"{market}_model_info_{timestamp}.pkl")
        joblib.dump(model_info, model_info_path)
        
        logger.info(f"Models for {market} saved. Open accuracy: {open_accuracy:.2f}, Close accuracy: {close_accuracy:.2f}, Jodi accuracy: {jodi_accuracy:.2f}")
        
        return model_info
    
    except Exception as e:
        logger.error(f"Error training model for {market}: {e}")
        import traceback
        traceback.print_exc()
        return None