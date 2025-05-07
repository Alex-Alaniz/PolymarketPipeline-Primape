#!/usr/bin/env python3
"""
Add event fields to the PendingMarket table.

This script adds the event_id and event_name columns to the PendingMarket table
to support event-based market grouping.
"""

import os
import sys
import logging
import psycopg2
from psycopg2 import sql

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migrate')

def add_event_fields():
    """Add event_id and event_name fields to the PendingMarket table."""
    # Get database connection from environment
    database_url = os.environ.get("DATABASE_URL")
    
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        return False
    
    try:
        # Connect to the database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check if columns exist
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'pending_markets'
            AND column_name IN ('event_id', 'event_name')
        """)
        
        existing_columns = [row[0] for row in cursor.fetchall()]
        
        # Add event_id column if it doesn't exist
        if 'event_id' not in existing_columns:
            logger.info("Adding event_id column to pending_markets table")
            
            cursor.execute("""
                ALTER TABLE pending_markets
                ADD COLUMN event_id VARCHAR(255)
            """)
            
            logger.info("Successfully added event_id column")
        else:
            logger.info("event_id column already exists")
        
        # Add event_name column if it doesn't exist
        if 'event_name' not in existing_columns:
            logger.info("Adding event_name column to pending_markets table")
            
            cursor.execute("""
                ALTER TABLE pending_markets
                ADD COLUMN event_name VARCHAR(255)
            """)
            
            logger.info("Successfully added event_name column")
        else:
            logger.info("event_name column already exists")
        
        # Commit changes
        conn.commit()
        
        # Close connection
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error performing migration: {str(e)}")
        return False

def main():
    """Main function to run the migration."""
    logger.info("Starting migration to add event fields to pending_markets")
    
    # Get user confirmation
    if len(sys.argv) <= 1 or sys.argv[1] != '--confirm':
        print("This script will add event_id and event_name columns to the pending_markets table.")
        print("Run with --confirm to execute the migration.")
        return 1
    
    # Run the migration
    if add_event_fields():
        logger.info("Migration completed successfully")
        return 0
    else:
        logger.error("Migration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())