"""
Database models for the Polymarket pipeline.

This module defines the database models used by the pipeline,
including markets, events, approval events, and pipeline runs.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, Integer, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from flask_sqlalchemy import SQLAlchemy

# Create SQLAlchemy base class
db = SQLAlchemy()

# Define models

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
    raw_data = db.Column(db.JSON)  # Complete original data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
class Market(db.Model):
    """
    Market model for storing market data.
    """
    __tablename__ = 'markets'
    
    id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='binary')
    category = db.Column(db.String(100), default='news')  # Store category here
    options = db.Column(db.JSON)  # Array of options for this market
    option_images = db.Column(db.JSON)  # Mapping of option name -> image URL
    expiry = db.Column(db.BigInteger)
    original_market_id = db.Column(db.String(255))
    status = db.Column(db.String(50), default='new')
    banner_url = db.Column(db.Text)  # URL of the banner image from API
    icon_url = db.Column(db.Text)  # URL of the icon from API
    apechain_market_id = db.Column(db.String(255))  # ID on ApeChain after deployment
    github_commit = db.Column(db.String(255))
    blockchain_tx = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class ApprovalEvent(db.Model):
    """
    Approval event model for tracking approvals/rejections.
    """
    __tablename__ = 'approval_events'
    
    id = db.Column(db.Integer, primary_key=True)
    market_id = db.Column(db.String(255), db.ForeignKey('markets.id'))
    stage = db.Column(db.String(50))  # initial or final
    status = db.Column(db.String(50))  # approved, rejected, timeout
    message_id = db.Column(db.String(255))
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    market = relationship('Market', backref='approval_events')

class PipelineRun(db.Model):
    """
    Pipeline run model for tracking pipeline executions.
    """
    __tablename__ = 'pipeline_runs'
    
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, default=datetime.now)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(50), default='running')
    markets_processed = db.Column(db.Integer, default=0)
    markets_approved = db.Column(db.Integer, default=0)
    markets_rejected = db.Column(db.Integer, default=0)
    markets_failed = db.Column(db.Integer, default=0)
    markets_deployed = db.Column(db.Integer, default=0)
    error = db.Column(db.Text)

class PendingMarket(db.Model):
    """
    Model for storing markets awaiting approval in Slack.
    Markets in this table have been categorized by AI but not yet approved.
    Once approved, they will be moved to the Market table.
    """
    __tablename__ = 'pending_markets'
    
    poly_id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='news')
    banner_url = db.Column(db.Text)  # URL from API, not generated
    icon_url = db.Column(db.Text)  # URL from API, not generated
    options = db.Column(db.JSON)  # Array of options for this market
    option_images = db.Column(db.JSON)  # Mapping of option name -> image URL
    expiry = db.Column(db.BigInteger)
    slack_message_id = db.Column(db.String(255))
    raw_data = db.Column(db.JSON)  # Complete original data
    needs_manual_categorization = db.Column(db.Boolean, default=False)
    posted = db.Column(db.Boolean, default=False)  # Track if posted to Slack
    fetched_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class ProcessedMarket(db.Model):
    """
    Model for tracking processed markets from Polymarket API.
    This prevents re-processing the same markets multiple times.
    """
    __tablename__ = 'processed_markets'
    
    # Polymarket condition_id is the unique identifier for markets
    condition_id = db.Column(db.String(255), primary_key=True)
    question = db.Column(db.Text)
    category = db.Column(db.String(50), default='news')  # Store category here
    first_seen = db.Column(db.DateTime, default=datetime.now)
    last_processed = db.Column(db.DateTime, default=datetime.now)
    process_count = db.Column(db.Integer, default=1)  # Number of times this market has been processed
    # Store if this market was posted to any channel
    posted = db.Column(db.Boolean, default=False)
    message_id = db.Column(db.String(255))  # Slack/Discord message ID if posted
    # Status tracking
    approved = db.Column(db.Boolean)  # True=approved, False=rejected, None=pending
    approval_date = db.Column(db.DateTime)  # When approval/rejection happened
    approver = db.Column(db.String(255))  # User ID of approver/rejecter
    # Original raw data
    raw_data = db.Column(db.JSON)  # Store the original API response JSON

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
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # Relationship
    pending_market = relationship('PendingMarket', backref='approval_logs')