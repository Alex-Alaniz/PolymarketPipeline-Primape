#!/usr/bin/env python3
"""
Reset and setup the database with the new event-based model.

This script will:
1. Drop all existing tables
2. Create the new schema with proper event-market relationships
3. Set up the initial database structure

WARNING: This will delete all existing data. Make sure you have backups if needed.
"""

import os
import sys
import logging
from datetime import datetime
from sqlalchemy import create_engine, MetaData, Table, Column, String, Text
from sqlalchemy import Boolean, Integer, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from flask import Flask

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('db_setup')

# Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Create engine and metadata
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
metadata = MetaData()
Base = declarative_base()

# Define models
class Event(Base):
    """
    Event model for storing market events.
    
    An event represents a category or grouping of markets, such as "UEFA Champions League" 
    which might have multiple markets like "Will Arsenal win?", "Will Barcelona win?", etc.
    """
    __tablename__ = 'events'
    
    id = Column(String(255), primary_key=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(String(50), nullable=False, default='news')
    sub_category = Column(String(100))
    banner_url = Column(Text)  # URL of the event banner image
    icon_url = Column(Text)  # URL of the event icon image
    source_id = Column(String(255))  # Original ID from the source (e.g., Polymarket)
    raw_data = Column(JSON)  # Complete original data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Market(Base):
    """
    Market model for storing market data.
    
    A market belongs to an event and represents a specific question or betting opportunity
    within that event.
    """
    __tablename__ = 'markets'
    
    id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    type = Column(String(50), default='binary')
    event_id = Column(String(255), ForeignKey('events.id'))  # FK to the event
    original_market_id = Column(String(255))  # ID from the source (e.g., Polymarket)
    options = Column(JSON)  # Array of options for this market
    option_images = Column(JSON)  # JSON mapping of option name -> image URL
    expiry = Column(BigInteger)  # Expiry timestamp
    status = Column(String(50), default='new')  # Status of this market
    banner_path = Column(Text)  # Path to the banner image file
    banner_uri = Column(Text)  # URI of the banner image for frontend
    icon_url = Column(Text)  # URL of the icon for this market
    apechain_market_id = Column(String(255))  # ID on ApeChain after deployment
    github_commit = Column(String(255))  # GitHub commit hash for image assets
    blockchain_tx = Column(String(255))  # Blockchain transaction hash
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship('Event', backref='markets')
    
class ApprovalEvent(Base):
    """Approval event model for tracking approvals/rejections."""
    __tablename__ = 'approval_events'
    
    id = Column(Integer, primary_key=True)
    market_id = Column(String(255), ForeignKey('markets.id'))
    stage = Column(String(50))  # initial or final
    status = Column(String(50))  # approved, rejected, timeout
    message_id = Column(String(255))
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    market = relationship('Market', backref='approval_events')

class PipelineRun(Base):
    """Pipeline run model for tracking pipeline executions."""
    __tablename__ = 'pipeline_runs'
    
    id = Column(Integer, primary_key=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    status = Column(String(50), default='running')
    markets_processed = Column(Integer, default=0)
    markets_approved = Column(Integer, default=0)
    markets_rejected = Column(Integer, default=0)
    markets_failed = Column(Integer, default=0)
    markets_deployed = Column(Integer, default=0)
    error = Column(Text)

class PendingMarket(Base):
    """
    Model for storing markets awaiting approval in Slack.
    Markets in this table have been categorized by AI but not yet approved.
    Once approved, they will be moved to the Event and Market tables.
    """
    __tablename__ = 'pending_markets'
    
    poly_id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    event_name = Column(Text)  # Name of the event this market belongs to
    event_id = Column(String(255))  # ID of the event (if known)
    category = Column(String(50), nullable=False, default='news')
    banner_url = Column(Text)  # Banner URL for the event
    icon_url = Column(Text)  # Icon URL for the market
    options = Column(JSON)  # Array of options for this market
    option_images = Column(JSON)  # Mapping of option IDs to image URLs
    expiry = Column(BigInteger)
    slack_message_id = Column(String(255))
    raw_data = Column(JSON)  # Complete original data
    needs_manual_categorization = Column(Boolean, default=False)
    posted = Column(Boolean, default=False)  # Track if posted to Slack
    fetched_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ProcessedMarket(Base):
    """
    Model for tracking processed markets from Polymarket API.
    This prevents re-processing the same markets multiple times.
    """
    __tablename__ = 'processed_markets'
    
    # Polymarket condition_id is the unique identifier for markets
    condition_id = Column(String(255), primary_key=True)
    question = Column(Text)
    event_name = Column(Text)  # Name of the event this market belongs to
    event_id = Column(String(255))  # ID of the event (if known)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_processed = Column(DateTime, default=datetime.utcnow)
    process_count = Column(Integer, default=1)  # Number of times this market has been processed
    # Store if this market was posted to any channel
    posted = Column(Boolean, default=False)
    message_id = Column(String(255))  # Slack/Discord message ID if posted
    # Status tracking
    approved = Column(Boolean)  # True=approved, False=rejected, None=pending
    approval_date = Column(DateTime)  # When approval/rejection happened
    approver = Column(String(255))  # User ID of approver/rejecter
    # Original raw data
    raw_data = Column(JSON)  # Store the original API response JSON

class ApprovalLog(Base):
    """
    Model for logging approval decisions on pending markets.
    """
    __tablename__ = 'approval_log'
    
    id = Column(Integer, primary_key=True)
    poly_id = Column(String(255), ForeignKey('pending_markets.poly_id'))
    slack_msg_id = Column(String(255))
    reviewer = Column(String(255))
    decision = Column(String(50))  # 'approved' or 'rejected'
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    pending_market = relationship('PendingMarket', backref='approval_logs')

def reset_database():
    """
    Drop all tables from the database and recreate them.
    """
    try:
        # Confirm before proceeding
        if not os.environ.get('SKIP_CONFIRMATION'):
            print("WARNING: This script will delete ALL data in the database.")
            print("Are you sure you want to continue? This cannot be undone.")
            response = input("Type 'YES' to confirm: ")
            if response != 'YES':
                print("Database reset cancelled.")
                return 1
        
        logger.info("Dropping all tables...")
        Base.metadata.drop_all(engine)
        logger.info("Creating new tables...")
        Base.metadata.create_all(engine)
        
        logger.info("Database reset and setup complete!")
        return 0
    
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(reset_database())