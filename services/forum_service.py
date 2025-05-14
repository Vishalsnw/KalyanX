import datetime
from app import db
from models import ForumCategory, ForumPost, ForumComment
from config import Config


def initialize_forum_categories():
    """Initialize forum categories if they don't exist"""
    # Check if categories exist
    count = ForumCategory.query.count()
    
    if count == 0:
        # Create default categories from config
        for category_data in Config.FORUM_CATEGORIES:
            category = ForumCategory(
                name=category_data['name'],
                description=category_data['description']
            )
            db.session.add(category)
        
        db.session.commit()
        return True
    
    return False


def get_categories():
    """Get all forum categories with post counts"""
    categories = ForumCategory.query.all()
    
    # Manually add post counts
    for category in categories:
        category.post_count = ForumPost.query.filter_by(category_id=category.id).count()
        
        # Get latest post
        latest_post = ForumPost.query.filter_by(
            category_id=category.id
        ).order_by(ForumPost.created_at.desc()).first()
        
        category.latest_post = latest_post
    
    return categories


def get_posts_by_category(category_id, page=1, per_page=20):
    """Get paginated posts for a category"""
    posts = ForumPost.query.filter_by(
        category_id=category_id
    ).order_by(ForumPost.created_at.desc())
    
    # Get total count
    total = posts.count()
    
    # Get paginated results
    start = (page - 1) * per_page
    posts = posts.offset(start).limit(per_page).all()
    
    return posts, total


def get_recent_posts(limit=10):
    """Get recent posts across all categories"""
    posts = ForumPost.query.order_by(
        ForumPost.created_at.desc()
    ).limit(limit).all()
    
    return posts


def get_post_details(post_id):
    """Get post details including comments"""
    post = ForumPost.query.get(post_id)
    
    if not post:
        return None
    
    # Increment view count
    post.views += 1
    db.session.commit()
    
    # Get comments
    comments = ForumComment.query.filter_by(
        post_id=post_id,
        parent_id=None  # Only top-level comments
    ).order_by(ForumComment.created_at).all()
    
    return post, comments


def create_post(user_id, category_id, title, content):
    """Create a new forum post"""
    post = ForumPost(
        user_id=user_id,
        category_id=category_id,
        title=title,
        content=content
    )
    
    db.session.add(post)
    db.session.commit()
    
    return post


def create_comment(user_id, post_id, content, parent_id=None):
    """Create a new comment on a post"""
    comment = ForumComment(
        user_id=user_id,
        post_id=post_id,
        content=content,
        parent_id=parent_id
    )
    
    db.session.add(comment)
    db.session.commit()
    
    return comment


def get_user_post_history(user_id, limit=10):
    """Get a user's post history"""
    posts = ForumPost.query.filter_by(
        user_id=user_id
    ).order_by(ForumPost.created_at.desc()).limit(limit).all()
    
    return posts


def get_user_comment_history(user_id, limit=10):
    """Get a user's comment history"""
    comments = ForumComment.query.filter_by(
        user_id=user_id
    ).order_by(ForumComment.created_at.desc()).limit(limit).all()
    
    return comments


def search_forum(query_string, limit=20):
    """Search forum posts and comments"""
    # Search posts
    posts = ForumPost.query.filter(
        ForumPost.title.ilike(f"%{query_string}%") | 
        ForumPost.content.ilike(f"%{query_string}%")
    ).order_by(ForumPost.created_at.desc()).limit(limit).all()
    
    # Search comments
    comments = ForumComment.query.filter(
        ForumComment.content.ilike(f"%{query_string}%")
    ).order_by(ForumComment.created_at.desc()).limit(limit).all()
    
    return posts, comments
