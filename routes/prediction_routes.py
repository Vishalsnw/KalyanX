from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, abort, g
from flask_login import login_required, current_user
from datetime import datetime, date, timedelta
import pandas as pd
from app import db
from models import Result, Prediction, PredictionView
from services.prediction_service import get_latest_results, get_predictions_for_date, update_predictions_for_market
from services.data_service import get_recent_results, get_result_by_date
from utils import format_date, is_matching_prediction, get_ist_now, get_ist_date, format_ist_datetime
from utils.decorators import trial_or_login_required
from config import Config
from scheduler import is_market_operating, find_next_valid_day

prediction_bp = Blueprint('prediction', __name__)


@prediction_bp.route('/')
def index():
    """Landing page - Always redirects to dashboard for all visitors"""
    # Always show dashboard directly for everyone, as requested
    return redirect(url_for('prediction.dashboard'))


@prediction_bp.route('/dashboard')
@trial_or_login_required
def dashboard():
    """User dashboard"""
    # Get today's date in IST
    today = get_ist_date()
    
    # Get all markets
    markets = Config.MARKETS.keys()
    
    # Get recent results
    recent_results = {}
    for market in markets:
        recent_results[market] = get_recent_results(market=market, limit=5)
    
    # Get predictions for each market based on next operating day
    predictions = {}
    prediction_dates = {}
    # Allow access for both logged-in users with access and trial users
    # For anonymous users, we'll check g.is_trial_user or g.has_premium_access
    has_access = current_user.is_authenticated and current_user.has_access
    is_trial = g.get('is_trial_user', False) 
    has_premium = g.get('has_premium_access', False)
    
    if has_access or is_trial or has_premium:
        for market in markets:
            # Check if market operates today
            if is_market_operating(market, today):
                market_date = today
            else:
                # Find next valid day for this market
                market_date = find_next_valid_day(market, today)
            
            market_predictions = get_predictions_for_date(market_date, market=market)
            if market_predictions:
                # Record that user viewed this prediction (only for authenticated users)
                if current_user.is_authenticated:
                    for pred in market_predictions:
                        # Check if view record already exists
                        existing_view = PredictionView.query.filter_by(
                            user_id=current_user.id,
                            prediction_id=pred.id
                        ).first()
                        
                        if not existing_view:
                            view = PredictionView(
                                user_id=current_user.id,
                                prediction_id=pred.id
                            )
                            db.session.add(view)
                    
                    db.session.commit()
                
                predictions[market] = market_predictions[0]
                prediction_dates[market] = market_date
    
    # Check for matching predictions to highlight
    matched_predictions = {}
    # Same condition as above for consistency
    has_access = current_user.is_authenticated and current_user.has_access
    is_trial = g.get('is_trial_user', False) 
    has_premium = g.get('has_premium_access', False)
    
    if (has_access or is_trial or has_premium) and predictions:
        for market, prediction in predictions.items():
            # Get result for this market on the prediction date
            result = Result.query.filter_by(
                date=prediction.date,
                market=market
            ).first()
            
            if result:
                # Check for matches
                prediction_data = {
                    'open_digits': prediction.open_digits,
                    'close_digits': prediction.close_digits,
                    'jodi_list': prediction.jodi_list,
                    'patti_list': prediction.patti_list
                }
                
                result_data = {
                    'open': result.open,
                    'close': result.close,
                    'jodi': result.jodi
                }
                
                matches = is_matching_prediction(prediction_data, result_data)
                if any(matches.values()):
                    matched_predictions[market] = matches
    
    return render_template(
        'dashboard.html',
        results=recent_results,
        predictions=predictions,
        prediction_dates=prediction_dates,
        matched_predictions=matched_predictions,
        markets=markets,
        today=today,
        format_date=format_date
    )


@prediction_bp.route('/predictions')
@trial_or_login_required
def predictions():
    """Predictions page"""
    # Check if user has access (either logged in with access or trial user)
    has_access = current_user.is_authenticated and current_user.has_access
    is_trial = g.get('is_trial_user', False) 
    has_premium = g.get('has_premium_access', False)
    
    if not (has_access or is_trial or has_premium):
        flash('Please subscribe to access predictions', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # Get date parameter (default to the future date with most predictions)
    today = get_ist_date()
    
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # Find the future date with most predictions
            future_dates = db.session.query(Prediction.date, db.func.count(Prediction.id).label('count')) \
                .filter(Prediction.date >= today) \
                .group_by(Prediction.date) \
                .order_by(db.desc('count')) \
                .first()
            
            if future_dates:
                selected_date = future_dates[0]
            else:
                selected_date = today
    else:
        # Find the future date with most predictions
        future_dates = db.session.query(Prediction.date, db.func.count(Prediction.id).label('count')) \
            .filter(Prediction.date >= today) \
            .group_by(Prediction.date) \
            .order_by(db.desc('count')) \
            .first()
        
        if future_dates:
            selected_date = future_dates[0]
        else:
            selected_date = today
    
    # Get market parameter (default to all)
    market = request.args.get('market')
    
    # Get predictions for selected date and market
    predictions = get_predictions_for_date(selected_date, market)
    
    # Get results for the same date and market for comparison
    results = get_result_by_date(selected_date, market)
    
    # Create a mapping of results by market for easy lookup
    results_by_market = {result.market: result for result in results}
    
    # Determine matching predictions
    matched_predictions = {}
    for prediction in predictions:
        if prediction.market in results_by_market:
            result = results_by_market[prediction.market]
            
            prediction_data = {
                'open_digits': prediction.open_digits,
                'close_digits': prediction.close_digits,
                'jodi_list': prediction.jodi_list,
                'patti_list': prediction.patti_list
            }
            
            result_data = {
                'open': result.open,
                'close': result.close,
                'jodi': result.jodi
            }
            
            matches = is_matching_prediction(prediction_data, result_data)
            if any(matches.values()):
                matched_predictions[prediction.market] = matches
    
    # Get date range for navigation
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)
    date_range = [day_after.strftime('%Y-%m-%d'), tomorrow.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')] + [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(1, 7)]
    
    # Get prediction dates per market (if a market doesn't operate on the selected date)
    prediction_dates = {}
    
    return render_template(
        'predictions.html',
        predictions=predictions,
        results=results_by_market,
        matched_predictions=matched_predictions,
        selected_date=selected_date,
        date_range=date_range,
        markets=Config.MARKETS.keys(),
        selected_market=market,
        format_date=format_date,
        prediction_dates=prediction_dates,
        is_market_operating=is_market_operating
    )


@prediction_bp.route('/results')
@trial_or_login_required
def results():
    """Results page"""
    # Get date parameter (default to today)
    date_str = request.args.get('date')
    if date_str:
        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()
    
    # Get market parameter (default to all)
    market = request.args.get('market')
    
    # Get results
    results = get_result_by_date(selected_date, market)
    
    # Get date range for navigation (including tomorrow)
    today = date.today()
    tomorrow = today + timedelta(days=1)
    date_range = [tomorrow.strftime('%Y-%m-%d')] + [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]
    
    return render_template(
        'results.html',
        results=results,
        selected_date=selected_date,
        date_range=date_range,
        markets=Config.MARKETS.keys(),
        selected_market=market
    )


@prediction_bp.route('/api/update-predictions/<market>', methods=['POST'])
@login_required
def api_update_predictions(market):
    """API endpoint to manually update predictions for a market"""
    # Only admins can trigger this
    if not current_user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    # Update predictions
    prediction = update_predictions_for_market(market)
    
    if prediction:
        return jsonify({
            "success": True,
            "message": f"Predictions updated for {market}",
            "prediction": {
                "date": prediction.date.strftime('%Y-%m-%d'),
                "market": prediction.market,
                "open_digits": prediction.open_digits,
                "close_digits": prediction.close_digits,
                "jodi_list": prediction.jodi_list,
                "patti_list": prediction.patti_list
            }
        })
    else:
        return jsonify({
            "success": False,
            "message": f"Failed to update predictions for {market}"
        }), 400
