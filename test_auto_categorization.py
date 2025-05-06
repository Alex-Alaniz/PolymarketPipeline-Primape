#!/usr/bin/env python3

"""
Test Auto-Categorization

This script tests the auto-categorization of markets using the GPT-4o-mini model.
It categorizes a few sample markets and prints the results.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any

from utils.market_categorizer import categorize_market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_categorization")

# Sample market questions to test categorization
SAMPLE_MARKETS = [
    "Will Bitcoin price exceed $100,000 by December 2025?",
    "Who will win the 2025 Super Bowl?",
    "Will Donald Trump win the 2024 US Presidential Election?",
    "Will Tesla stock price increase by more than 20% in 2025?",
    "Will ChatGPT have more than 500 million monthly active users by end of 2025?",
    "Will Apple release a foldable iPhone in 2025?",
    "Will Taylor Swift win a Grammy Award in 2026?",
    "Will a human set foot on Mars before 2030?",
    "Will Ethereum merge to Proof-of-Stake successfully in 2025?",
    "Will there be a recession in the United States in 2025?",
]

def test_market_categorization():
    """
    Test the categorization of sample markets.
    """
    logger.info("Testing market categorization with GPT-4o-mini")
    
    results = []
    
    for i, question in enumerate(SAMPLE_MARKETS):
        logger.info(f"Categorizing market {i+1}: {question}")
        
        # Attempt to categorize the market
        category = categorize_market(question)
        
        # Store result
        result = {
            "question": question,
            "category": category
        }
        results.append(result)
        
        logger.info(f"Market \"{question}\" categorized as: {category}")
        
    # Print summary
    logger.info("\nCategorization Results:")
    for i, result in enumerate(results):
        logger.info(f"{i+1}. \"{result['question']}\" => {result['category']}")
        
    return results

def main():
    """
    Main function to run the test.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        try:
            # Run the test
            results = test_market_categorization()
            
            # Print success message
            print(f"\nSuccessfully categorized {len(results)} sample markets")
            
            # Group by category
            categories = {}
            for result in results:
                category = result["category"] or "undefined"
                if category not in categories:
                    categories[category] = []
                categories[category].append(result["question"])
                
            # Print category breakdown
            print("\nCategory Breakdown:")
            for category, questions in categories.items():
                print(f"{category}: {len(questions)} markets")
                
            return 0
            
        except Exception as e:
            logger.error(f"Error testing categorization: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())