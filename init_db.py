#!/usr/bin/env python3

"""
Initialize database tables for the Polymarket pipeline.

This script creates all necessary database tables for tracking processed markets.
Run this script once to set up the database before using market_tracker.
"""

import os
import sys
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("init_db")

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask
from models import db, Market, ApprovalEvent, PipelineRun, ProcessedMarket

def init_database():
    """
    Initialize the database and create all tables.
    """
    try:
        # Create Flask app
        app = Flask(__name__)
        
        # Configure database
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 300,
            "pool_pre_ping": True,
        }
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        
        # Initialize database with app
        db.init_app(app)
        
        # Create all tables
        with app.app_context():
            logger.info("Creating database tables...")
            db.create_all()
            logger.info("All database tables created successfully")
            
            # Display tables created
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            logger.info(f"Tables in database: {', '.join(tables)}")
            
            # Log columns for ProcessedMarket table
            columns = inspector.get_columns('processed_markets')
            logger.info(f"Columns in processed_markets table:")
            for column in columns:
                logger.info(f"  - {column['name']} ({column['type']})")
        
        return True
    
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False

def main():
    """
    Main function to run the database initialization.
    """
    logger.info("Starting database initialization")
    
    if not os.environ.get("DATABASE_URL"):
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    success = init_database()
    
    if success:
        logger.info("Database initialization completed successfully")
    else:
        logger.error("Database initialization failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
