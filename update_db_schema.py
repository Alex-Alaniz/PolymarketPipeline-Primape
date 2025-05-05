#!/usr/bin/env python3

"""
Update Database Schema

This script updates the database schema to match the current models.
It adds new fields and ensures all necessary tables exist.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("update_db_schema")

def add_column_if_not_exists(conn, table, column, column_type):
    """
    Add a column to a table if it doesn't already exist.
    
    Args:
        conn: Database connection
        table: Table name
        column: Column name
        column_type: Column type (e.g., 'VARCHAR(255)')
    
    Returns:
        bool: True if column was added, False if it already existed
    """
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
        AND column_name = %s
    """, (table, column))
    
    if cursor.fetchone() is None:
        # Column doesn't exist, add it
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            conn.commit()
            logger.info(f"Added column '{column}' to table '{table}'")
            return True
        except Exception as e:
            conn.rollback()
            logger.error(f"Error adding column '{column}' to table '{table}': {str(e)}")
            return False
    else:
        logger.info(f"Column '{column}' already exists in table '{table}'")
        return False

def update_db_schema():
    """
    Update the database schema with new columns.
    """
    logger.info("Updating database schema...")
    
    # Import Flask app to get application context
    from main import app
    from models import db
    
    # Use application context for database operations
    with app.app_context():
        # Get SQLAlchemy connection
        connection = db.session.connection()
        
        # Get raw connection
        conn = connection.connection
        
        # Add new columns to the markets table
        add_column_if_not_exists(conn, 'markets', 'icon_url', 'VARCHAR(255)')
        add_column_if_not_exists(conn, 'markets', 'apechain_market_id', 'VARCHAR(255)')
        
        # Commit the changes
        db.session.commit()
        
        logger.info("Database schema update complete")
        
def main():
    """
    Main function to run the database schema update.
    """
    try:
        update_db_schema()
        return 0
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())