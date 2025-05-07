#!/usr/bin/env python3

"""
Test Full Deployment Pipeline

This script tests the entire market deployment pipeline:
1. Create a test market with event fields
2. Set its status to 'deployment_approved'
3. Run the deployment script
4. Verify the blockchain transaction and market ID are recorded

It serves as an end-to-end test of the deployment workflow.
"""

import os
import sys
import time
import logging
import json
import uuid
from datetime import datetime, timedelta

from main import app
from models import db, Market
import deploy_approved_markets
import track_market_id_after_deployment
from utils.apechain import get_market_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_deployment_pipeline")

def create_test_market():
    """Create a test market with approval for deployment."""
    try:
        # Generate a unique test ID
        test_id = f"test-full-deployment-{int(time.time())}"
        
        # Create expiry date (30 days from now)
        expiry = int((datetime.utcnow() + timedelta(days=30)).timestamp())
        
        # Create test options
        options = json.dumps(["Yes", "No"])
        
        # Create test market with event fields
        market = Market(
            id=test_id,
            question="Is this full deployment pipeline test successful?",
            category="test",
            expiry=expiry,
            options=options,
            status="deployment_approved",  # Set status for deployment
            event_id="test-event-1",
            event_name="Test Pipeline Event"
        )
        
        db.session.add(market)
        db.session.commit()
        
        logger.info(f"Created test market with ID: {test_id}")
        return test_id
        
    except Exception as e:
        logger.error(f"Error creating test market: {str(e)}")
        return None

def run_deployment_pipeline(market_id):
    """Run the deployment pipeline."""
    try:
        logger.info("Running deployment pipeline...")
        result = deploy_approved_markets.main()
        logger.info(f"Deployment result: {result}")
        
        return result == 0
    except Exception as e:
        logger.error(f"Error running deployment pipeline: {str(e)}")
        return False

def run_tracking_pipeline():
    """Run the market tracking pipeline."""
    try:
        logger.info("Running tracking pipeline...")
        result = track_market_id_after_deployment.main()
        logger.info(f"Tracking result: {result}")
        
        return result == 0
    except Exception as e:
        logger.error(f"Error running tracking pipeline: {str(e)}")
        return False

def verify_market_deployment(market_id):
    """Verify that the market was deployed successfully."""
    try:
        # Get market from database
        market = Market.query.filter_by(id=market_id).first()
        
        if not market:
            logger.error(f"Market {market_id} not found in database")
            return False
        
        # Check if transaction hash exists
        if not market.blockchain_tx:
            logger.error(f"Market {market_id} has no blockchain transaction hash")
            return False
        
        logger.info(f"Market {market_id} has transaction hash: {market.blockchain_tx}")
        
        # Check if Apechain market ID exists
        if not market.apechain_market_id:
            logger.warning(f"Market {market_id} has no Apechain market ID yet")
            return False
        
        logger.info(f"Market {market_id} has Apechain ID: {market.apechain_market_id}")
        
        # Verify status is deployed
        if market.status != "deployed":
            logger.warning(f"Market {market_id} has status '{market.status}', expected 'deployed'")
            return False
        
        logger.info(f"Market {market_id} has correct status: {market.status}")
        
        # Verify event fields
        if not market.event_id or not market.event_name:
            logger.warning(f"Market {market_id} is missing event fields")
            return False
        
        logger.info(f"Market {market_id} has event ID: {market.event_id}")
        logger.info(f"Market {market_id} has event name: {market.event_name}")
        
        # Try to get market info from blockchain
        if market.apechain_market_id:
            market_info = get_market_info(market.apechain_market_id)
            if market_info:
                logger.info(f"Successfully retrieved market info from blockchain: {market_info}")
            else:
                logger.warning(f"Could not retrieve market info from blockchain for ID {market.apechain_market_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error verifying market deployment: {str(e)}")
        return False

def cleanup_test_market(market_id):
    """Clean up the test market (optional - usually we want to keep it for record)."""
    try:
        # NOTE: In production, we should NEVER delete deployed markets as they represent 
        # real assets on the blockchain. Only use this in testing with non-mainnet deployments.
        market = Market.query.filter_by(id=market_id).first()
        
        if market:
            # For test markets, we can delete them after testing
            # But only if they haven't been deployed to the real blockchain
            if market.blockchain_tx and market.blockchain_tx != "0x8d55d21c98e1c3c98b9d79edc054e7ad8e55de01a445a51b1f8f154aeabbccb1":
                logger.warning(f"Not deleting market {market_id} as it has a real blockchain transaction")
                return False
            
            # This is a test market with a test transaction, safe to delete
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
    logger.info("Starting full deployment pipeline test")
    
    with app.app_context():
        # Step 1: Create a test market
        market_id = create_test_market()
        
        if not market_id:
            logger.error("Failed to create test market")
            return 1
        
        # Step 2: Run the deployment pipeline
        deployment_success = run_deployment_pipeline(market_id)
        
        if not deployment_success:
            logger.error("Deployment pipeline failed")
            return 1
        
        # Step 3: Run the tracking pipeline
        tracking_success = run_tracking_pipeline()
        
        if not tracking_success:
            logger.error("Tracking pipeline failed")
            return 1
        
        # Step 4: Verify deployment
        verification_success = verify_market_deployment(market_id)
        
        if not verification_success:
            logger.error("Deployment verification failed")
            return 1
        
        # Step 5: Clean up (if desired)
        # Uncomment to clean up test markets (not recommended for production)
        # cleanup_test_market(market_id)
        
        logger.info("Full deployment pipeline test completed successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())