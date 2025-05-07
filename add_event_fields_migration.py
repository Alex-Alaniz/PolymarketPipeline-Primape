#!/usr/bin/env python3

"""
Migration script for adding event fields to tables.

This script adds event_id and event_name fields to both the markets and
pending_markets tables if they don't already exist. This is a standalone
script that can be run to ensure proper event relationship structure.
"""

import os
import sys
import logging
from sqlalchemy import Column, String
from sqlalchemy.engine import reflection
from sqlalchemy.sql.schema import MetaData

from main import app
from models import db, Market, PendingMarket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("event_migration")

def check_column_exists(table_name, column_name):
    """
    Check if a column exists in a table.
    
    Args:
        table_name: Name of the table to check
        column_name: Name of the column to check
        
    Returns:
        bool: True if the column exists, False otherwise
    """
    inspector = reflection.Inspector.from_engine(db.engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def add_events_to_markets():
    """
    Add event_id and event_name columns to the markets table if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        needs_commit = False
        logger.info("Checking markets table for event fields...")
        
        # Check and add event_id
        if not check_column_exists('markets', 'event_id'):
            logger.info("Adding event_id column to markets table")
            # Can't use ORM for this, need to use raw SQL
            db.session.execute('ALTER TABLE markets ADD COLUMN event_id VARCHAR(255)')
            needs_commit = True
        else:
            logger.info("event_id column already exists in markets table")
        
        # Check and add event_name
        if not check_column_exists('markets', 'event_name'):
            logger.info("Adding event_name column to markets table")
            db.session.execute('ALTER TABLE markets ADD COLUMN event_name VARCHAR(255)')
            needs_commit = True
        else:
            logger.info("event_name column already exists in markets table")
        
        if needs_commit:
            db.session.commit()
            logger.info("Successfully added event fields to markets table")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding event fields to markets table: {str(e)}")
        db.session.rollback()
        return False

def add_events_to_pending_markets():
    """
    Add event_id and event_name columns to the pending_markets table if they don't exist.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        needs_commit = False
        logger.info("Checking pending_markets table for event fields...")
        
        # Check and add event_id
        if not check_column_exists('pending_markets', 'event_id'):
            logger.info("Adding event_id column to pending_markets table")
            db.session.execute('ALTER TABLE pending_markets ADD COLUMN event_id VARCHAR(255)')
            needs_commit = True
        else:
            logger.info("event_id column already exists in pending_markets table")
        
        # Check and add event_name
        if not check_column_exists('pending_markets', 'event_name'):
            logger.info("Adding event_name column to pending_markets table")
            db.session.execute('ALTER TABLE pending_markets ADD COLUMN event_name VARCHAR(255)')
            needs_commit = True
        else:
            logger.info("event_name column already exists in pending_markets table")
        
        if needs_commit:
            db.session.commit()
            logger.info("Successfully added event fields to pending_markets table")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding event fields to pending_markets table: {str(e)}")
        db.session.rollback()
        return False

def main():
    """
    Main function to run the migration.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting event fields migration")
    
    with app.app_context():
        # Add event fields to markets table
        markets_success = add_events_to_markets()
        
        # Add event fields to pending_markets table
        pending_success = add_events_to_pending_markets()
        
        if markets_success and pending_success:
            logger.info("Successfully completed event fields migration")
            return 0
        else:
            logger.error("Failed to complete event fields migration")
            return 1

if __name__ == "__main__":
    sys.exit(main())