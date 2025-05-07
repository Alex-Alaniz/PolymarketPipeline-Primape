#!/usr/bin/env python3
"""
Validate the fix for market categorization.

This script validates that the market categorizer correctly handles
different error conditions and doesn't default all markets to "news".
"""

import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("validate_fix")

# Import the categorizer
from utils.market_categorizer import categorize_market, categorize_markets

def test_error_handling():
    """
    Test how the categorizer handles errors.
    
    This uses mock data designed to trigger the error handling code.
    """
    logger.info("Testing categorization error handling...")
    
    # Test cases with various keywords that should trigger different categories
    test_markets = [
        {"question": "Will Joe Biden win the 2024 election?"},
        {"question": "Will Bitcoin reach $100,000 before the end of 2025?"},
        {"question": "Will the New York Yankees win the World Series?"},
        {"question": "Will Apple stock price exceed $200 in 2024?"},
        {"question": "Will there be a major news event in June?"}
    ]
    
    # Force errors in various ways
    # 1. Test individual market categorization error handling
    logger.info("Testing individual market categorization with simulated API error...")
    
    # Save original functions to restore later
    original_openai_client = None
    try:
        # Import the client
        from utils.market_categorizer import openai_client
        # Save original
        original_openai_client = openai_client
        
        # Mock failure by setting client to None (will trigger error handling)
        import utils.market_categorizer
        utils.market_categorizer.openai_client = None
        
        # Test individual categorization for each market
        for i, market in enumerate(test_markets):
            question = market["question"]
            category, needs_manual = categorize_market(question)
            logger.info(f"Market {i+1}: '{question}' → '{category}' (needs_manual: {needs_manual})")
        
        # Restore original client
        utils.market_categorizer.openai_client = original_openai_client
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        if original_openai_client:
            utils.market_categorizer.openai_client = original_openai_client
    
    # 2. Test batch categorization error handling
    logger.info("\nTesting batch categorization with simulated API error...")
    try:
        # Mock failure again
        original_openai_client = utils.market_categorizer.openai_client
        utils.market_categorizer.openai_client = None
        
        # Categorize batch
        categorized = categorize_markets(test_markets)
        
        # Display results
        logger.info("Batch categorization results:")
        category_counts = {}
        for i, market in enumerate(categorized):
            question = market.get("question", "")
            category = market.get("ai_category", "unknown")
            needs_manual = market.get("needs_manual_categorization", False)
            
            # Count category
            if category in category_counts:
                category_counts[category] += 1
            else:
                category_counts[category] = 1
                
            logger.info(f"Market {i+1}: '{question}' → '{category}' (needs_manual: {needs_manual})")
        
        # Log category distribution
        logger.info("\nCategory distribution:")
        for category, count in category_counts.items():
            percentage = count / len(categorized) * 100
            logger.info(f"  - {category}: {count} markets ({percentage:.1f}%)")
        
        # Check if all defaulted to news (the bug we're trying to fix)
        if len(category_counts) == 1 and "news" in category_counts:
            logger.error("TEST FAILED: All markets categorized as 'news' - bug still present!")
        else:
            logger.info("TEST PASSED: Markets categorized into multiple categories")
        
        # Restore original client
        utils.market_categorizer.openai_client = original_openai_client
    except Exception as e:
        logger.error(f"Error in test: {str(e)}")
        if original_openai_client:
            utils.market_categorizer.openai_client = original_openai_client

def main():
    """Main function"""
    logger.info("Validating market categorization fix...")
    test_error_handling()
    logger.info("Validation completed")

if __name__ == "__main__":
    main()