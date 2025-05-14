import os
import datetime
import requests
import json
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from models import User, OTP
import jwt
from datetime import timedelta
from flask import render_template, url_for
from utils import generate_otp, generate_referral_code, calculate_expiry_date
from config import Config
from services.email_service import send_otp as send_email_otp, send_email


def generate_and_send_otp(mobile):
    """Generate OTP and send to mobile number (legacy method)"""
    # Generate a 6-digit OTP
    otp_code = generate_otp(6)
    
    # Set expiry time (10 minutes from now)
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
    
    # Store OTP in database
    new_otp = OTP(
        mobile=mobile,
        otp=otp_code,
        expiry=expiry
    )
    
    db.session.add(new_otp)
    db.session.commit()
    
    # We will replace this with Firebase phone auth
    
    return True


def generate_and_send_email_otp(email):
    """Generate OTP and send to email address"""
    # Generate a 6-digit OTP
    otp_code = generate_otp(6)
    
    # Set expiry time (10 minutes from now)
    expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=Config.OTP_EXPIRY_MINUTES)
    
    # Store OTP in database
    new_otp = OTP(
        email=email,
        otp=otp_code,
        expiry=expiry
    )
    
    db.session.add(new_otp)
    db.session.commit()
    
    try:
        # Send OTP via email
        send_email_otp(email, otp_code)
        
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send OTP: {str(e)}")
        return False


def verify_otp(identifier, otp_code):
    """Verify the OTP entered by the user"""
    current_time = datetime.datetime.utcnow()
    
    # Find the most recent unexpired OTP for this mobile number or email
    otp_record = OTP.query.filter(
        ((OTP.mobile == identifier) | (OTP.email == identifier)),
        OTP.otp == otp_code,
        OTP.expiry > current_time,
        OTP.verified == False
    ).order_by(OTP.created_at.desc()).first()
    
    # If not found, try by email
    if not otp_record:
        otp_record = OTP.query.filter(
            OTP.email == identifier,
            OTP.otp == otp_code,
            OTP.expiry > datetime.datetime.utcnow(),
            OTP.verified == False
        ).order_by(OTP.created_at.desc()).first()
    
    if otp_record:
        # Mark OTP as verified
        otp_record.verified = True
        db.session.commit()
        return True
    
    return False


def verify_email_otp(email, otp_code):
    """Verify the OTP entered by the user for email"""
    # Find the most recent unexpired OTP for this email
    otp_record = OTP.query.filter(
        OTP.email == email,
        OTP.otp == otp_code,
        OTP.expiry > datetime.datetime.utcnow(),
        OTP.verified == False
    ).order_by(OTP.created_at.desc()).first()
    
    if otp_record:
        # Mark OTP as verified
        otp_record.verified = True
        db.session.commit()
        return True
    
    return False


def register_user(mobile, pin, email=None):
    """Register a new user after OTP verification"""
    # Check if user already exists by mobile
    existing_user = User.query.filter_by(mobile=mobile).first()
    
    # If email is provided, also check by email
    if not existing_user and email:
        existing_user = User.query.filter_by(email=email).first()
    
    if existing_user:
        # Update existing user's PIN if needed
        existing_user.set_pin(pin)
        # Update email if provided and not already set
        if email and not existing_user.email:
            existing_user.email = email
        db.session.commit()
        return existing_user
    
    # Create new user
    new_user = User(
        mobile=mobile,
        email=email,
        registration_date=datetime.datetime.utcnow(),
        trial_end_date=calculate_expiry_date(Config.TRIAL_DAYS),
        is_premium=False,
        referral_code=generate_referral_code()
    )
    
    # Set PIN
    new_user.set_pin(pin)
    
    # Add to database
    db.session.add(new_user)
    db.session.commit()
    
    return new_user


def login_with_pin(identifier, pin):
    """Login a user with mobile/email and PIN"""
    # Try to find user by mobile first
    user = User.query.filter_by(mobile=identifier).first()
    
    # If not found, try by email
    if not user:
        user = User.query.filter_by(email=identifier).first()
    
    if user and user.check_pin(pin):
        # Update last login time
        user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        return user
    
    return None


def register_with_referral(mobile, pin, referral_code):
    """Register a user with a referral code"""
    # Find the referring user
    referring_user = User.query.filter_by(referral_code=referral_code).first()
    
    if not referring_user:
        return None, "Invalid referral code"
    
    # Register the new user
    new_user = register_user(mobile, pin)
    
    # Link the referral
    new_user.referred_by = referring_user.id
    db.session.commit()
    
    return new_user, "Registered successfully with referral"


def update_user_notification_preferences(user_id, preferences):
    """Update user notification preferences"""
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    user.notification_preferences = preferences
    db.session.commit()
    
    return True


def update_push_subscription(user_id, subscription_json):
    """Update user's push notification subscription"""
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    user.push_subscription = subscription_json
    db.session.commit()
    
    return True


def process_successful_referral(referrer_id):
    """Process a successful referral (when a referred user subscribes)"""
    referrer = User.query.get(referrer_id)
    
    if not referrer:
        return False
    
    # If user already has premium, extend by 1 month
    if referrer.is_premium and referrer.premium_end_date:
        referrer.premium_end_date += datetime.timedelta(days=30 * Config.REFERRAL_MONTHS)
    else:
        # Otherwise, give them 1 month of premium
        referrer.is_premium = True
        referrer.premium_end_date = calculate_expiry_date(30 * Config.REFERRAL_MONTHS)
    
    db.session.commit()
    
    return True


def generate_reset_token(user_id):
    """Generate a token for PIN reset"""
    expiration = datetime.datetime.utcnow() + timedelta(hours=1)
    payload = {
        'user_id': user_id,
        'exp': expiration
    }
    secret_key = os.environ.get('SESSION_SECRET', 'dev_key')
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def verify_reset_token(token):
    """Verify PIN reset token and get user"""
    secret_key = os.environ.get('SESSION_SECRET', 'dev_key')
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        user_id = payload.get('user_id')
        return User.query.get(user_id)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Exception) as e:
        current_app.logger.error(f"Token verification error: {str(e)}")
        return None


def send_pin_reset_email(email):
    """Send PIN reset email with reset link"""
    # Find user by email
    user = User.query.filter_by(email=email).first()
    
    if not user:
        return False
    
    # Generate reset token
    token = generate_reset_token(user.id)
    
    # Create reset URL
    reset_url = url_for('auth.reset_pin', token=token, _external=True)
    
    # Get current year for email footer
    current_year = datetime.datetime.now().year
    
    # Render email template
    html_content = render_template(
        'emails/reset_pin_email.html',
        reset_url=reset_url,
        current_year=current_year
    )
    
    # Plain text version
    text_content = f"""
Reset Your KalyanX PIN

Click the link below to reset your PIN:
{reset_url}

This link will expire in 60 minutes.
    """
    
    # Send email
    try:
        send_email(
            to_email=email,
            subject="Reset Your KalyanX PIN",
            body=text_content,
            html_body=html_content
        )
        return True
    except Exception as e:
        current_app.logger.error(f"Failed to send reset email: {str(e)}")
        return False


def reset_user_pin(user_id, new_pin):
    """Reset user's PIN"""
    user = User.query.get(user_id)
    
    if not user:
        return False
    
    # Update PIN
    user.set_pin(new_pin)
    db.session.commit()
    
    return True
