from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from flask_login import login_required, current_user
import datetime
from app import db
from models import User, Subscription
from services.subscription_service import create_razorpay_order, verify_payment, process_subscription, get_subscription_history
from services.notification_service import send_subscription_success_notification
from config import Config

subscription_bp = Blueprint('subscription', __name__)


@subscription_bp.route('/plans')
@login_required
def plans():
    """Subscription plans page"""
    return render_template('subscription.html')


@subscription_bp.route('/checkout')
@login_required
def checkout():
    """Subscription checkout page"""
    # Create Razorpay order
    order = create_razorpay_order(current_user.id)
    
    if not order:
        flash('Failed to create payment order. Please try again.', 'danger')
        return redirect(url_for('subscription.plans'))
    
    return render_template('checkout.html', order=order)


@subscription_bp.route('/payment/verify', methods=['POST'])
@login_required
def verify_payment_route():
    """Verify Razorpay payment"""
    payment_id = request.form.get('razorpay_payment_id')
    order_id = request.form.get('razorpay_order_id')
    signature = request.form.get('razorpay_signature')
    
    # Verify payment signature
    if verify_payment(payment_id, order_id, signature):
        # Process subscription
        success, message = process_subscription(current_user.id, payment_id, order_id)
        
        if success:
            # Send notification
            send_subscription_success_notification(current_user.id, current_user.premium_end_date)
            
            flash('Your subscription has been activated successfully!', 'success')
            return redirect(url_for('subscription.success'))
        else:
            flash(f'Failed to process subscription: {message}', 'danger')
            return redirect(url_for('subscription.plans'))
    else:
        flash('Payment verification failed. Please contact support.', 'danger')
        return redirect(url_for('subscription.plans'))


@subscription_bp.route('/payment/success')
@login_required
def success():
    """Payment success page"""
    return render_template('payment_success.html')


@subscription_bp.route('/subscription-history')
@login_required
def history():
    """Subscription history page"""
    subscriptions = get_subscription_history(current_user.id)
    return render_template('subscription_history.html', subscriptions=subscriptions)


@subscription_bp.route('/api/create-order', methods=['POST'])
@login_required
def api_create_order():
    """API endpoint to create a Razorpay order"""
    order = create_razorpay_order(current_user.id)
    
    if order:
        return jsonify(order)
    else:
        return jsonify({"error": "Failed to create order"}), 400


@subscription_bp.route('/api/subscription-status')
@login_required
def api_subscription_status():
    """API endpoint to get user's subscription status"""
    return jsonify({
        "is_premium": current_user.is_premium,
        "is_trial_active": current_user.is_trial_active,
        "has_access": current_user.has_access,
        "days_remaining": current_user.days_remaining,
        "premium_end_date": current_user.premium_end_date.strftime('%Y-%m-%d') if current_user.premium_end_date else None,
        "trial_end_date": current_user.trial_end_date.strftime('%Y-%m-%d') if current_user.trial_end_date else None
    })
