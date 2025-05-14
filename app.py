import os
import logging
import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_login import LoginManager
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from pywebpush import webpush


class Base(DeclarativeBase):
    pass


# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
migrate = Migrate()

# Initialize scheduler
scheduler = BackgroundScheduler()

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "kalyanx-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Set permanent session
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)  # Trial period length

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Configure default sender for emails (used for logging in development)
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@kalyanx.com')

# Initialize extensions with the app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
migrate.init_app(app, db)

# Configure webpush
app.config['VAPID_PRIVATE_KEY'] = os.environ.get('VAPID_PRIVATE_KEY')
app.config['VAPID_PUBLIC_KEY'] = os.environ.get('VAPID_PUBLIC_KEY')
app.config['VAPID_CLAIMS'] = {
    'sub': 'mailto:webpush@kalyanx.com'
}

# Razorpay configuration
app.config['RAZORPAY_KEY_ID'] = os.environ.get('RAZORPAY_KEY_ID')
app.config['RAZORPAY_KEY_SECRET'] = os.environ.get('RAZORPAY_KEY_SECRET')

# Import models
with app.app_context():
    import models

    # Create all tables
    db.create_all()

    # Set up login manager
    @login_manager.user_loader
    def load_user(user_id):
        return models.User.query.get(int(user_id))

# Import flask modules
from flask import g, session, request

# Register blueprints
from routes.auth_routes import auth_bp
from routes.prediction_routes import prediction_bp
from routes.subscription_routes import subscription_bp
from routes.forum_routes import forum_bp
from routes.admin_routes import admin_bp
from routes.static_routes import static_bp
from routes.api_routes import api_bp

app.register_blueprint(auth_bp)
app.register_blueprint(prediction_bp)
app.register_blueprint(subscription_bp)
app.register_blueprint(forum_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(static_bp)
app.register_blueprint(api_bp, url_prefix='/api')

# Import scheduler tasks
from scheduler import setup_scheduler

# Start scheduler with error handling
try:
    with app.app_context():
        # Set a timeout for scheduler jobs
        scheduler.configure(executors={'default': {'type': 'threadpool', 'max_workers': 5}})
        # Add jobs with proper error handling
        setup_scheduler(scheduler)
        # Start scheduler in background
        scheduler.start()
        logger.info("Scheduler started successfully")
except Exception as e:
    logger.error(f"Failed to start scheduler: {str(e)}")
    # Continue without scheduler in case of error

# Create a filter for timestamps
@app.template_filter('timestamp_to_date')
def timestamp_to_date(timestamp):
    """Convert Unix timestamp to formatted date"""
    try:
        return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M')
    except Exception:
        return 'Invalid date'

# Add a before request function to set trial user status for all templates
@app.before_request
def before_request():
    try:
        # ALWAYS grant premium access to all visitors regardless of time
        session['trial_access'] = True  # Force this to always be true
        session.permanent = True  # Make the session last longer
        
        # Always grant premium access for everyone
        g.is_trial_user = True
        g.has_premium_access = True  # Ensure they see all premium content
        
        # Make premium access available to templates
        app.jinja_env.globals['is_trial_user'] = True
        app.jinja_env.globals['has_premium_access'] = True
    except Exception as e:
        logger.error(f"Error in before_request: {str(e)}")
        # Don't fail if there's an error - still allow the request to proceed

logger.info("Application initialized successfully")

# Add a simple health check route
@app.route('/health')
def health_check():
    """Health check endpoint for debugging"""
    return 'OK', 200
