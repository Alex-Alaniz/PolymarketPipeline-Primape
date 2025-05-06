#!/usr/bin/env python3

"""
Run a full pipeline test with a test market.

This script:
1. Resets the database
2. Creates a test market
3. Posts it for approval
4. Approves it
5. Deploys it to ApeChain
6. Verifies the deployment
"""

import os
import sys
import logging
import time
import json
from datetime import datetime, timedelta
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pipeline_test")

def reset_database():
    """Reset the database to start fresh."""
    logger.info("Resetting database...")
    
    # Import reset_db module
    import reset_db
    
    # Run the reset
    success = reset_db.reset_database()
    
    if not success:
        logger.error("Failed to reset database")
        return False
    
    logger.info("Database reset successful")
    return True

def create_test_market():
    """Create a test market for deployment approval testing."""
    logger.info("Creating test market...")
    
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

def post_for_deployment():
    """Post the test market for deployment approval."""
    logger.info("Posting market for deployment approval...")
    
    # Import the deployment approval module
    from main import app
    import check_deployment_approvals
    
    with app.app_context():
        # Post for approval
        posted = check_deployment_approvals.post_markets_for_deployment_approval()
        
        if not posted:
            logger.error("No markets posted for deployment approval")
            return False
        
        logger.info(f"Posted {len(posted)} markets for deployment approval")
        return True

def simulate_approval():
    """Simulate approval of all pending deployment markets."""
    logger.info("Simulating approval...")
    
    # Import modules
    from main import app
    from models import db, Market, ApprovalEvent
    from utils.messaging import add_reaction
    
    with app.app_context():
        # Find all pending approval events
        events = ApprovalEvent.query.filter_by(
            stage="final",
            status="pending"
        ).all()
        
        if not events:
            logger.error("No pending approval events found")
            return False
        
        # Add approval reactions
        for event in events:
            market = Market.query.get(event.market_id)
            if not market:
                logger.warning(f"Market {event.market_id} not found")
                continue
                
            logger.info(f"Adding approval reaction to message {event.message_id} for market {market.id}")
            
            # Add white_check_mark reaction
            success = add_reaction(event.message_id, "white_check_mark")
            
            if success:
                logger.info(f"Successfully added approval reaction for market {market.id}")
            else:
                logger.error(f"Failed to add approval reaction for market {market.id}")
                return False
        
        return True

def process_deployments():
    """Process the deployments after approval."""
    logger.info("Processing deployments...")
    
    # Import modules
    from main import app
    import check_deployment_approvals
    
    with app.app_context():
        # Check for approvals and process deployments
        pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
        
        logger.info(f"Deployment results: {pending} pending, {approved} approved, {rejected} rejected")
        
        if approved > 0:
            return True
        else:
            return False

def verify_deployments():
    """Verify that markets were properly deployed."""
    logger.info("Verifying deployments...")
    
    # Import modules
    from main import app
    from models import db, Market
    
    with app.app_context():
        # Get all markets
        markets = Market.query.all()
        
        deployed_count = 0
        failed_count = 0
        
        for market in markets:
            logger.info(f"Market {market.id}:")
            logger.info(f"  - Status: {market.status}")
            logger.info(f"  - ApeChain ID: {market.apechain_market_id}")
            logger.info(f"  - Blockchain Tx: {market.blockchain_tx}")
            
            if market.status == "deployed" and market.apechain_market_id:
                deployed_count += 1
            elif market.status == "deployment_failed":
                failed_count += 1
        
        logger.info(f"Verification results: {deployed_count} deployed, {failed_count} failed")
        
        return deployed_count > 0

def run_pipeline_test():
    """Run a complete pipeline test."""
    logger.info("Starting pipeline test")
    
    # Reset database
    if not reset_database():
        return False
    
    # Create test market
    market_id = create_test_market()
    if not market_id:
        return False
    
    # Post for deployment
    if not post_for_deployment():
        return False
    
    # Wait for message to be posted
    logger.info("Waiting for Slack message to be processed...")
    time.sleep(2)
    
    # Simulate approval
    if not simulate_approval():
        return False
    
    # Wait for approval to be processed
    logger.info("Waiting for approval to be processed...")
    time.sleep(2)
    
    # Process deployments
    if not process_deployments():
        return False
    
    # Verify deployments
    if not verify_deployments():
        return False
    
    logger.info("Pipeline test completed successfully!")
    return True

def main():
    """Main function to run the pipeline test."""
    success = run_pipeline_test()
    
    if success:
        logger.info("🎉 Pipeline test passed!")
        return 0
    else:
        logger.error("❌ Pipeline test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())