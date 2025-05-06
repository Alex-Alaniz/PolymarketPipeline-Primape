#!/usr/bin/env python3

"""
Flush Unposted Markets from Database

This script removes all markets with:
- posted = FALSE 
- message_id = NULL

from the ProcessedMarket table. This allows the pipeline to refetch
and recategorize these markets with the updated categorization system.

Important: This script preserves markets that have already been posted
to Slack (posted=TRUE) to maintain the approval workflow for those markets.
"""

import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import flask app for database context
from main import app
from models import db, ProcessedMarket, PendingMarket

def flush_unposted_markets():
    """
    Remove unposted markets from the database.
    
    Only removes markets where:
    - posted = FALSE
    - message_id = NULL
    
    Returns:
        int: Number of markets deleted
    """
    try:
        # Find all unposted markets
        unposted_markets = ProcessedMarket.query.filter_by(
            posted=False,
            message_id=None
        ).all()
        
        # Get count before deletion
        count = len(unposted_markets)
        logger.info(f"Found {count} unposted markets to delete")
        
        # Delete records
        for market in unposted_markets:
            logger.debug(f"Deleting market {market.condition_id}: {market.question}")
            db.session.delete(market)
        
        # Commit changes
        db.session.commit()
        logger.info(f"Successfully deleted {count} unposted markets")
        
        return count
    
    except Exception as e:
        logger.error(f"Error deleting unposted markets: {str(e)}")
        db.session.rollback()
        return 0

def flush_pending_markets():
    """
    Remove all markets from the PendingMarket table.
    
    Returns:
        int: Number of pending markets deleted
    """
    try:
        # Find all pending markets
        pending_markets = PendingMarket.query.all()
        
        # Get count before deletion
        count = len(pending_markets)
        logger.info(f"Found {count} pending markets to delete")
        
        # Delete records
        for market in pending_markets:
            logger.debug(f"Deleting pending market {market.poly_id}: {market.question}")
            db.session.delete(market)
        
        # Commit changes
        db.session.commit()
        logger.info(f"Successfully deleted {count} pending markets")
        
        return count
    
    except Exception as e:
        logger.error(f"Error deleting pending markets: {str(e)}")
        db.session.rollback()
        return 0

def show_database_stats():
    """
    Show statistics about the current database state.
    """
    try:
        posted_markets = ProcessedMarket.query.filter_by(posted=True).count()
        unposted_markets = ProcessedMarket.query.filter_by(posted=False, message_id=None).count()
        pending_markets = PendingMarket.query.count()
        
        logger.info("Database statistics:")
        logger.info(f"  Posted markets: {posted_markets}")
        logger.info(f"  Unposted markets: {unposted_markets}")
        logger.info(f"  Pending markets: {pending_markets}")
        
    except Exception as e:
        logger.error(f"Error getting database statistics: {str(e)}")

def main():
    """
    Main function to flush unposted markets.
    """
    with app.app_context():
        try:
            # Show initial stats
            logger.info("Initial database state:")
            show_database_stats()
            
            # Flush unposted markets from ProcessedMarket table
            deleted_unposted = flush_unposted_markets()
            
            # Flush markets from PendingMarket table
            deleted_pending = flush_pending_markets()
            
            # Show final stats
            logger.info("\nFinal database state:")
            show_database_stats()
            
            # Final summary
            logger.info(f"\nSummary: Deleted {deleted_unposted} unposted markets and {deleted_pending} pending markets")
            logger.info("You can now run the pipeline to refetch and recategorize markets")
            
            return 0
            
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())