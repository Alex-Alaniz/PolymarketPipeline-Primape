"""
Test Option Images Processing for Multi-Option Markets

This script tests the image handling for multi-option markets like Champions League
and Europa League, ensuring each option has its own appropriate image.
"""
import json
import logging
import os
import sys
from typing import Dict, List, Any

import requests
from loguru import logger

from utils.market_transformer import MarketTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger.remove()
logger.add(sys.stdout, level="INFO")

def fetch_test_markets() -> List[Dict[str, Any]]:
    """
    Fetch a specific set of test markets that includes Champions League and Europa League.
    
    Returns:
        List of market data dictionaries from Polymarket API
    """
    logger.info("Fetching test markets from Polymarket API...")
    
    # Use these queries that are likely to have multi-option markets
    queries = [
        {"q": "Champions League Winner", "cat": "soccer"},
        {"q": "Europa League Winner", "cat": "soccer"},
        {"q": "Stanley Cup", "cat": "hockey"}
    ]
    
    all_markets = []
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    
    try:
        for query in queries:
            params = {
                "limit": 20,
                **query
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            markets = response.json()
            logger.info(f"Fetched {len(markets)} markets for query: {query['q']}")
            all_markets.extend(markets)
        
        logger.info(f"Combined total: {len(all_markets)} markets")
        return all_markets
        
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        return []

def process_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Process markets using the MarketTransformer to create multi-option markets.
    
    Args:
        markets: List of market data dictionaries from Polymarket API
        
    Returns:
        List of transformed market dictionaries
    """
    logger.info("Processing markets with MarketTransformer...")
    transformer = MarketTransformer()
    transformed_markets = transformer.transform_markets(markets)
    
    logger.info(f"Transformed {len(transformed_markets)} markets")
    return transformed_markets

def analyze_option_images(transformed_markets: List[Dict[str, Any]]):
    """
    Analyze the option images in transformed markets.
    
    Args:
        transformed_markets: List of transformed market dictionaries
    """
    logger.info("Analyzing option images in transformed markets...")
    
    # Counters for statistics
    total_multi_option_markets = 0
    total_options = 0
    options_with_event_image = 0
    options_with_unique_image = 0
    options_without_image = 0
    
    for market in transformed_markets:
        if market.get("is_multiple_option"):
            total_multi_option_markets += 1
            market_title = market.get("question")
            logger.info(f"\n{'='*40}")
            logger.info(f"MULTI-OPTION MARKET: {market_title}")
            logger.info(f"{'='*40}")
            
            # Get outcomes
            outcomes = json.loads(market.get("outcomes", "[]"))
            total_options += len(outcomes)
            
            # Get option images
            option_images = json.loads(market.get("option_images", "{}"))
            
            # Check event image
            event_image = market.get("event_image")
            if event_image:
                logger.info(f"Event banner: {event_image}")
            
            # Check for "Another team" or similar options
            another_team_options = [opt for opt in outcomes if "another" in opt.lower()]
            if another_team_options:
                logger.info(f"Found 'Another team' type options: {another_team_options}")
            
            # Analyze each option and its image
            logger.info("\nOPTIONS:")
            for i, option in enumerate(outcomes):
                image_url = option_images.get(option)
                if image_url:
                    if image_url == event_image:
                        logger.warning(f"Option {i+1}: ✗ '{option}' USES EVENT IMAGE")
                        options_with_event_image += 1
                    else:
                        logger.info(f"Option {i+1}: ✓ '{option}' has unique image")
                        options_with_unique_image += 1
                else:
                    logger.error(f"Option {i+1}: ! '{option}' has NO IMAGE")
                    options_without_image += 1
            
            logger.info("-" * 40)
    
    # Print summary statistics
    logger.info("\n\nSUMMARY STATISTICS:")
    logger.info(f"Total multi-option markets: {total_multi_option_markets}")
    logger.info(f"Total options: {total_options}")
    logger.info(f"Options with unique image: {options_with_unique_image} ({options_with_unique_image/total_options*100:.1f}%)")
    logger.info(f"Options using event image: {options_with_event_image} ({options_with_event_image/total_options*100:.1f}%)")
    logger.info(f"Options without image: {options_without_image} ({options_without_image/total_options*100:.1f}%)")

def main():
    """Main function to run the option images test"""
    logger.info("Starting option images test...")
    
    # Fetch test markets
    markets = fetch_test_markets()
    if not markets:
        logger.error("No markets found, exiting")
        return
    
    # Process markets
    transformed_markets = process_markets(markets)
    if not transformed_markets:
        logger.error("No transformed markets, exiting")
        return
    
    # Analyze option images
    analyze_option_images(transformed_markets)
    
    logger.info("Option images test completed")

if __name__ == "__main__":
    main()