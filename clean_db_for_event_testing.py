#!/usr/bin/env python3

"""
Clean Database for Event Testing

This script cleans the database for testing event-based markets.
It deletes all pending markets to ensure we start from a clean state.
"""

import os
import sys
import logging
from datetime import datetime

from models import db, PendingMarket, Market
from main import app

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("db_cleaner")

def reset_pending_markets():
    """
    Reset pending markets table.
    
    This deletes all pending markets but preserves already deployed markets.
    """
    try:
        with app.app_context():
            # Count pending markets before deletion
            count_before = db.session.query(PendingMarket).count()
            logger.info(f"Found {count_before} pending markets before cleaning")
            
            # Delete all pending markets
            db.session.query(PendingMarket).delete()
            db.session.commit()
            
            # Verify deletion
            count_after = db.session.query(PendingMarket).count()
            logger.info(f"Found {count_after} pending markets after cleaning")
            
            # Count deployed markets
            deployed_count = db.session.query(Market).count()
            logger.info(f"Preserved {deployed_count} deployed markets")
            
            return True
    except Exception as e:
        logger.error(f"Error resetting pending markets: {e}")
        db.session.rollback()
        return False

def main():
    """
    Main function to run the database cleaning.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting database cleaning for event testing")
    
    success = reset_pending_markets()
    
    if success:
        logger.info("Successfully cleaned database for event testing")
        return 0
    else:
        logger.error("Failed to clean database for event testing")
        return 1

if __name__ == "__main__":
    sys.exit(main())