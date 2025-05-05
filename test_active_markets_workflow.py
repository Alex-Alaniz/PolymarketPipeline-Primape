#!/usr/bin/env python3

"""
Test script for the active market workflow.

This script demonstrates the workflow of fetching, filtering, and selecting
active markets across diverse categories from Polymarket API.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone

from filter_active_markets import fetch_markets, filter_active_markets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("test_active_markets")

def test_market_diversity():
    """Test the diversity of markets being fetched."""
    logger.info("Testing market diversity...")
    
    # Fetch markets
    markets = fetch_markets()
    
    if not markets:
        logger.error("Failed to fetch markets")
        return False
    
    # Count markets by category before filtering
    pre_categories = {}
    for market in markets:
        category = market.get("fetched_category", "general")
        pre_categories[category] = pre_categories.get(category, 0) + 1
    
    logger.info(f"Fetched {len(markets)} total markets")
    logger.info("Category distribution before filtering:")
    for category, count in pre_categories.items():
        logger.info(f"  - {category}: {count} markets")
    
    # Filter active markets
    active_markets = filter_active_markets(markets)
    
    if not active_markets:
        logger.error("No active markets found after filtering")
        return False
    
    # Count markets by category after filtering
    post_categories = {}
    for market in active_markets:
        category = market.get("fetched_category", "general")
        post_categories[category] = post_categories.get(category, 0) + 1
    
    logger.info(f"Filtered to {len(active_markets)} active markets")
    logger.info("Category distribution after filtering:")
    for category, count in post_categories.items():
        logger.info(f"  - {category}: {count} markets")
    
    # Check icon and image URLs
    valid_image_urls = 0
    valid_icon_urls = 0
    
    for market in active_markets:
        if market.get("image") and isinstance(market.get("image"), str):
            valid_image_urls += 1
        if market.get("icon") and isinstance(market.get("icon"), str):
            valid_icon_urls += 1
    
    logger.info(f"Image URLs: {valid_image_urls}/{len(active_markets)} markets have valid image URLs")
    logger.info(f"Icon URLs: {valid_icon_urls}/{len(active_markets)} markets have valid icon URLs")
    
    # Check expiry dates
    now = datetime.now(timezone.utc)
    future_expiry = 0
    
    for market in active_markets:
        try:
            end_date = datetime.fromisoformat(market.get("endDate", "").replace('Z', '+00:00'))
            if end_date > now:
                future_expiry += 1
        except:
            pass
    
    logger.info(f"Expiry dates: {future_expiry}/{len(active_markets)} markets have future expiry dates")
    
    # Check diversity criterion (at least 3 different categories with at least 10 markets each)
    categories_with_min_10 = sum(1 for count in post_categories.values() if count >= 10)
    logger.info(f"Diversity: {categories_with_min_10} categories have at least 10 markets")
    
    diversity_success = categories_with_min_10 >= 3
    image_success = valid_image_urls == len(active_markets)
    icon_success = valid_icon_urls == len(active_markets)
    future_success = future_expiry == len(active_markets)
    
    return diversity_success and image_success and icon_success and future_success

def display_sample_markets(markets, count=5):
    """Display a sample of markets."""
    if not markets or count <= 0:
        return
    
    sample = markets[:count]
    logger.info(f"\nSample of {len(sample)} active markets:")
    
    for i, market in enumerate(sample):
        logger.info(f"\nMarket #{i+1}:")
        logger.info(f"  Category: {market.get('fetched_category', 'general')}")
        logger.info(f"  Question: {market.get('question', 'N/A')}")
        logger.info(f"  End Date: {market.get('endDate', 'N/A')}")
        logger.info(f"  Image: {market.get('image', 'N/A')}")
        logger.info(f"  Icon: {market.get('icon', 'N/A')}")

def main():
    """Main function to run the tests."""
    logger.info("Starting active markets workflow test")
    
    # Test market diversity
    diversity_success = test_market_diversity()
    
    # Fetch and display a sample of markets
    markets = fetch_markets()
    active_markets = filter_active_markets(markets) if markets else []
    display_sample_markets(active_markets)
    
    # Report results
    logger.info("\n=== TEST RESULTS ===")
    logger.info(f"Market diversity: {'✓ PASS' if diversity_success else '✗ FAIL'}")
    logger.info("====================\n")
    
    if diversity_success:
        logger.info("Active markets workflow test PASSED!")
        return 0
    else:
        logger.error("Active markets workflow test FAILED!")
        return 1

if __name__ == "__main__":
    sys.exit(main())