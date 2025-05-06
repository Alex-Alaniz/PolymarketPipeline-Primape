#!/usr/bin/env python3
"""
Test the full pipeline with batch processing for both regular and categorized markets.

This script tests the following components:
1. Fetching markets from the Polymarket API
2. Storing them in both ProcessedMarket and PendingMarket tables
3. Posting markets in batches from both tables
4. Verifying that batching works correctly with the posted flag

Usage:
    python test_full_pipeline_batching.py
"""

import json
import os
import sys
from datetime import datetime, timedelta

from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import ProcessedMarket, PendingMarket, Market, db
from flask import Flask
import post_unposted_markets
import post_unposted_pending_markets
import fetch_active_markets_with_tracker
import fetch_and_categorize_markets
from config import SLACK_BOT_TOKEN, SLACK_CHANNEL

# Setup logger
logger.remove()
logger.add(sys.stderr, level="DEBUG")

# Initialize Flask app to provide context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def check_db_state():
    """Check the state of the ProcessedMarket and PendingMarket tables."""
    with app.app_context():
        processed_markets = ProcessedMarket.query.all()
        pending_markets = PendingMarket.query.all()
        
        processed_posted = ProcessedMarket.query.filter_by(posted=True).count()
        processed_unposted = ProcessedMarket.query.filter_by(posted=False).count()
        
        pending_posted = PendingMarket.query.filter_by(posted=True).count()
        pending_unposted = PendingMarket.query.filter_by(posted=False).count()
        
        logger.info(f"Total ProcessedMarket entries: {len(processed_markets)}")
        logger.info(f"  - Posted: {processed_posted}")
        logger.info(f"  - Unposted: {processed_unposted}")
        
        logger.info(f"Total PendingMarket entries: {len(pending_markets)}")
        logger.info(f"  - Posted: {pending_posted}")
        logger.info(f"  - Unposted: {pending_unposted}")
        
        return {
            "processed": {
                "total": len(processed_markets),
                "posted": processed_posted,
                "unposted": processed_unposted
            },
            "pending": {
                "total": len(pending_markets),
                "posted": pending_posted,
                "unposted": pending_unposted
            }
        }

def setup_test_data():
    """Set up test data for batch posting tests.
    
    Fetches markets from the Polymarket API and stores them in both
    ProcessedMarket and PendingMarket tables without posting to Slack.
    """
    logger.info("Setting up test data...")
    
    with app.app_context():
        # Clear any existing test data
        ProcessedMarket.query.delete()
        PendingMarket.query.delete()
        db.session.commit()
        
        # Fetch markets and store in ProcessedMarket table
        logger.info("Fetching markets for ProcessedMarket table...")
        markets = fetch_active_markets_with_tracker.fetch_markets(limit=30)
        filtered_markets = fetch_active_markets_with_tracker.filter_active_non_expired_markets(markets)
        processed_markets = fetch_active_markets_with_tracker.track_markets_in_db(filtered_markets)
        logger.info(f"Added {len(processed_markets)} markets to ProcessedMarket table")
        
        # Fetch markets and store in PendingMarket table
        logger.info("Fetching markets for PendingMarket table...")
        markets = fetch_and_categorize_markets.fetch_markets(limit=30)
        filtered_markets = fetch_and_categorize_markets.filter_active_non_expired_markets(markets)
        pending_markets = fetch_and_categorize_markets.store_pending_markets(filtered_markets)
        logger.info(f"Added {len(pending_markets)} markets to PendingMarket table")
        
        return check_db_state()

def test_post_unposted_markets(max_to_post=5):
    """Test posting unposted markets from the ProcessedMarket table."""
    logger.info("Testing post_unposted_markets...")
    
    # Modify the function to limit the number of markets posted
    def get_limited_unposted_markets():
        with app.app_context():
            markets = ProcessedMarket.query.filter_by(posted=False).limit(max_to_post).all()
            logger.info(f"Selected {len(markets)} unposted markets for posting")
            return markets
    
    # Replace the original function with our modified version for testing
    original_get_unposted = post_unposted_markets.get_unposted_markets
    post_unposted_markets.get_unposted_markets = get_limited_unposted_markets
    
    try:
        with app.app_context():
            before = check_db_state()
            # Call the main function which will use our patched get_unposted_markets
            post_unposted_markets.main()
            after = check_db_state()
            
            # Calculate how many were actually posted
            posted_count = before["processed"]["unposted"] - after["processed"]["unposted"]
            
            logger.info(f"Posted {posted_count} markets from ProcessedMarket table")
            logger.info(f"Remaining unposted: {after['processed']['unposted']}")
            
            return posted_count
    finally:
        # Restore the original function
        post_unposted_markets.get_unposted_markets = original_get_unposted

def test_post_unposted_pending_markets(max_to_post=5):
    """Test posting unposted markets from the PendingMarket table."""
    logger.info("Testing post_unposted_pending_markets...")
    
    # Modify the function to limit the number of markets posted
    def get_limited_unposted_markets():
        with app.app_context():
            markets = PendingMarket.query.filter_by(posted=False).limit(max_to_post).all()
            logger.info(f"Selected {len(markets)} unposted pending markets for posting")
            return markets
    
    # Replace the original function with our modified version for testing
    original_get_unposted = post_unposted_pending_markets.get_unposted_markets
    post_unposted_pending_markets.get_unposted_markets = get_limited_unposted_markets
    
    try:
        with app.app_context():
            before = check_db_state()
            # Call the main function which will use our patched get_unposted_markets
            post_unposted_pending_markets.main()
            after = check_db_state()
            
            # Calculate how many were actually posted
            posted_count = before["pending"]["unposted"] - after["pending"]["unposted"]
            
            logger.info(f"Posted {posted_count} markets from PendingMarket table")
            logger.info(f"Remaining unposted: {after['pending']['unposted']}")
            
            return posted_count
    finally:
        # Restore the original function
        post_unposted_pending_markets.get_unposted_markets = original_get_unposted

def test_full_batching():
    """Test the full batching process for both market tables."""
    logger.info("=== Starting Full Pipeline Batching Test ===")
    
    # Set up test data
    initial_state = setup_test_data()
    logger.info("Initial state:")
    logger.info(f"ProcessedMarket: {initial_state['processed']['total']} total, {initial_state['processed']['unposted']} unposted")
    logger.info(f"PendingMarket: {initial_state['pending']['total']} total, {initial_state['pending']['unposted']} unposted")
    
    # Test batch posting from ProcessedMarket
    logger.info("\n=== Testing ProcessedMarket Batching ===")
    batch_sizes = [5, 10, 3]  # Try different batch sizes
    for i, batch_size in enumerate(batch_sizes):
        logger.info(f"\nBatch {i+1}: Posting up to {batch_size} markets from ProcessedMarket")
        posted = test_post_unposted_markets(max_to_post=batch_size)
        logger.info(f"Posted {posted} markets in this batch")
    
    # Test batch posting from PendingMarket
    logger.info("\n=== Testing PendingMarket Batching ===")
    batch_sizes = [5, 10, 3]  # Try different batch sizes
    for i, batch_size in enumerate(batch_sizes):
        logger.info(f"\nBatch {i+1}: Posting up to {batch_size} markets from PendingMarket")
        posted = test_post_unposted_pending_markets(max_to_post=batch_size)
        logger.info(f"Posted {posted} markets in this batch")
    
    # Final state
    final_state = check_db_state()
    logger.info("\n=== Final State ===")
    logger.info(f"ProcessedMarket: {final_state['processed']['total']} total, {final_state['processed']['posted']} posted, {final_state['processed']['unposted']} unposted")
    logger.info(f"PendingMarket: {final_state['pending']['total']} total, {final_state['pending']['posted']} posted, {final_state['pending']['unposted']} unposted")
    
    # Calculate success
    processed_success = final_state['processed']['posted'] > initial_state['processed']['posted']
    pending_success = final_state['pending']['posted'] > initial_state['pending']['posted']
    
    if processed_success and pending_success:
        logger.info("✅ Test PASSED: Both ProcessedMarket and PendingMarket batch posting works")
        return True
    else:
        logger.error("❌ Test FAILED: One or both batch posting processes failed")
        if not processed_success:
            logger.error("  - ProcessedMarket batch posting failed")
        if not pending_success:
            logger.error("  - PendingMarket batch posting failed")
        return False

if __name__ == "__main__":
    try:
        success = test_full_batching()
        if success:
            logger.info("All tests completed successfully!")
            sys.exit(0)
        else:
            logger.error("Some tests failed!")
            sys.exit(1)
    except Exception as e:
        logger.exception(f"Test failed with exception: {str(e)}")
        sys.exit(1)