#!/usr/bin/env python3

"""
Filter Active Polymarket Markets

This module provides functions to filter Polymarket markets to only include
those that are currently active, non-expired, and have valid image assets.
"""

import requests
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("filter_active_markets")

def fetch_markets(limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API using the gamma API endpoint.
    Fetches a diverse set of markets across different categories.
    
    Args:
        limit: Maximum number of markets to fetch per query
        
    Returns:
        List of market data dictionaries
    """
    all_markets = []
    
    # Categories to explicitly target for diversity
    categories = [
        {"query": "politics", "count": 50},
        {"query": "sports", "count": 50},
        {"query": "crypto", "count": 30},
        {"query": "news", "count": 40},
        {"query": "tech", "count": 30}
    ]
    
    # Base parameters for all requests
    base_params = {
        "closed": "false",
        "archived": "false",
        "active": "true"
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }
    
    # First get general markets
    general_url = "https://gamma-api.polymarket.com/markets"
    params = base_params.copy()
    params["limit"] = limit
    
    logger.info(f"Fetching general markets from: {general_url}")
    
    try:
        response = requests.get(general_url, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if isinstance(data, list):
                all_markets.extend(data)
                logger.info(f"Fetched {len(data)} general markets from API")
            else:
                logger.error(f"Unexpected response format for general markets: {type(data)}")
        else:
            logger.error(f"Failed to fetch general markets: HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching general markets: {str(e)}")
    
    # Now fetch category-specific markets
    for category in categories:
        category_url = "https://gamma-api.polymarket.com/markets/search"
        params = base_params.copy()
        params["limit"] = category["count"]
        params["q"] = category["query"]
        
        logger.info(f"Fetching {category['query']} markets from: {category_url}")
        
        try:
            response = requests.get(category_url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if isinstance(data, list):
                    # Enrich with category data for better tracking
                    for market in data:
                        market["fetched_category"] = category["query"]
                    
                    all_markets.extend(data)
                    logger.info(f"Fetched {len(data)} {category['query']} markets from API")
                else:
                    logger.error(f"Unexpected response format for {category['query']} markets: {type(data)}")
            else:
                logger.error(f"Failed to fetch {category['query']} markets: HTTP {response.status_code}")
        
        except Exception as e:
            logger.error(f"Error fetching {category['query']} markets: {str(e)}")
    
    # Remove duplicates by ID
    unique_markets = {}
    for market in all_markets:
        if market.get("id") and market.get("id") not in unique_markets:
            unique_markets[market.get("id")] = market
    
    result = list(unique_markets.values())
    logger.info(f"Combined total of {len(result)} unique markets after removing duplicates")
    
    return result

def is_valid_url(url: Any) -> bool:
    """
    Check if a value is a valid URL string.
    
    Args:
        url: Value to check, can be any type
        
    Returns:
        Boolean indicating if the value is a valid URL string
    """
    # First check if the value is a string and not empty
    if not url or not isinstance(url, str):
        return False
        
    # Basic URL validation pattern
    pattern = re.compile(
        r'^(?:http|https)://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+'
        r'(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(pattern.match(url))

def filter_active_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to include only valid, currently open, and non-expired markets.
    
    Filtering criteria:
    - "closed" is false
    - "archived" is false
    - "active" is true
    - "endDate" is a valid ISO timestamp in the future
    - "image" is a non-empty string and valid URL
    - "icon" is a non-empty string and valid URL
    
    Args:
        markets: List of market data dictionaries from the Polymarket API
        
    Returns:
        Filtered list of markets meeting all criteria
    """
    now = datetime.now(timezone.utc)
    filtered_markets = []
    
    # Track filtering stats
    total_count = len(markets)
    closed_count = 0
    archived_count = 0
    inactive_count = 0
    expired_count = 0
    missing_image_count = 0
    missing_icon_count = 0
    valid_count = 0
    
    for market in markets:
        # Check if market is closed
        if market.get("closed", True):
            closed_count += 1
            continue
            
        # Check if market is archived
        if market.get("archived", True):
            archived_count += 1
            continue
            
        # Check if market is active
        if not market.get("active", False):
            inactive_count += 1
            continue
        
        # Check if endDate is valid and in the future
        end_date_str = market.get("endDate")
        if not end_date_str:
            expired_count += 1
            continue
            
        try:
            # Parse ISO timestamp, ensuring it's in UTC
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            
            # Compare with current time
            if end_date <= now:
                expired_count += 1
                continue
        except (ValueError, TypeError):
            # Invalid date format
            expired_count += 1
            continue
        
        # Check if image is valid
        image_url = market.get("image", "")
        if not image_url or not is_valid_url(image_url):
            missing_image_count += 1
            continue
            
        # Check if icon is valid
        icon_url = market.get("icon", "")
        if not icon_url or not is_valid_url(icon_url):
            missing_icon_count += 1
            continue
        
        # Market passes all filters
        filtered_markets.append(market)
        valid_count += 1
    
    # Log filtering results
    logger.info(f"Filtering results:")
    logger.info(f"  - Total markets: {total_count}")
    logger.info(f"  - Closed markets filtered out: {closed_count}")
    logger.info(f"  - Archived markets filtered out: {archived_count}")
    logger.info(f"  - Inactive markets filtered out: {inactive_count}")
    logger.info(f"  - Expired markets filtered out: {expired_count}")
    logger.info(f"  - Markets with missing/invalid image: {missing_image_count}")
    logger.info(f"  - Markets with missing/invalid icon: {missing_icon_count}")
    logger.info(f"  - Valid active markets: {valid_count}")
    
    return filtered_markets

def save_filtered_markets(markets: List[Dict[str, Any]], filename: str = "active_markets.json"):
    """
    Save filtered market data to a JSON file.
    
    Args:
        markets: List of filtered market data dictionaries
        filename: Name of the file to save to
    """
    if not markets:
        logger.warning("No valid markets to save.")
        return
    
    try:
        with open(filename, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "count": len(markets),
                "markets": markets
            }, f, indent=2)
        
        logger.info(f"Saved {len(markets)} active markets to {filename}")
    except Exception as e:
        logger.error(f"Error saving markets to file: {str(e)}")

def display_active_markets(markets: List[Dict[str, Any]], max_display: int = 5):
    """
    Display active markets in a readable format.
    
    Args:
        markets: List of filtered market data dictionaries
        max_display: Maximum number of markets to display
    """
    if not markets:
        logger.info("No active markets to display.")
        return
    
    count = min(len(markets), max_display)
    
    logger.info(f"\nSample of {count} active markets:")
    
    for i, market in enumerate(markets[:count]):
        logger.info(f"\nMarket #{i+1}:")
        logger.info(f"  Question: {market.get('question', 'N/A')}")
        logger.info(f"  ID: {market.get('id', 'N/A')}")
        logger.info(f"  Condition ID: {market.get('conditionId', 'N/A')}")
        logger.info(f"  End Date: {market.get('endDate', 'N/A')}")
        logger.info(f"  Outcomes: {market.get('outcomes', 'N/A')}")
        logger.info(f"  Current Prices: {market.get('outcomePrices', 'N/A')}")
        logger.info(f"  Image URL: {market.get('image', 'N/A')}")
        logger.info(f"  Volume: {market.get('volume', 'N/A')}")
        logger.info(f"  Description: {market.get('description', 'N/A')[:100]}..." if market.get('description') else "N/A")

def main():
    """
    Main function to run the market filtering.
    """
    logger.info("Starting active market filter")
    
    # Fetch markets from Polymarket API - using the default limit
    markets = fetch_markets()
    
    if not markets:
        logger.error("No markets fetched. Exiting.")
        return
    
    # Filter markets based on criteria
    active_markets = filter_active_markets(markets)
    
    # Save filtered markets to file
    save_filtered_markets(active_markets, "data/active_markets.json")
    
    # Display sample of active markets with category breakdown
    logger.info("\nMarket category breakdown:")
    categories = {}
    for market in active_markets:
        category = market.get("fetched_category", "general")
        categories[category] = categories.get(category, 0) + 1
    
    for category, count in categories.items():
        logger.info(f"  - {category.capitalize()}: {count} markets")
    
    # Display sample of active markets
    display_active_markets(active_markets)
    
    logger.info("\nActive market filtering complete")

if __name__ == "__main__":
    main()
