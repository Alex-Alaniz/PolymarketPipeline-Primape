#!/usr/bin/env python3
"""
Reset the database with a simplified schema that focuses on:
1. Storing categories for markets
2. Tracking images from APIs (not generating with OpenAI)
3. Mapping ApeChain marketIDs for frontend integration

This maintains the working approach from the first pipeline run.
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask
from sqlalchemy import Column, String, Text, Boolean, Integer, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine

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
Base = declarative_base()

# Define simplified models
class Market(Base):
    """Market model for storing market data."""
    __tablename__ = 'markets'
    
    id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    type = Column(String(50), default='binary')
    category = Column(String(100), default='news')  # Store category here
    options = Column(JSON)  # Array of options for this market
    option_images = Column(JSON)  # Mapping of option name -> image URL
    expiry = Column(BigInteger)
    original_market_id = Column(String(255))
    status = Column(String(50), default='new')
    banner_url = Column(Text)  # URL of the banner image from API
    icon_url = Column(Text)  # URL of the icon from API
    apechain_market_id = Column(String(255))  # ID on ApeChain after deployment
    github_commit = Column(String(255))
    blockchain_tx = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

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
    Once approved, they will be moved to the Market table.
    """
    __tablename__ = 'pending_markets'
    
    poly_id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default='news')
    banner_url = Column(Text)  # URL from API, not generated
    icon_url = Column(Text)  # URL from API, not generated
    options = Column(JSON)  # Array of options for this market
    option_images = Column(JSON)  # Mapping of option name -> image URL
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
    category = Column(String(50), default='news')  # Store category here
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
        
        # Get list of all tables in the database
        with engine.connect() as conn:
            result = conn.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Found {len(tables)} tables in database: {', '.join(tables)}")
            
            # Drop tables related to image generation
            image_tables = [t for t in tables if 'image' in t.lower() and t not in ['markets', 'pending_markets', 'processed_markets']]
            for table in image_tables:
                logger.info(f"Dropping image-related table: {table}")
                conn.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
        
        logger.info("Dropping all existing tables...")
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