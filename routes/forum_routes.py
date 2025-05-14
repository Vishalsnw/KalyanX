from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user
from app import db
from models import ForumCategory, ForumPost, ForumComment, User
from services.forum_service import (
    initialize_forum_categories, get_categories, get_posts_by_category,
    get_post_details, create_post, create_comment, get_recent_posts, search_forum
)
from config import Config

forum_bp = Blueprint('forum', __name__)


@forum_bp.route('/forum')
@login_required
def index():
    """Forum index page"""
    # Check if user has access
    if not current_user.has_access and not current_user.is_admin:
        flash('Forum access is available only for premium members', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # Initialize forum categories if needed
    initialize_forum_categories()
    
    # Get categories with post counts
    categories = get_categories()
    
    # Get recent posts
    recent_posts = get_recent_posts(limit=5)
    
    return render_template(
        'forum.html',
        categories=categories,
        recent_posts=recent_posts
    )


@forum_bp.route('/forum/category/<int:category_id>')
@login_required
def category(category_id):
    """Category page showing all posts"""
    # Check if user has access
    if not current_user.has_access and not current_user.is_admin:
        flash('Forum access is available only for premium members', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # Get category
    category = ForumCategory.query.get_or_404(category_id)
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get posts for this category
    posts, total = get_posts_by_category(category_id, page, per_page)
    
    # Calculate pagination
    total_pages = (total + per_page - 1) // per_page
    
    return render_template(
        'forum_category.html',
        category=category,
        posts=posts,
        page=page,
        total_pages=total_pages
    )


@forum_bp.route('/forum/post/<int:post_id>')
@login_required
def post(post_id):
    """Post detail page with comments"""
    # Check if user has access
    if not current_user.has_access and not current_user.is_admin:
        flash('Forum access is available only for premium members', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # Get post and comments
    post_data = get_post_details(post_id)
    
    if not post_data:
        abort(404)
    
    post, comments = post_data
    
    return render_template(
        'forum_post.html',
        post=post,
        comments=comments
    )


@forum_bp.route('/forum/create-post', methods=['GET', 'POST'])
@login_required
def create_post_route():
    """Create a new post"""
    # Check if user has access
    if not current_user.has_access and not current_user.is_admin:
        flash('Forum access is available only for premium members', 'warning')
        return redirect(url_for('subscription.plans'))
    
    # Get categories
    categories = ForumCategory.query.all()
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id', type=int)
        
        # Validate input
        if not title or not content or not category_id:
            flash('Please fill out all fields', 'danger')
            return render_template('forum_create_post.html', categories=categories)
        
        # Create post
        post = create_post(current_user.id, category_id, title, content)
        
        flash('Post created successfully', 'success')
        return redirect(url_for('forum.post', post_id=post.id))
    
    return render_template('forum_create_post.html', categories=categories)


@forum_bp.route('/forum/post/<int:post_id>/comment', methods=['POST'])
@login_required
def create_comment_route(post_id):
    """Create a comment on a post"""
    # Check if user has access
    if not current_user.has_access and not current_user.is_admin:
        flash('Forum access is available only for premium members', 'warning')
        return redirect(url_for('subscription.plans'))
    
    content = request.form.get('content')
    parent_id = request.form.get('parent_id', type=int)
    
    if not content:
        flash('Comment cannot be empty', 'danger')
        return redirect(url_for('forum.post', post_id=post_id))
    
    # Create comment
    comment = create_comment(current_user.id, post_id, content, parent_id)
    
    flash('Comment added successfully', 'success')
    return redirect(url_for('forum.post', post_id=post_id))


@forum_bp.route('/forum/search')
@login_required
def search():
    """Search forum posts and comments"""
    # Check if user has access
    if not current_user.has_access and not current_user.is_admin:
        flash('Forum access is available only for premium members', 'warning')
        return redirect(url_for('subscription.plans'))
    
    query = request.args.get('q', '')
    
    if not query:
        return render_template('forum_search.html', query='', posts=[], comments=[])
    
    # Search posts and comments
    posts, comments = search_forum(query)
    
    return render_template(
        'forum_search.html',
        query=query,
        posts=posts,
        comments=comments
    )
