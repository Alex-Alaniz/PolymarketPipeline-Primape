"""
Test the image handling for "Another Team" and similar generic options in multi-option markets.

This script:
1. Fetches markets from Polymarket API
2. Identifies multi-option markets with options like "Another Team" or "Other Team"
3. Verifies the options aren't using the event banner image after our fix
"""
import json
import logging
import os
import requests
import sys
from typing import List, Dict, Any, Optional

from utils.market_transformer import MarketTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_sports_markets() -> List[Dict[str, Any]]:
    """Fetch sports markets from Polymarket"""
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    
    # Define categories to search
    categories = ["soccer", "nba", "nfl", "mlb", "nhl", "sports"]
    
    all_markets = []
    for category in categories:
        params = {"limit": 50, "cat": category}
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            markets = response.json()
            logger.info(f"Fetched {len(markets)} {category} markets")
            all_markets.extend(markets)
            
        except Exception as e:
            logger.error(f"Error fetching {category} markets: {e}")
    
    logger.info(f"Fetched {len(all_markets)} total sports markets")
    return all_markets

def analyze_generic_options(markets: List[Dict[str, Any]]):
    """Analyze markets for generic options like 'Another Team'"""
    if not markets:
        logger.error("No markets found")
        return
    
    # Transform markets with current code
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(markets)
    
    # Find multi-option markets
    multi_option_markets = [m for m in transformed if m.get("is_multiple_option", False)]
    logger.info(f"Found {len(multi_option_markets)} multi-option markets")
    
    # Count of markets with generic options
    markets_with_generic_options = 0
    
    # Count of generic options using event banner before fix
    generic_options_count = 0
    using_event_image_count = 0
    
    # Check each multi-option market
    for market in multi_option_markets:
        # Get market details
        question = market.get("question", "")
        outcomes = json.loads(market.get("outcomes", "[]"))
        option_images = json.loads(market.get("option_images", "{}"))
        event_image = market.get("event_image")
        
        # Check for generic options
        generic_options = []
        for option in outcomes:
            if "another" in option.lower() or "other" in option.lower():
                generic_options.append(option)
        
        if generic_options:
            markets_with_generic_options += 1
            generic_options_count += len(generic_options)
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"MARKET: {question}")
            logger.info(f"{'=' * 80}")
            
            # Check each generic option
            for option in generic_options:
                image_url = option_images.get(option)
                if image_url and event_image:
                    using_event_image = (image_url == event_image)
                    if using_event_image:
                        using_event_image_count += 1
                        logger.info(f"Option '{option}': USING EVENT IMAGE (ISSUE)")
                    else:
                        logger.info(f"Option '{option}': Has unique image (FIXED)")
                else:
                    logger.info(f"Option '{option}': No image data available")
    
    # Summary
    logger.info(f"\n{'=' * 80}")
    logger.info("SUMMARY OF GENERIC OPTIONS ANALYSIS")
    logger.info(f"{'=' * 80}")
    logger.info(f"Total markets analyzed: {len(transformed)}")
    logger.info(f"Multi-option markets found: {len(multi_option_markets)}")
    logger.info(f"Markets with generic options: {markets_with_generic_options}")
    logger.info(f"Total generic options found: {generic_options_count}")
    logger.info(f"Generic options using event banner: {using_event_image_count}")
    
    # Success rate
    if generic_options_count > 0:
        success_rate = 100 * (generic_options_count - using_event_image_count) / generic_options_count
        logger.info(f"Success rate: {success_rate:.2f}% fixed (not using event banner)")
    
    logger.info(f"{'=' * 80}")

def main():
    """Main function to run the generic option test"""
    logger.info("Starting generic option image test")
    
    # Fetch sports markets
    markets = fetch_sports_markets()
    
    # Analyze generic options
    analyze_generic_options(markets)
    
    logger.info("Test completed")

if __name__ == "__main__":
    main()