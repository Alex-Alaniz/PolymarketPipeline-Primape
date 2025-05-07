#!/usr/bin/env python3

"""
Production Pipeline Runner

This script runs the complete Polymarket → Apechain pipeline in production:
1. Fetches markets from Polymarket API
2. Transforms markets into event-based format where appropriate
3. Posts new markets to Slack for approval
4. Processes market approvals from Slack
5. Deploys approved markets to Apechain
6. Updates database with deployment status

Run this script to execute the full pipeline or specific stages.
"""

import os
import sys
import json
import logging
import time
import argparse
from datetime import datetime, timedelta

# Set up Flask app context for database operations
from main import app
from models import db, Market, PendingMarket, ProcessedMarket

# Import pipeline components
from utils.transform_markets_with_events import transform_markets_with_events
from fetch_and_categorize_markets_with_events import fetch_and_categorize_markets
from post_unposted_markets import post_markets_to_slack
from check_pending_approvals import check_market_approvals
from deploy_event_markets import deploy_event_markets
from deploy_approved_markets import deploy_approved_markets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("production_pipeline")

def run_fetch_stage(args):
    """
    Run the fetch and categorize stage.
    
    Args:
        args: Command line arguments
        
    Returns:
        int: Number of markets fetched and categorized
    """
    logger.info("===== RUNNING FETCH STAGE =====")
    try:
        with app.app_context():
            # Get market count before fetch
            pending_count_before = PendingMarket.query.count()
            
            # Run fetch and categorize
            num_markets = fetch_and_categorize_markets(
                batch_size=args.batch_size, 
                post_to_slack=False  # Don't post yet, we'll do that in the next stage
            )
            
            # Get market count after fetch
            pending_count_after = PendingMarket.query.count()
            new_markets = pending_count_after - pending_count_before
            
            logger.info(f"Fetch stage complete: {new_markets} new markets added to database")
            return new_markets
    
    except Exception as e:
        logger.error(f"Error in fetch stage: {str(e)}")
        return 0

def run_post_stage(args):
    """
    Run the post to Slack stage.
    
    Args:
        args: Command line arguments
        
    Returns:
        int: Number of markets posted to Slack
    """
    logger.info("===== RUNNING POST STAGE =====")
    try:
        with app.app_context():
            # Get unposted markets count
            unposted_count = PendingMarket.query.filter_by(posted=False).count()
            logger.info(f"Found {unposted_count} unposted markets")
            
            if unposted_count == 0:
                logger.info("No markets to post, skipping stage")
                return 0
            
            # Run post stage with batch limit
            num_posted = post_markets_to_slack(batch_size=args.batch_size)
            
            logger.info(f"Post stage complete: {num_posted} markets posted to Slack")
            return num_posted
    
    except Exception as e:
        logger.error(f"Error in post stage: {str(e)}")
        return 0

def run_approval_stage(args):
    """
    Run the approval processing stage.
    
    Args:
        args: Command line arguments
        
    Returns:
        tuple: (pending, approved, rejected) counts
    """
    logger.info("===== RUNNING APPROVAL STAGE =====")
    try:
        with app.app_context():
            # Run approval check
            pending_count, approved_count, rejected_count = check_market_approvals()
            
            logger.info(f"Approval stage complete: {pending_count} pending, {approved_count} approved, {rejected_count} rejected")
            return pending_count, approved_count, rejected_count
    
    except Exception as e:
        logger.error(f"Error in approval stage: {str(e)}")
        return 0, 0, 0

def run_deployment_stage(args):
    """
    Run the deployment stage.
    
    Args:
        args: Command line arguments
        
    Returns:
        tuple: (event_markets_deployed, regular_markets_deployed)
    """
    logger.info("===== RUNNING DEPLOYMENT STAGE =====")
    try:
        # First deploy event markets
        logger.info("Deploying event markets...")
        total_events, deployed_events = deploy_event_markets()
        
        # Then deploy regular markets
        logger.info("Deploying regular markets...")
        total_markets, deployed_markets = deploy_approved_markets()
        
        logger.info(f"Deployment stage complete: {deployed_events}/{total_events} events and {deployed_markets}/{total_markets} regular markets deployed")
        return deployed_events, deployed_markets
    
    except Exception as e:
        logger.error(f"Error in deployment stage: {str(e)}")
        return 0, 0

def run_full_pipeline(args):
    """
    Run the complete pipeline from fetch to deployment.
    
    Args:
        args: Command line arguments
        
    Returns:
        dict: Pipeline statistics
    """
    logger.info("===== STARTING FULL PIPELINE =====")
    start_time = datetime.now()
    
    # Track statistics
    stats = {
        "markets_fetched": 0,
        "markets_posted": 0,
        "markets_approved": 0,
        "markets_rejected": 0,
        "events_deployed": 0,
        "markets_deployed": 0,
        "start_time": start_time,
        "end_time": None,
        "duration": None
    }
    
    try:
        # Run fetch stage
        if not args.skip_fetch:
            stats["markets_fetched"] = run_fetch_stage(args)
            logger.info(f"Fetched {stats['markets_fetched']} markets")
        else:
            logger.info("Skipping fetch stage")
        
        # Run post stage
        if not args.skip_post:
            stats["markets_posted"] = run_post_stage(args)
            logger.info(f"Posted {stats['markets_posted']} markets to Slack")
        else:
            logger.info("Skipping post stage")
        
        # Run approval stage
        if not args.skip_approval:
            _, stats["markets_approved"], stats["markets_rejected"] = run_approval_stage(args)
            logger.info(f"Processed approvals: {stats['markets_approved']} approved, {stats['markets_rejected']} rejected")
        else:
            logger.info("Skipping approval stage")
        
        # Run deployment stage
        if not args.skip_deployment:
            stats["events_deployed"], stats["markets_deployed"] = run_deployment_stage(args)
            logger.info(f"Deployed {stats['events_deployed']} events and {stats['markets_deployed']} markets")
        else:
            logger.info("Skipping deployment stage")
        
        # Calculate statistics
        stats["end_time"] = datetime.now()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        
        logger.info("===== PIPELINE COMPLETE =====")
        logger.info(f"Total run time: {stats['duration']:.2f} seconds")
        logger.info(f"Markets fetched: {stats['markets_fetched']}")
        logger.info(f"Markets posted: {stats['markets_posted']}")
        logger.info(f"Markets approved: {stats['markets_approved']}")
        logger.info(f"Markets rejected: {stats['markets_rejected']}")
        logger.info(f"Events deployed: {stats['events_deployed']}")
        logger.info(f"Markets deployed: {stats['markets_deployed']}")
        
        return stats
    
    except Exception as e:
        logger.error(f"Error in full pipeline: {str(e)}")
        stats["end_time"] = datetime.now()
        stats["duration"] = (stats["end_time"] - stats["start_time"]).total_seconds()
        return stats

def main():
    """
    Main function to parse arguments and run the pipeline.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    parser = argparse.ArgumentParser(description="Run the Polymarket-Apechain production pipeline")
    
    # Stage selection arguments
    parser.add_argument("--fetch-only", action="store_true", help="Only run the fetch stage")
    parser.add_argument("--post-only", action="store_true", help="Only run the post stage")
    parser.add_argument("--approval-only", action="store_true", help="Only run the approval stage")
    parser.add_argument("--deployment-only", action="store_true", help="Only run the deployment stage")
    
    # Stage skipping arguments
    parser.add_argument("--skip-fetch", action="store_true", help="Skip the fetch stage")
    parser.add_argument("--skip-post", action="store_true", help="Skip the post stage")
    parser.add_argument("--skip-approval", action="store_true", help="Skip the approval stage")
    parser.add_argument("--skip-deployment", action="store_true", help="Skip the deployment stage")
    
    # Other arguments
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for fetching and posting")
    
    args = parser.parse_args()
    
    try:
        # Determine which stages to run
        if args.fetch_only:
            run_fetch_stage(args)
        elif args.post_only:
            run_post_stage(args)
        elif args.approval_only:
            run_approval_stage(args)
        elif args.deployment_only:
            run_deployment_stage(args)
        else:
            # Run full pipeline
            run_full_pipeline(args)
        
        return 0
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())