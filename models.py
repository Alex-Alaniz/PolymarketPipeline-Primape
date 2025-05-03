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