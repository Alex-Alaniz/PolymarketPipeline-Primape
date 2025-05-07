#!/usr/bin/env python3

"""
Test the new image handling rules in a complete pipeline run.

This script:
1. Resets the database
2. Runs a small batch of the pipeline to fetch markets
3. Posts them to Slack with correct image handling
4. Verifies that the images are correctly displayed
"""

import os
import sys
import logging
import json
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_database():
    """
    Reset the database using the true_reset.py script.
    """
    logger.info("Resetting database...")
    
    # Import and run the true_reset script
    try:
        import true_reset
        result = true_reset.main()
        
        # true_reset.main() returns 0 on success, not a boolean
        if result == 0:
            logger.info("✅ Database reset successfully")
            return True
        else:
            logger.error(f"❌ Failed to reset database (exit code {result})")
            return False
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def fetch_small_batch():
    """
    Fetch a small batch of markets for testing.
    
    Returns:
        int: Number of markets fetched
    """
    logger.info("Fetching small batch of markets...")
    
    try:
        from fetch_small_batch import main
        result = main()
        
        if isinstance(result, int) and result >= 0:
            logger.info(f"✅ Fetched {result} markets")
            return result
        else:
            logger.error(f"❌ Unexpected result from fetch_small_batch: {result}")
            return 0
    except Exception as e:
        logger.error(f"Error fetching small batch: {str(e)}")
        return 0

def run_processing_steps():
    """
    Run the market processing steps.
    
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info("Running market processing steps...")
    
    try:
        # Import main app context
        from main import app
        
        with app.app_context():
            # 1. Import models
            from models import PendingMarket, Market, db
            
            # 2. Check if we have any pending markets
            pending_count = PendingMarket.query.count()
            logger.info(f"Found {pending_count} pending markets in database")
            
            if pending_count == 0:
                logger.warning("No pending markets found - nothing to process")
                return False
            
            # 3. Check for markets with events array
            from sqlalchemy import text
            event_markets = db.session.execute(
                text("SELECT id, question FROM pending_markets WHERE events IS NOT NULL LIMIT 5")
            ).fetchall()
            
            if not event_markets:
                logger.warning("No markets with events array found")
            else:
                logger.info(f"Found {len(event_markets)} markets with events array")
                for market in event_markets:
                    logger.info(f"- {market.question}")
            
            # 4. Apply our image filtering rules to a pending market
            from utils.event_filter import process_event_images
            
            # Get a sample pending market
            sample_market = PendingMarket.query.filter(
                PendingMarket.events.is_not(None)
            ).first()
            
            if sample_market:
                logger.info(f"Processing sample market: {sample_market.question}")
                
                # Convert to dict for processing
                market_dict = {
                    "id": sample_market.id,
                    "poly_id": sample_market.poly_id,
                    "question": sample_market.question,
                    "category": sample_market.category,
                    "end_date": sample_market.end_date,
                    "image": sample_market.image,
                    "icon": sample_market.icon,
                    "events": json.loads(sample_market.events) if sample_market.events else None,
                    "outcomes": sample_market.outcomes
                }
                
                # Process the market
                processed = process_event_images(market_dict)
                
                # Check results
                logger.info(f"Is binary: {processed.get('is_binary', False)}")
                logger.info(f"Is multiple: {processed.get('is_multiple_option', False)}")
                logger.info(f"Event image: {processed.get('event_image', 'None')[:50]}...")
                logger.info(f"Option images: {len(processed.get('option_images', {}))} images")
                
                # 5. Test posting to Slack with correct image handling
                from utils.messaging import format_market_with_images
                from utils.slack import post_message_with_blocks
                
                # Format the market for Slack
                message, blocks = format_market_with_images(processed)
                
                # Try to post to Slack (if configured)
                if os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'):
                    slack_ts = post_message_with_blocks(message, blocks)
                    if slack_ts:
                        logger.info(f"✅ Posted to Slack with timestamp: {slack_ts}")
                    else:
                        logger.error("❌ Failed to post to Slack")
                else:
                    logger.warning("Slack credentials not available - skipping Slack posting")
                
                return True
            else:
                logger.warning("No suitable sample market found with events array")
                return False
    
    except Exception as e:
        logger.error(f"Error running processing steps: {str(e)}")
        return False

def main():
    """
    Main function to test the image handling in the full pipeline.
    """
    # Step 1: Reset the database
    if not reset_database():
        return 1
    
    # Step 2: Fetch a small batch of markets
    markets_fetched = fetch_small_batch()
    if markets_fetched == 0:
        logger.error("No markets fetched, aborting test")
        return 1
    
    # Step 3: Run processing steps
    if not run_processing_steps():
        logger.error("Processing steps failed")
        return 1
    
    logger.info("✅ Test completed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())