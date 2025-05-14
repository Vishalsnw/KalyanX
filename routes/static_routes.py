from flask import Blueprint, render_template, current_app, redirect

static_bp = Blueprint('static', __name__)

@static_bp.route('/about')
def about():
    """About Us page"""
    return render_template('static/about.html')

@static_bp.route('/contact')
def contact():
    """Contact Us page"""
    return render_template('static/contact.html')

@static_bp.route('/privacy')
def privacy():
    """Privacy Policy page"""
    return render_template('static/privacy.html')

@static_bp.route('/terms')
def terms():
    """Terms & Conditions page"""
    return render_template('static/terms.html')

@static_bp.route('/pricing')
def pricing():
    """Pricing page"""
    subscription_amount = current_app.config.get('SUBSCRIPTION_AMOUNT', 2650)
    trial_days = current_app.config.get('TRIAL_DAYS', 7)
    referral_months = current_app.config.get('REFERRAL_MONTHS', 1)
    
    return render_template(
        'static/pricing.html',
        subscription_amount=subscription_amount,
        trial_days=trial_days,
        referral_months=referral_months
    )

@static_bp.route('/test-trial-system')
def test_trial_system():
    """Test page for the trial system"""
    return redirect('/static/test-trial-system.html')
