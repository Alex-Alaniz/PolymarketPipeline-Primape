#!/usr/bin/env python3

"""
Run Pipeline Steps

This script allows you to run each step of the Polymarket pipeline individually:
1. Fetch and categorize markets
2. Check for pending market approvals
3. Check for image approvals
4. Check for deployment approvals
5. Sync Slack and database

This is a live test that interacts with the actual Slack workspace and database.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'pipeline_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)

# Import flask app for database context
from main import app


def run_fetch_and_categorize():
    """
    Run the market fetching and categorization step.
    This fetches markets from Polymarket API, categorizes them, and posts to Slack.
    """
    logger.info("Running market fetching and categorization...")
    
    from fetch_and_categorize_markets import main as fetch_main
    
    with app.app_context():
        result = fetch_main()
        
        if result == 0:
            logger.info("Market fetching and categorization completed successfully")
        else:
            logger.error("Market fetching and categorization failed")
            
        return result


def check_pending_approvals():
    """
    Check for pending market approvals in Slack.
    """
    logger.info("Checking for pending market approvals...")
    
    from check_pending_market_approvals import main as approval_main
    
    with app.app_context():
        result = approval_main()
        
        if result == 0:
            logger.info("Pending market approval check completed successfully")
        else:
            logger.error("Pending market approval check failed")
            
        return result


def check_image_approvals():
    """
    Check for image approvals in Slack.
    """
    logger.info("Checking for image approvals...")
    
    from check_image_approvals import main as image_main
    
    with app.app_context():
        result = image_main()
        
        if result == 0:
            logger.info("Image approval check completed successfully")
        else:
            logger.error("Image approval check failed")
            
        return result


def check_deployment_approvals():
    """
    Check for deployment approvals in Slack.
    """
    logger.info("Checking for deployment approvals...")
    
    from check_deployment_approvals import main as deployment_main
    
    with app.app_context():
        result = deployment_main()
        
        if result == 0:
            logger.info("Deployment approval check completed successfully")
        else:
            logger.error("Deployment approval check failed")
            
        return result


def sync_slack_db():
    """
    Synchronize Slack and database.
    """
    logger.info("Synchronizing Slack and database...")
    
    from sync_slack_db import main as sync_main
    
    with app.app_context():
        result = sync_main()
        
        if result == 0:
            logger.info("Slack and database synchronization completed successfully")
        else:
            logger.error("Slack and database synchronization failed")
            
        return result


def run_full_pipeline():
    """
    Run the full pipeline in sequence.
    """
    logger.info("Running full pipeline...")
    
    # Run each step in sequence
    steps = [
        ("Market Fetching", run_fetch_and_categorize),
        ("Pending Approvals", check_pending_approvals),
        ("Image Approvals", check_image_approvals),
        ("Deployment Approvals", check_deployment_approvals),
        ("Slack-DB Sync", sync_slack_db)
    ]
    
    success = True
    for step_name, step_func in steps:
        logger.info(f"Running step: {step_name}")
        result = step_func()
        if result != 0:
            logger.error(f"Step '{step_name}' failed with code {result}")
            success = False
            break
        logger.info(f"Step '{step_name}' completed successfully")
    
    if success:
        logger.info("Full pipeline completed successfully")
        return 0
    else:
        logger.error("Full pipeline failed")
        return 1


def check_environment():
    """
    Check if the environment is properly configured.
    """
    logger.info("Checking environment configuration...")
    
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_CHANNEL_ID",
        "OPENAI_API_KEY",
        "DATABASE_URL"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables before running the pipeline")
        return False
    
    logger.info("Environment is properly configured")
    return True


def main():
    """
    Main function that parses arguments and runs the appropriate steps.
    """
    parser = argparse.ArgumentParser(description="Run Polymarket pipeline steps")
    parser.add_argument("--step", choices=["fetch", "market-approvals", "image-approvals", 
                                         "deployment-approvals", "sync", "full"], 
                      help="Which pipeline step to run")
    
    args = parser.parse_args()
    
    # Check environment first
    if not check_environment():
        return 1
    
    # Run the selected step
    if args.step == "fetch":
        return run_fetch_and_categorize()
    elif args.step == "market-approvals":
        return check_pending_approvals()
    elif args.step == "image-approvals":
        return check_image_approvals()
    elif args.step == "deployment-approvals":
        return check_deployment_approvals()
    elif args.step == "sync":
        return sync_slack_db()
    elif args.step == "full":
        return run_full_pipeline()
    else:
        # If no step specified, print usage
        parser.print_help()
        logger.info("\nPlease specify which step to run using the --step argument")
        return 0


if __name__ == "__main__":
    # Use the app context
    sys.exit(main())