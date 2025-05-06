#!/usr/bin/env python3

"""
End-to-End Pipeline Test

This script tests the complete Polymarket pipeline:
1. Resets the database
2. Cleans the Slack channel
3. Fetches markets from Polymarket API
4. Posts them to Slack with enhanced formatting
5. Simulates market approval by adding reactions to messages
6. Runs the market approval checker
7. Posts approved markets for deployment approval
8. Simulates deployment approval by adding reactions
9. Runs the deployment approval checker
10. Verifies deployment to Apechain
"""

import os
import sys
import time
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("e2e_test")

def reset_database():
    """Reset the database to start fresh."""
    logger.info("Resetting database...")
    
    # Import reset_db module
    import reset_db
    
    # Run the reset
    reset_db.reset_database()
    logger.info("Database reset successful")

def clean_slack_channel():
    """Clean the Slack channel."""
    logger.info("Cleaning Slack channel...")
    
    # Import clean_slack_channel module
    import clean_slack_channel
    
    # Run the cleaning
    clean_slack_channel.clean_channel()
    logger.info("Slack channel cleaned")

def fetch_and_post_markets():
    """Fetch markets from Polymarket API and post to Slack."""
    logger.info("Fetching and posting markets...")
    
    # Import fetch_active_markets_with_tracker module
    import fetch_active_markets_with_tracker
    
    # Run the fetching and posting
    fetch_active_markets_with_tracker.main()
    logger.info("Markets fetched and posted")

def get_pending_market_messages():
    """Get messages from Slack for pending markets."""
    logger.info("Getting pending market messages...")
    
    # Import Flask app and models
    from main import app
    from models import db, ProcessedMarket
    
    with app.app_context():
        # Query for markets that are posted but have no approval status
        markets = ProcessedMarket.query.filter_by(posted=True, approved=None).all()
        
        # Extract message IDs
        message_ids = [market.message_id for market in markets if market.message_id]
        
        logger.info(f"Found {len(message_ids)} pending market messages")
        return message_ids

def simulate_market_approvals(message_ids, approve_all=True):
    """Simulate market approvals by adding reactions to messages."""
    logger.info(f"Simulating {'approval' if approve_all else 'mixed approvals'} for {len(message_ids)} markets...")
    
    # Import messaging utils
    from utils.messaging import add_reaction
    
    # Process each message
    for i, message_id in enumerate(message_ids):
        if approve_all or i % 2 == 0:  # Approve all or every other market
            # Add approval reaction
            add_reaction(message_id, "white_check_mark")
            logger.info(f"Added approval reaction to message {message_id}")
        else:
            # Add rejection reaction
            add_reaction(message_id, "x")
            logger.info(f"Added rejection reaction to message {message_id}")
        
        # Sleep briefly to avoid rate limiting
        time.sleep(0.5)

def run_market_approval_check():
    """Run the market approval checker."""
    logger.info("Running market approval check...")
    
    # Import check_market_approvals module
    import check_market_approvals
    
    # Run the approval check
    with app.app_context():
        pending, approved, rejected = check_market_approvals.check_market_approvals()
        
        logger.info(f"Market approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return pending, approved, rejected

def post_for_deployment_approval():
    """Post approved markets for deployment approval."""
    logger.info("Posting markets for deployment approval...")
    
    # Import check_deployment_approvals module
    import check_deployment_approvals
    
    # Run the posting
    with app.app_context():
        markets = check_deployment_approvals.post_markets_for_deployment_approval()
        
        if markets:
            logger.info(f"Posted {len(markets)} markets for deployment approval")
            # Return market IDs and message IDs
            return [(market.id, ApprovalEvent.query.filter_by(
                market_id=market.id, 
                stage="final",
                status="pending"
            ).order_by(ApprovalEvent.created_at.desc()).first().message_id) 
                    for market in markets]
        else:
            logger.info("No markets posted for deployment approval")
            return []

def get_pending_deployment_messages():
    """Get messages from Slack for pending deployment approvals."""
    logger.info("Getting pending deployment messages...")
    
    # Import Flask app and models
    from main import app
    from models import db, Market, ApprovalEvent
    
    with app.app_context():
        # Query for approval events for markets pending deployment
        events = ApprovalEvent.query.join(Market).filter(
            Market.status == "pending_deployment",
            ApprovalEvent.stage == "final",
            ApprovalEvent.status == "pending"
        ).all()
        
        # Extract message IDs
        message_ids = [(event.market_id, event.message_id) for event in events if event.message_id]
        
        logger.info(f"Found {len(message_ids)} pending deployment messages")
        return message_ids

def simulate_deployment_approvals(message_ids, approve_all=True):
    """Simulate deployment approvals by adding reactions to messages."""
    logger.info(f"Simulating {'approval' if approve_all else 'mixed approvals'} for {len(message_ids)} deployment requests...")
    
    # Import messaging utils
    from utils.messaging import add_reaction
    
    # Process each message
    for i, (market_id, message_id) in enumerate(message_ids):
        if approve_all or i % 2 == 0:  # Approve all or every other market
            # Add approval reaction
            add_reaction(message_id, "white_check_mark")
            logger.info(f"Added approval reaction to deployment message {message_id} for market {market_id}")
        else:
            # Add rejection reaction
            add_reaction(message_id, "x")
            logger.info(f"Added rejection reaction to deployment message {message_id} for market {market_id}")
        
        # Sleep briefly to avoid rate limiting
        time.sleep(0.5)

def run_deployment_approval_check():
    """Run the deployment approval checker."""
    logger.info("Running deployment approval check...")
    
    # Import check_deployment_approvals module
    import check_deployment_approvals
    
    # Run the approval check
    with app.app_context():
        pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
        
        logger.info(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return pending, approved, rejected

def verify_deployments():
    """Verify that markets were deployed to Apechain."""
    logger.info("Verifying deployments...")
    
    # Import Flask app and models
    from main import app
    from models import db, Market
    
    with app.app_context():
        # Query for markets that should be deployed
        deployed = Market.query.filter_by(status="deployed").all()
        
        logger.info(f"Found {len(deployed)} deployed markets")
        
        for market in deployed:
            logger.info(f"Market {market.id} deployed to Apechain with ID {market.apechain_market_id}")
            logger.info(f"  - Transaction hash: {market.blockchain_tx}")
        
        return deployed

def main():
    """Run the end-to-end test."""
    logger.info("Starting end-to-end pipeline test")
    
    # Import Flask app for later use
    from main import app
    from models import db, Market, ProcessedMarket, ApprovalEvent
    
    # Clear the terminal
    os.system('clear')
    
    # Step 1: Reset the database
    reset_database()
    
    # Step 2: Clean the Slack channel
    clean_slack_channel()
    
    # Step 3: Fetch and post markets
    fetch_and_post_markets()
    
    # Step 4: Get pending market messages
    message_ids = get_pending_market_messages()
    
    if not message_ids:
        logger.error("❌ ERROR: No messages to approve")
        return
    
    # Step 5: Simulate market approvals - approve some, reject others
    simulate_market_approvals(message_ids, approve_all=False)
    
    # Step 6: Run the market approval check
    pending, approved, rejected = run_market_approval_check()
    
    if approved == 0:
        logger.error("❌ ERROR: No markets were approved")
        return
    
    # Step 7: Post for deployment approval
    deployment_messages = post_for_deployment_approval()
    
    if not deployment_messages:
        # Try getting pending deployment messages directly
        deployment_messages = get_pending_deployment_messages()
        
    if not deployment_messages:
        logger.error("❌ ERROR: No markets posted for deployment approval")
        return
    
    # Step 8: Simulate deployment approvals - approve all
    simulate_deployment_approvals(deployment_messages, approve_all=True)
    
    # Step 9: Run the deployment approval check
    d_pending, d_approved, d_rejected = run_deployment_approval_check()
    
    if d_approved == 0:
        logger.error("❌ ERROR: No markets were approved for deployment")
        return
    
    # Step 10: Verify deployments
    deployed = verify_deployments()
    
    if not deployed:
        logger.error("❌ ERROR: No markets were deployed")
        return
    
    # Success!
    logger.info("✅ SUCCESS: End-to-end pipeline test completed successfully")
    logger.info(f"  - Markets posted: {len(message_ids)}")
    logger.info(f"  - Markets approved: {approved}")
    logger.info(f"  - Markets rejected: {rejected}")
    logger.info(f"  - Markets deployed: {len(deployed)}")

if __name__ == "__main__":
    main()