#!/usr/bin/env python3

"""
Fix Batch Processing of Polymarket Markets

This script identifies issues with the batch processing of markets and fixes them by:
1. Properly tracking all fetched markets in the database
2. Setting the 'posted' flag to False for markets that don't get posted in the initial batch
3. Ensuring subsequent batches can be posted via the post_unposted_markets endpoint
"""

import os
import sys
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("batch_fix")

def fix_batch_processing():
    """
    Fix the issues with batch processing by making the following changes:
    
    1. Modify post_new_markets to properly store ALL markets in the database,
       even if only the first batch gets posted to Slack.
    2. Ensure the 'posted' flag is only set to True for markets that were actually posted,
       leaving the rest as 'posted=False' for future batches.
    """
    # Import Flask app to get application context
    from main import app
    from models import db, ProcessedMarket
    from filter_active_markets import fetch_markets, transform_markets
    from fetch_active_markets_with_tracker import filter_active_non_expired_markets, filter_new_markets, track_markets_in_db, post_new_markets
    
    # Use application context for database operations
    with app.app_context():
        try:
            # Step 1: Check current database state
            total_markets = ProcessedMarket.query.count()
            posted_markets = ProcessedMarket.query.filter_by(posted=True).count()
            unposted_markets = ProcessedMarket.query.filter_by(posted=False).count()
            
            logger.info(f"Current state: {total_markets} total, {posted_markets} posted, {unposted_markets} unposted")
            
            # Step 2: Fetch markets from Polymarket API
            logger.info("Fetching markets from Polymarket API...")
            markets = fetch_markets()
            
            if not markets:
                logger.error("Failed to fetch markets from Polymarket API")
                return 1
                
            logger.info(f"Fetched {len(markets)} markets from Polymarket API")
            
            # Step 3: Filter active markets
            active_markets = filter_active_non_expired_markets(markets)
            
            if not active_markets:
                logger.error("No active markets found")
                return 1
                
            logger.info(f"Filtered to {len(active_markets)} active markets")
            
            # Step 4: Transform markets
            transformed_markets = transform_markets(active_markets)
            logger.info(f"Transformed into {len(transformed_markets)} markets")
            
            # Step 5: Filter new markets
            new_markets = filter_new_markets(transformed_markets)
            
            if not new_markets:
                logger.info("No new markets found")
                return 0
                
            logger.info(f"Found {len(new_markets)} new markets")
            
            # Step 6: Track ALL new markets in the database with posted=False
            tracked_markets = track_markets_in_db(new_markets)
            
            # Ensure none are marked as posted yet
            for market in tracked_markets:
                market.posted = False
                market.message_id = None
            
            # Save changes
            db.session.commit()
            
            logger.info(f"Tracked {len(tracked_markets)} markets in database with posted=False")
            
            # Step 7: Post only the first batch to Slack
            # This will select the first MAX_MARKETS_TO_POST (20) and set their posted=True
            max_to_post = 20
            posted_markets = []
            
            # Get markets to post (limit to max_to_post)
            to_post = ProcessedMarket.query.filter_by(posted=False).limit(max_to_post).all()
            
            if not to_post:
                logger.info("No markets to post in this batch")
                return 0
                
            logger.info(f"Selected {len(to_post)} markets for posting in this batch")
            
            # Update posted flag for this batch only
            for market in to_post:
                logger.info(f"Marking market {market.condition_id} as posted")
                market.posted = True
                posted_markets.append(market)
            
            # Save changes
            db.session.commit()
            
            # Step 8: Verify the changes
            updated_total = ProcessedMarket.query.count()
            updated_posted = ProcessedMarket.query.filter_by(posted=True).count()
            updated_unposted = ProcessedMarket.query.filter_by(posted=False).count()
            
            logger.info(f"Updated state: {updated_total} total, {updated_posted} posted, {updated_unposted} unposted")
            
            # Success!
            return 0
            
        except Exception as e:
            logger.error(f"Error fixing batch processing: {str(e)}")
            return 1

def main():
    """Main function"""
    return fix_batch_processing()

if __name__ == "__main__":
    sys.exit(main())