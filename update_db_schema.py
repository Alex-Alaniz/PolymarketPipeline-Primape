#!/usr/bin/env python
"""
Update database schema for the Polymarket pipeline.

This script updates the database schema to add the option_images column to the Market table.
Run this script to apply the necessary database changes.
"""

import sys
import logging
from sqlalchemy import Column, JSON

from main import app
from models import db, Market

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('update_db')

def update_database():
    """Add option_images column to Market table."""
    with app.app_context():
        try:
            # Check if column already exists
            column_exists = False
            for column in Market.__table__.columns:
                if column.name == 'option_images':
                    column_exists = True
                    break
            
            if not column_exists:
                # Add option_images column
                logger.info("Adding option_images column to Market table...")
                
                # Use SQLAlchemy to add the column
                column = Column('option_images', JSON)
                column.create(Market.__table__, bind=db.engine)
                
                logger.info("Column added successfully")
            else:
                logger.info("option_images column already exists, no changes made")
            
            return True
        except Exception as e:
            logger.error(f"Error updating database schema: {str(e)}")
            return False

def main():
    """Main function to update the database schema."""
    try:
        logger.info("Starting database schema update")
        success = update_database()
        
        if success:
            logger.info("Database schema update complete")
            return 0
        else:
            logger.error("Database schema update failed")
            return 1
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())