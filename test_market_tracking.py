#!/usr/bin/env python3

"""
Test Market Tracking Functionality

This script tests the full workflow of tracking markets after deployment:
1. Create a test market with blockchain_tx but no apechain_market_id
2. Run the market tracking script
3. Verify the market was updated with an Apechain market ID
"""

import os
import logging
import json
from datetime import datetime, timedelta

from main import app
from models import db, Market
from utils.apechain import get_deployed_market_id_from_tx
import track_market_id_after_deployment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_market_tracking")

# Mock transaction hash that will be used for testing
# This should be a real transaction hash from the blockchain that deployed a market
MOCK_TX_HASH = "0x8d55d21c98e1c3c98b9d79edc054e7ad8e55de01a445a51b1f8f154aeabbccb1"

def create_test_market():
    """Create a test market with a blockchain transaction hash but no Apechain market ID."""
    # Create expiry timestamp (Unix timestamp in seconds)
    expiry_date = datetime.now() + timedelta(days=30)
    expiry_timestamp = int(expiry_date.timestamp())
    
    # Create JSON string for options
    options = json.dumps(["Yes", "No"])
    
    market = Market(
        id="test-market-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        question="Will this test market be successfully tracked?",
        type="binary",
        category="test",
        options=options,
        expiry=expiry_timestamp,  # Unix timestamp as BigInteger
        status="pending_tracking",
        blockchain_tx=MOCK_TX_HASH,
        event_id="test-event",
        event_name="Test Event"
    )
    
    db.session.add(market)
    db.session.commit()
    
    logger.info(f"Created test market with ID: {market.id}")
    return market

def run_tracking():
    """Run the market tracking function."""
    logger.info("Running market tracking...")
    processed, updated, failed = track_market_id_after_deployment.track_deployed_markets()
    logger.info(f"Tracking results: {processed} processed, {updated} updated, {failed} failed")
    return processed, updated, failed

def verify_market_tracking(market_id):
    """Verify that the market was properly tracked and updated."""
    market = Market.query.get(market_id)
    
    if not market:
        logger.error(f"Market {market_id} not found")
        return False
    
    if not market.apechain_market_id:
        logger.error(f"Market {market_id} was not updated with an Apechain market ID")
        return False
    
    logger.info(f"Market {market_id} was successfully tracked with Apechain ID: {market.apechain_market_id}")
    return True

def cleanup_test_market(market_id):
    """Clean up the test market."""
    market = Market.query.get(market_id)
    
    if market:
        db.session.delete(market)
        db.session.commit()
        logger.info(f"Deleted test market with ID: {market_id}")

def main():
    """Main function to run the test."""
    with app.app_context():
        try:
            # Create test market
            market = create_test_market()
            
            # Run tracking
            processed, updated, failed = run_tracking()
            
            # Verify tracking
            success = verify_market_tracking(market.id)
            
            # Clean up (optional - comment out to keep the test market in the database)
            # cleanup_test_market(market.id)
            
            if success:
                logger.info("Market tracking test passed!")
                return 0
            else:
                logger.error("Market tracking test failed!")
                return 1
                
        except Exception as e:
            logger.error(f"Error in test: {str(e)}")
            return 1

if __name__ == "__main__":
    main()