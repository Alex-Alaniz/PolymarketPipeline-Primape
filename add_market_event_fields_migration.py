#!/usr/bin/env python3

"""
Migration script for adding event fields to Market table.

This script adds additional event-related fields to the Market table:
- event_image
- event_icon
- is_event
- option_market_ids

This ensures our final Market table can store event-based market structure.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, MetaData, Table, Column, String, Boolean, JSON, inspect, text
from sqlalchemy.engine import reflection

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("market_event_migration")

# Get database URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)
metadata = MetaData()
inspector = inspect(engine)

def check_column_exists(table_name, column_name):
    """
    Check if a column exists in a table.
    
    Args:
        table_name: Name of the table to check
        column_name: Name of the column to check
        
    Returns:
        bool: True if the column exists, False otherwise
    """
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)

def add_column_if_not_exists(table_name, column_name, column_type):
    """
    Add a column to a table if it doesn't already exist.
    
    Args:
        table_name: Name of the table
        column_name: Name of the column to add
        column_type: SQLAlchemy column type
        
    Returns:
        bool: True if column added or already exists, False on error
    """
    try:
        if check_column_exists(table_name, column_name):
            logger.info(f"{column_name} column already exists in {table_name} table")
            return True
        
        # Add the column
        with engine.begin() as conn:
            column_type_str = str(column_type.compile(dialect=engine.dialect))
            conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_str}"))
            
        logger.info(f"Added {column_name} column to {table_name} table")
        return True
    except Exception as e:
        logger.error(f"Error adding {column_name} column to {table_name}: {e}")
        return False

def add_extended_event_fields():
    """
    Add extended event fields to the markets table.
    
    Returns:
        bool: True if successful, False if there was an error
    """
    try:
        # Check if table exists
        if not inspector.has_table("markets"):
            logger.error("markets table does not exist")
            return False
        
        # Add event_image column
        if not add_column_if_not_exists("markets", "event_image", String()):
            return False
        
        # Add event_icon column
        if not add_column_if_not_exists("markets", "event_icon", String()):
            return False
        
        # Add is_event column
        if not add_column_if_not_exists("markets", "is_event", Boolean()):
            return False
        
        # Add option_market_ids column
        if not add_column_if_not_exists("markets", "option_market_ids", JSON()):
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error adding extended event fields: {e}")
        return False

def main():
    """
    Main function to run the migration.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting Market table event fields migration")
    
    success = add_extended_event_fields()
    
    if success:
        logger.info("Successfully completed Market table event fields migration")
        return 0
    else:
        logger.error("Failed to complete Market table event fields migration")
        return 1

if __name__ == "__main__":
    sys.exit(main())