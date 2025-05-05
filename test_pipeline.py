#!/usr/bin/env python3

"""
Test script for the full Polymarket pipeline.

This script tests the entire pipeline flow, from fetching markets to processing approvals.
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_pipeline")

def main():
    """
    Test the full pipeline flow.
    """
    logger.info("=== Starting Pipeline Test ===")
    
    # Step 1: Test fetching markets
    logger.info("\nStep 1: Testing market fetching")
    logger.info("-" * 40)
    
    # Run filter_active_markets.py
    logger.info("Running filter_active_markets.py...")
    try:
        import filter_active_markets
        filter_active_markets.main()
        logger.info("✅ Successfully fetched and filtered active markets")
    except Exception as e:
        logger.error(f"❌ Failed to fetch active markets: {e}")
        return 1
    
    # Step 2: Test posting markets to Slack
    logger.info("\nStep 2: Testing market posting to Slack")
    logger.info("-" * 40)
    
    # Check if Slack environment variables are set
    if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_CHANNEL_ID"):
        logger.warning("⚠️ Skipping Slack tests as environment variables are not set")
        logger.warning("To test Slack integration, set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID")
    else:
        # Run fetch_active_markets_with_tracker.py
        logger.info("Running fetch_active_markets_with_tracker.py...")
        try:
            import fetch_active_markets_with_tracker
            fetch_active_markets_with_tracker.main()
            logger.info("✅ Successfully posted markets to Slack")
        except Exception as e:
            logger.error(f"❌ Failed to post markets to Slack: {e}")
            return 1
    
    # Step 3: Test checking approvals
    logger.info("\nStep 3: Testing checking market approvals")
    logger.info("-" * 40)
    
    if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_CHANNEL_ID"):
        logger.warning("⚠️ Skipping approval checks as environment variables are not set")
    else:
        # Run check_market_approvals.py
        logger.info("Running check_market_approvals.py...")
        try:
            import check_market_approvals
            check_market_approvals.main()
            logger.info("✅ Successfully checked market approvals")
        except Exception as e:
            logger.error(f"❌ Failed to check market approvals: {e}")
            return 1
    
    # Step 4: Test full pipeline
    logger.info("\nStep 4: Testing full pipeline")
    logger.info("-" * 40)
    
    # Run pipeline.py
    logger.info("Running pipeline.py...")
    try:
        from pipeline import PolymarketPipeline
        pipeline = PolymarketPipeline()
        exit_code = pipeline.run()
        
        if exit_code == 0:
            logger.info("✅ Full pipeline executed successfully")
        else:
            logger.error("❌ Pipeline failed with exit code", exit_code)
            return exit_code
            
    except Exception as e:
        logger.error(f"❌ Exception running full pipeline: {e}")
        return 1
    
    logger.info("\n=== Pipeline Test Completed Successfully ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
