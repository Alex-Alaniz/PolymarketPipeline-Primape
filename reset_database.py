#!/usr/bin/env python3

"""
Reset Database

This script performs a thorough reset of the database for testing purposes.
It deletes data from all relevant tables while preserving the database structure.
"""

import os
import sys
import logging
from datetime import datetime

from models import db, PendingMarket, Market, ApprovalEvent, ProcessedMarket, PipelineRun
from main import app

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("db_reset")

def reset_database_tables():
    """
    Reset all relevant database tables.
    
    This deletes all data from the tables but preserves the structure.
    """
    try:
        with app.app_context():
            # List of tables to clean
            table_classes = [
                (PendingMarket, "pending markets"),
                (Market, "deployed markets"),
                (ApprovalEvent, "approval events"),
                (ProcessedMarket, "processed markets"),
                (PipelineRun, "pipeline runs")
            ]
            
            # Delete data from each table
            for table_class, description in table_classes:
                try:
                    # Count records before deletion
                    count_before = db.session.query(table_class).count()
                    logger.info(f"Found {count_before} {description} before cleaning")
                    
                    # Delete all records
                    db.session.query(table_class).delete()
                    
                    # Verify deletion
                    count_after = db.session.query(table_class).count()
                    logger.info(f"Found {count_after} {description} after cleaning")
                except Exception as e:
                    logger.error(f"Error clearing {description}: {e}")
                    db.session.rollback()
                    return False
            
            # Commit the transaction after all deletions
            db.session.commit()
            logger.info("Successfully reset all database tables")
            
            return True
            
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        db.session.rollback()
        return False

def main():
    """
    Main function to run the database reset.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting complete database reset")
    
    # Confirm with the user
    print("WARNING: This will delete ALL data from your database tables.")
    print("Are you sure you want to continue? (yes/no)")
    
    # Check if --force flag was provided
    if "--force" in sys.argv:
        confirmation = "yes"
    else:
        confirmation = input().strip().lower()
    
    if confirmation != "yes":
        logger.info("Database reset cancelled by user")
        return 0
    
    # Reset the database
    success = reset_database_tables()
    
    if success:
        logger.info("Successfully reset database")
        return 0
    else:
        logger.error("Failed to reset database")
        return 1

if __name__ == "__main__":
    sys.exit(main())