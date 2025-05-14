import os
import logging
from app import app
from flask import g
from services.firebase_service import initialize_firebase

# Configure logging with more detailed information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Firebase at app startup
try:
    logger.info("Initializing Firebase from main.py...")
    firebase_app = initialize_firebase()
    if firebase_app:
        logger.info(f"Firebase initialized successfully with app name: {firebase_app.name}")
    else:
        logger.error("Failed to initialize Firebase in main.py")
except Exception as e:
    logger.error(f"Error initializing Firebase in main.py: {str(e)}")

# Add Firebase credentials to global context
@app.before_request
def add_firebase_credentials():
    g.firebase_api_key = os.environ.get('FIREBASE_API_KEY', 'AIzaSyBdksK14GepHhzd7xpCYhtQ1xh03sLOAH0')
    g.firebase_project_id = os.environ.get('FIREBASE_PROJECT_ID', 'kalyanx-replit')
    g.firebase_app_id = os.environ.get('FIREBASE_APP_ID', '1:531899366727:web:8ff86e1a4f29654ccb2062')
    # Log every request to help with debugging
    logger.debug(f"Request: {g.get('request_endpoint', 'unknown')} - {g.get('request_method', 'unknown')}")

# Add a simplified health check route
@app.route('/basic-health')
def basic_health():
    """Super simple health check endpoint"""
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Running with debug enabled for troubleshooting
    logger.info(f"Starting application on port {port} with host 0.0.0.0")
    app.run(host='0.0.0.0', port=port, debug=True)