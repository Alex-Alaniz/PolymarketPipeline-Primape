#!/usr/bin/env python3
"""
Test script for the Polymarket CLOB API integration.

This script tests the integration with the Polymarket CLOB API,
validating that we can fetch and transform market data correctly.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("clob_integration")

# Add the current directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the necessary modules
from utils.polymarket import PolymarketExtractor
from transform_polymarket_data_capitalized import PolymarketTransformer

def main():
    """Test the Polymarket CLOB API integration"""
    
    logger.info("Starting CLOB API integration test")
    
    # Step 1: Fetch data from Polymarket CLOB API
    logger.info("Step 1: Fetching data from Polymarket CLOB API")
    extractor = PolymarketExtractor()
    
    try:
        markets = extractor.fetch_polymarket_data()
        if markets and len(markets) > 0:
            logger.info(f"Successfully fetched {len(markets)} markets from Polymarket CLOB API")
            
            # Save the first 5 markets for inspection
            sample_path = os.path.join("data", "sample_clob_markets.json")
            os.makedirs(os.path.dirname(sample_path), exist_ok=True)
            with open(sample_path, 'w') as f:
                json.dump(markets[:5], f, indent=2)
            logger.info(f"Saved 5 sample markets to {sample_path}")
            
            # Log a sample market for immediate inspection
            logger.info("Sample market from CLOB API:")
            logger.info(json.dumps(markets[0], indent=2))
        else:
            logger.error("Failed to fetch markets from Polymarket CLOB API")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        sys.exit(1)
    
    # Step 2: Transform the fetched markets
    logger.info("Step 2: Transforming markets from CLOB API")
    transformer = PolymarketTransformer()
    
    try:
        transformed_markets = transformer.transform_markets_from_api(markets)
        if transformed_markets and len(transformed_markets) > 0:
            logger.info(f"Successfully transformed {len(transformed_markets)} markets from CLOB API")
            
            # Save the transformed markets for inspection
            transformed_path = os.path.join("data", "transformed_clob_markets.json")
            with open(transformed_path, 'w') as f:
                json.dump(transformed_markets, f, indent=2)
            logger.info(f"Saved transformed markets to {transformed_path}")
            
            # Log a sample transformed market
            logger.info("Sample transformed market:")
            logger.info(json.dumps(transformed_markets[0], indent=2))
        else:
            logger.error("Failed to transform markets from CLOB API")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Error transforming markets: {str(e)}")
        sys.exit(1)
    
    # Test complete
    logger.info("CLOB API integration test completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())