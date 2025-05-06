#!/usr/bin/env python3

"""
Initialize Database with New Tables

This script initializes the database with the new tables needed for auto-categorization
without affecting existing data. It creates the pending_markets and approvals_log tables
if they don't already exist.
"""

import os
import logging
from typing import List, Dict, Any, Optional

from models import db, Market, PendingMarket, ApprovalLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("init_db_new_tables")

def init_db_new_tables(drop_if_exists: bool = False) -> bool:
    """
    Initialize the database with new tables for auto-categorization.
    
    Args:
        drop_if_exists: If True, drop existing tables before creating
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        inspector = db.inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        tables_to_create = []
        
        # Check if pending_markets table exists
        if 'pending_markets' not in existing_tables:
            logger.info("pending_markets table not found, will create")
            tables_to_create.append(PendingMarket.__table__)
        elif drop_if_exists:
            logger.info("Drop enabled, dropping pending_markets table")
            db.session.execute(f'DROP TABLE IF EXISTS pending_markets')
            db.session.commit()
            tables_to_create.append(PendingMarket.__table__)
        else:
            logger.info("pending_markets table already exists, skipping")
            
        # Check if approvals_log table exists
        if 'approvals_log' not in existing_tables:
            logger.info("approvals_log table not found, will create")
            tables_to_create.append(ApprovalLog.__table__)
        elif drop_if_exists:
            logger.info("Drop enabled, dropping approvals_log table")
            db.session.execute(f'DROP TABLE IF EXISTS approvals_log')
            db.session.commit()
            tables_to_create.append(ApprovalLog.__table__)
        else:
            logger.info("approvals_log table already exists, skipping")
            
        # Create tables if needed
        if tables_to_create:
            logger.info(f"Creating {len(tables_to_create)} new tables")
            db.metadata.create_all(db.engine, tables=tables_to_create)
            logger.info("Tables created successfully")
        else:
            logger.info("No new tables to create")
            
        return True
        
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        return False
        
def main():
    """
    Main function to initialize the database with new tables.
    """
    # Import Flask app to get application context
    from main import app
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Initialize database with new tables")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before creating")
    args = parser.parse_args()
    
    # Use application context for database operations
    with app.app_context():
        success = init_db_new_tables(drop_if_exists=args.drop)
        
        if success:
            print("Database initialized successfully")
            return 0
        else:
            print("Error initializing database")
            return 1
            
if __name__ == "__main__":
    import sys
    sys.exit(main())