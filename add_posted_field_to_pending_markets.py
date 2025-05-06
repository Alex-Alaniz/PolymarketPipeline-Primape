#!/usr/bin/env python3

"""
Add posted field to the pending_markets table.

This script adds the 'posted' column to the PendingMarket table
to support batch processing of markets.
"""

import logging
from sqlalchemy import text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Flask app for database context
from main import app
from models import db

def add_posted_field():
    """Add the posted field to the pending_markets table."""
    with app.app_context():
        # Check if the column already exists
        try:
            # Use raw SQL to check if the column exists
            sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='pending_markets' AND column_name='posted'
            """)
            result = db.session.execute(sql).fetchone()
            
            if result:
                logger.info("Column 'posted' already exists in pending_markets table")
                return True
                
            # Column doesn't exist, add it
            logger.info("Adding 'posted' column to pending_markets table...")
            
            # Add the column with a default value of False
            sql = text("""
                ALTER TABLE pending_markets 
                ADD COLUMN posted BOOLEAN NOT NULL DEFAULT FALSE
            """)
            db.session.execute(sql)
            db.session.commit()
            
            logger.info("Successfully added 'posted' column to pending_markets table")
            return True
            
        except Exception as e:
            logger.error(f"Error adding column: {str(e)}")
            db.session.rollback()
            return False

def main():
    """Main function to add the posted field."""
    success = add_posted_field()
    
    if success:
        logger.info("Migration completed successfully!")
        return 0
    else:
        logger.error("Migration failed!")
        return 1

if __name__ == "__main__":
    main()