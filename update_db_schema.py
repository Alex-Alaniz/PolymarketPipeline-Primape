#!/usr/bin/env python
"""
Script to update the database schema with new columns for image generation tracking.
"""
import os
import sys
import logging
from datetime import datetime
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('db_update')

def connect_to_db():
    """Connect to the PostgreSQL database."""
    try:
        # Connect using environment variables
        conn = psycopg2.connect(
            dbname=os.environ.get('PGDATABASE'),
            user=os.environ.get('PGUSER'),
            password=os.environ.get('PGPASSWORD'),
            host=os.environ.get('PGHOST'),
            port=os.environ.get('PGPORT')
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        logger.info("Successfully connected to the database")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database: {str(e)}")
        sys.exit(1)

def check_column_exists(cursor, table, column):
    """Check if a column exists in a table."""
    cursor.execute(f"""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = '{table}' AND column_name = '{column}'
    """)
    return cursor.fetchone() is not None

def add_image_tracking_columns(cursor):
    """Add image generation tracking columns to the processed_markets table."""
    try:
        # Check if table exists
        cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'processed_markets')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            logger.error("The processed_markets table does not exist. Run init_db.py first.")
            return False
        
        # Add each column if it doesn't exist
        columns_to_add = [
            ('image_generated', 'BOOLEAN DEFAULT FALSE'),
            ('image_path', 'VARCHAR(255)'),
            ('image_generation_attempts', 'INTEGER DEFAULT 0'),
            ('image_approved', 'BOOLEAN'),
            ('image_approval_date', 'TIMESTAMP'),
            ('image_approver', 'VARCHAR(255)'),
            ('image_message_id', 'VARCHAR(255)'),
            ('image_uri', 'VARCHAR(255)')
        ]
        
        for column, data_type in columns_to_add:
            if not check_column_exists(cursor, 'processed_markets', column):
                logger.info(f"Adding column {column} to processed_markets table")
                cursor.execute(f"ALTER TABLE processed_markets ADD COLUMN {column} {data_type}")
            else:
                logger.info(f"Column {column} already exists in processed_markets table")
        
        logger.info("Successfully updated processed_markets table with image tracking columns")
        return True
    except Exception as e:
        logger.error(f"Error adding image tracking columns: {str(e)}")
        return False

def main():
    """Main function to update the database schema."""
    logger.info("Starting database schema update")
    
    # Connect to the database
    conn = connect_to_db()
    cursor = conn.cursor()
    
    try:
        # Add image tracking columns
        success = add_image_tracking_columns(cursor)
        
        if success:
            logger.info("Database schema update completed successfully")
        else:
            logger.error("Database schema update failed")
            
        # Show the current schema
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'processed_markets'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        logger.info("\nCurrent schema for processed_markets table:")
        for column, data_type in columns:
            logger.info(f"  - {column} ({data_type})")
            
    except Exception as e:
        logger.error(f"Error updating database schema: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()