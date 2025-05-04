"""
Database models for the Polymarket pipeline.
"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON

# Initialize database
db = SQLAlchemy()

class Market(db.Model):
    """Market model for storing market data."""
    __tablename__ = 'markets'

    id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='binary')
    category = db.Column(db.String(100))
    sub_category = db.Column(db.String(100))
    expiry = db.Column(db.BigInteger)
    original_market_id = db.Column(db.String(255))
    options = db.Column(JSON)
    status = db.Column(db.String(50), default='new')
    banner_path = db.Column(db.String(255))
    banner_uri = db.Column(db.String(255))
    github_commit = db.Column(db.String(255))
    blockchain_tx = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'question': self.question,
            'type': self.type,
            'category': self.category,
            'sub_category': self.sub_category,
            'expiry': self.expiry,
            'original_market_id': self.original_market_id,
            'options': self.options,
            'status': self.status,
            'banner_path': self.banner_path,
            'banner_uri': self.banner_uri,
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

class ProcessedMarket(db.Model):
    """Model for tracking processed markets from Polymarket API.
    This prevents re-processing the same markets multiple times."""
    __tablename__ = 'processed_markets'
    
    # Polymarket condition_id is the unique identifier for markets
    condition_id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_processed = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    process_count = db.Column(db.Integer, default=1)  # Number of times this market has been processed
    # Store if this market was posted to any channel
    posted = db.Column(db.Boolean, default=False)
    message_id = db.Column(db.String(255))  # Slack/Discord message ID if posted
    
    # Status tracking
    approved = db.Column(db.Boolean, nullable=True)  # True=approved, False=rejected, None=pending
    approval_date = db.Column(db.DateTime)  # When approval/rejection happened
    approver = db.Column(db.String(255))  # User ID of approver/rejecter
    
    # Image generation tracking
    image_generated = db.Column(db.Boolean, default=False)  # Whether an image has been generated
    image_path = db.Column(db.String(255))  # Path to the generated image
    image_generation_attempts = db.Column(db.Integer, default=0)  # Number of image generation attempts
    image_approved = db.Column(db.Boolean, nullable=True)  # True=approved, False=rejected, None=pending
    image_approval_date = db.Column(db.DateTime)  # When image approval/rejection happened
    image_approver = db.Column(db.String(255))  # User ID of image approver/rejecter
    image_message_id = db.Column(db.String(255))  # Slack/Discord message ID for image approval
    image_uri = db.Column(db.String(255))  # Final URI for the image (e.g., IPFS, S3, etc.)
    
    # Original raw data
    raw_data = db.Column(JSON)  # Store the original API response JSON
    
    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'condition_id': self.condition_id,
            'question': self.question,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_processed': self.last_processed.isoformat() if self.last_processed else None,
            'process_count': self.process_count,
            'posted': self.posted,
            'message_id': self.message_id,
            'approved': self.approved,
            'approval_date': self.approval_date.isoformat() if self.approval_date else None,
            'approver': self.approver,
            'image_generated': self.image_generated,
            'image_path': self.image_path,
            'image_generation_attempts': self.image_generation_attempts,
            'image_approved': self.image_approved,
            'image_approval_date': self.image_approval_date.isoformat() if self.image_approval_date else None,
            'image_approver': self.image_approver,
            'image_message_id': self.image_message_id,
            'image_uri': self.image_uri
        }