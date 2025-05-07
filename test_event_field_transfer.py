#!/usr/bin/env python3

"""
Test Event Field Transfer

This script tests the complete workflow for event fields:
1. Create a test pending market with event fields
2. Simulate approval of the pending market
3. Verify the event fields are correctly transferred to the Market table
4. Clean up the test market

This test ensures that event relationships are preserved throughout the pipeline.
"""

import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta

from main import app
from models import db, PendingMarket, Market, ApprovalLog
from check_pending_market_approvals import create_market_entry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_event_fields")

def create_test_pending_market():
    """Create a test pending market with event fields."""
    try:
        # Generate a unique test ID
        test_id = f"test-event-{int(time.time())}"
        
        # Create expiry date (30 days from now)
        expiry = int((datetime.utcnow() + timedelta(days=30)).timestamp())
        
        # Create test options
        options = json.dumps(["Yes", "No"])
        
        # Raw data
        raw_data = {
            "conditionId": test_id,
            "question": "Is this event field transfer test successful?",
            "outcomes": ["Yes", "No"],
            "category": "test",
            "endDate": datetime.utcnow().isoformat(),
            "is_multiple_option": False
        }
        
        # Create test pending market with event fields
        pending_market = PendingMarket(
            poly_id=test_id,
            question="Is this event field transfer test successful?",
            category="test",
            expiry=expiry,
            options=options,
            posted=False,
            needs_manual_categorization=False,
            raw_data=raw_data,
            event_id="test-event-group-1",
            event_name="Test Event Group"
        )
        
        db.session.add(pending_market)
        db.session.commit()
        
        logger.info(f"Created test pending market with ID: {test_id}")
        return test_id
        
    except Exception as e:
        logger.error(f"Error creating test pending market: {str(e)}")
        return None

def simulate_approval(market_id):
    """Simulate approval of a pending market."""
    try:
        pending_market = PendingMarket.query.filter_by(poly_id=market_id).first()
        
        if not pending_market:
            logger.error(f"Pending market {market_id} not found")
            return False
        
        logger.info(f"Simulating approval for pending market {market_id}")
        
        # Create approval log
        approval_log = ApprovalLog(
            poly_id=market_id,
            slack_msg_id=pending_market.slack_message_id or "test-msg-id",
            reviewer="test_script",
            decision="approved"
        )
        db.session.add(approval_log)
        
        # Create market entry
        success = create_market_entry(pending_market)
        
        if success:
            # Delete pending market after successful creation
            db.session.delete(pending_market)
            db.session.commit()
            logger.info(f"Successfully approved pending market {market_id}")
            return True
        else:
            logger.error(f"Failed to create market entry from pending market {market_id}")
            return False
        
    except Exception as e:
        logger.error(f"Error simulating approval: {str(e)}")
        return False

def verify_event_fields(market_id):
    """Verify that event fields were transferred correctly."""
    try:
        market = Market.query.filter_by(id=market_id).first()
        
        if not market:
            logger.error(f"Market {market_id} not found")
            return False
        
        logger.info(f"Checking market {market_id} for event fields:")
        
        # Check event ID
        if not market.event_id:
            logger.error(f"Market {market_id} has no event_id")
            return False
        
        logger.info(f"Market {market_id} has event_id: {market.event_id}")
        
        # Check event name
        if not market.event_name:
            logger.error(f"Market {market_id} has no event_name")
            return False
        
        logger.info(f"Market {market_id} has event_name: {market.event_name}")
        
        # Verify values are correct
        if market.event_id != "test-event-group-1":
            logger.error(f"Market {market_id} has incorrect event_id: {market.event_id}")
            return False
        
        if market.event_name != "Test Event Group":
            logger.error(f"Market {market_id} has incorrect event_name: {market.event_name}")
            return False
        
        logger.info(f"Market {market_id} has correct event fields")
        return True
        
    except Exception as e:
        logger.error(f"Error verifying event fields: {str(e)}")
        return False

def cleanup_test_market(market_id):
    """Clean up the test market."""
    try:
        market = Market.query.filter_by(id=market_id).first()
        
        if market:
            logger.info(f"Cleaning up test market {market_id}")
            db.session.delete(market)
            db.session.commit()
            logger.info(f"Deleted test market {market_id}")
            return True
        else:
            logger.warning(f"Market {market_id} not found for cleanup")
            return False
    
    except Exception as e:
        logger.error(f"Error cleaning up test market: {str(e)}")
        return False

def main():
    """Main function to run the test."""
    logger.info("Starting event field transfer test")
    
    with app.app_context():
        # Step 1: Create a test pending market
        market_id = create_test_pending_market()
        
        if not market_id:
            logger.error("Failed to create test pending market")
            return 1
        
        # Step 2: Simulate approval
        approval_success = simulate_approval(market_id)
        
        if not approval_success:
            logger.error("Failed to simulate approval")
            return 1
        
        # Step 3: Verify event fields
        verification_success = verify_event_fields(market_id)
        
        if not verification_success:
            logger.error("Event field verification failed")
            return 1
        
        # Step 4: Clean up
        cleanup_test_market(market_id)
        
        logger.info("Event field transfer test completed successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())