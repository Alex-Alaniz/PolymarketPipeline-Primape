#!/usr/bin/env python3

"""
Test Deploy Market to Apechain

This script deploys a test market to Apechain for testing purposes.
Use this to verify that the deployment process works correctly without
waiting for the approval workflow.

Usage:
    python test_deploy_market.py [market_id]
    
If market_id is not provided, a test market will be created.
"""

import os
import sys
import logging
import json
from datetime import datetime, timedelta

from main import app
from models import db, Market
from utils.apechain import deploy_market_to_apechain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_deploy_market")

def create_test_market():
    """Create a test market for deployment."""
    # Create expiry timestamp (Unix timestamp in seconds)
    expiry_date = datetime.now() + timedelta(days=30)
    expiry_timestamp = int(expiry_date.timestamp())
    
    # Create JSON string for options
    options = json.dumps(["Yes", "No"])
    
    market = Market(
        id="test-deployment-" + datetime.now().strftime("%Y%m%d%H%M%S"),
        question="Is this test market deployment successful?",
        type="binary",
        category="test",
        options=options,
        expiry=expiry_timestamp,
        status="deployment_test",
        event_id="test-event",
        event_name="Test Event"
    )
    
    db.session.add(market)
    db.session.commit()
    
    logger.info(f"Created test market with ID: {market.id}")
    return market

def get_market(market_id):
    """Get a market by ID."""
    market = Market.query.get(market_id)
    
    if not market:
        logger.error(f"Market {market_id} not found")
        return None
    
    return market

def deploy_market(market):
    """Deploy a market to Apechain."""
    logger.info(f"Deploying market {market.id} to Apechain")
    
    market_id, tx_hash = deploy_market_to_apechain(market)
    
    if market_id and tx_hash:
        logger.info(f"Successfully deployed market {market.id} with Apechain ID {market_id}")
        logger.info(f"Transaction hash: {tx_hash}")
        return True
    elif tx_hash:
        logger.info(f"Transaction sent for market {market.id}, but market ID not yet available")
        logger.info(f"Transaction hash: {tx_hash}")
        logger.info("Run track_market_id_after_deployment.py to update the market ID")
        return True
    else:
        logger.error(f"Failed to deploy market {market.id}")
        return False

def main():
    """Main function."""
    # Check if market ID was provided as command line argument
    market_id = None
    if len(sys.argv) > 1:
        market_id = sys.argv[1]
    
    with app.app_context():
        # Get or create the market
        if market_id:
            market = get_market(market_id)
            if not market:
                return 1
        else:
            market = create_test_market()
        
        # Display market details
        logger.info(f"Market details:")
        logger.info(f"  ID: {market.id}")
        logger.info(f"  Question: {market.question}")
        logger.info(f"  Category: {market.category}")
        logger.info(f"  Expiry: {market.expiry}")
        
        # Deploy the market
        success = deploy_market(market)
        
        return 0 if success else 1

if __name__ == "__main__":
    main()