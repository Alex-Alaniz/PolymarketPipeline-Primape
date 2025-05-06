#!/usr/bin/env python3

"""
Simple Test Script for Polymarket Pipeline

This script provides simple functions to test individual parts of the pipeline.
Run this script with different arguments to test different parts:

python simple_test_script.py reset - Reset database and clean slack
python simple_test_script.py fetch - Fetch and post markets to Slack
python simple_test_script.py approve - Add approval reactions to posted markets
python simple_test_script.py check - Check for approvals and process them
python simple_test_script.py deploy - Post approved markets for deployment
python simple_test_script.py deploy_approve - Add approval reactions to deployment posts
python simple_test_script.py deploy_check - Check deployment approvals and deploy
"""

import os
import sys
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_test")

def reset():
    """Reset the database and clean Slack."""
    logger.info("Resetting database...")
    import reset_db
    reset_db.reset_database()
    
    logger.info("Cleaning Slack channel...")
    import clean_slack_channel
    clean_slack_channel.clean_channel()
    
    logger.info("Reset complete")

def fetch():
    """Fetch and post markets to Slack."""
    logger.info("Fetching and posting markets...")
    import fetch_active_markets_with_tracker
    fetch_active_markets_with_tracker.main()
    
    logger.info("Markets posted to Slack")

def get_pending_messages():
    """Get pending message IDs from the database."""
    from main import app
    from models import db, ProcessedMarket
    
    with app.app_context():
        markets = ProcessedMarket.query.filter_by(posted=True, approved=None).all()
        message_ids = [market.message_id for market in markets if market.message_id]
        
        logger.info(f"Found {len(message_ids)} pending messages")
        return message_ids

def approve_markets():
    """Add approval reactions to pending markets."""
    message_ids = get_pending_messages()
    
    if not message_ids:
        logger.error("No pending messages found")
        return
    
    logger.info(f"Adding approval reactions to {len(message_ids)} messages")
    from utils.messaging import add_reaction
    
    for message_id in message_ids:
        add_reaction(message_id, "white_check_mark")
        logger.info(f"Added approval to message {message_id}")
        time.sleep(0.2)  # Avoid rate limiting
    
    logger.info("Added approval reactions to all messages")

def check_approvals():
    """Check for approvals and process them."""
    logger.info("Running market approval check...")
    from main import app
    import check_market_approvals
    
    with app.app_context():
        pending, approved, rejected = check_market_approvals.check_market_approvals()
        
        logger.info(f"Processed approvals: {pending} pending, {approved} approved, {rejected} rejected")
        return approved > 0

def post_for_deployment():
    """Post approved markets for deployment."""
    logger.info("Posting markets for deployment approval...")
    from main import app
    import check_deployment_approvals
    
    with app.app_context():
        markets = check_deployment_approvals.post_markets_for_deployment_approval()
        
        if markets:
            logger.info(f"Posted {len(markets)} markets for deployment approval")
            return True
        else:
            logger.info("No markets posted for deployment approval")
            return False

def get_pending_deployment_messages():
    """Get pending deployment message IDs from the database."""
    from main import app
    from models import db, Market, ApprovalEvent
    
    with app.app_context():
        events = ApprovalEvent.query.filter_by(stage="final", status="pending").all()
        message_ids = [event.message_id for event in events if event.message_id]
        
        logger.info(f"Found {len(message_ids)} pending deployment messages")
        return message_ids

def approve_deployments():
    """Add approval reactions to pending deployment messages."""
    message_ids = get_pending_deployment_messages()
    
    if not message_ids:
        logger.error("No pending deployment messages found")
        return
    
    logger.info(f"Adding approval reactions to {len(message_ids)} deployment messages")
    from utils.messaging import add_reaction
    
    for message_id in message_ids:
        add_reaction(message_id, "white_check_mark")
        logger.info(f"Added approval to deployment message {message_id}")
        time.sleep(0.2)  # Avoid rate limiting
    
    logger.info("Added approval reactions to all deployment messages")

def check_deployment_approvals():
    """Check for deployment approvals and deploy."""
    logger.info("Running deployment approval check...")
    from main import app
    import check_deployment_approvals
    
    with app.app_context():
        pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
        
        logger.info(f"Processed deployment approvals: {pending} pending, {approved} approved, {rejected} rejected")
        
        # Check for deployed markets
        from models import db, Market
        deployed = Market.query.filter_by(status="deployed").all()
        
        if deployed:
            logger.info(f"Successfully deployed {len(deployed)} markets to Apechain")
            for market in deployed:
                logger.info(f"  - Market {market.id} deployed with txid {market.blockchain_tx}")
        else:
            logger.warning("No markets were deployed")
        
        return approved > 0

def print_help():
    """Print help message."""
    print("""
Simple Test Script for Polymarket Pipeline

Usage:
  python simple_test_script.py <command>

Commands:
  reset         - Reset database and clean Slack
  fetch         - Fetch and post markets to Slack
  approve       - Add approval reactions to posted markets
  check         - Check for approvals and process them
  deploy        - Post approved markets for deployment
  deploy_approve - Add approval reactions to deployment posts
  deploy_check  - Check deployment approvals and deploy
  all           - Run the entire pipeline
  help          - Show this help message
""")

def run_all():
    """Run the entire pipeline."""
    print("Running entire pipeline...")
    
    # Step 1: Reset
    reset()
    
    # Step 2: Fetch and post markets
    fetch()
    
    # Step 3: Approve markets
    approve_markets()
    
    # Step 4: Check approvals
    if not check_approvals():
        logger.error("No markets were approved, stopping")
        return
    
    # Step 5: Post for deployment
    if not post_for_deployment():
        logger.error("No markets were posted for deployment, stopping")
        return
    
    # Step 6: Approve deployments
    approve_deployments()
    
    # Step 7: Check deployment approvals
    if not check_deployment_approvals():
        logger.error("No markets were deployed, stopping")
        return
    
    logger.info("✅ Pipeline completed successfully!")

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    if command == "reset":
        reset()
    elif command == "fetch":
        fetch()
    elif command == "approve":
        approve_markets()
    elif command == "check":
        check_approvals()
    elif command == "deploy":
        post_for_deployment()
    elif command == "deploy_approve":
        approve_deployments()
    elif command == "deploy_check":
        check_deployment_approvals()
    elif command == "all":
        run_all()
    elif command == "help":
        print_help()
    else:
        print(f"Unknown command: {command}")
        print_help()

if __name__ == "__main__":
    main()