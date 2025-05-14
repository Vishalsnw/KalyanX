import os


class Config:
    # Application Settings
    APP_NAME = "KalyanX"
    APP_DESCRIPTION = "Professional Satta Matka Prediction Platform"
    ADMIN_EMAIL = "admin@kalyanx.com"
    TIMEZONE = 'Asia/Kolkata'  # IST (UTC+5:30)
    
    # Subscription Settings
    TRIAL_DAYS = 7
    SUBSCRIPTION_AMOUNT = 2650  # in INR
    REFERRAL_MONTHS = 1
    
    # OTP Settings
    OTP_EXPIRY_MINUTES = 10
    MAX_OTP_ATTEMPTS = 3
    
    # ML Model Settings
    TRAINING_DAYS = 60
    MODEL_REFRESH_HOURS = 6
    PREDICTION_CONFIDENCE_THRESHOLD = 0.7
    
    # Result Fetch Settings
    FETCH_INTERVAL_MINUTES = 15
    
    # Markets Configuration
    MARKETS = {
        "Time Bazar": {
            "open_time": "13:00",
            "close_time": "14:30",
            "days": [0, 1, 2, 3, 4, 5]  # Monday to Saturday
        },
        "Milan Day": {
            "open_time": "15:15",
            "close_time": "17:15",
            "days": [0, 1, 2, 3, 4, 5]
        },
        "Kalyan": {
            "open_time": "16:30",
            "close_time": "18:30",
            "days": [0, 1, 2, 3, 4, 5]
        },
        "Milan Night": {
            "open_time": "21:00",
            "close_time": "23:00",
            "days": [0, 1, 2, 3, 4, 5]
        },
        "Main Bazar": {
            "open_time": "21:30",
            "close_time": "23:59",
            "days": [0, 1, 2, 3, 4, 5]
        }
    }
    
    # Forum Settings
    FORUM_CATEGORIES = [
        {"name": "General Discussion", "description": "Discuss anything related to Satta Matka"},
        {"name": "Strategy & Tips", "description": "Share and discuss strategies and tips"},
        {"name": "Market Analysis", "description": "Analyze different markets and their patterns"},
        {"name": "Predictions", "description": "Discuss the accuracy of predictions"},
        {"name": "Feedback & Suggestions", "description": "Provide feedback and suggestions for the platform"}
    ]
    
    # Message templates
    MSG_TEMPLATES = {
        "welcome": "Welcome to KalyanX! Your 7-day free trial has started. Explore our premium predictions.",
        "trial_expiry": "Your free trial expires in {days} days. Subscribe now to continue accessing premium predictions.",
        "subscription_success": "Thank you for subscribing to KalyanX Premium! Your subscription is active until {date}.",
        "referral_success": "Congratulations! You've earned a free month of KalyanX Premium from a successful referral.",
        "prediction_match": "Your prediction for {market} matched the actual result! Open: {open}, Close: {close}, Jodi: {jodi}"
    }
