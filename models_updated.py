"""
Database models for the Polymarket pipeline.
"""
import os
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

# Initialize database
db = SQLAlchemy()

# Maximum age for pending markets (in days)
PENDING_MARKET_MAX_AGE_DAYS = 7

class Event(db.Model):
    """
    Event model for storing market events.
    
    An event represents a category or grouping of markets, such as "UEFA Champions League" 
    which might have multiple markets like "Will Arsenal win?", "Will Barcelona win?", etc.
    """
    __tablename__ = 'events'
    
    id = db.Column(db.String(255), primary_key=True)
    name = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False, default='news')
    sub_category = db.Column(db.String(100))
    banner_url = db.Column(db.Text)  # URL of the event banner image
    icon_url = db.Column(db.Text)  # URL of the event icon image
    source_id = db.Column(db.String(255))  # Original ID from the source (e.g., Polymarket)
    raw_data = db.Column(JSON)  # Complete original data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'sub_category': self.sub_category,
            'banner_url': self.banner_url,
            'icon_url': self.icon_url,
            'source_id': self.source_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Market(db.Model):
    """
    Market model for storing market data.
    
    A market belongs to an event and represents a specific question or betting opportunity
    within that event.
    """
    __tablename__ = 'markets'
    
    id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='binary')
    event_id = db.Column(db.String(255), db.ForeignKey('events.id'))  # FK to the event
    original_market_id = db.Column(db.String(255))  # ID from the source (e.g., Polymarket)
    options = db.Column(JSON)  # Array of options for this market
    option_images = db.Column(JSON)  # JSON mapping of option name -> image URL
    expiry = db.Column(db.BigInteger)  # Expiry timestamp
    status = db.Column(db.String(50), default='new')  # Status of this market
    banner_path = db.Column(db.Text)  # Path to the banner image file
    banner_uri = db.Column(db.Text)  # URI of the banner image for frontend
    icon_url = db.Column(db.Text)  # URL of the icon for this market
    apechain_market_id = db.Column(db.String(255))  # ID on ApeChain after deployment
    github_commit = db.Column(db.String(255))  # GitHub commit hash for image assets
    blockchain_tx = db.Column(db.String(255))  # Blockchain transaction hash
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    event = db.relationship('Event', backref=db.backref('markets', lazy='dynamic'))
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'question': self.question,
            'type': self.type,
            'event_id': self.event_id,
            'original_market_id': self.original_market_id,
            'options': self.options,
            'option_images': self.option_images,
            'expiry': self.expiry,
            'status': self.status,
            'banner_path': self.banner_path,
            'banner_uri': self.banner_uri,
            'icon_url': self.icon_url,
            'apechain_market_id': self.apechain_market_id,
            'github_commit': self.github_commit,
            'blockchain_tx': self.blockchain_tx,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ApprovalEvent(db.Model):
    """Approval event model for tracking approvals/rejections."""
    __tablename__ = 'approval_events'
    
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.String(255), db.ForeignKey('markets.id'))
    stage = db.Column(db.String(50))  # initial or final
    status = db.Column(db.String(50))  # approved, rejected, timeout
    message_id = db.Column(db.String(255))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    market = db.relationship('Market', backref=db.backref('approval_events', lazy='dynamic'))
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'market_id': self.market_id,
            'stage': self.stage,
            'status': self.status,
            'message_id': self.message_id,
            'reason': self.reason,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class PipelineRun(db.Model):
    """Pipeline run model for tracking pipeline executions."""
    __tablename__ = 'pipeline_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='running')
    markets_processed = db.Column(db.Integer, default=0)
    markets_approved = db.Column(db.Integer, default=0)
    markets_rejected = db.Column(db.Integer, default=0)
    markets_failed = db.Column(db.Integer, default=0)
    markets_deployed = db.Column(db.Integer, default=0)
    error = db.Column(db.Text)
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'status': self.status,
            'markets_processed': self.markets_processed,
            'markets_approved': self.markets_approved,
            'markets_rejected': self.markets_rejected,
            'markets_failed': self.markets_failed,
            'markets_deployed': self.markets_deployed,
            'error': self.error
        }

class PendingMarket(db.Model):
    """
    Model for storing markets awaiting approval in Slack.
    Markets in this table have been categorized by AI but not yet approved.
    Once approved, they will be moved to the Event and Market tables.
    """
    __tablename__ = 'pending_markets'
    
    poly_id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text, nullable=False)
    event_name = db.Column(db.Text)  # Name of the event this market belongs to
    event_id = db.Column(db.String(255))  # ID of the event (if known)
    category = db.Column(db.String(50), nullable=False, default='news')
    banner_url = db.Column(db.Text)  # Banner URL for the event
    icon_url = db.Column(db.Text)  # Icon URL for the market
    options = db.Column(JSON)  # Array of options for this market
    option_images = db.Column(JSON)  # Mapping of option IDs to image URLs
    expiry = db.Column(db.BigInteger)
    slack_message_id = db.Column(db.String(255))
    raw_data = db.Column(JSON)  # Complete original data
    needs_manual_categorization = db.Column(db.Boolean, default=False)
    posted = db.Column(db.Boolean, default=False)  # Track if posted to Slack
    fetched_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_expired(self):
        """Check if this pending market has been waiting for approval too long."""
        if not self.fetched_at:
            return False
        
        cutoff = datetime.utcnow() - timedelta(days=PENDING_MARKET_MAX_AGE_DAYS)
        return self.fetched_at < cutoff
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'poly_id': self.poly_id,
            'question': self.question,
            'event_name': self.event_name,
            'event_id': self.event_id,
            'category': self.category,
            'banner_url': self.banner_url,
            'icon_url': self.icon_url,
            'options': self.options,
            'option_images': self.option_images,
            'expiry': self.expiry,
            'slack_message_id': self.slack_message_id,
            'needs_manual_categorization': self.needs_manual_categorization,
            'posted': self.posted,
            'fetched_at': self.fetched_at.isoformat() if self.fetched_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ProcessedMarket(db.Model):
    """
    Model for tracking processed markets from Polymarket API.
    This prevents re-processing the same markets multiple times.
    """
    __tablename__ = 'processed_markets'
    
    # Polymarket condition_id is the unique identifier for markets
    condition_id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text)
    event_name = db.Column(db.Text)  # Name of the event this market belongs to
    event_id = db.Column(db.String(255))  # ID of the event (if known)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_processed = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    process_count = db.Column(db.Integer, default=1)  # Number of times this market has been processed
    # Store if this market was posted to any channel
    posted = db.Column(db.Boolean, default=False)
    message_id = db.Column(db.String(255))  # Slack/Discord message ID if posted
    
    # Status tracking
    approved = db.Column(db.Boolean)  # True=approved, False=rejected, None=pending
    approval_date = db.Column(db.DateTime)  # When approval/rejection happened
    approver = db.Column(db.String(255))  # User ID of approver/rejecter
    
    # Original raw data
    raw_data = db.Column(JSON)  # Store the original API response JSON
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'condition_id': self.condition_id,
            'question': self.question,
            'event_name': self.event_name,
            'event_id': self.event_id,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_processed': self.last_processed.isoformat() if self.last_processed else None,
            'process_count': self.process_count,
            'posted': self.posted,
            'message_id': self.message_id,
            'approved': self.approved,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'approver': self.approver
        }

class ApprovalLog(db.Model):
    """
    Model for logging approval decisions on pending markets.
    """
    __tablename__ = 'approval_log'
    
    id = db.Column(db.Integer, primary_key=True)
    poly_id = db.Column(db.String(255), db.ForeignKey('pending_markets.poly_id'))
    slack_msg_id = db.Column(db.String(255))
    reviewer = db.Column(db.String(255))
    decision = db.Column(db.String(50))  # 'approved' or 'rejected'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    pending_market = db.relationship('PendingMarket', backref=db.backref('approval_logs', lazy='dynamic'))
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'poly_id': self.poly_id,
            'slack_msg_id': self.slack_msg_id,
            'reviewer': self.reviewer,
            'decision': self.decision,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }