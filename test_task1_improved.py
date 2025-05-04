"""
Test script for Task 1: Slack Integration + Market Data Fetching with improved Polymarket API integration.

This script runs the task1_fetch_and_post module to test fetching Polymarket data 
and posting to Slack for initial approval, using our improved API integration.

Usage:
    python test_task1_improved.py
"""

import os
import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_task1")

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import necessary modules
from utils.messaging import MessagingClient
from transform_polymarket_data_capitalized import PolymarketTransformer
from tasks.task1_fetch_and_post import run_task, format_market_message
from config import DATA_DIR, TMP_DIR

def main():
    """Run Task 1 test with improved Polymarket API integration"""
    logger.info("Starting Task 1 test with improved Polymarket API integration")
    
    # Ensure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(TMP_DIR, exist_ok=True)
    
    try:
        # Initialize messaging client
        messaging_client = MessagingClient()
        logger.info(f"Initialized messaging client for platform: {messaging_client.platform}")
        
        # First, manually fetch markets using PolymarketTransformer
        transformer = PolymarketTransformer()
        markets = transformer.transform_markets_from_api([])  # This will fetch from CLOB API
        
        if markets:
            logger.info(f"Successfully fetched {len(markets)} markets using improved integration")
            
            # Save markets to file for inspection
            markets_file = os.path.join(TMP_DIR, "test_task1_markets.json")
            with open(markets_file, 'w') as f:
                json.dump(markets, f, indent=2)
            logger.info(f"Saved markets to {markets_file}")
            
            # Format the first market as a message to test formatting
            if len(markets) > 0:
                logger.info("Example formatted message:")
                message = format_market_message(markets[0])
                logger.info(message)
            
            # Now run the actual task
            logger.info("Running Task 1 to post markets to Slack")
            posted_markets, stats = run_task(messaging_client)
            
            # Save task results
            results_file = os.path.join(TMP_DIR, f"task1_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(results_file, 'w') as f:
                json.dump({
                    "posted_markets": posted_markets,
                    "stats": stats
                }, f, indent=2)
            
            logger.info(f"Task 1 completed with status: {stats['status']}")
            logger.info(f"Markets fetched: {stats['markets_fetched']}")
            logger.info(f"Markets posted: {stats['markets_posted']}")
            logger.info(f"Results saved to {results_file}")
            
            if stats["errors"]:
                logger.warning("Errors occurred during task execution:")
                for error in stats["errors"]:
                    logger.warning(f"  - {error}")
        else:
            logger.error("No markets fetched from Polymarket API")
    
    except Exception as e:
        logger.error(f"Error in Task 1 test: {str(e)}")
        raise

if __name__ == "__main__":
    main()