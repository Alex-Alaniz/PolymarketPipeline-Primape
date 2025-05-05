#!/usr/bin/env python3

"""
Test script for active markets workflow.

This script tests the complete active market tracking and approval workflow,
including fetching, filtering, posting to Slack, and checking approvals.

It uses mock Slack implementation for testing without actual API calls.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import time
import json

# Set testing environment flag
os.environ["TESTING"] = "true"

from models import db, Market, ProcessedMarket
from filter_active_markets import fetch_markets, filter_active_markets
from fetch_active_markets_with_tracker import filter_new_markets, post_new_markets
from check_market_approvals import check_market_approvals
from test_utils.mock_slack import approve_test_market, reject_test_market, clear_test_data as clear_mock_slack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_active_markets")

def clear_test_db_data():
    """Clear all test data from the database."""
    logger.info("Clearing test data from database...")
    
    # Delete test records
    try:
        # Find test markets by looking for TEST prefix in question
        test_processed = ProcessedMarket.query.filter(
            ProcessedMarket.question.like("TEST:%")
        ).all()
        
        for market in test_processed:
            db.session.delete(market)
            
        # Find test Market entries
        test_markets = Market.query.filter(
            Market.question.like("TEST:%")
        ).all()
        
        for market in test_markets:
            db.session.delete(market)
        
        db.session.commit()
        logger.info(f"Cleared {len(test_processed)} test processed markets and {len(test_markets)} test markets")
        
    except Exception as e:
        logger.error(f"Error clearing test data: {str(e)}")
        db.session.rollback()

def create_test_markets(count=5):
    """Create test market data for testing."""
    logger.info(f"Creating {count} test markets...")
    
    test_markets = []
    categories = ["politics", "sports", "crypto", "entertainment", "science"]
    
    for i in range(count):
        category = categories[i % len(categories)]
        market_id = f"test-market-{i}-{int(time.time())}"
        condition_id = f"test-condition-{i}-{int(time.time())}"
        
        # Create market data
        market = {
            "id": market_id,
            "conditionId": condition_id,
            "question": f"TEST: Will this test market {i} be approved?",
            "endDate": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
            "fetched_category": category,
            "image": "https://example.com/image.jpg",
            "icon": "https://example.com/icon.jpg",
            "active": True,
            "closed": False,
            "archived": False
        }
        
        test_markets.append(market)
    
    logger.info(f"Created {len(test_markets)} test markets")
    return test_markets

def test_market_tracking():
    """Test tracking markets in the database."""
    logger.info("Testing market tracking...")
    
    # Create test markets
    test_markets = create_test_markets(5)
    
    # Post markets to mock Slack
    posted_markets = post_new_markets(test_markets, max_to_post=3)
    
    if not posted_markets:
        logger.error("Failed to post any markets")
        return False
    
    logger.info(f"Posted {len(posted_markets)} markets to Slack")
    
    # Check that markets were tracked in the database
    condition_ids = [market.get("conditionId") for market in test_markets]
    tracked_markets = ProcessedMarket.query.filter(
        ProcessedMarket.condition_id.in_(condition_ids)
    ).all()
    
    logger.info(f"Found {len(tracked_markets)} tracked markets in database")
    
    return len(tracked_markets) > 0

def test_market_approval_workflow():
    """Test the complete market approval workflow."""
    logger.info("Testing market approval workflow...")
    
    # Clear any existing data to ensure we start fresh
    clear_test_db_data()
    clear_mock_slack()
    
    # Create and post test markets
    test_markets = create_test_markets(3)
    
    # First track the markets in database
    from fetch_active_markets_with_tracker import track_markets_in_db
    tracked_markets = track_markets_in_db(test_markets)
    
    # Then post directly to Slack, bypassing the filter_new_markets check
    from utils.messaging import post_markets_to_slack
    posted_results = post_markets_to_slack(test_markets)
    
    # Update the tracked markets with message IDs
    for i, (market_data, message_id) in enumerate(posted_results):
        if i < len(tracked_markets) and message_id:
            tracked_markets[i].posted = True
            tracked_markets[i].message_id = message_id
    
    # Save changes
    db.session.commit()
    
    # Use tracked_markets as our posted_markets
    posted_markets = tracked_markets
    
    if not posted_markets:
        logger.error("Failed to post any markets")
        return False
    
    # Get message IDs
    message_ids = [market.message_id for market in posted_markets if market.message_id]
    
    if not message_ids:
        logger.error("No message IDs found for posted markets")
        return False
    
    # Approve some markets using mock Slack
    logger.info("Approving markets in mock Slack...")
    for i, message_id in enumerate(message_ids):
        # Approve first market, reject second, leave third pending
        if i == 0:
            approve_test_market(message_id)
            logger.info(f"Approved market with message ID {message_id}")
        elif i == 1:
            reject_test_market(message_id)
            logger.info(f"Rejected market with message ID {message_id}")
    
    # Run approval check
    pending, approved, rejected = check_market_approvals()
    
    logger.info(f"Approval check results: {pending} pending, {approved} approved, {rejected} rejected")
    
    # Check that approved markets were added to Market table
    approved_in_markets = Market.query.filter(
        Market.question.like("TEST:%")
    ).all()
    
    logger.info(f"Found {len(approved_in_markets)} markets in Market table")
    
    # Check that approval status was updated in ProcessedMarket
    verified_approvals = ProcessedMarket.query.filter(
        ProcessedMarket.question.like("TEST:%"),
        ProcessedMarket.approved == True
    ).all()
    
    verified_rejections = ProcessedMarket.query.filter(
        ProcessedMarket.question.like("TEST:%"),
        ProcessedMarket.approved == False
    ).all()
    
    logger.info(f"Found {len(verified_approvals)} approved and {len(verified_rejections)} rejected markets in ProcessedMarket")
    
    # Verify expected counts
    logger.info(f"Expected: approved=1, rejected=1, pending=1, approved_in_markets=2")
    logger.info(f"Actual: approved={approved}, rejected={rejected}, pending={pending}, approved_in_markets={len(approved_in_markets)}")
    
    # We have 2 markets in the Markets table because we create a "placeholder" for rejected markets
    return (
        approved == 1 and 
        rejected == 1 and 
        len(approved_in_markets) == 2  # Updated: 1 approved + 1 rejected entry
    )

def main():
    """Main function to run the workflow tests."""
    logger.info("Starting active markets workflow tests")
    
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # Clean up any previous test data
        clear_test_db_data()
        clear_mock_slack()
        
        # Run tests
        tracking_success = test_market_tracking()
        approval_success = test_market_approval_workflow()
        
        # Report results
        logger.info("\n=== TEST RESULTS ===")
        logger.info(f"Market tracking:    {'✓ PASS' if tracking_success else '✗ FAIL'}")
        logger.info(f"Approval workflow:  {'✓ PASS' if approval_success else '✗ FAIL'}")
        logger.info("====================\n")
        
        # Final cleanup
        clear_test_db_data()
        clear_mock_slack()
    
    if tracking_success and approval_success:
        logger.info("All tests PASSED!")
        return 0
    else:
        logger.error("Some tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())