import os
import datetime
import razorpay
from flask import current_app
from app import db
from models import User, Subscription
from utils import calculate_expiry_date
from config import Config
from services.auth_service import process_successful_referral


def create_razorpay_order(user_id, amount=Config.SUBSCRIPTION_AMOUNT):
    """Create a Razorpay order for subscription payment"""
    try:
        # Initialize Razorpay client
        client = razorpay.Client(
            auth=(
                current_app.config['RAZORPAY_KEY_ID'],
                current_app.config['RAZORPAY_KEY_SECRET']
            )
        )
        
        # Create order
        data = {
            'amount': int(amount * 100),  # Convert to paise
            'currency': 'INR',
            'receipt': f'sub_receipt_{user_id}_{datetime.datetime.now().timestamp()}',
            'payment_capture': 1,  # Auto-capture
            'notes': {
                'user_id': user_id,
                'subscription_type': 'monthly'
            }
        }
        
        order = client.order.create(data=data)
        
        # Return order details
        return {
            'order_id': order['id'],
            'amount': amount,
            'currency': 'INR',
            'key': current_app.config['RAZORPAY_KEY_ID']
        }
    
    except Exception as e:
        current_app.logger.error(f"Razorpay order creation failed: {str(e)}")
        return None


def verify_payment(payment_id, order_id, signature):
    """Verify Razorpay payment signature"""
    try:
        # Initialize Razorpay client
        client = razorpay.Client(
            auth=(
                current_app.config['RAZORPAY_KEY_ID'],
                current_app.config['RAZORPAY_KEY_SECRET']
            )
        )
        
        # Create verification data
        params_dict = {
            'razorpay_payment_id': payment_id,
            'razorpay_order_id': order_id,
            'razorpay_signature': signature
        }
        
        # Verify signature
        client.utility.verify_payment_signature(params_dict)
        return True
    
    except Exception as e:
        current_app.logger.error(f"Payment verification failed: {str(e)}")
        return False


def process_subscription(user_id, payment_id, order_id):
    """Process a successful subscription payment"""
    try:
        # Get user
        user = User.query.get(user_id)
        
        if not user:
            return False, "User not found"
        
        # Calculate subscription end date (1 month from now)
        if user.is_premium and user.premium_end_date and user.premium_end_date > datetime.datetime.utcnow():
            # If already premium, extend by 1 month
            end_date = user.premium_end_date + datetime.timedelta(days=30)
        else:
            # Otherwise, set to 1 month from now
            end_date = calculate_expiry_date(30)
        
        # Create subscription record
        subscription = Subscription(
            user_id=user_id,
            start_date=datetime.datetime.utcnow(),
            end_date=end_date,
            amount=Config.SUBSCRIPTION_AMOUNT,
            payment_id=payment_id,
            order_id=order_id,
            status='success'
        )
        
        db.session.add(subscription)
        
        # Update user's premium status
        user.is_premium = True
        user.premium_end_date = end_date
        
        # Check if user was referred - if this is their first subscription
        first_subscription = Subscription.query.filter_by(user_id=user_id, status='success').count() == 0
        
        if first_subscription and user.referred_by:
            # Process referral reward for the referring user
            process_successful_referral(user.referred_by)
        
        db.session.commit()
        
        return True, "Subscription processed successfully"
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Subscription processing failed: {str(e)}")
        return False, f"Subscription processing failed: {str(e)}"


def get_subscription_history(user_id):
    """Get subscription history for a user"""
    subscriptions = Subscription.query.filter_by(
        user_id=user_id
    ).order_by(Subscription.start_date.desc()).all()
    
    return subscriptions


def get_subscription_stats():
    """Get overall subscription statistics"""
    # Get total number of subscriptions
    total_subscriptions = Subscription.query.filter_by(status='success').count()
    
    # Get active subscriptions
    now = datetime.datetime.utcnow()
    active_subscriptions = Subscription.query.join(User).filter(
        Subscription.status == 'success',
        User.is_premium == True,
        User.premium_end_date > now
    ).count()
    
    # Get revenue for current month
    start_of_month = datetime.datetime(now.year, now.month, 1)
    monthly_revenue = db.session.query(db.func.sum(Subscription.amount)).filter(
        Subscription.status == 'success',
        Subscription.start_date >= start_of_month
    ).scalar() or 0
    
    # Get total revenue
    total_revenue = db.session.query(db.func.sum(Subscription.amount)).filter(
        Subscription.status == 'success'
    ).scalar() or 0
    
    # Get monthly subscription counts
    monthly_counts = db.session.query(
        db.func.date_trunc('month', Subscription.start_date).label('month'),
        db.func.count().label('count')
    ).filter(
        Subscription.status == 'success'
    ).group_by('month').order_by('month').all()
    
    monthly_data = {
        str(month.strftime('%Y-%m')): count for month, count in monthly_counts
    }
    
    # Return stats
    return {
        'total_subscriptions': total_subscriptions,
        'active_subscriptions': active_subscriptions,
        'monthly_revenue': monthly_revenue,
        'total_revenue': total_revenue,
        'monthly_data': monthly_data
    }
