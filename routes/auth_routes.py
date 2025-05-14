import os
import re
import datetime
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session, abort, current_app
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from models import User, OTP
from services.auth_service import (
    generate_and_send_otp, generate_and_send_email_otp, 
    verify_otp, verify_email_otp,
    register_user, login_with_pin, register_with_referral, 
    update_user_notification_preferences, update_push_subscription,
    send_pin_reset_email, verify_reset_token, reset_user_pin,
    generate_reset_token
)
from services.notification_service import send_welcome_notification
from utils import generate_referral_code, calculate_expiry_date
from config import Config
# Import Firebase service
try:
    from services.firebase_service import verify_firebase_token, get_user_from_token, initialize_firebase
except ImportError:
    # If Firebase isn't configured, create dummy functions
    def verify_firebase_token(id_token):
        return None

    def get_user_from_token(id_token):
        return None
        
    def initialize_firebase():
        return None

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page - Mobile login and Google Sign-In"""
    if current_user.is_authenticated:
        return redirect(url_for('prediction.dashboard'))

    # Check if this is an admin login attempt
    is_admin_login = request.args.get('admin') == '1'
    
    # Process login
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        pin = request.form.get('pin')
        
        if mobile and pin:
            # Clean mobile number
            mobile = re.sub(r'\D', '', mobile)
            
            # Login with mobile and PIN
            user = login_with_pin(mobile, pin)
            
            if user:
                # For admin login, check if user has admin rights
                if is_admin_login and not user.is_admin:
                    flash('You do not have admin privileges. Please use the regular login.', 'danger')
                    return redirect(url_for('auth.login'))
                
                login_user(user)
                # Record login time
                user.last_login = datetime.datetime.utcnow()
                db.session.commit()
                
                # Redirect to appropriate dashboard
                next_page = request.args.get('next')
                if user.is_admin and is_admin_login:
                    return redirect(next_page or url_for('admin.index'))
                else:
                    return redirect(next_page or url_for('prediction.dashboard'))
            else:
                flash('Invalid mobile number or PIN. Please try again.', 'danger')
        else:
            flash('Please enter both mobile number and PIN.', 'warning')

    # Get Firebase configuration for frontend
    return render_template(
        'login.html', 
        referral=request.args.get('ref'),
        firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
        firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
        firebase_app_id=os.environ.get("FIREBASE_APP_ID")
    )

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page with mobile verification and Google Sign-In"""
    if current_user.is_authenticated:
        return redirect(url_for('prediction.dashboard'))

    # Process mobile registration
    if request.method == 'POST':
        mobile = request.form.get('mobile')
        
        if mobile:
            # Clean mobile number
            mobile = re.sub(r'\D', '', mobile)
            
            # Check if mobile already exists
            existing_user = User.query.filter_by(mobile=mobile).first()
            if existing_user:
                flash('Mobile number already registered. Please login instead.', 'warning')
                return redirect(url_for('auth.login'))
            
            # Save mobile in session and send OTP
            session['registration_mobile'] = mobile
            
            # Get referral code if any
            referral = request.form.get('referral')
            if referral:
                session['referral_code'] = referral
            
            # Generate and send OTP
            if generate_and_send_otp(mobile):
                flash('OTP sent to your mobile number', 'success')
                return redirect(url_for('auth.verify_otp_route'))
            else:
                flash('Failed to send OTP. Please try again.', 'danger')
        else:
            flash('Please enter a valid mobile number.', 'warning')

    # Get Firebase configuration for frontend
    return render_template(
        'register.html', 
        referral=request.args.get('ref'),
        firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
        firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
        firebase_app_id=os.environ.get("FIREBASE_APP_ID")
    )


# Direct registration route disabled
@auth_bp.route('/register-direct', methods=['GET', 'POST'])
def register_direct_route():
    """Direct registration page (no verification) - DISABLED"""
    # Redirect to Google Sign-In
    flash('Direct registration is no longer available. Please use Google Sign-In.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp_route():
    """OTP verification page for both mobile and email"""
    identifier = session.get('registration_email') or session.get('registration_mobile')
    if not identifier:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        otp_code = request.form.get('otp')
        if not otp_code:
            otp_code = ''.join(request.form.get(f'otp_{i}', '') for i in range(6))

        # Verify OTP
        if verify_otp(identifier, otp_code):
            # Move to PIN creation
            if session.get('registration_email'):
                return redirect(url_for('auth.create_email_pin'))
            return redirect(url_for('auth.create_pin'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')

    is_email = bool(session.get('registration_email'))
    return render_template('verify_otp.html', email=is_email)

@auth_bp.route('/verify-email-otp', methods=['GET', 'POST'])
def verify_email_otp_route():
    """OTP verification page for email"""
    if 'registration_email' not in session:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        otp_code = request.form.get('otp')
        email = session['registration_email']

        # Verify OTP
        if verify_email_otp(email, otp_code):
            # Move to PIN creation
            return redirect(url_for('auth.create_email_pin'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')

    return render_template('verify_otp.html', email=True)

@auth_bp.route('/create-pin', methods=['GET', 'POST'])
def create_pin():
    """PIN creation page for mobile registration"""
    if 'registration_mobile' not in session:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        pin = request.form.get('pin')
        confirm_pin = request.form.get('confirm_pin')
        mobile = session['registration_mobile']
        referral_code = session.get('referral_code')
        firebase_uid = session.get('firebase_uid')

        # Validate PINs
        if pin != confirm_pin:
            flash('PINs do not match', 'danger')
            return render_template('create_pin.html')

        if not pin or len(pin) != 4 or not pin.isdigit():
            flash('PIN must be exactly 4 digits', 'danger')
            return render_template('create_pin.html')

        # Register user
        if referral_code:
            user, message = register_with_referral(mobile, pin, referral_code)
        else:
            user = register_user(mobile, pin)

        if user:
            # Update Firebase UID if available
            if firebase_uid:
                user.firebase_uid = firebase_uid
                db.session.commit()
                
            # Send welcome notification
            send_welcome_notification(user.id)

            # Log the user in
            login_user(user)

            # Clear session
            session.pop('registration_mobile', None)
            if 'referral_code' in session:
                session.pop('referral_code', None)
            if 'firebase_uid' in session:
                session.pop('firebase_uid', None)

            flash('Registration successful! Your 7-day free trial has started.', 'success')
            return redirect(url_for('prediction.dashboard'))
        else:
            flash('Registration failed. Please try again.', 'danger')

    return render_template('create_pin.html')

@auth_bp.route('/create-email-pin', methods=['GET', 'POST'])
def create_email_pin():
    """PIN creation page for email registration"""
    if 'registration_email' not in session:
        return redirect(url_for('auth.register'))

    if request.method == 'POST':
        pin = request.form.get('pin')
        confirm_pin = request.form.get('confirm_pin')
        email = session['registration_email']
        mobile = request.form.get('mobile', '')  # Mobile is optional but still accepted
        referral_code = session.get('referral_code')

        # Validate PINs
        if pin != confirm_pin:
            flash('PINs do not match', 'danger')
            return render_template('create_pin.html', email=True)

        if not pin or len(pin) != 4 or not pin.isdigit():
            flash('PIN must be exactly 4 digits', 'danger')
            return render_template('create_pin.html', email=True)

        # Register user with email
        if not mobile:
            # Generate a short unique identifier for mobile field (max 15 chars)
            mobile = f"dr{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]

        if referral_code:
            # Since register_with_referral expects mobile, we'll register and then update
            user, message = register_with_referral(mobile, pin, referral_code)
            if user:
                user.email = email
                db.session.commit()
        else:
            user = register_user(mobile, pin, email)

        if user:
            # Send welcome notification
            send_welcome_notification(user.id)

            # Log the user in
            login_user(user)

            # Clear session
            session.pop('registration_email', None)
            if 'referral_code' in session:
                session.pop('referral_code', None)

            flash('Registration successful! Your 7-day free trial has started.', 'success')
            return redirect(url_for('prediction.dashboard'))
        else:
            flash('Registration failed. Please try again.', 'danger')

    return render_template('create_pin.html', email=True)

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/check-mobile', methods=['POST'])
def check_mobile():
    """Check if mobile already exists"""
    mobile = request.form.get('mobile')

    if not mobile:
        return jsonify({"error": "Mobile number required"}), 400

    user = User.query.filter_by(mobile=mobile).first()

    if user:
        return jsonify({"exists": True, "message": "Mobile number already registered"})
    else:
        return jsonify({"exists": False})

@auth_bp.route('/check-email', methods=['POST'])
def check_email():
    """Check if email already exists"""
    email = request.form.get('email')

    if not email:
        return jsonify({"error": "Email required"}), 400

    user = User.query.filter_by(email=email).first()

    if user:
        return jsonify({"exists": True, "message": "Email already registered"})
    else:
        return jsonify({"exists": False})

@auth_bp.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend OTP to mobile number"""
    mobile = session.get('registration_mobile')

    if not mobile:
        return jsonify({"error": "No mobile number found"}), 400

    if generate_and_send_otp(mobile):
        return jsonify({"success": True, "message": "OTP sent successfully"})
    else:
        return jsonify({"success": False, "message": "Failed to send OTP"})

@auth_bp.route('/resend-email-otp', methods=['POST'])
def resend_email_otp():
    """Resend OTP to email address"""
    email = session.get('registration_email')

    if not email:
        return jsonify({"error": "No email address found"}), 400

    if generate_and_send_email_otp(email):
        return jsonify({"success": True, "message": "OTP sent successfully"})
    else:
        return jsonify({"success": False, "message": "Failed to send OTP"})

@auth_bp.route('/referral/<code>')
def referral(code):
    """Handle referral link"""
    # Store referral code in session
    session['referral_code'] = code

    # Redirect to registration
    return redirect(url_for('auth.register', ref=code))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('profile.html')

@auth_bp.route('/verify-phone', methods=['GET'])
def verify_phone():
    """Firebase phone verification page"""
    # Check if user is already authenticated
    if current_user.is_authenticated:
        return redirect(url_for('prediction.dashboard'))
        
    # Get referral code if any
    referral = request.args.get('referral')
    
    # Initialize Firebase
    initialize_firebase()
    
    # Render the verification page
    return render_template(
        'verify_phone.html', 
        referral=referral,
        firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
        firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
        firebase_app_id=os.environ.get("FIREBASE_APP_ID")
    )
    
@auth_bp.route('/firebase-phone-verified', methods=['POST'])
def firebase_phone_verified():
    """Handle Firebase phone verification success"""
    # Parse JSON request
    data = request.json
    
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
        
    # Get Firebase ID token and phone number
    id_token = data.get('idToken')
    phone_number = data.get('phoneNumber')
    firebase_uid = data.get('uid')
    referral = data.get('referral')
    
    if not id_token or not phone_number:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    # Verify Firebase token
    user_info = get_user_from_token(id_token)
    
    if not user_info:
        return jsonify({"success": False, "message": "Invalid Firebase token"}), 401
    
    # Clean phone number (remove +91 prefix)
    if phone_number.startswith('+91'):
        mobile = phone_number[3:]
    else:
        mobile = re.sub(r'\D', '', phone_number)
    
    # Check if user already exists by mobile or firebase_uid
    existing_user = User.query.filter((User.mobile == mobile) | (User.firebase_uid == firebase_uid)).first()
    
    if existing_user:
        # User exists, check if it's their first Firebase login
        if not existing_user.firebase_uid:
            # Update Firebase UID
            existing_user.firebase_uid = firebase_uid
            db.session.commit()
        
        # Store mobile in session
        session['registration_mobile'] = mobile
        
        # Store referral code if any
        if referral:
            session['referral_code'] = referral
            
        # If user already has PIN set
        if existing_user.pin_hash:
            # Login the user
            login_user(existing_user)
            
            # Update last login
            existing_user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "Login successful!",
                "redirect": url_for('prediction.dashboard')
            })
        else:
            # User needs to set PIN
            return jsonify({
                "success": True,
                "message": "Phone verified successfully!",
                "redirect": url_for('auth.create_pin')
            })
    else:
        # New user - store mobile in session
        session['registration_mobile'] = mobile
        
        # Store Firebase UID in session
        session['firebase_uid'] = firebase_uid
        
        # Store referral code if any
        if referral:
            session['referral_code'] = referral
            
        # Redirect to PIN creation
        return jsonify({
            "success": True,
            "message": "Phone verified successfully!",
            "redirect": url_for('auth.create_pin')
        })

@auth_bp.route('/update-notification-preferences', methods=['POST'])
@login_required
def update_notification_preferences():
    """Update user notification preferences"""
    preferences = request.json.get('preferences', {})

    if update_user_notification_preferences(current_user.id, preferences):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 400

@auth_bp.route('/verify-email-complete')
def verify_email_complete():
    """
    Handles Firebase email verification link completion.
    This page is loaded after the user clicks the link in their email.
    The client-side JavaScript will handle the Firebase auth completion.
    """
    return render_template(
        'verify_email_complete.html',
        firebase_api_key=os.environ.get("FIREBASE_API_KEY"),
        firebase_project_id=os.environ.get("FIREBASE_PROJECT_ID"),
        firebase_app_id=os.environ.get("FIREBASE_APP_ID")
    )


# Route removed to fix token verification conflicts

    # If the user exists, update their info if needed
    if existing_user:
        existing_user.set_pin(pin)
        if email and not existing_user.email:
            existing_user.email = email
        if phone_number and not existing_user.mobile:
            existing_user.mobile = phone_number
        if name and not existing_user.name:
            existing_user.name = name
        if profile_picture and not existing_user.profile_image:
            existing_user.profile_image = profile_picture

        # Record login time
        existing_user.last_login = datetime.datetime.utcnow()
        db.session.commit()
        login_user(existing_user)

        return jsonify({
            "success": True, 
            "message": "Login successful", 
            "redirect": url_for('prediction.dashboard')
        })

    # Create new user
    if referral_code:
        # Check if referral code is valid
        referring_user = User.query.filter_by(referral_code=referral_code).first()
        if not referring_user:
            referral_code = None  # Invalid referral code

    # Determine which identifier to use (email or mobile)
    identifier = None
    if email:
        identifier = email
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"success": False, "message": "Email already registered"}), 400
    elif phone_number:
        identifier = phone_number
        # Check if mobile already exists
        existing_user = User.query.filter_by(mobile=phone_number).first()
        if existing_user:
            return jsonify({"success": False, "message": "Mobile number already registered"}), 400
    else:
        # No identifier provided, generate a temporary one
        identifier = f"fb{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]

    # Register user
    try:
        now = datetime.datetime.utcnow()

        if phone_number:
            user = register_user(phone_number, pin, email)
        else:
            user = register_user(identifier, pin, email)

        # Add Firebase UID and other details
        user.firebase_uid = firebase_uid
        user.name = name or (email.split('@')[0] if email else identifier)
        user.profile_image = profile_picture
        user.last_login = now

        db.session.commit()

        # Log the user in
        login_user(user)

        # Process referral if valid
        if referral_code and referring_user:
            # Add referral relationship
            user.referred_by = referring_user.id
            db.session.commit()

        return jsonify({
            "success": True, 
            "message": "Registration successful", 
            "redirect": url_for('prediction.dashboard')
        })
    except Exception as e:
        db.session.rollback()
        # Use Python's logging instead of app.logger
        import logging
        logging.error(f"Firebase registration error: {str(e)}")
        return jsonify({"success": False, "message": "Registration failed. Please try again."}), 500


@auth_bp.route('/subscribe-push', methods=['POST'])
@login_required
def subscribe_push():
    """Subscribe to push notifications"""
    subscription_json = request.json

    if update_push_subscription(current_user.id, subscription_json):
        return jsonify({"success": True})
    else:
        return jsonify({"success": False}), 400

# Removed duplicate endpoint

@auth_bp.route('/verify-firebase-token', methods=['POST'])
def legacy_verify_firebase_token_route():
    """Legacy endpoint for verifying Firebase token (form data)"""
    # Redirect all requests to the API route to avoid duplication
    return redirect(url_for('api.verify_firebase_token_route'), code=307)

    # Verify the Firebase token
    decoded_token = verify_firebase_token(token)
    if not decoded_token:
        return jsonify({"success": False, "message": "Invalid or expired token"}), 400

    # Get user info from token
    firebase_uid = decoded_token.get('uid')
    if not firebase_uid:
        return jsonify({"success": False, "message": "Invalid token data"}), 400

    # Check if user with this firebase_uid already exists
    existing_user = User.query.filter_by(firebase_uid=firebase_uid).first()

    # If the user exists, update their info if needed
    if existing_user:
        existing_user.set_pin(pin)
        if email and not existing_user.email:
            existing_user.email = email
        if mobile and not existing_user.mobile:
            existing_user.mobile = mobile
        db.session.commit()
        login_user(existing_user)
        return jsonify({
            "success": True, 
            "message": "Login successful", 
            "redirect": url_for('prediction.dashboard')
        })

    # Create new user
    if referral_code:
        # Check if referral code is valid
        referring_user = User.query.filter_by(referral_code=referral_code).first()
        if not referring_user:
            referral_code = None  # Invalid referral code

    # Determine which identifier to use (email or mobile)
    identifier = None
    if email:
        identifier = email
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({"success": False, "message": "Email already registered"}), 400
    elif mobile:
        identifier = mobile
        # Check if mobile already exists
        existing_user = User.query.filter_by(mobile=mobile).first()
        if existing_user:
            return jsonify({"success": False, "message": "Mobile number already registered"}), 400
    else:
        # No identifier provided, generate a temporary one
        identifier = f"fb{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]

    # Register user
    try:
        if mobile:
            user = register_user(mobile, pin, email)
        else:
            user = register_user(identifier, pin, email)

        # Add Firebase UID
        user.firebase_uid = firebase_uid

        # Add referral if provided
        if referral_code and referring_user:
            user.referred_by = referring_user.id

        db.session.commit()

        # Send welcome notification
        send_welcome_notification(user.id)

        # Log the user in
        login_user(user)

        return jsonify({
            "success": True, 
            "message": "Registration successful! Your 7-day free trial has started.", 
            "redirect": url_for('prediction.dashboard')
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Registration failed: {str(e)}"}), 500

@auth_bp.route('/forgot-pin', methods=['GET', 'POST'])
def forgot_pin():
    """Forgot PIN page"""
    if current_user.is_authenticated:
        return redirect(url_for('prediction.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')

        if not email:
            flash('Please enter your email address', 'danger')
            return render_template('forgot_pin.html')

        # Attempt to find user by email
        user = User.query.filter_by(email=email).first()

        # If user not found by email, attempt to find by checking if email is stored in mobile field
        # This happens when users register directly without verification
        if not user:
            # Generate the identifier pattern we might have used during direct registration
            # Try a few patterns to catch different registration methods
            # First, check if this user registered through direct registration with timestamp
            email_prefix = email.split('@')[0][:8]  # Get first part of the email to match possible prefix
            potential_users = User.query.filter(User.mobile.like(f"dr{email_prefix}%")).all()

            # Check each potential user if their email matches
            for potential_user in potential_users:
                if potential_user.email == email:
                    user = potential_user
                    break

        if not user:
            # To prevent user enumeration, still show success message
            flash('PIN reset instructions have been sent to your email if it exists in our system.', 'success')
            return redirect(url_for('auth.login'))

        # Generate reset token but store it in session for development fallback
        token = generate_reset_token(user.id)
        session['dev_reset_token'] = token
        session['dev_reset_email'] = email

        # Try to send reset email
        if send_pin_reset_email(email):
            flash('PIN reset instructions have been sent to your email if it exists in our system.', 'success')
            # Add development note indicating possible use of direct reset link
            flash('If you don\'t receive the email, check your spam folder or use the "View Reset Link" button below.', 'info')
            return redirect(url_for('auth.view_reset_link'))
        else:
            flash('Unable to send reset email. Please try again or use the direct reset link.', 'warning')
            return redirect(url_for('auth.view_reset_link'))

    return render_template('forgot_pin.html')


@auth_bp.route('/reset-pin/<token>', methods=['GET', 'POST'])
def reset_pin(token):
    """Reset PIN page"""
    if current_user.is_authenticated:
        return redirect(url_for('prediction.dashboard'))

    # Verify token
    user = verify_reset_token(token)
    if not user:
        flash('Invalid or expired reset link. Please try again.', 'danger')
        return redirect(url_for('auth.forgot_pin'))

    if request.method == 'POST':
        new_pin = request.form.get('new_pin')
        confirm_pin = request.form.get('confirm_pin')

        # Validate PINs
        if not new_pin or len(new_pin) != 4 or not new_pin.isdigit():
            flash('PIN must be exactly 4 digits', 'danger')
            return render_template('reset_pin.html', token=token)

        if new_pin != confirm_pin:
            flash('PINs do not match', 'danger')
            return render_template('reset_pin.html', token=token)

        # Reset PIN
        if reset_user_pin(user.id, new_pin):
            flash('Your PIN has been reset successfully. You can now login with your new PIN.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Failed to reset PIN. Please try again.', 'danger')

    return render_template('reset_pin.html', token=token)


@auth_bp.route('/view-reset-link', methods=['GET', 'POST'])
def view_reset_link():
    """Development endpoint to view reset links directly"""
    email = request.args.get('email')
    token = None
    reset_url = None

    # Check if there's a token in session
    if 'dev_reset_token' in session and 'dev_reset_email' in session:
        token = session['dev_reset_token']
        email = session['dev_reset_email']
        reset_url = url_for('auth.reset_pin', token=token, _external=True)
        return render_template('view_reset_link.html', token=token, email=email, reset_url=reset_url)

    # If we got here from a form submission on this page
    if request.method == 'POST':
        email = request.form.get('email')
        if not email:
            flash('Please enter your email address', 'danger')
            return render_template('view_reset_link.html', token=None)

        # Try to find the user
        user = User.query.filter_by(email=email).first()

        # If user not found by email directly, check for direct registration pattern
        if not user:
            # First, check if this user registered through direct registration with timestamp
            email_prefix = email.split('@')[0][:8]  # Get first part of the email to match possible prefix
            potential_users = User.query.filter(User.mobile.like(f"dr{email_prefix}%")).all()

            # Check each potential user if their email matches
            for potential_user in potential_users:
                if potential_user.email == email:
                    user = potential_user
                    break

        if not user:
            flash('No account found with that email address', 'danger')
            return render_template('view_reset_link.html', token=None)

        # Generate a reset token and store in session
        token = generate_reset_token(user.id)
        session['dev_reset_token'] = token
        session['dev_reset_email'] = email

        reset_url = url_for('auth.reset_pin', token=token, _external=True)
        flash('Reset link generated successfully', 'success')
        return render_template('view_reset_link.html', token=token, email=email, reset_url=reset_url)

    # If we have no token and this is a GET request, show form
    return render_template('view_reset_link.html', token=token, email=email)


@auth_bp.route('/direct-register', methods=['POST'])
def direct_register():
    """Register user directly without verification (alternative method for API)"""

    data = request.json
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400

    email = data.get('email')
    pin = data.get('pin')
    referral_code = data.get('referral_code')

    if not email or not pin:
        return jsonify({"success": False, "message": "Email and PIN required"}), 400

    # Check if email already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered"}), 400

    # Create user directly
    try:
        # Generate a referral code
        ref_code = generate_referral_code()

        # Create user with trial period
        trial_end_date = datetime.datetime.utcnow() + datetime.timedelta(days=7)

        # If there's a referral code, register with it
        if referral_code:
            user, _ = register_with_referral(f"direct_{email}", pin, referral_code)
            if user:
                user.email = email
                db.session.commit()
        else:
            # Create a standard user
            # Generate a short unique identifier for mobile field (max 15 chars)
            mobile_identifier = f"dr{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]

            new_user = User(
                email=email,
                mobile=mobile_identifier,  # Use short identifier as mobile placeholder
                is_premium=False,
                referral_code=ref_code,
                trial_end_date=trial_end_date
            )

            # Set PIN
            new_user.set_pin(pin)

            # Add to database
            db.session.add(new_user)
            db.session.commit()
            user = new_user

        if user:
            # Send welcome notification
            send_welcome_notification(user.id)

            # Log the user in
            login_user(user)

            return jsonify({
                "success": True, 
                "message": "Registration successful! Your 7-day free trial has started.",
                "redirect": url_for('prediction.dashboard')
            })
        else:
            return jsonify({"success": False, "message": "Registration failed. Please try again."}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": f"Registration failed: {str(e)}"}), 500


@auth_bp.route('/direct-register-form', methods=['GET', 'POST'])
def direct_register_route():
    """Direct form-based registration without email verification"""

    if current_user.is_authenticated:
        return redirect(url_for('prediction.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        pin = request.form.get('pin')
        confirm_pin = request.form.get('confirm_pin')
        referral_code = request.form.get('referral_code')

        # Validate inputs
        if not email or not pin or not confirm_pin:
            flash('All fields are required', 'danger')
            return render_template('direct_register.html', referral=referral_code)

        # Check if email is valid
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Please enter a valid email address', 'danger')
            return render_template('direct_register.html', referral=referral_code)

        # Check if PIN is 4 digits
        if not re.match(r"^\d{4}$", pin):
            flash('PIN must be exactly 4 digits', 'danger')
            return render_template('direct_register.html', referral=referral_code)

        # Check if PINs match
        if pin != confirm_pin:
            flash('PINs do not match', 'danger')
            return render_template('direct_register.html', referral=referral_code)

        # Check if email already exists
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email is already registered', 'danger')
            return render_template('direct_register.html', referral=referral_code)

        try:
            # Register the user directly
            user = None
            if referral_code:
                referring_user = User.query.filter_by(referral_code=referral_code).first()
                if referring_user:
                    # Generate a short unique identifier for mobile field (max 15 chars)
                    mobile_identifier = f"dr{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]

                    # Register with referral
                    user, message = register_with_referral(mobile_identifier, pin, referral_code)
                    if user:
                        user.email = email
                        db.session.commit()
                else:
                    # Invalid referral code, register normally
                    mobile_identifier = f"dr{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]
                    user = register_user(mobile_identifier, pin, email)
            else:
                # Register normally without referral
                mobile_identifier = f"dr{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"[:15]
                user = register_user(mobile_identifier, pin, email)

            if user:
                # Send welcome notification
                send_welcome_notification(user.id)

                # Log the user in
                login_user(user)

                flash('Registration successful! Your 7-day free trial has started.', 'success')
                return redirect(url_for('prediction.dashboard'))
            else:
                flash('Registration failed. Please try again later.', 'danger')

        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            flash(f'Registration error: {str(e)}', 'danger')

    return render_template('direct_register.html', referral=request.args.get('ref'))