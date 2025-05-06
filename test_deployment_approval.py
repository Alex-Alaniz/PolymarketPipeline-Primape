#!/usr/bin/env python3

"""
Test the deployment approval process for ApeChain integration.

This script posts test markets for deployment approval and checks
if the deployment process works correctly with the ApeChain integration.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import time
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_deployment")

def create_test_market():
    """Create a test market for deployment approval testing."""
    # Import Flask app to get application context
    from main import app
    from models import db, Market, ProcessedMarket, ApprovalEvent
    
    # Generate a unique ID for the test market
    market_id = f"test-market-{uuid.uuid4()}"
    
    # Calculate expiry date (30 days from now)
    expiry = datetime.utcnow() + timedelta(days=30)
    
    with app.app_context():
        # Create a test market
        market = Market(
            id=market_id,
            question="Test Market: Will this deploy successfully to ApeChain?",
            type="binary",
            category="Test",
            sub_category="Deployment",
            expiry=int(expiry.timestamp()),
            options=["Yes", "No"],
            status="new",  # New status means approved but not yet deployed
            banner_uri="https://example.com/test-banner.jpg",
            icon_url="https://example.com/test-icon.png"
        )
        
        # Save to database
        db.session.add(market)
        db.session.commit()
        
        logger.info(f"Created test market with ID: {market_id}")
        return market_id

def run_deployment_approval():
    """Run the deployment approval process for test markets."""
    # Import modules
    from main import app
    import check_deployment_approvals
    
    with app.app_context():
        # First post markets for deployment approval
        posted = check_deployment_approvals.post_markets_for_deployment_approval()
        logger.info(f"Posted {len(posted)} markets for deployment approval")
        
        # Return posted market IDs
        return [market.id for market in posted]

def simulate_approval(market_id):
    """Simulate an approval reaction on the deployment message."""
    # Import modules
    from main import app
    from models import db, ApprovalEvent
    from utils.messaging import add_reaction, get_message_reactions
    
    with app.app_context():
        # Find the approval event
        event = ApprovalEvent.query.filter_by(
            market_id=market_id,
            stage="final",
            status="pending"
        ).first()
        
        if not event:
            logger.error(f"No pending approval event found for market {market_id}")
            return False
        
        # Add approval reaction
        logger.info(f"Adding approval reaction to message {event.message_id}")
        
        # Add white_check_mark reaction
        success = add_reaction(event.message_id, "white_check_mark")
        
        if success:
            logger.info(f"Successfully added approval reaction for market {market_id}")
        else:
            logger.error(f"Failed to add approval reaction for market {market_id}")
            
        return success

def check_deployment_result(market_id):
    """Check if the market was successfully deployed to ApeChain."""
    # Import modules
    from main import app
    from models import db, Market
    
    with app.app_context():
        # Find the market
        market = Market.query.get(market_id)
        
        if not market:
            logger.error(f"Market {market_id} not found")
            return None
        
        logger.info(f"Market status: {market.status}")
        logger.info(f"ApeChain market ID: {market.apechain_market_id}")
        logger.info(f"Blockchain transaction: {market.blockchain_tx}")
        
        result = {
            "status": market.status,
            "apechain_market_id": market.apechain_market_id,
            "blockchain_tx": market.blockchain_tx
        }
        
        return result

def run_deployment_test():
    """Run a complete deployment test."""
    try:
        logger.info("Starting deployment approval test")
        
        # Create test market
        market_id = create_test_market()
        logger.info(f"Created test market: {market_id}")
        
        # Post for deployment approval
        posted_ids = run_deployment_approval()
        logger.info(f"Posted markets: {posted_ids}")
        
        if market_id not in posted_ids:
            logger.error(f"Test market {market_id} was not posted for deployment approval")
            return False
        
        # Give a moment for the message to be posted to Slack
        logger.info("Waiting for Slack message to be processed...")
        time.sleep(2)
        
        # Simulate approval
        success = simulate_approval(market_id)
        if not success:
            logger.error("Failed to simulate approval")
            return False
        
        # Wait for deployment to complete
        logger.info("Waiting for deployment to process...")
        time.sleep(5)
        
        # Run the approval check
        from main import app
        import check_deployment_approvals
        
        with app.app_context():
            pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
            logger.info(f"Deployment results: {pending} pending, {approved} approved, {rejected} rejected")
        
        # Check results
        result = check_deployment_result(market_id)
        logger.info(f"Deployment result: {result}")
        
        if result and result.get("status") == "deployed" and result.get("apechain_market_id"):
            logger.info("Deployment test PASSED!")
            return True
        else:
            logger.error("Deployment test FAILED")
            return False
        
    except Exception as e:
        logger.error(f"Test failed with exception: {str(e)}")
        return False

def main():
    """Main function to run the deployment test."""
    # Run the deployment test
    success = run_deployment_test()
    
    # Log result
    if success:
        logger.info("🎉 Deployment test completed successfully")
        return 0
    else:
        logger.error("❌ Deployment test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())