from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
import pandas as pd
import datetime
from app import db
from models import User, Result, Prediction, Subscription, ForumPost
from services.data_service import get_dashboard_stats, import_csv_data
from services.prediction_service import train_models_for_all_markets, get_prediction_accuracy
from services.firebase_service import verify_firebase_token, initialize_firebase
from config import Config
import firebase_admin
from firebase_admin import auth, firestore
import json
# Remove duplicate import
# import datetime

admin_bp = Blueprint('admin', __name__)


@admin_bp.before_request
def check_admin():
    """Check if user is an admin before processing request"""
    if not current_user.is_authenticated or not current_user.is_admin:
        abort(403)


@admin_bp.route('/admin')
@login_required
def index():
    """Admin dashboard page"""
    # Get dashboard stats
    stats = get_dashboard_stats()

    # Get prediction accuracy
    accuracy = get_prediction_accuracy()

    return render_template(
        'admin.html',
        stats=stats,
        accuracy=accuracy
    )


@admin_bp.route('/admin/users')
@login_required
def users():
    """User management page"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Get users with pagination
    query = User.query.order_by(User.registration_date.desc())
    total = query.count()
    users = query.offset((page - 1) * per_page).limit(per_page).all()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin_users.html',
        users=users,
        page=page,
        total_pages=total_pages,
        total_users=total
    )


@admin_bp.route('/admin/results')
@login_required
def results():
    """Results management page"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Get market filter
    market = request.args.get('market')

    # Build query
    query = Result.query.order_by(Result.date.desc())

    if market:
        query = query.filter_by(market=market)

    # Get data with pagination
    total = query.count()
    results = query.offset((page - 1) * per_page).limit(per_page).all()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin_results.html',
        results=results,
        page=page,
        total_pages=total_pages,
        total_results=total,
        markets=Config.MARKETS.keys(),
        selected_market=market
    )


@admin_bp.route('/admin/predictions')
@login_required
def predictions():
    """Predictions management page"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Get filters
    market = request.args.get('market')
    date_str = request.args.get('date')

    # Build query
    query = Prediction.query.order_by(Prediction.date.desc())

    if market:
        query = query.filter_by(market=market)

    if date_str:
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(date=date)
        except:
            pass

    # Get data with pagination
    total = query.count()
    predictions = query.offset((page - 1) * per_page).limit(per_page).all()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin_predictions.html',
        predictions=predictions,
        page=page,
        total_pages=total_pages,
        total_predictions=total,
        markets=Config.MARKETS.keys(),
        selected_market=market,
        selected_date=date_str or ''
    )


@admin_bp.route('/admin/subscriptions')
@login_required
def subscriptions():
    """Subscriptions management page"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Build query
    query = Subscription.query.order_by(Subscription.created_at.desc())

    # Get data with pagination
    total = query.count()
    subscriptions = query.offset((page - 1) * per_page).limit(per_page).all()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin_subscriptions.html',
        subscriptions=subscriptions,
        page=page,
        total_pages=total_pages,
        total_subscriptions=total
    )


@admin_bp.route('/admin/forum')
@login_required
def forum():
    """Forum management page"""
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Get category filter
    category_id = request.args.get('category')

    # Get all categories
    from models import ForumCategory
    categories = ForumCategory.query.all()

    # Build query
    query = ForumPost.query.order_by(ForumPost.created_at.desc())

    if category_id:
        query = query.filter_by(category_id=category_id)

    # Get data with pagination
    total = query.count()
    posts = query.offset((page - 1) * per_page).limit(per_page).all()

    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page

    return render_template(
        'admin_forum.html',
        posts=posts,
        page=page,
        total_pages=total_pages,
        total_posts=total,
        categories=categories,
        selected_category=category_id
    )


@admin_bp.route('/admin/import-csv', methods=['GET', 'POST'])
@login_required
def import_csv():
    """Import CSV data page"""
    if request.method == 'POST':
        if 'csv_file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)

        csv_file = request.files['csv_file']

        if csv_file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)

        # Save uploaded file
        file_path = f'uploads/{csv_file.filename}'
        csv_file.save(file_path)

        try:
            # Import data
            import_csv_data(file_path)
            flash('Data imported successfully', 'success')
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'danger')

        return redirect(url_for('admin.results'))

    return render_template('admin_import.html')


@admin_bp.route('/admin/train-models', methods=['POST'])
@login_required
def train_models():
    """Train ML models for all markets"""
    try:
        train_models_for_all_markets()
        flash('Models trained successfully', 'success')
    except Exception as e:
        flash(f'Training failed: {str(e)}', 'danger')

    return redirect(url_for('admin.index'))


@admin_bp.route('/admin/toggle-premium/<int:user_id>', methods=['POST'])
@login_required
def toggle_premium(user_id):
    """Toggle premium status for a user"""
    user = User.query.get_or_404(user_id)

    if user.is_premium:
        user.is_premium = False
        user.premium_end_date = None
        message = f'Premium status removed for user {user.mobile}'
    else:
        user.is_premium = True
        user.premium_end_date = datetime.datetime.now() + datetime.timedelta(days=30)
        message = f'Premium status granted to user {user.mobile} for 30 days'

    db.session.commit()

    flash(message, 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/delete-post', methods=['POST'])
@login_required
def delete_post():
    """Delete a forum post"""
    post_id = request.form.get('post_id', type=int)
    post = ForumPost.query.get_or_404(post_id)

    # Delete related comments
    for comment in post.comments:
        db.session.delete(comment)

    db.session.delete(post)
    db.session.commit()

    flash('Post deleted successfully', 'success')
    return redirect(url_for('admin.forum'))


@admin_bp.route('/admin/delete-prediction', methods=['POST'])
@login_required
def delete_prediction():
    """Delete a prediction"""
    prediction_id = request.form.get('prediction_id', type=int)
    prediction = Prediction.query.get_or_404(prediction_id)

    db.session.delete(prediction)
    db.session.commit()

    flash('Prediction deleted successfully', 'success')
    return redirect(url_for('admin.predictions'))


@admin_bp.route('/admin/edit-result', methods=['POST'])
@login_required
def edit_result():
    """Edit a result"""
    result_id = request.form.get('result_id', type=int)
    result = Result.query.get_or_404(result_id)

    # Update fields
    try:
        date_str = request.form.get('date')
        result.date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        result.market = request.form.get('market')
        result.open = request.form.get('open') or None
        result.close = request.form.get('close') or None
        result.jodi = request.form.get('jodi') or None

        # Update dependent fields
        if result.open and result.close and len(result.open) == 3 and len(result.close) == 3:
            result.jodi = result.open[2] + result.close[2]

        result.day_of_week = result.date.strftime('%A')
        result.is_weekend = result.date.weekday() >= 5  # Saturday or Sunday

        # Calculate open and close sums
        if result.open and len(result.open) == 3:
            result.open_sum = sum(int(digit) for digit in result.open)

        if result.close and len(result.close) == 3:
            result.close_sum = sum(int(digit) for digit in result.close)

        result.updated_at = datetime.datetime.now()

        db.session.commit()
        flash('Result updated successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Update failed: {str(e)}', 'danger')

    return redirect(url_for('admin.results'))


@admin_bp.route('/admin/extend-premium', methods=['POST'])
@login_required
def extend_premium():
    """Extend premium membership for a user"""
    user_id = request.form.get('user_id', type=int)
    months = request.form.get('months', type=int, default=1)

    user = User.query.get_or_404(user_id)

    # Calculate new end date
    if user.is_premium and user.premium_end_date and user.premium_end_date > datetime.datetime.now():
        # Extend existing subscription
        new_end_date = user.premium_end_date + datetime.timedelta(days=30 * months)
    else:
        # New subscription
        new_end_date = datetime.datetime.now() + datetime.timedelta(days=30 * months)
        user.is_premium = True

    user.premium_end_date = new_end_date

    # Create subscription record
    subscription = Subscription(
        user_id=user.id,
        start_date=datetime.datetime.now(),
        end_date=new_end_date,
        amount=0.00,  # Admin extension, no payment
        payment_id=f"admin_extension_{user.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        order_id=f"admin_order_{user.id}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
        status='success'
    )

    db.session.add(subscription)
    db.session.commit()

    flash(f'Premium membership extended for {user.mobile} by {months} month(s)', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/toggle-admin', methods=['POST'])
@login_required
def toggle_admin():
    """Toggle admin status for a user"""
    user_id = request.form.get('user_id', type=int)

    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin

    db.session.commit()

    status = "granted" if user.is_admin else "removed"
    flash(f'Admin status {status} for user {user.mobile}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/reset-pin', methods=['POST'])
@login_required
def reset_pin():
    """Reset PIN for a user"""
    user_id = request.form.get('user_id', type=int)

    user = User.query.get_or_404(user_id)
    # Set a default PIN of 1234
    user.set_pin('1234')

    db.session.commit()

    flash(f'PIN reset to 1234 for user {user.mobile}', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/import-results', methods=['POST'])
@login_required
def import_results():
    """Import latest results"""
    try:
        # Run the fetch_results.py script
        from fetch_results import main as fetch_results
        fetch_results()
        flash('Results imported successfully', 'success')
    except Exception as e:
        flash(f'Import failed: {str(e)}', 'danger')

    return redirect(url_for('admin.results'))


@admin_bp.route('/admin/generate-predictions', methods=['POST'])
@login_required
def generate_predictions():
    """Generate predictions for all markets"""
    try:
        # Run the generate_predictions.py script
        from generate_predictions import main as gen_predictions
        gen_predictions()
        flash('Predictions generated successfully', 'success')
    except Exception as e:
        flash(f'Generation failed: {str(e)}', 'danger')

    return redirect(url_for('admin.predictions'))


@admin_bp.route('/admin/firebase-users', methods=['GET', 'POST'])
@login_required
def firebase_users():
    """Firebase users management page"""
    error_message = None
    user_data = None
    search_type = request.args.get('search_type', 'email')
    search_term = request.args.get('search_term', '')

    try:
        # Ensure Firebase is initialized
        app = initialize_firebase()
        if not app:
            error_message = "Failed to initialize Firebase"
            return render_template(
                'admin_firebase_users.html',
                user_data=None,
                error_message=error_message,
                search_type='email',
                search_term='',
                premium_users=[]
            )

        try:
            # Initialize Firestore client
            db_client = firestore.client()
            users_collection = db_client.collection('users')
        except Exception as e:
            error_message = f"Failed to initialize Firestore client: {str(e)}"
            return render_template(
                'admin_firebase_users.html',
                user_data=None,
                error_message=error_message,
                search_type='email',
                search_term='',
                premium_users=[]
            )

        # Handle form submission for updating premium status
        if request.method == 'POST' and 'uid' in request.form:
            uid = request.form.get('uid')
            is_premium = request.form.get('is_premium') == 'true'
            months = int(request.form.get('months', 1))

            # Calculate expiry date (current time + specified months)
            now = datetime.datetime.now()
            expiry_date = now + datetime.timedelta(days=30*months)
            expiry_timestamp = int(expiry_date.timestamp() * 1000)  # Convert to milliseconds timestamp

            # Update user document in Firestore
            user_ref = users_collection.document(uid)

            if is_premium:
                user_ref.set({
                    'isPremium': True,
                    'premiumStartDate': int(now.timestamp() * 1000),
                    'premiumExpiryDate': expiry_timestamp,
                    'lastUpdated': int(now.timestamp() * 1000)
                }, merge=True)
                flash(f'Premium status granted to user for {months} month(s) until {expiry_date.strftime("%Y-%m-%d")}', 'success')
            else:
                user_ref.set({
                    'isPremium': False,
                    'premiumExpiryDate': None,
                    'lastUpdated': int(now.timestamp() * 1000)
                }, merge=True)
                flash('Premium status removed from user', 'success')

            # Redirect to refresh
            return redirect(url_for('admin.firebase_users', search_type=search_type, search_term=search_term))

        # Handle search
        if search_term:
            if search_type == 'email':
                # Get user by email
                try:
                    firebase_user = auth.get_user_by_email(search_term)
                    uid = firebase_user.uid

                    # Get Firestore data
                    user_doc = users_collection.document(uid).get()
                    firestore_data = user_doc.to_dict() if user_doc.exists else {}

                    # Combine data
                    user_data = {
                        'uid': firebase_user.uid,
                        'email': firebase_user.email,
                        'displayName': firebase_user.display_name,
                        'photoURL': firebase_user.photo_url,
                        'emailVerified': firebase_user.email_verified,
                        'creationTime': firebase_user.user_metadata.creation_timestamp,
                        'lastSignInTime': firebase_user.user_metadata.last_sign_in_timestamp,
                        'isPremium': firestore_data.get('isPremium', False),
                        'premiumExpiryDate': firestore_data.get('premiumExpiryDate'),
                        'premiumActive': firestore_data.get('isPremium', False) and 
                                        firestore_data.get('premiumExpiryDate', 0) > (datetime.datetime.now().timestamp() * 1000)
                    }
                except auth.UserNotFoundError:
                    error_message = f"No user found with email: {search_term}"

            elif search_type == 'uid':
                # Get user by UID
                try:
                    firebase_user = auth.get_user(search_term)

                    # Get Firestore data
                    user_doc = users_collection.document(search_term).get()
                    firestore_data = user_doc.to_dict() if user_doc.exists else {}

                    # Combine data
                    user_data = {
                        'uid': firebase_user.uid,
                        'email': firebase_user.email,
                        'displayName': firebase_user.display_name,
                        'photoURL': firebase_user.photo_url,
                        'emailVerified': firebase_user.email_verified,
                        'creationTime': firebase_user.user_metadata.creation_timestamp,
                        'lastSignInTime': firebase_user.user_metadata.last_sign_in_timestamp,
                        'isPremium': firestore_data.get('isPremium', False),
                        'premiumExpiryDate': firestore_data.get('premiumExpiryDate'),
                        'premiumActive': firestore_data.get('isPremium', False) and 
                                        firestore_data.get('premiumExpiryDate', 0) > (datetime.datetime.now().timestamp() * 1000)
                    }
                except auth.UserNotFoundError:
                    error_message = f"No user found with UID: {search_term}"

        # Recent premium users
        premium_users = []
        try:
            premium_users_query = users_collection.where('isPremium', '==', True).limit(10).get()
            for doc in premium_users_query:
                data = doc.to_dict()
                user_id = doc.id

                # Try to get user from Firebase Auth
                try:
                    auth_user = auth.get_user(user_id)
                    premium_users.append({
                        'uid': user_id,
                        'email': auth_user.email,
                        'displayName': auth_user.display_name,
                        'isPremium': data.get('isPremium', False),
                        'premiumExpiryDate': data.get('premiumExpiryDate'),
                        'premiumActive': data.get('isPremium', False) and 
                                        data.get('premiumExpiryDate', 0) > (datetime.datetime.now().timestamp() * 1000)
                    })
                except:
                    # Skip if auth user not found
                    continue
        except Exception as e:
            error_message = "Firebase Firestore API is not enabled. Please enable it in the Firebase Console."
            flash(error_message, 'danger')
            premium_users = []

        return render_template(
            'admin_firebase_users.html',
            user_data=user_data,
            error_message=error_message,
            search_type=search_type,
            search_term=search_term,
            premium_users=premium_users
        )

    except Exception as e:
        error_message = f"Firebase operation failed: {str(e)}"
        return render_template(
            'admin_firebase_users.html',
            user_data=user_data,
            error_message=error_message,
            search_type=search_type,
            search_term=search_term,
            premium_users=[]
        )