"""
Test specific problematic markets for image handling

This script tests specific markets that are known to have issues with option images:
1. Europa League Winner - "Another Team" option using event banner
2. Champions League - Barcelona option using event banner
"""
import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional

import requests

from utils.market_transformer import MarketTransformer

# Create a logger
logger = logging.getLogger("test_specific_markets")

# Setup logging
logging.basicConfig(level=logging.INFO)

def fetch_specific_markets() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch specific markets that we know have issues.
    
    Returns:
        Dictionary with market type as key and list of markets as value
    """
    logger.info("Fetching specific problematic markets...")
    
    # Market queries
    queries = [
        {"name": "europa_league", "q": "Europa League", "cat": "soccer"},
        {"name": "champions_league", "q": "Champions League", "cat": "soccer"},
        {"name": "premier_league", "q": "EPL", "cat": "soccer"}
    ]
    
    results = {}
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    
    for query in queries:
        params = {
            "limit": 30,
            "q": query["q"],
            "cat": query["cat"]
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            markets = response.json()
            logger.info(f"Fetched {len(markets)} markets for query: {query['q']}")
            results[query["name"]] = markets
            
        except Exception as e:
            logger.error(f"Error fetching markets for {query['q']}: {str(e)}")
            results[query["name"]] = []
    
    return results

def analyze_market_in_detail(markets: List[Dict[str, Any]], market_name: str) -> Optional[Dict[str, Any]]:
    """
    Transform and analyze a specific market in detail.
    
    Args:
        markets: List of market data dictionaries
        market_name: Name of the market to focus on
        
    Returns:
        Transformed market data if found, None otherwise
    """
    if not markets:
        logger.error(f"No markets provided for {market_name}")
        return None
    
    logger.info(f"Analyzing {len(markets)} {market_name} markets")
    
    # Transform markets
    transformer = MarketTransformer()
    transformed_markets = transformer.transform_markets(markets)
    
    # Find the specific multi-option market
    target_market = None
    for market in transformed_markets:
        if market.get("is_multiple_option") and market_name.lower() in market.get("question", "").lower():
            target_market = market
            break
    
    if not target_market:
        logger.error(f"No multi-option {market_name} market found")
        return None
    
    logger.info(f"Found {market_name} multi-option market: {target_market.get('question')}")
    
    # Detailed analysis of the market
    analyze_market_options(target_market)
    
    return target_market

def analyze_market_options(market: Dict[str, Any]):
    """
    Analyze the options and their images in a multi-option market.
    
    Args:
        market: Transformed market data dictionary
    """
    logger.info(f"MARKET: {market.get('question')}")
    logger.info(f"ID: {market.get('id')}")
    
    # Get outcomes
    outcomes = json.loads(market.get("outcomes", "[]"))
    logger.info(f"Options ({len(outcomes)}): {outcomes}")
    
    # Get option images
    option_images = json.loads(market.get("option_images", "{}"))
    
    # Check event image
    event_image = market.get("event_image")
    logger.info(f"Event image: {event_image}")
    
    # Original market IDs
    original_ids = market.get("original_market_ids", [])
    logger.info(f"Original market IDs ({len(original_ids)}): {original_ids}")
    
    # Analyze each option and its image
    logger.info("\nOPTION DETAILS:")
    for i, option in enumerate(outcomes):
        image_url = option_images.get(option)
        if image_url:
            using_event_image = (image_url == event_image)
            status = "🚫 USING EVENT IMAGE" if using_event_image else "✅ Has unique image"
            logger.info(f"Option {i+1}: {option}")
            logger.info(f"  - Image: {image_url}")
            logger.info(f"  - Status: {status}")
        else:
            logger.info(f"Option {i+1}: {option}")
            logger.info(f"  - Image: None")
            logger.info(f"  - Status: ❌ NO IMAGE")
        logger.info("---")

# Removed Slack posting functionality to simplify testing

def main():
    """Main function to run the targeted market testing"""
    logger.info("Starting specific market test...")
    
    # Fetch markets
    markets_by_type = fetch_specific_markets()
    
    # Analyze Europa League
    europa_market = analyze_market_in_detail(markets_by_type.get("europa_league", []), "Europa League")
    
    # Analyze Champions League
    champions_market = analyze_market_in_detail(markets_by_type.get("champions_league", []), "Champions League")
    
    # Analyze Premier League
    premier_market = analyze_market_in_detail(markets_by_type.get("premier_league", []), "EPL Top Goalscorer")
    
    # We'll focus on analysis only, not posting to Slack
    
    logger.info("Specific market test completed")

if __name__ == "__main__":
    main()