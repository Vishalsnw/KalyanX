import os
import json
import logging
import sys

# Set up logging with more detailed information
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add logging handler to also log to stdout (console)
stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stdout_handler.setFormatter(formatter)
logger.addHandler(stdout_handler)

# Define flag for Firebase availability
FIREBASE_AVAILABLE = False
firebase_app = None

# Check if Firebase credentials are available
def is_firebase_configured():
    """Check if Firebase credentials are configured"""
    required_vars = ['FIREBASE_API_KEY', 'FIREBASE_PROJECT_ID', 'FIREBASE_APP_ID']
    configured = all(os.environ.get(var) for var in required_vars)
    
    # Log the configuration status
    if configured:
        logger.info("Firebase is properly configured with required environment variables")
        for var in required_vars:
            logger.info(f"{var} is set")
    else:
        logger.error("Firebase is not properly configured")
        for var in required_vars:
            if not os.environ.get(var):
                logger.error(f"Missing {var} environment variable")
                
    return configured

# Enable Firebase for Google Sign-In
try:
    import firebase_admin
    from firebase_admin import auth, credentials
    FIREBASE_AVAILABLE = True
    logger.info("Firebase admin SDK is available and imported successfully")
except ImportError as e:
    logger.error(f"Firebase admin SDK import error: {str(e)}")
    logger.warning("Firebase admin SDK not installed. Install with: pip install firebase-admin")
    FIREBASE_AVAILABLE = False

# Initialize Firebase function - called within app context when needed
def initialize_firebase():
    """Initialize Firebase Admin SDK if available and not already initialized"""
    global firebase_app
    
    if not FIREBASE_AVAILABLE:
        logger.warning("Firebase admin SDK not available")
        return None
        
    try:
        from firebase_admin import firestore
        
        # IMPORTANT: Removed recursive call to initialize_firebase() which was causing infinite recursion
        # Don't check Firestore yet, as firebase_app might not be initialized at this point
        
        # Only try to use Firestore if firebase_app exists
        if firebase_app:
            db = firestore.client()
            # Test Firestore connection
            db.collection('test').limit(1).get()
            logger.info("Firestore API is enabled and working")
        else:
            logger.debug("Firebase app not yet initialized, skipping Firestore check")
    except Exception as e:
        logger.error(f"Firestore API error: {str(e)}")
        if "403" in str(e):
            logger.error("Firestore API is not enabled. Please enable it in the Firebase Console")
        else:
            logger.error("Failed to initialize Firestore client")
        
    if firebase_app:
        # Already initialized
        logger.info("Firebase app is already initialized, returning existing instance")
        return firebase_app
        
    if not is_firebase_configured():
        logger.warning("Firebase environment variables not properly configured")
        
        # Check each environment variable
        for key in ['FIREBASE_API_KEY', 'FIREBASE_PROJECT_ID', 'FIREBASE_APP_ID']:
            value = os.environ.get(key)
            if value:
                logger.info(f"{key} is set to: {value[:3]}...{value[-3:]}")
            else:
                logger.error(f"{key} is missing")
                
        return None
        
    try:
        # For Firebase Authentication, we need to explicitly set the project ID
        
        # Use the credentials from environment variables
        project_id = os.environ.get("FIREBASE_PROJECT_ID")
        
        # Log that we're initializing with credentials
        logger.info(f"Initializing Firebase with project ID: {project_id}")
        
        # Try to use service account credentials first
        try:
            # Check for credentials file
            cred_path = "firebase-service-account.json"
            if os.path.exists(cred_path):
                logger.info(f"Initializing Firebase with service account credentials from {cred_path}")
                
                # Initialize with the service account file
                cred = credentials.Certificate(cred_path)
                firebase_app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized successfully with service account")
            else:
                # Fallback to project ID only if no service account file
                logger.info(f"Service account file not found, initializing with project ID: {project_id}")
                
                # Set environment variable for Google Cloud project
                if project_id:
                    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
                    
                # Create the Firebase app with explicit project ID option
                firebase_app = firebase_admin.initialize_app(options={
                    'projectId': project_id,
                })
                logger.info("Firebase Admin SDK initialized successfully with explicit project ID")
            
        except Exception as init_error:
            logger.error(f"Failed to initialize with credentials/project ID: {str(init_error)}")
            
            # Try as fallback without options
            try:
                logger.info("Attempting initialization without options")
                # Try without credentials and without options, just with environment variable
                firebase_app = firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized without options")
            except Exception as default_error:
                logger.error(f"Failed to initialize with fallback method: {str(default_error)}")
                raise
                
        return firebase_app
    except ValueError as e:
        # This error occurs if the app is already initialized
        if "already exists" in str(e):
            logger.info("Firebase Admin SDK already initialized")
            # Get the existing app
            firebase_app = firebase_admin.get_app()
            return firebase_app
        else:
            logger.error(f"ValueError initializing Firebase: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {str(e)}")
        logger.error(f"Exception type: {type(e).__name__}")
        return None

def get_firebase_config():
    """
    Get Firebase configuration for client-side initialization
    """
    if not is_firebase_configured():
        return None
        
    return {
        "apiKey": os.environ.get("FIREBASE_API_KEY"),
        "authDomain": f"{os.environ.get('FIREBASE_PROJECT_ID')}.firebaseapp.com",
        "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
        "appId": os.environ.get("FIREBASE_APP_ID"),
    }

def verify_firebase_token(id_token):
    """
    Verify the Firebase ID token and return user info
    Using the same approach as the Node.js example:
    
    admin.auth().verifyIdToken(idToken)
      .then((decodedToken) => {
        const uid = decodedToken.uid;
        // Token valid, proceed
      })
      .catch((error) => {
        console.error("Token verification failed:", error);
        res.status(401).send("Invalid or expired token");
      });
    
    Args:
        id_token (str): The Firebase ID token to verify
        
    Returns:
        dict: User information if verification is successful
        None: If verification fails
    """
    # Initialize Firebase if not already done
    if not firebase_app:
        initialize_firebase()
        
    if not FIREBASE_AVAILABLE or not firebase_app:
        logger.error("Firebase not properly configured")
        return None
        
    try:
        # Access auth from firebase_admin after verifying it's available
        from firebase_admin import auth
        
        # Simple, direct verification without extra layers
        logger.info("Verifying Firebase ID token directly")
        try:
            # This is equivalent to the admin.auth().verifyIdToken() in Node.js
            decoded_token = auth.verify_id_token(id_token)
            
            # Log success
            uid = decoded_token.get('uid')
            logger.info(f"Token verified successfully for UID: {uid}")
            
            # Return decoded token info
            return {
                'uid': uid,
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'email_verified': decoded_token.get('email_verified', False)
            }
        except Exception as verify_error:
            # Log specific error (equivalent to the catch block in Node.js)
            logger.error(f"Token verification failed: {str(verify_error)}")
            return None
            
    except ImportError:
        logger.error("Firebase auth module not available")
        return None
    except Exception as e:
        logger.error(f"Firebase token verification error: {str(e)}")
        return None

def get_user_from_token(id_token):
    """
    Verify the Firebase ID token and extract user information
    
    Args:
        id_token (str): The Firebase ID token to verify
        
    Returns:
        dict: User information including uid, email, phone_number if available
        None: If verification fails
    """
    # Verify the token
    decoded_token = verify_firebase_token(id_token)
    
    if not decoded_token:
        return None
    
    # Extract user information
    user_info = {
        'uid': decoded_token.get('uid'),
        'email': decoded_token.get('email'),
        'phone_number': decoded_token.get('phone_number'),
        'email_verified': decoded_token.get('email_verified', False),
        'name': decoded_token.get('name'),
        'picture': decoded_token.get('picture')
    }
    
    return user_info

def create_firebase_user(email=None, phone_number=None):
    """
    Create a new user in Firebase Authentication
    
    Args:
        email (str, optional): User's email address
        phone_number (str, optional): User's phone number
        
    Returns:
        str: Firebase UID of the created user
        None: If creation fails
    """
    # Initialize Firebase if not already done
    if not firebase_app:
        initialize_firebase()
        
    if not FIREBASE_AVAILABLE or not firebase_app:
        logger.error("Firebase not properly configured")
        return None
        
    try:
        # Access auth from firebase_admin after verifying it's available
        from firebase_admin import auth
        user_properties = {}
        if email:
            user_properties['email'] = email
        if phone_number:
            user_properties['phone_number'] = phone_number
            
        user = auth.create_user(**user_properties)
        return user.uid
    except ImportError:
        logger.error("Firebase auth module not available")
        return None
    except Exception as e:
        logger.error(f"Firebase user creation error: {str(e)}")
        return None

def delete_firebase_user(uid):
    """
    Delete a user from Firebase Authentication
    
    Args:
        uid (str): The Firebase UID of the user to delete
        
    Returns:
        bool: True if deletion is successful, False otherwise
    """
    # Initialize Firebase if not already done
    if not firebase_app:
        initialize_firebase()
        
    if not FIREBASE_AVAILABLE or not firebase_app:
        logger.error("Firebase not properly configured")
        return False
        
    try:
        # Access auth from firebase_admin after verifying it's available
        from firebase_admin import auth
        auth.delete_user(uid)
        return True
    except ImportError:
        logger.error("Firebase auth module not available")
        return False
    except Exception as e:
        logger.error(f"Firebase user deletion error: {str(e)}")
        return False