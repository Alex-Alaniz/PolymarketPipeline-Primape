#!/usr/bin/env python3

"""
Add event fields to markets table.

This script adds the 'event_id' and 'event_name' columns to the Market table
to support proper event tracking and grouping of related markets.
"""

import os
import logging
from datetime import datetime
import flask
import sqlalchemy
from sqlalchemy import exc

from main import app
from models import db, Market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("add_event_fields")

def add_event_fields():
    """Add the event fields to the markets table."""
    with app.app_context():
        try:
            # Check if the columns already exist
            inspector = sqlalchemy.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('markets')]
            
            with db.engine.connect() as connection:
                if 'event_id' in columns:
                    logger.info("event_id column already exists in markets table")
                else:
                    # Add event_id column
                    logger.info("Adding event_id column to markets table")
                    connection.execute(sqlalchemy.text('ALTER TABLE markets ADD COLUMN event_id VARCHAR(255)'))
                    connection.commit()
                    logger.info("event_id column added successfully")
                
                if 'event_name' in columns:
                    logger.info("event_name column already exists in markets table")
                else:
                    # Add event_name column
                    logger.info("Adding event_name column to markets table")
                    connection.execute(sqlalchemy.text('ALTER TABLE markets ADD COLUMN event_name VARCHAR(255)'))
                    connection.commit()
                    logger.info("event_name column added successfully")
                    
            logger.info("Event fields added to markets table")
            return True
        except exc.SQLAlchemyError as e:
            logger.error(f"Error adding event fields to markets table: {str(e)}")
            return False

def main():
    """Main function to add event fields."""
    success = add_event_fields()
    return 0 if success else 1

if __name__ == "__main__":
    main()