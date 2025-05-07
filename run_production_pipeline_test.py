#!/usr/bin/env python3
"""
Production Pipeline Test

This script runs the full production pipeline from fetching markets to deployment:
1. Fetches markets with fallback to sample data if API is unreachable
2. Categorizes markets using efficient batch processing
3. Posts markets to Slack for approval
4. Checks for approvals and processes them
5. Deploys approved markets to Apechain

Use this script to test the entire pipeline in a production environment.
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline_test.log")
    ]
)
logger = logging.getLogger('pipeline_test')

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import models and pipeline components
from models import db, Market, PendingMarket, ProcessedMarket, PipelineRun
db.init_app(app)

def run_fetch_markets():
    """Run the fetch and categorize markets step."""
    logger.info("Step 1: Fetching and categorizing markets")
    
    try:
        # Run the fetch_with_fallback.py script (which uses sample data if API fails)
        import fetch_with_fallback
        with app.app_context():
            exit_code = fetch_with_fallback.main()
        
        if exit_code != 0:
            logger.error("Market fetch and categorization failed")
            return False
            
        logger.info("Market fetch and categorization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in market fetch step: {str(e)}")
        return False

def run_post_markets():
    """Run the post unposted markets to Slack step."""
    logger.info("Step 2: Posting markets to Slack for approval")
    
    try:
        # Run the post_unposted_pending_markets.py script
        import post_unposted_pending_markets
        with app.app_context():
            exit_code = post_unposted_pending_markets.main()
        
        if exit_code != 0:
            logger.error("Posting markets to Slack failed")
            return False
            
        logger.info("Markets posted to Slack successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in posting markets step: {str(e)}")
        return False

def run_check_approvals():
    """Run the check pending market approvals step."""
    logger.info("Step 3: Checking for market approvals in Slack")
    
    try:
        # Run the check_pending_market_approvals.py script
        import check_pending_market_approvals
        with app.app_context():
            pending, approved, rejected = check_pending_market_approvals.check_pending_market_approvals()
        
        logger.info(f"Approval check results: {pending} pending, {approved} approved, {rejected} rejected")
        return True
        
    except Exception as e:
        logger.error(f"Error in checking approvals step: {str(e)}")
        return False

def run_post_deployment_approvals():
    """Run the post markets for deployment approval step."""
    logger.info("Step 4: Posting approved markets for deployment approval")
    
    try:
        # Run the check_deployment_approvals.py script
        import check_deployment_approvals
        with app.app_context():
            check_deployment_approvals.post_markets_for_deployment_approval()
            
        logger.info("Markets posted for deployment approval")
        return True
        
    except Exception as e:
        logger.error(f"Error in posting for deployment approval: {str(e)}")
        return False

def run_check_deployment_approvals():
    """Run the check deployment approvals step."""
    logger.info("Step 5: Checking for deployment approvals in Slack")
    
    try:
        # Run the check_deployment_approvals.py script
        import check_deployment_approvals
        with app.app_context():
            pending, approved, rejected = check_deployment_approvals.check_deployment_approvals()
        
        logger.info(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return True
        
    except Exception as e:
        logger.error(f"Error in checking deployment approvals: {str(e)}")
        return False

def run_track_deployment():
    """Run the track market ID after deployment step."""
    logger.info("Step 6: Tracking market IDs after deployment")
    
    try:
        # Run the track_market_id_after_deployment.py script
        import track_market_id_after_deployment
        with app.app_context():
            exit_code = track_market_id_after_deployment.main()
        
        if exit_code != 0:
            logger.error("Tracking market IDs failed")
            return False
            
        logger.info("Market ID tracking completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error in tracking market IDs: {str(e)}")
        return False

def create_test_market():
    """Create a test market for approval flow testing."""
    logger.info("Creating test market for approval flow")
    
    with app.app_context():
        try:
            # Check if we already have pending markets
            pending_count = db.session.query(PendingMarket).filter_by(posted=False).count()
            
            if pending_count > 0:
                logger.info(f"Already have {pending_count} pending markets, skipping test market creation")
                return True
                
            # Create a test pending market
            import insert_test_pending_market
            insert_test_pending_market.insert_test_market()
            
            logger.info("Test market created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating test market: {str(e)}")
            return False

def main():
    """Main function to run the production pipeline test."""
    logger.info("Starting production pipeline test")
    
    # Create a pipeline run record
    with app.app_context():
        try:
            pipeline_run = PipelineRun(
                start_time=datetime.utcnow(),
                status="running"
            )
            db.session.add(pipeline_run)
            db.session.commit()
            logger.info(f"Created pipeline run record with ID {pipeline_run.id}")
        except Exception as e:
            logger.error(f"Error creating pipeline run: {str(e)}")
            return 1
    
    # For testing purposes, let's create a test market first
    create_test_market()
    
    # Run each step of the pipeline
    success = True
    
    # Step 1: Fetch and categorize markets
    if success:
        success = run_fetch_markets()
        
    # Step 2: Post markets to Slack for approval
    if success:
        success = run_post_markets()
        
    # Step The following steps require manual action in Slack:
    if success:
        logger.info("\n----- MANUAL ACTION REQUIRED -----")
        logger.info("1. Check Slack and approve/reject markets")
        logger.info("2. Add 👍 reaction to approve a market")
        logger.info("3. Add 👎 reaction to reject a market")
        logger.info("4. Wait for the next pipeline steps to process approvals")
        logger.info("-----------------------------\n")
        
        # Allow time for manual approval
        user_input = input("Have you approved/rejected markets in Slack? (yes/no): ")
        if user_input.lower() != 'yes':
            logger.warning("Manual approval not confirmed, continuing anyway but pipeline may not complete")
    
    # Step 3: Check for approvals
    if success:
        success = run_check_approvals()
        
    # Step 4: Post for deployment approvals
    if success:
        success = run_post_deployment_approvals()
        
    # Step 5: Another manual step for deployment approvals
    if success:
        logger.info("\n----- MANUAL ACTION REQUIRED -----")
        logger.info("1. Check Slack and approve/reject markets for deployment")
        logger.info("2. Add 👍 reaction to approve deployment")
        logger.info("3. Add 👎 reaction to reject deployment")
        logger.info("4. Wait for the final pipeline steps")
        logger.info("-----------------------------\n")
        
        # Allow time for manual deployment approval
        user_input = input("Have you approved/rejected deployments in Slack? (yes/no): ")
        if user_input.lower() != 'yes':
            logger.warning("Manual deployment approval not confirmed, continuing anyway but pipeline may not complete")
    
    # Step 6: Check deployment approvals
    if success:
        success = run_check_deployment_approvals()
        
    # Step 7: Track market IDs after deployment
    if success:
        success = run_track_deployment()
    
    # Update pipeline run record
    with app.app_context():
        try:
            pipeline_run.end_time = datetime.utcnow()
            pipeline_run.status = "completed" if success else "failed"
            db.session.commit()
            logger.info(f"Updated pipeline run {pipeline_run.id} status to {pipeline_run.status}")
        except Exception as e:
            logger.error(f"Error updating pipeline run: {str(e)}")
    
    # Log final status
    if success:
        logger.info("Production pipeline test completed successfully")
        return 0
    else:
        logger.error("Production pipeline test failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())