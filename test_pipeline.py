#!/usr/bin/env python3

"""
Test script for the Polymarket pipeline.

This script tests the end-to-end functionality of the Polymarket pipeline,
including fetching markets, filtering them, and simulating the approval process.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
import time

# Set testing environment flag
os.environ["TESTING"] = "true"

from models import db, Market, ProcessedMarket
from filter_active_markets import fetch_markets, filter_active_markets
from check_market_approvals import check_market_approvals
from pipeline import PolymarketPipeline
from test_utils.mock_slack import post_message, approve_test_market, reject_test_market, clear_test_data as clear_mock_slack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_pipeline")

def clear_test_data():
    """Clear any existing test data."""
    logger.info("Clearing test data...")
    
    # Delete test markets from the Market table
    test_markets = Market.query.filter(Market.question.like("TEST:%")).all()
    for market in test_markets:
        db.session.delete(market)
    
    # Delete test markets from the ProcessedMarket table
    test_processed = ProcessedMarket.query.filter(ProcessedMarket.question.like("TEST:%")).all()
    for processed in test_processed:
        db.session.delete(processed)
    
    db.session.commit()
    logger.info(f"Cleared {len(test_markets)} test markets and {len(test_processed)} test processed markets")

def create_test_market(index=1):
    """Create a test market record."""
    market_id = f"test-market-{index}-{int(time.time())}"
    question = f"TEST: Will this test market {index} pass all checks?"
    expiry = datetime.utcnow() + timedelta(days=30)
    
    # Create a raw market object similar to what we'd get from the API
    raw_market = {
        "id": market_id,
        "conditionId": f"test-condition-{index}",
        "question": question,
        "outcomes": '["Yes", "No"]',
        "outcomePrices": '[0.5, 0.5]',
        "endDate": expiry.isoformat() + "Z",
        "description": "This is a test market for pipeline testing",
        "image": "https://example.com/image.jpg",
        "icon": "https://example.com/icon.png",
        "active": True,
        "closed": False,
        "archived": False,
        "volume": "1000",
        "fetched_category": "test"
    }
    
    # Create a ProcessedMarket record
    processed = ProcessedMarket(
        condition_id=raw_market["conditionId"],
        question=raw_market["question"],
        raw_data=raw_market
    )
    
    db.session.add(processed)
    db.session.commit()
    
    logger.info(f"Created test ProcessedMarket: {market_id}")
    return processed

def simulate_market_approval(processed_market, approve=True):
    """Simulate the approval or rejection of a market in Slack.
    
    Args:
        processed_market: The ProcessedMarket object to approve/reject
        approve: If True, approve the market; if False, reject it
    """
    logger.info(f"Simulating {'approval' if approve else 'rejection'} for market: {processed_market.question}")
    
    # Post to mock Slack
    from utils.messaging import post_market_for_approval
    
    # Check if market is already posted
    if not processed_market.posted or not processed_market.message_id:
        # Use the raw data to post the market
        message_id = post_market_for_approval(processed_market.raw_data)
        
        # Mark as posted to slack
        processed_market.posted = True
        processed_market.message_id = message_id
        db.session.commit()
    
    # Add the appropriate reaction
    if approve:
        approve_test_market(processed_market.message_id)
    else:
        reject_test_market(processed_market.message_id)
    
    # Update the database record
    processed_market.approved = approve
    processed_market.approval_date = datetime.utcnow()
    processed_market.approver = "TEST_USER"
    db.session.commit()
    
    logger.info(f"Market {processed_market.condition_id} marked as {'approved' if approve else 'rejected'}")
    return processed_market

def test_market_fetching():
    """Test the market fetching and filtering functionality."""
    logger.info("Testing market fetching...")
    
    # Fetch markets from Polymarket API
    markets = fetch_markets()
    
    if not markets:
        logger.error("Failed to fetch any markets from API")
        return False
    
    logger.info(f"Successfully fetched {len(markets)} markets from API")
    
    # Filter active markets
    active_markets = filter_active_markets(markets)
    
    if not active_markets:
        logger.error("No active markets found after filtering")
        return False
    
    logger.info(f"Successfully filtered to {len(active_markets)} active markets")
    
    # Check category distribution
    categories = {}
    for market in active_markets:
        category = market.get("fetched_category", "general")
        categories[category] = categories.get(category, 0) + 1
    
    logger.info("Market category distribution:")
    for category, count in categories.items():
        logger.info(f"  - {category}: {count} markets")
    
    return True

def test_approval_workflow():
    """Test the market approval workflow."""
    logger.info("Testing approval workflow...")
    
    # Create some test markets
    test_markets = [create_test_market(i) for i in range(1, 4)]
    
    # Simulate approval/rejection for markets
    simulate_market_approval(test_markets[0], approve=True)  # Approve market 1
    simulate_market_approval(test_markets[1], approve=False) # Reject market 2
    # Market 3 remains pending
    
    # Run the approval check to actually create the market entries
    try:
        pending, approved, rejected = check_market_approvals()
        logger.info(f"Approval check results: {pending} pending, {approved} approved, {rejected} rejected")
        
        # Check if our test markets were detected correctly
        approved_in_db = Market.query.filter(
            Market.question.like("TEST:%"),
            Market.status.in_(["new", "deployed", "rejected"])  # Include rejected markets
        ).all()
        
        logger.info(f"Found {len(approved_in_db)} test markets in the Market table")
        for market in approved_in_db:
            logger.info(f"  - {market.id}: {market.question} (Status: {market.status})")
        
        # The test is successful if both the approved market and the rejected market
        # are properly recorded in the Market table
        # Expected: 2 entries in the Market table (1 approved, 1 rejected)
        return len(approved_in_db) == 2
    
    except Exception as e:
        logger.error(f"Error testing approval workflow: {str(e)}")
        return False

def test_pipeline_execution():
    """Test the complete pipeline execution."""
    logger.info("Testing pipeline execution...")
    
    try:
        # Create a pipeline instance
        pipeline = PolymarketPipeline()
        
        # Run the pipeline
        exit_code = pipeline.run()
        
        if exit_code == 0:
            logger.info("Pipeline executed successfully")
            
            # Check stats
            logger.info("Pipeline stats:")
            for key, value in pipeline.stats.items():
                logger.info(f"  - {key}: {value}")
            
            return True
        else:
            logger.error(f"Pipeline execution failed with exit code {exit_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error executing pipeline: {str(e)}")
        return False

def main():
    """Main function to run the tests."""
    logger.info("Starting pipeline tests")
    
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # Clean up any previous test data
        clear_test_data()
        
        # Run the tests
        fetching_success = test_market_fetching()
        approval_success = test_approval_workflow()
        pipeline_success = test_pipeline_execution()
        
        # Report results
        logger.info("\n=== TEST RESULTS ===")
        logger.info(f"Market fetching:    {'✓ PASS' if fetching_success else '✗ FAIL'}")
        logger.info(f"Approval workflow:  {'✓ PASS' if approval_success else '✗ FAIL'}")
        logger.info(f"Pipeline execution: {'✓ PASS' if pipeline_success else '✗ FAIL'}")
        logger.info("====================\n")
        
        # Final cleanup
        clear_test_data()
    
    if fetching_success and approval_success and pipeline_success:
        logger.info("All tests PASSED!")
        return 0
    else:
        logger.error("Some tests FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())