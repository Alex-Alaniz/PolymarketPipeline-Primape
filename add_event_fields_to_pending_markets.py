#!/usr/bin/env python3
"""
Add event fields to pending_markets table.

This script adds the 'event_id' and 'event_name' columns to the PendingMarket table
to support proper event tracking and grouping of related markets.
"""

import logging
import sys
from flask import Flask
from sqlalchemy import Column, String
from sqlalchemy.exc import OperationalError

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('add_event_fields')

# Import app and db from your main application
from main import app, db

def add_event_fields():
    """Add the event fields to the pending_markets table."""
    try:
        # Add columns if they don't exist
        with app.app_context():
            # Check if the columns already exist
            columns = [column['column_name'] for column in db.session.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'pending_markets'"
            ).fetchall()]
            
            # Add event_id if it doesn't exist
            if 'event_id' not in columns:
                db.session.execute(
                    "ALTER TABLE pending_markets ADD COLUMN event_id VARCHAR(255)"
                )
                logger.info("Added 'event_id' column to pending_markets table")
            else:
                logger.info("Column 'event_id' already exists in pending_markets table")
                
            # Add event_name if it doesn't exist
            if 'event_name' not in columns:
                db.session.execute(
                    "ALTER TABLE pending_markets ADD COLUMN event_name VARCHAR(255)"
                )
                logger.info("Added 'event_name' column to pending_markets table")
            else:
                logger.info("Column 'event_name' already exists in pending_markets table")
                
            # Commit the changes
            db.session.commit()
            
            logger.info("Successfully added event fields to pending_markets table")
            return True
            
    except OperationalError as e:
        logger.error(f"Database error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error adding event fields: {str(e)}")
        return False

def main():
    """Main function to add event fields."""
    logger.info("Starting migration to add event fields to pending_markets table")
    
    # Add the fields
    success = add_event_fields()
    
    if success:
        logger.info("Migration completed successfully")
        return 0
    else:
        logger.error("Migration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())