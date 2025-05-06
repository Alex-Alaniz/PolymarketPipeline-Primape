#!/usr/bin/env python3
"""
Test Market Categorization with GPT-4o-mini

Simple test script to check if market categorization is working correctly.
"""

import sys
import json
import logging

# Configure basic logging
logging.basicConfig(level=logging.INFO, 
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("categorization_test")

# Import necessary functions
from fetch_and_categorize_markets import fetch_markets
from utils.market_categorizer import categorize_markets

def main():
    """Main test function"""
    try:
        # Step 1: Fetch a few markets from Gamma API
        logger.info("Fetching sample markets from Gamma API...")
        markets = fetch_markets(limit=3)
        
        if not markets:
            logger.error("Failed to fetch markets from API")
            return 1
            
        logger.info(f"Successfully fetched {len(markets)} sample markets")
        
        # Step 2: Test categorization
        logger.info("Testing categorization with GPT-4o-mini...")
        categorized_markets = categorize_markets(markets)
        
        if not categorized_markets:
            logger.error("Failed to categorize markets")
            return 1
        
        # Print results
        logger.info("Categorization results:")
        for market in categorized_markets:
            question = market.get("question", "N/A")
            category = market.get("ai_category", "unknown")
            logger.info(f"Market: '{question}' → Category: {category}")
            
            # Check if the category is valid
            valid_categories = ["politics", "crypto", "sports", "business", "culture", "news", "tech"]
            if category not in valid_categories:
                logger.warning(f"Invalid category: {category}")
        
        # Test successful
        logger.info("✅ Categorization test completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())