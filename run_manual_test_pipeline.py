#!/usr/bin/env python3

"""
Manual Test Pipeline

This script runs an end-to-end test of the market deployment pipeline:
1. Fetches markets from Polymarket
2. Categorizes them using AI
3. Posts them to Slack for manual approval
4. Sets up a cron job to check for approvals/rejections
5. Processes approved markets for deployment

This script is designed for manual testing of the full pipeline.
"""

import os
import sys
import time
import logging
import json
import argparse
from datetime import datetime, timedelta

from main import app
from models import db, PendingMarket, Market, ApprovalLog
from utils.polymarket import fetch_markets
from utils.batch_categorizer import categorize_markets
from post_markets_to_slack import post_pending_markets_to_slack
from check_pending_market_approvals import check_pending_market_approvals
from check_deployment_approvals import check_deployment_approvals
from deploy_approved_markets import deploy_markets, find_markets_for_deployment
from track_market_id_after_deployment import track_deployed_markets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("pipeline_test.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("test_pipeline")

def check_slack_credentials():
    """Check if Slack credentials are configured correctly."""
    slack_token = os.environ.get('SLACK_BOT_TOKEN')
    slack_channel = os.environ.get('SLACK_CHANNEL_ID')
    
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN is not set in environment variables")
        return False
    
    if not slack_channel:
        logger.error("SLACK_CHANNEL_ID is not set in environment variables")
        return False
    
    logger.info("Slack credentials are configured")
    return True

def check_openai_credentials():
    """Check if OpenAI API key is configured correctly."""
    api_key = os.environ.get('OPENAI_API_KEY')
    
    if not api_key:
        logger.error("OPENAI_API_KEY is not set in environment variables")
        return False
    
    logger.info("OpenAI API key is configured")
    return True

def check_apechain_credentials():
    """Check if Apechain credentials are configured correctly."""
    rpc_url = os.environ.get('APECHAIN_RPC_URL')
    wallet_address = os.environ.get('WALLET_ADDRESS')
    wallet_private_key = os.environ.get('WALLET_PRIVATE_KEY')
    
    if not rpc_url:
        logger.error("APECHAIN_RPC_URL is not set in environment variables")
        return False
    
    if not wallet_address:
        logger.error("WALLET_ADDRESS is not set in environment variables")
        return False
    
    if not wallet_private_key:
        logger.error("WALLET_PRIVATE_KEY is not set in environment variables")
        return False
    
    logger.info("Apechain credentials are configured")
    return True

def fetch_and_categorize(market_count=5):
    """Fetch and categorize markets."""
    try:
        logger.info(f"Fetching up to {market_count} markets from Polymarket API")
        markets = fetch_markets(limit=market_count)
        
        if not markets:
            logger.error("Failed to fetch markets")
            return False
        
        logger.info(f"Successfully fetched {len(markets)} markets")
        
        # Categorize the markets
        logger.info("Categorizing markets...")
        categorized = categorize_markets(markets)
        
        if not categorized:
            logger.error("Failed to categorize markets")
            return False
        
        logger.info(f"Successfully categorized {len(categorized)} markets")
        
        # Create PendingMarket entries
        added = 0
        for market in categorized:
            try:
                # Check if market already exists
                existing = PendingMarket.query.filter_by(poly_id=market['id']).first()
                if existing:
                    logger.info(f"Market {market['id']} already exists in pending_markets table")
                    continue
                
                # Create options array
                options = []
                if 'outcomes' in market and market['outcomes']:
                    if isinstance(market['outcomes'], str):
                        try:
                            options = json.loads(market['outcomes'])
                        except:
                            options = ["Yes", "No"]
                    else:
                        options = market['outcomes']
                else:
                    options = ["Yes", "No"]
                
                # Parse expiry timestamp
                expiry = None
                if 'endDate' in market and market['endDate']:
                    try:
                        expiry = int(datetime.fromisoformat(
                            market['endDate'].replace("Z", "+00:00")
                        ).timestamp())
                    except Exception as e:
                        logger.error(f"Error parsing endDate: {str(e)}")
                
                # Extract event info if available
                event_id = market.get('eventId')
                event_name = market.get('eventName')
                
                # Create pending market
                pending_market = PendingMarket(
                    poly_id=market['id'],
                    question=market.get('question', ''),
                    category=market.get('category', 'news'),
                    options=json.dumps(options) if isinstance(options, list) else options,
                    expiry=expiry,
                    raw_data=market,
                    posted=False,
                    event_id=event_id,
                    event_name=event_name
                )
                
                db.session.add(pending_market)
                added += 1
                
            except Exception as e:
                logger.error(f"Error adding market {market.get('id')}: {str(e)}")
        
        db.session.commit()
        logger.info(f"Added {added} new markets to pending_markets table")
        
        return True
    
    except Exception as e:
        logger.error(f"Error in fetch_and_categorize: {str(e)}")
        return False

def post_markets_to_slack():
    """Post pending markets to Slack for approval."""
    try:
        logger.info("Posting pending markets to Slack...")
        count = post_pending_markets_to_slack()
        
        if count > 0:
            logger.info(f"Successfully posted {count} markets to Slack")
            return True
        else:
            logger.warning("No markets were posted to Slack")
            return False
    
    except Exception as e:
        logger.error(f"Error posting markets to Slack: {str(e)}")
        return False

def check_approvals():
    """Check for market approvals in Slack."""
    try:
        logger.info("Checking for market approvals in Slack...")
        pending, approved, rejected = check_pending_market_approvals()
        
        logger.info(f"Approval results: {pending} pending, {approved} approved, {rejected} rejected")
        
        if approved > 0:
            logger.info("Some markets were approved! They will be eligible for deployment")
        
        return True
    
    except Exception as e:
        logger.error(f"Error checking for approvals: {str(e)}")
        return False

def check_deployments():
    """Check for markets approved for deployment."""
    try:
        logger.info("Checking for markets approved for deployment...")
        pending, approved, rejected = check_deployment_approvals()
        
        logger.info(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
        
        if approved > 0:
            logger.info("Some markets were approved for deployment!")
        
        return True
    
    except Exception as e:
        logger.error(f"Error checking for deployment approvals: {str(e)}")
        return False

def deployment_check():
    """Check for markets that can be deployed to blockchain."""
    try:
        logger.info("Checking for markets ready for deployment...")
        markets = find_markets_for_deployment()
        
        if markets:
            logger.info(f"Found {len(markets)} markets approved for deployment")
            
            # NOTE: In this test script, we don't actually deploy to the blockchain
            # unless explicitly requested
            logger.info("In test mode: NOT deploying markets to blockchain")
            logger.info("To deploy these markets, run: python deploy_approved_markets.py")
            
            # Print market details
            for market in markets:
                logger.info(f"Market ready for deployment: {market.id} - {market.question}")
        else:
            logger.info("No markets ready for deployment")
        
        return True
    
    except Exception as e:
        logger.error(f"Error checking for deployable markets: {str(e)}")
        return False

def track_markets():
    """Track markets that have been deployed."""
    try:
        logger.info("Checking for deployed markets...")
        processed, updated, failed = track_deployed_markets()
        
        logger.info(f"Tracking results: {processed} processed, {updated} updated, {failed} failed")
        
        return True
    
    except Exception as e:
        logger.error(f"Error tracking deployed markets: {str(e)}")
        return False

def main():
    """Main function to run the test pipeline."""
    parser = argparse.ArgumentParser(description='Run the market pipeline test.')
    parser.add_argument('--count', type=int, default=5, help='Number of markets to fetch (default: 5)')
    parser.add_argument('--step', type=str, choices=['all', 'fetch', 'post', 'check', 'deploy', 'track'], 
                        default='all', help='Which step to run (default: all)')
    
    args = parser.parse_args()
    
    logger.info(f"Starting manual pipeline test, step: {args.step}")
    
    with app.app_context():
        # Check credentials
        slack_ok = check_slack_credentials()
        openai_ok = check_openai_credentials()
        apechain_ok = check_apechain_credentials()
        
        if not slack_ok or not openai_ok or not apechain_ok:
            logger.error("Missing credentials, please set the required environment variables")
            return 1
        
        # Run the pipeline
        if args.step in ['all', 'fetch']:
            success = fetch_and_categorize(args.count)
            if not success and args.step == 'fetch':
                return 1
        
        if args.step in ['all', 'post']:
            success = post_markets_to_slack()
            if not success and args.step == 'post':
                return 1
            
            logger.info("\n=== MANUAL APPROVAL REQUIRED ===")
            logger.info("Please check Slack and approve/reject markets by adding reactions:")
            logger.info("  - Use 👍 to approve a market")
            logger.info("  - Use 👎 to reject a market")
            logger.info("After you've approved/rejected markets, run this script with --step check")
        
        if args.step in ['all', 'check']:
            success = check_approvals()
            if not success and args.step == 'check':
                return 1
            
            if args.step == 'check':
                logger.info("\n=== NEXT STEPS ===")
                logger.info("To prepare markets for deployment, run:")
                logger.info("  python check_deployment_approvals.py")
                logger.info("Then approve them in Slack")
                logger.info("Then run this script with --step deploy")
        
        if args.step in ['all', 'deploy']:
            success = check_deployments()
            if not success and args.step == 'deploy':
                return 1
            
            deployment_check()
            
            if args.step == 'deploy':
                logger.info("\n=== NEXT STEPS ===")
                logger.info("If markets are ready for deployment, run:")
                logger.info("  python deploy_approved_markets.py")
                logger.info("Then run this script with --step track")
        
        if args.step in ['all', 'track']:
            success = track_markets()
            if not success and args.step == 'track':
                return 1
        
        logger.info("Manual pipeline test completed successfully")
        return 0

if __name__ == "__main__":
    sys.exit(main())