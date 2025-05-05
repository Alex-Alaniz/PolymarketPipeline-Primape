#!/usr/bin/env python3

"""
Update database schema for the Polymarket pipeline.

This script adds new fields to the Market table for icon_url and apechain_market_id.
Run this script once to update the database schema.
"""

import os
import sys
import logging
from datetime import datetime

from sqlalchemy import Column, String
from sqlalchemy.exc import OperationalError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_update")

def add_column_if_not_exists(engine, table_name, column_name, column_type):
    """
    Add a column to a table if it doesn't already exist.
    
    Args:
        engine: SQLAlchemy engine
        table_name: Name of the table to alter
        column_name: Name of the column to add
        column_type: SQLAlchemy column type
    
    Returns:
        bool: True if column was added, False if it already existed or on error
    """
    column_type_str = str(column_type.compile())
    
    # Check if column exists
    check_sql = f"""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = '{table_name}' 
    AND column_name = '{column_name}'
    """
    
    try:
        conn = engine.connect()
        result = conn.execute(check_sql)
        exists = result.scalar() is not None
        conn.close()
        
        if exists:
            logger.info(f"Column {column_name} already exists in {table_name}")
            return False
            
        # Add column
        conn = engine.connect()
        add_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type_str}"
        conn.execute(add_sql)
        conn.close()
        
        logger.info(f"Added column {column_name} to {table_name}")
        return True
        
    except Exception as e:
        logger.error(f"Error adding column {column_name} to {table_name}: {str(e)}")
        return False

def update_database_schema():
    """
    Update the database schema with new columns.
    """
    # Import Flask app to get application context and database engine
    from main import app, db
    
    try:
        # Use application context
        with app.app_context():
            engine = db.engine
            
            # Add icon_url column to markets table
            add_column_if_not_exists(
                engine, 
                "markets", 
                "icon_url", 
                Column(String(255))
            )
            
            # Add apechain_market_id column to markets table
            add_column_if_not_exists(
                engine, 
                "markets", 
                "apechain_market_id", 
                Column(String(255))
            )
            
            logger.info("Database schema update complete")
            return True
            
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return False

def main():
    """
    Main function to update the database schema.
    """
    logger.info("Starting database schema update")
    success = update_database_schema()
    
    if success:
        logger.info("Database schema update completed successfully")
        return 0
    else:
        logger.error("Database schema update failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())