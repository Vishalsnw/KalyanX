import datetime
import json
import os
from flask import current_app
from app import db
from models import User, Notification
from utils import format_date
from config import Config
from pywebpush import webpush
from services.fast2sms_service import send_notification as send_sms_notification


def send_notification(user_id, title, message, notification_type, reference_id=None, send_sms=False):
    """Create a notification for a user and send push if possible"""
    # Create database record
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        reference_id=reference_id,
        created_at=datetime.datetime.utcnow()
    )
    
    db.session.add(notification)
    db.session.commit()
    
    # Try to send push notification
    try_send_push_notification(user_id, title, message)
    
    # Try to send SMS notification if requested
    if send_sms:
        try_send_sms_notification(user_id, title, message)
    
    return notification


def try_send_sms_notification(user_id, title, message):
    """Try to send an SMS notification to a user"""
    user = User.query.get(user_id)
    
    if not user or not user.mobile:
        return False
    
    # Check if Fast2SMS API key is available
    api_key = os.environ.get("FAST2SMS_API_KEY")
    if not api_key:
        current_app.logger.warning(f"Cannot send SMS: Fast2SMS API key not configured")
        return False
    
    try:
        # Send SMS notification using Fast2SMS
        sms_sent = send_sms_notification(user.mobile, title, message)
        if sms_sent:
            current_app.logger.info(f"SMS notification sent to {user.mobile}")
            return True
        else:
            current_app.logger.error(f"Failed to send SMS notification to {user.mobile}")
            return False
    except Exception as e:
        current_app.logger.error(f"SMS notification failed: {str(e)}")
        return False


def try_send_push_notification(user_id, title, message):
    """Try to send a web push notification to a user if they have a subscription"""
    user = User.query.get(user_id)
    
    if not user or not user.push_subscription:
        return False
    
    try:
        # Prepare notification payload
        payload = json.dumps({
            'title': title,
            'body': message,
            'icon': '/static/img/icon.png'
        })
        
        # Send push notification
        webpush(
            subscription_info=user.push_subscription,
            data=payload,
            vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
            vapid_claims=current_app.config['VAPID_CLAIMS']
        )
        
        return True
    except Exception as e:
        current_app.logger.error(f"Push notification failed: {str(e)}")
        return False


def get_unread_notifications(user_id):
    """Get unread notifications for a user"""
    notifications = Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).order_by(Notification.created_at.desc()).all()
    
    return notifications


def mark_notification_read(notification_id, user_id):
    """Mark a notification as read"""
    notification = Notification.query.filter_by(
        id=notification_id,
        user_id=user_id
    ).first()
    
    if notification:
        notification.is_read = True
        db.session.commit()
        return True
    
    return False


def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user"""
    Notification.query.filter_by(
        user_id=user_id,
        is_read=False
    ).update({Notification.is_read: True})
    
    db.session.commit()
    return True


def send_trial_expiry_notification(user_id, days_remaining):
    """Send notification about trial expiry"""
    # Get message template
    message = Config.MSG_TEMPLATES['trial_expiry'].format(days=days_remaining)
    
    # Send notification with SMS for imminent expiry (1-2 days)
    send_notification(
        user_id=user_id,
        title="Your Free Trial is Ending Soon",
        message=message,
        notification_type="subscription",
        send_sms=(days_remaining <= 2)  # Send SMS only when 1-2 days remaining
    )


def send_welcome_notification(user_id):
    """Send welcome notification to new user"""
    # Get message template
    message = Config.MSG_TEMPLATES['welcome']
    
    # Send notification with SMS
    send_notification(
        user_id=user_id,
        title="Welcome to KalyanX",
        message=message,
        notification_type="system",
        send_sms=True  # Send SMS for welcome message
    )


def send_subscription_success_notification(user_id, end_date):
    """Send subscription success notification"""
    # Format date
    formatted_date = format_date(end_date)
    
    # Get message template
    message = Config.MSG_TEMPLATES['subscription_success'].format(date=formatted_date)
    
    # Send notification with SMS
    send_notification(
        user_id=user_id,
        title="Subscription Activated",
        message=message,
        notification_type="subscription",
        send_sms=True  # Send SMS for subscription confirmation
    )


def send_referral_success_notification(user_id):
    """Send referral success notification"""
    # Get message template
    message = Config.MSG_TEMPLATES['referral_success']
    
    # Send notification with SMS
    send_notification(
        user_id=user_id,
        title="Referral Bonus Activated",
        message=message,
        notification_type="referral",
        send_sms=True  # Send SMS for referral bonus activation
    )


def send_prediction_match_notification(user_id, prediction, result):
    """Send notification when prediction matches result"""
    # Get market and result details
    market = result.market
    open_val = result.open
    close_val = result.close
    jodi_val = result.jodi
    
    # Get message template
    message = Config.MSG_TEMPLATES['prediction_match'].format(
        market=market,
        open=open_val,
        close=close_val,
        jodi=jodi_val
    )
    
    # Send notification with SMS
    send_notification(
        user_id=user_id,
        title="Prediction Matched!",
        message=message,
        notification_type="prediction",
        reference_id=prediction.id,
        send_sms=True  # Send SMS when prediction matches result
    )
