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
    Also resets the sequence IDs to start from 1 again.
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
            
            # Use SQLAlchemy to get the raw connection for SQL statements
            connection = db.engine.raw_connection()
            cursor = connection.cursor()
            
            # Delete data from each table and reset sequence
            for table_class, description in table_classes:
                try:
                    # Get table name from the model
                    table_name = table_class.__tablename__
                    
                    # Count records before deletion
                    count_before = db.session.query(table_class).count()
                    logger.info(f"Found {count_before} {description} before cleaning")
                    
                    # Delete all records
                    db.session.query(table_class).delete()
                    
                    # Reset the sequence for the primary key
                    sequence_name = f"{table_name}_id_seq"
                    try:
                        # Check if the sequence exists
                        cursor.execute(f"SELECT EXISTS(SELECT FROM pg_sequences WHERE sequencename = '{sequence_name}')")
                        sequence_exists = cursor.fetchone()[0]
                        
                        if sequence_exists:
                            cursor.execute(f"ALTER SEQUENCE {sequence_name} RESTART WITH 1")
                            logger.info(f"Reset sequence for {table_name} to start from 1")
                        else:
                            logger.info(f"No sequence found for {table_name}")
                    except Exception as seq_error:
                        logger.warning(f"Could not reset sequence for {table_name}: {seq_error}")
                    
                    # Verify deletion
                    count_after = db.session.query(table_class).count()
                    logger.info(f"Found {count_after} {description} after cleaning")
                except Exception as e:
                    logger.error(f"Error clearing {description}: {e}")
                    db.session.rollback()
                    connection.close()
                    return False
            
            # Commit the transaction after all deletions
            db.session.commit()
            connection.commit()
            connection.close()
            
            logger.info("Successfully reset all database tables and sequences")
            
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