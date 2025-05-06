#!/usr/bin/env python3
"""
Test Fetching Markets from Gamma API

Simple test script to check if we can fetch markets from the new Gamma API.
"""

import sys
import json
import logging
from datetime import datetime

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("gamma_api_test")

# Import necessary functions
from fetch_and_categorize_markets import fetch_markets, filter_active_non_expired_markets

def main():
    """Main test function"""
    try:
        # Step 1: Fetch markets from Gamma API
        logger.info("Fetching markets from Gamma API...")
        markets = fetch_markets(limit=5)
        
        if not markets:
            logger.error("Failed to fetch markets from API")
            return 1
            
        logger.info(f"Successfully fetched {len(markets)} markets from Gamma API")
        
        # Print the first market as sample
        first_market = markets[0]
        logger.info(f"Sample market question: {first_market.get('question', 'N/A')}")
        logger.info(f"Sample market ID: {first_market.get('id', 'N/A')}")
        logger.info(f"Sample market conditionId: {first_market.get('conditionId', 'N/A')}")
        
        # Step 2: Filter markets
        active_markets = filter_active_non_expired_markets(markets)
        logger.info(f"Filtered to {len(active_markets)} active, non-expired markets")
        
        # Test successful
        logger.info("✅ API test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())