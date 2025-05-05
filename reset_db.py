#!/usr/bin/env python3

"""
Reset the database for the Polymarket pipeline.

This script drops all tables in the database and reinitializes them,
allowing for a clean state for testing the pipeline.
"""

import os
import sys
import logging
from sqlalchemy import text
from models import db, Market, ProcessedMarket, ApprovalEvent, PipelineRun

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_reset")

def reset_database():
    """
    Reset the database by dropping all tables and recreating them.
    """
    # Import Flask app here to avoid circular imports
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        try:
            # Get all tables
            tables = [Market.__table__, ProcessedMarket.__table__, 
                      ApprovalEvent.__table__, PipelineRun.__table__]
            
            # Drop all tables
            logger.info("Dropping all tables...")
            for table in tables:
                logger.info(f"Dropping table {table.name}...")
                db.session.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))
            
            db.session.commit()
            logger.info("All tables dropped successfully")
            
            # Create all tables
            logger.info("Creating all tables...")
            db.create_all()
            logger.info("All tables created successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            return False

def main():
    """
    Main function to run the database reset.
    """
    logger.info("Starting database reset...")
    
    success = reset_database()
    
    if success:
        logger.info("Database reset completed successfully")
        return 0
    else:
        logger.error("Database reset failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())