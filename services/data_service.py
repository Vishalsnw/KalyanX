import pandas as pd
import datetime
import os
from app import db
from models import Result, User, Subscription, ForumPost
from utils import calculate_derived_fields, parse_date
from config import Config


def import_csv_data(csv_file_path):
    """Import data from CSV file into the database"""
    # Read CSV file
    df = pd.read_csv(csv_file_path)
    
    # Process each row
    for _, row in df.iterrows():
        try:
            # Parse date
            date_str = row['Date']
            date_obj = parse_date(date_str)
            
            # Skip if result already exists
            existing_result = Result.query.filter_by(
                date=date_obj,
                market=row['Market']
            ).first()
            
            if existing_result:
                continue
            
            # Convert 'Off' values to None
            open_val = None if row['Open'] == 'Off' else row['Open']
            jodi_val = None if row['Jodi'] == 'Off' else row['Jodi']
            close_val = None if row['Close'] == 'Off' else row['Close']
            
            # Create result data dictionary
            result_data = {
                'date': date_obj,
                'market': row['Market'],
                'open': open_val,
                'jodi': jodi_val,
                'close': close_val,
                'day_of_week': row['day_of_week'],
                'is_weekend': bool(row['is_weekend']),
                'is_holiday': bool(row['is_holiday']) if 'is_holiday' in row else False
            }
            
            # Add numeric fields if present and not NaN
            for field in ['open_sum', 'close_sum', 'prev_jodi_distance']:
                if field in row and not pd.isna(row[field]):
                    result_data[field] = float(row[field])
            
            # Add string fields if present and not NaN
            for field in ['mirror_open', 'mirror_close', 'reverse_jodi']:
                if field in row and not pd.isna(row[field]):
                    result_data[field] = str(row[field])
            
            # Calculate any missing derived fields
            derived_fields = calculate_derived_fields(result_data)
            for key, value in derived_fields.items():
                if key not in result_data or result_data[key] is None:
                    result_data[key] = value
            
            # Create new result
            new_result = Result(**result_data)
            db.session.add(new_result)
        
        except Exception as e:
            print(f"Error processing row: {row}, Error: {str(e)}")
    
    # Commit all changes
    db.session.commit()


def get_dashboard_stats():
    """Get stats for the admin dashboard"""
    stats = {}
    
    # User stats
    stats['total_users'] = User.query.count()
    stats['new_users_today'] = User.query.filter(
        User.registration_date >= datetime.datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    stats['active_trial_users'] = User.query.filter(
        User.is_premium == False,
        User.trial_end_date >= datetime.datetime.now()
    ).count()
    stats['premium_users'] = User.query.filter_by(is_premium=True).count()
    
    # Registration timeline
    last_30_days = datetime.datetime.now() - datetime.timedelta(days=30)
    daily_registrations = db.session.query(
        db.func.date_trunc('day', User.registration_date).label('day'),
        db.func.count().label('count')
    ).filter(
        User.registration_date >= last_30_days
    ).group_by('day').order_by('day').all()
    
    stats['registration_timeline'] = {
        str(day.strftime('%Y-%m-%d')): count for day, count in daily_registrations
    }
    
    # Subscription stats
    stats['total_subscriptions'] = Subscription.query.filter_by(status='success').count()
    stats['subscription_revenue'] = db.session.query(
        db.func.sum(Subscription.amount)
    ).filter_by(status='success').scalar() or 0
    
    # Result stats
    stats['total_results'] = Result.query.count()
    stats['markets'] = db.session.query(
        Result.market, db.func.count(Result.id)
    ).group_by(Result.market).all()
    stats['markets'] = {market: count for market, count in stats['markets']}
    
    # Forum stats
    stats['total_forum_posts'] = ForumPost.query.count()
    stats['forum_posts_today'] = ForumPost.query.filter(
        ForumPost.created_at >= datetime.datetime.now().replace(hour=0, minute=0, second=0)
    ).count()
    
    return stats


def get_recent_results(market=None, limit=20):
    """Get recent results for display"""
    query = Result.query.order_by(Result.date.desc())
    
    if market:
        query = query.filter_by(market=market)
    
    results = query.limit(limit).all()
    return results


def get_result_by_date(date, market=None):
    """Get results for a specific date"""
    query = Result.query.filter_by(date=date)
    
    if market:
        query = query.filter_by(market=market)
    
    return query.all()
