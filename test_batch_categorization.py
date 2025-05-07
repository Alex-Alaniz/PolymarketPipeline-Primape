#!/usr/bin/env python3
"""
Test the batch categorization functionality.

This script tests the batch categorizer on the sample markets from sample_markets.json.
"""

import json
import logging
import os
import sys
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_batch")

# Import the batch categorizer
from utils.batch_categorizer import batch_categorize_markets

def load_sample_markets(filename: str = "sample_markets.json") -> List[Dict[str, Any]]:
    """
    Load sample markets from the provided JSON file.
    
    Args:
        filename: Path to the sample markets JSON file
        
    Returns:
        List of market data dictionaries
    """
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading sample markets: {str(e)}")
        return []

def enhance_sample_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add necessary fields to sample markets for testing.
    
    Args:
        markets: List of raw market data dictionaries
        
    Returns:
        List of enhanced market dictionaries
    """
    enhanced_markets = []
    
    for i, market in enumerate(markets):
        enhanced = market.copy()
        
        # Add ID if not present
        if "id" not in enhanced:
            enhanced["id"] = f"sample-{i}"
            
        # Extract question and options
        enhanced["question"] = market.get("title", "")
        
        # Add to list
        enhanced_markets.append(enhanced)
    
    return enhanced_markets

def main():
    """Main function to test batch categorization"""
    logger.info("Testing batch categorization...")
    
    # Load sample markets
    logger.info("Loading sample markets from sample_markets.json...")
    raw_markets = load_sample_markets()
    if not raw_markets:
        logger.error("No sample markets found or error loading markets")
        sys.exit(1)
    
    # Enhance markets with necessary fields
    markets = enhance_sample_markets(raw_markets)
    logger.info(f"Prepared {len(markets)} sample markets for testing")
    
    # Perform batch categorization
    logger.info("Running batch categorization...")
    categorized_markets = batch_categorize_markets(markets)
    
    # Display results
    logger.info("\nCategorization results:")
    for i, market in enumerate(categorized_markets):
        question = market.get("question", "")
        category = market.get("ai_category", "unknown")
        needs_manual = market.get("needs_manual_categorization", False)
        
        logger.info(f"Market {i+1}: '{question[:50]}...' → {category} (needs_manual: {needs_manual})")
    
    # Count categories
    categories = {}
    for market in categorized_markets:
        category = market.get("ai_category")
        if category in categories:
            categories[category] += 1
        else:
            categories[category] = 1
    
    # Print distribution
    logger.info("\nCategory distribution:")
    for category, count in categories.items():
        percentage = count / len(categorized_markets) * 100
        logger.info(f"  - {category}: {count} markets ({percentage:.1f}%)")
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    main()