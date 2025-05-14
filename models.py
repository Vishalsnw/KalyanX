import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.ext.hybrid import hybrid_property


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(15), unique=True, nullable=True)  # Made nullable for email-only users
    email = db.Column(db.String(100), unique=True, nullable=True)  # Email field
    pin_hash = db.Column(db.String(256))
    name = db.Column(db.String(100), nullable=True)  # User's name
    profile_image = db.Column(db.String(250), nullable=True)  # URL to profile image
    registration_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    trial_end_date = db.Column(db.DateTime)
    is_premium = db.Column(db.Boolean, default=False)
    premium_end_date = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)
    referral_code = db.Column(db.String(10), unique=True)
    referred_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    last_login = db.Column(db.DateTime)
    notification_preferences = db.Column(db.JSON, default={})
    push_subscription = db.Column(db.JSON, nullable=True)
    firebase_uid = db.Column(db.String(40), unique=True, nullable=True)  # Firebase UID
    
    # Relationships
    subscriptions = db.relationship('Subscription', backref='user', lazy='dynamic')
    predictions = db.relationship('PredictionView', backref='user', lazy='dynamic')
    forum_posts = db.relationship('ForumPost', backref='user', lazy='dynamic')
    forum_comments = db.relationship('ForumComment', backref='user', lazy='dynamic')
    notifications = db.relationship('Notification', backref='user', lazy='dynamic')
    
    def set_pin(self, pin):
        self.pin_hash = generate_password_hash(pin)
    
    def check_pin(self, pin):
        return check_password_hash(self.pin_hash, pin)
    
    @hybrid_property
    def is_trial_active(self):
        if not self.trial_end_date:
            return False
        return self.trial_end_date > datetime.datetime.utcnow()
    
    @hybrid_property
    def has_access(self):
        return self.is_premium or self.is_trial_active
    
    @hybrid_property
    def days_remaining(self):
        if self.is_premium and self.premium_end_date:
            delta = self.premium_end_date - datetime.datetime.utcnow()
            return max(0, delta.days)
        elif self.is_trial_active:
            delta = self.trial_end_date - datetime.datetime.utcnow()
            return max(0, delta.days)
        return 0


class Subscription(db.Model):
    __tablename__ = 'subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_id = db.Column(db.String(100), unique=True)
    order_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='pending')  # pending, success, failed
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    

class Result(db.Model):
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    market = db.Column(db.String(50), nullable=False)
    open = db.Column(db.String(10), nullable=True)
    jodi = db.Column(db.String(10), nullable=True)
    close = db.Column(db.String(10), nullable=True)
    day_of_week = db.Column(db.String(10), nullable=True)
    is_weekend = db.Column(db.Boolean, default=False)
    open_sum = db.Column(db.Float, nullable=True)
    close_sum = db.Column(db.Float, nullable=True)
    mirror_open = db.Column(db.String(10), nullable=True)
    mirror_close = db.Column(db.String(10), nullable=True)
    reverse_jodi = db.Column(db.String(10), nullable=True)
    is_holiday = db.Column(db.Boolean, default=False)
    prev_jodi_distance = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('date', 'market', name='unique_date_market'),
    )


class Prediction(db.Model):
    __tablename__ = 'predictions'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    market = db.Column(db.String(50), nullable=False)
    open_digits = db.Column(db.JSON, nullable=True)  # List of 2 single digits
    close_digits = db.Column(db.JSON, nullable=True)  # List of 2 single digits
    jodi_list = db.Column(db.JSON, nullable=True)     # List of 10 jodis
    patti_list = db.Column(db.JSON, nullable=True)    # List of 4 pattis
    confidence_score = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('date', 'market', name='unique_date_market_prediction'),
    )
    
    # Add a relationship to the result for the same date and market
    result = db.relationship(
        'Result',
        primaryjoin="and_(Prediction.date==Result.date, Prediction.market==Result.market)",
        foreign_keys="[Prediction.date, Prediction.market]",
        viewonly=True,
        uselist=False
    )


class PredictionView(db.Model):
    __tablename__ = 'prediction_views'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    prediction_id = db.Column(db.Integer, db.ForeignKey('predictions.id'), nullable=False)
    viewed_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    prediction = db.relationship('Prediction', backref='views')


class ForumCategory(db.Model):
    __tablename__ = 'forum_categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    posts = db.relationship('ForumPost', backref='category', lazy='dynamic')


class ForumPost(db.Model):
    __tablename__ = 'forum_posts'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('forum_categories.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    comments = db.relationship('ForumComment', backref='post', lazy='dynamic')
    views = db.Column(db.Integer, default=0)
    
    @hybrid_property
    def comment_count(self):
        return self.comments.count()


class ForumComment(db.Model):
    __tablename__ = 'forum_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('forum_posts.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('forum_comments.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Self-referential relationship for nested comments
    replies = db.relationship('ForumComment', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')


class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # prediction, subscription, referral, system
    reference_id = db.Column(db.Integer, nullable=True)  # ID of the related entity
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_user_read', user_id, is_read),
    )


class OTP(db.Model):
    __tablename__ = 'otps'
    
    id = db.Column(db.Integer, primary_key=True)
    mobile = db.Column(db.String(15), nullable=True)  # Made nullable
    email = db.Column(db.String(100), nullable=True)  # Added email field
    otp = db.Column(db.String(6), nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    __table_args__ = (
        db.Index('idx_mobile_otp', mobile, otp),
        db.Index('idx_email_otp', email, otp),
    )


class MLModel(db.Model):
    __tablename__ = 'ml_models'
    
    id = db.Column(db.Integer, primary_key=True)
    market = db.Column(db.String(50), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # open, close, jodi
    model_path = db.Column(db.String(255), nullable=False)
    accuracy = db.Column(db.Float, nullable=True)
    training_date = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    __table_args__ = (
        db.UniqueConstraint('market', 'model_type', name='unique_market_model'),
    )
