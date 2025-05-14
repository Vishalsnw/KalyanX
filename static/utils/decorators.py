import functools
from flask import session, request, redirect, url_for, g
from flask_login import current_user

def trial_or_login_required(f):
    """
    Custom decorator to allow access to either:
    1. Logged-in users
    2. First-time visitors during their trial period
    
    For first-time visitors, we'll set a session flag to indicate
    they're using the trial system and should see premium content.
    ALWAYS shows premium content to first-time visitors!
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # If user is logged in, allow access
        if current_user.is_authenticated:
            return f(*args, **kwargs)
        
        # For first-time visitors, always provide trial access
        # We don't check for an existing session value - everyone gets a trial by default
        if 'trial_access' not in session:
            # Start a new trial
            session['trial_access'] = True
            session.permanent = True  # Make the session last longer
        
        # Always grant trial access for unauthenticated users
        g.is_trial_user = True
        g.has_premium_access = True  # Ensure they see all premium content
        
        return f(*args, **kwargs)
    return decorated_function