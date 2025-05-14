import os
import datetime
from flask import Blueprint, request, jsonify, current_app, url_for, session
from flask_login import login_user, current_user
from werkzeug.security import generate_password_hash
from app import db
from models import User, Prediction, Result
from config import Config
from utils import generate_referral_code, get_ist_now, get_ist_date

# Import Firebase services
try:
    from services.firebase_service import verify_firebase_token, get_user_from_token
except ImportError:
    # If Firebase isn't configured, create dummy functions
    def verify_firebase_token(id_token):
        return None
        
    def get_user_from_token(id_token):
        return None

api_bp = Blueprint('api', __name__)

@api_bp.route('/verify-firebase-token', methods=['POST'])
def verify_firebase_token_route():
    """Verify Firebase ID token and create/login user using the Node.js style approach:
    
    admin.auth().verifyIdToken(idToken)
      .then((decodedToken) => {
        const uid = decodedToken.uid;
        // Token valid, proceed
      })
      .catch((error) => {
        console.error("Token verification failed:", error);
        res.status(401).send("Invalid or expired token");
      });
    """
    # Log the entire request to help debug
    print("Received request to verify Firebase token")
    
    data = request.json
    if not data:
        print("No data provided in request")
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    id_token = data.get('idToken')
    pin = data.get('pin', '1234')  # Default PIN if not provided
    referral_code = data.get('referralCode')
    
    if not id_token:
        print("No token provided in request")
        return jsonify({"success": False, "message": "No token provided"}), 400
    
    # Use Node.js style approach with admin.auth().verifyIdToken()
    try:
        # Import Firebase Admin modules
        import firebase_admin
        from firebase_admin import auth
        
        # First, make sure Firebase is initialized
        try:
            app = firebase_admin.get_app()
            print(f"Using existing Firebase app: {app.name}, Project ID: {app.project_id}")
        except ValueError:
            print("Firebase app not initialized, initializing now...")
            from services.firebase_service import initialize_firebase
            app = initialize_firebase()
            if not app:
                return jsonify({"success": False, "message": "Could not initialize Firebase"}), 500
        
        # Now verify the token with auth.verify_id_token()
        print(f"Verifying token (length: {len(id_token)})")
        
        try:
            # This is EXACTLY like Node.js admin.auth().verifyIdToken(idToken)
            decoded_token = auth.verify_id_token(id_token)
            
            # Extract user data from token
            firebase_uid = decoded_token.get('uid')
            email = decoded_token.get('email')
            name = decoded_token.get('name', '')
            profile_picture = decoded_token.get('picture')
            
            print(f"Token verified successfully for UID: {firebase_uid}")
            
            if not email:
                print("Email required but not found in token")
                return jsonify({"success": False, "message": "Email is required"}), 400
            
            # Check if user exists
            existing_user = User.query.filter(
                (User.email == email) | (User.firebase_uid == firebase_uid)
            ).first()
            
        except auth.InvalidIdTokenError as token_error:
            # Exactly like Node.js example catch block
            error_message = str(token_error)
            print(f"Invalid token error: {error_message}")
            return jsonify({"success": False, "message": "Invalid token"}), 401
            
        except auth.ExpiredIdTokenError as expired_error:
            print(f"Token expired: {str(expired_error)}")
            return jsonify({"success": False, "message": "Token expired"}), 401
            
        except Exception as verify_error:
            error_message = str(verify_error)
            print(f"Token verification failed: {error_message}")
            return jsonify({"success": False, "message": "Token verification failed"}), 401
            
    except ImportError:
        print("Firebase admin auth module not available")
        return jsonify({"success": False, "message": "Firebase authentication not configured"}), 500
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"success": False, "message": f"Authentication error: {str(e)}"}), 500
    
    # If we get here, token was verified successfully
        
    # If user exists, update Firebase UID if needed and set PIN
    if existing_user:
        if not existing_user.firebase_uid:
            existing_user.firebase_uid = firebase_uid
        existing_user.set_pin(pin)
        
        # Update other details if available
        if name and not existing_user.name:
            existing_user.name = name
        if profile_picture and not existing_user.profile_image:
            existing_user.profile_image = profile_picture
            
        db.session.commit()
        login_user(existing_user)
        
        # Check if this is an admin login and redirect accordingly
        is_admin_login = request.args.get('admin') == '1'
        
        # For admin login, check if user has admin rights
        if is_admin_login and not existing_user.is_admin:
            return jsonify({
                "success": False,
                "message": "You do not have admin privileges",
                "redirect": url_for('auth.login')
            }), 403
        
        # Redirect to appropriate dashboard based on admin status
        redirect_url = url_for('admin.index') if existing_user.is_admin and is_admin_login else url_for('prediction.dashboard')
        
        return jsonify({
            "success": True, 
            "message": "Login successful", 
            "redirect": redirect_url
        })
    
    # Create new user with Google data
    now = get_ist_now()
    new_user = User(
        email=email,
        firebase_uid=firebase_uid,
        name=name or email.split('@')[0],
        profile_image=profile_picture,
        is_premium=False,
        registration_date=now,
        trial_end_date=now + datetime.timedelta(days=Config.TRIAL_DAYS),
        referral_code=generate_referral_code()
    )
    
    # Set PIN
    new_user.set_pin(pin)
    
    # Apply referral code if provided
    if referral_code:
        # Find referring user
        referring_user = User.query.filter_by(referral_code=referral_code).first()
        if referring_user:
            new_user.referred_by = referring_user.id
            
            # Add premium months to referring user
            if referring_user.premium_end_date and referring_user.premium_end_date > now:
                referring_user.premium_end_date += datetime.timedelta(days=30 * Config.REFERRAL_MONTHS)
            else:
                referring_user.premium_end_date = now + datetime.timedelta(days=30 * Config.REFERRAL_MONTHS)
                referring_user.is_premium = True
    
    # Save new user
    db.session.add(new_user)
    db.session.commit()
    
    # Log in
    login_user(new_user)
    
    # Send welcome notification
    try:
        from services.notification_service import send_welcome_notification
        send_welcome_notification(new_user.id)
    except Exception as notif_error:
        print(f"Error sending welcome notification: {str(notif_error)}")
        # Don't fail the request just because notification failed
    
    return jsonify({
        "success": True, 
        "message": "Account created successfully", 
        "redirect": url_for('prediction.dashboard')
    })

# Add more API endpoints below as needed

@api_bp.route('/test-firebase', methods=['GET'])
def test_firebase():
    """Simple endpoint to test Firebase initialization"""
    try:
        # Import Firebase admin
        import firebase_admin
        from firebase_admin import auth

        # Check if Firebase is initialized
        try:
            app = firebase_admin.get_app()
            initialized = True
            app_name = app.name
            project_id = app.project_id
        except ValueError:
            initialized = False
            app_name = "None"
            project_id = "None"

        # Get Firebase configuration
        from services.firebase_service import get_firebase_config
        config = get_firebase_config()

        return jsonify({
            "success": True,
            "firebase_admin_imported": True,
            "firebase_initialized": initialized,
            "app_name": app_name,
            "project_id": project_id,
            "client_config": config
        })

    except ImportError:
        return jsonify({
            "success": False,
            "message": "Firebase Admin SDK not available",
            "firebase_admin_imported": False
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error testing Firebase: {str(e)}"
        })