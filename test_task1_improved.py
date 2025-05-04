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
import traceback
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_task1.log')
    ]
)
logger = logging.getLogger("test_task1")

# Configure paths
DATA_DIR = os.path.join(os.getcwd(), 'data')
TMP_DIR = os.path.join(os.getcwd(), 'tmp')
LOGS_DIR = os.path.join(os.getcwd(), 'logs')

# Ensure directories exist
for directory in [DATA_DIR, TMP_DIR, LOGS_DIR]:
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Ensured directory exists: {directory}")

# Log environment information
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"Python version: {sys.version}")
logger.info(f"Python path: {sys.path}")

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
logger.info(f"Added to path: {current_dir}")

try:
    # Import necessary modules
    logger.info("Importing modules...")
    from utils.messaging import MessagingClient
    logger.info("MessagingClient imported successfully")
    from transform_polymarket_data_capitalized import PolymarketTransformer
    logger.info("PolymarketTransformer imported successfully")
    from tasks.task1_fetch_and_post import run_task, format_market_message
    logger.info("task1_fetch_and_post functions imported successfully")
    from config import DATA_DIR as CONFIG_DATA_DIR, TMP_DIR as CONFIG_TMP_DIR
    logger.info("Config variables imported successfully")
    
    # Use config dirs if defined
    if CONFIG_DATA_DIR:
        DATA_DIR = CONFIG_DATA_DIR
        logger.info(f"Using DATA_DIR from config: {DATA_DIR}")
    if CONFIG_TMP_DIR:
        TMP_DIR = CONFIG_TMP_DIR
        logger.info(f"Using TMP_DIR from config: {TMP_DIR}")
except Exception as e:
    logger.error(f"Error during imports: {str(e)}")
    logger.error(traceback.format_exc())
    sys.exit(1)

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
        
        # Need to fetch the API data first
        logger.info("Fetching data from Polymarket API...")
        from utils.polymarket import PolymarketExtractor
        
        try:
            # Initialize the extractor
            extractor = PolymarketExtractor()
            logger.info("PolymarketExtractor initialized")
            
            # Fetch raw markets from the CLOB API
            api_markets = extractor.fetch_polymarket_data()
            logger.info(f"Fetched {len(api_markets)} raw markets from Polymarket CLOB API")
            
            # Save the raw data for inspection
            raw_markets_file = os.path.join(TMP_DIR, "test_task1_raw_markets.json")
            with open(raw_markets_file, 'w') as f:
                json.dump(api_markets, f, indent=2)
            logger.info(f"Saved raw markets to {raw_markets_file}")
            
            # Transform the fetched markets
            markets = transformer.transform_markets_from_api(api_markets)
            logger.info(f"Transformed {len(markets)} markets from API data")
        except Exception as e:
            logger.error(f"Error fetching from CLOB API: {str(e)}")
            logger.error(traceback.format_exc())
            markets = []
        
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