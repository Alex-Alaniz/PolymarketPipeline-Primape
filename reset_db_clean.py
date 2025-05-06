#!/usr/bin/env python3
"""
Reset Database for Clean Deployment

This script drops all tables and recreates a clean schema without image generation
tables, preserving only the essential structure needed for the core pipeline.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('db_reset')

# Flask setup for database context
from flask import Flask
from sqlalchemy import create_engine, MetaData, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, BigInteger
from sqlalchemy.dialects.postgresql import JSON

# Initialize app with database connection
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Create database engine and session
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
Session = sessionmaker(bind=engine)
session = Session()
metadata = MetaData()
Base = declarative_base()

# Define the essential models we want to keep
class Market(Base):
    """Market model for storing market data."""
    __tablename__ = 'markets'

    id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    type = Column(String(50), default='binary')
    category = Column(String(100))
    sub_category = Column(String(100))
    expiry = Column(BigInteger)
    original_market_id = Column(String(255))
    options = Column(JSON)
    status = Column(String(50), default='new')
    banner_path = Column(Text)
    banner_uri = Column(Text)
    icon_url = Column(String(255))
    option_images = Column(JSON)  # JSON mapping of option name -> image URL
    apechain_market_id = Column(String(255))
    github_commit = Column(String(255))
    blockchain_tx = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ApprovalEvent(Base):
    """Approval event model for tracking approvals/rejections."""
    __tablename__ = 'approval_events'

    id = Column(Integer, primary_key=True)
    market_id = Column(String(255), nullable=False)
    stage = Column(String(50))
    status = Column(String(50))
    message_id = Column(String(255))
    reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    """Model for storing markets awaiting approval in Slack."""
    __tablename__ = 'pending_markets'
    
    poly_id = Column(String(255), primary_key=True)
    question = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default='news')
    banner_url = Column(Text)
    icon_url = Column(Text)
    options = Column(JSON)
    option_images = Column(JSON)
    expiry = Column(BigInteger)
    slack_message_id = Column(String(255))
    raw_data = Column(JSON)
    needs_manual_categorization = Column(Boolean, default=False)
    posted = Column(Boolean, default=False)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ApprovalLog(Base):
    """Model for logging approval events for pending markets."""
    __tablename__ = 'approvals_log'
    
    id = Column(Integer, primary_key=True)
    poly_id = Column(String(255), nullable=False)
    slack_msg_id = Column(String(255))
    reviewer = Column(String(255))
    decision = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

class ProcessedMarket(Base):
    """Model for tracking processed markets from Polymarket API."""
    __tablename__ = 'processed_markets'
    
    condition_id = Column(String(255), primary_key=True)
    question = Column(Text)
    category = Column(String(50), default='news')
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_processed = Column(DateTime, default=datetime.utcnow)
    process_count = Column(Integer, default=1)
    posted = Column(Boolean, default=False)
    message_id = Column(String(255))
    approved = Column(Boolean, nullable=True)
    approval_date = Column(DateTime)
    approver = Column(String(255))
    raw_data = Column(JSON)

def list_tables():
    """List all tables in the database."""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    logger.info(f"Found {len(tables)} tables in database:")
    for table in tables:
        logger.info(f"  - {table}")
    return tables

def drop_all_tables():
    """Drop all tables in the database."""
    # First, try to use raw SQL to drop all tables with CASCADE
    try:
        connection = engine.connect()
        # Disable foreign key constraints temporarily
        connection.execute("SET session_replication_role = 'replica';")
        
        # Get all table names from the database
        tables = list_tables()
        
        # Drop tables in reverse order to handle dependencies
        for table_name in reversed(tables):
            logger.info(f"Dropping table: {table_name}")
            try:
                connection.execute(f'DROP TABLE IF EXISTS "{table_name}" CASCADE;')
            except Exception as e:
                logger.error(f"Error dropping table {table_name}: {str(e)}")
        
        # Re-enable foreign key constraints
        connection.execute("SET session_replication_role = 'origin';")
        connection.close()
        logger.info("All tables dropped successfully")
        return
    except Exception as e:
        logger.warning(f"Failed to drop tables with raw SQL: {str(e)}")
        logger.info("Falling back to SQLAlchemy method...")
    
    # Fallback: SQLAlchemy method
    tables = list_tables()
    metadata.reflect(bind=engine)
    
    # Try to drop tables in reverse order to handle dependencies
    for table_name in reversed(tables):
        if table_name in metadata.tables:
            table = metadata.tables[table_name]
            logger.info(f"Dropping table: {table_name}")
            
            # Try with cascade first, fallback to non-cascade if it fails
            try:
                table.drop(engine, checkfirst=True)
            except Exception as e:
                logger.warning(f"Error dropping table {table_name} with CASCADE: {str(e)}")
                try:
                    # Try without cascade as a fallback
                    table.drop(engine, checkfirst=True)
                except Exception as e2:
                    logger.error(f"Failed to drop table {table_name}: {str(e2)}")
    
    logger.info("All tables dropped successfully")

def create_clean_tables():
    """Create clean tables based on our defined models."""
    logger.info("Creating clean tables...")
    Base.metadata.create_all(engine)
    logger.info("Clean tables created successfully")

def main():
    """Main function to reset the database."""
    try:
        # Step 1: Drop all existing tables
        logger.info("Starting database reset...")
        drop_all_tables()
        
        # Step 2: Create fresh tables
        create_clean_tables()
        
        # Step 3: Verify tables were created
        tables = list_tables()
        
        # Check if our essential tables exist
        expected_tables = {
            'markets', 
            'approval_events', 
            'pipeline_runs', 
            'pending_markets', 
            'approvals_log', 
            'processed_markets'
        }
        
        missing_tables = expected_tables - set(tables)
        if missing_tables:
            logger.error(f"Missing essential tables: {missing_tables}")
            return 1
        
        logger.info("Database reset completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())