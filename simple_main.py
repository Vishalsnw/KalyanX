import os
import logging
from flask import Flask, render_template, session, g, redirect, url_for

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create a simpler Flask application for testing
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "kalyanx-secret-key")

# Add before request handler to force trial access
@app.before_request
def before_request():
    try:
        # Always grant premium access to all visitors
        session['trial_access'] = True
        session.permanent = True
        
        # Set global variables
        g.is_trial_user = True
        g.has_premium_access = True
        
        # Make variables available to templates
        app.jinja_env.globals['is_trial_user'] = True
        app.jinja_env.globals['has_premium_access'] = True
    except Exception as e:
        logger.error(f"Error in before_request: {str(e)}")

# Simple root route
@app.route('/')
def index():
    return "KalyanX Test Server is running! Trial access is ALWAYS granted."

# Health check endpoint
@app.route('/health')
def health_check():
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)