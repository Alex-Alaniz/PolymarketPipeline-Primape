#!/usr/bin/env python3

"""
Filter Active Polymarket Markets

This module provides functions to filter Polymarket markets to only include
those that are currently active, non-expired, and have valid image assets.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("filter_markets")

# Categories to fetch markets from
CATEGORIES = {
    "politics": 50,
    "sports": 50,
    "crypto": 30,
    "entertainment": 40,
    "science": 30
}

def fetch_markets(limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API using the gamma API endpoint.
    Fetches a diverse set of markets across different categories.
    
    Args:
        limit: Maximum number of markets to fetch per query
        
    Returns:
        List of market data dictionaries
    """
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets"
    
    # Base parameters
    params = {
        "closed": "false",
        "archived": "false",
        "active": "true",
        "limit": str(limit)
    }
    
    all_markets = []
    
    # Fetch markets for each category
    for category, count in CATEGORIES.items():
        try:
            category_params = params.copy()
            category_params["category"] = category
            category_params["limit"] = str(count)
            
            logger.info(f"Fetching {count} {category} markets from Polymarket API")
            
            response = requests.get(base_url, params=category_params)
            
            if response.status_code == 200:
                category_markets = response.json()
                
                # Add category tag to raw data for tracking
                for market in category_markets:
                    market["fetched_category"] = category
                
                all_markets.extend(category_markets)
                
                logger.info(f"Successfully fetched {len(category_markets)} {category} markets")
            else:
                logger.error(f"Failed to fetch {category} markets: Status {response.status_code}")
                logger.error(f"Response: {response.text}")
                
        except Exception as e:
            logger.error(f"Error fetching {category} markets: {str(e)}")
    
    logger.info(f"Fetched a total of {len(all_markets)} markets across all categories")
    
    # Generate simplified market representation for debugging
    simplified = [
        {
            "id": market.get("id"),
            "conditionId": market.get("conditionId"),
            "question": market.get("question"),
            "endDate": market.get("endDate"),
            "category": market.get("fetched_category"),
            "closed": market.get("closed"),
            "archived": market.get("archived"),
            "active": market.get("active")
        }
        for market in all_markets
    ]
    
    # Save to JSON for debugging if needed
    # with open("fetched_markets.json", "w") as f:
    #    json.dump(simplified, f, indent=2)
    
    return all_markets

def is_valid_url(url: Any) -> bool:
    """
    Check if a value is a valid URL string.
    
    Args:
        url: Value to check, can be any type
        
    Returns:
        Boolean indicating if the value is a valid URL string
    """
    if not isinstance(url, str) or not url:
        return False
        
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

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
    if not markets:
        return []
        
    # Use UTC for consistent timezone-aware comparison
    now = datetime.now().astimezone()
    filtered_markets = []
    
    # Tracking for debugging
    filter_reasons = {
        "closed": 0,
        "archived": 0,
        "inactive": 0,
        "expired": 0,
        "invalid_image": 0,
        "invalid_icon": 0,
        "passed": 0
    }
    
    for market in markets:
        # Check closed
        if market.get("closed") == True:
            filter_reasons["closed"] += 1
            continue
            
        # Check archived
        if market.get("archived") == True:
            filter_reasons["archived"] += 1
            continue
            
        # Check active
        if market.get("active") != True:
            filter_reasons["inactive"] += 1
            continue
            
        # Check end date
        end_date_str = market.get("endDate")
        if not end_date_str:
            filter_reasons["expired"] += 1
            continue
            
        try:
            # Parse ISO format timestamp (strip Z for compatibility)
            end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
            
            # Check if end date is in the future
            if end_date <= now:
                filter_reasons["expired"] += 1
                continue
                
        except Exception as e:
            logger.warning(f"Error parsing end date {end_date_str}: {str(e)}")
            filter_reasons["expired"] += 1
            continue
            
        # Check image URL
        if not is_valid_url(market.get("image")):
            filter_reasons["invalid_image"] += 1
            continue
            
        # Check icon URL
        if not is_valid_url(market.get("icon")):
            filter_reasons["invalid_icon"] += 1
            continue
            
        # Market passed all filters
        filtered_markets.append(market)
        filter_reasons["passed"] += 1
    
    # Log filter statistics
    logger.info(f"Market filtering results:")
    for reason, count in filter_reasons.items():
        logger.info(f"  - {reason}: {count}")
    
    # Check category distribution
    categories = {}
    for market in filtered_markets:
        category = market.get("fetched_category", "general")
        categories[category] = categories.get(category, 0) + 1
    
    logger.info("Category distribution after filtering:")
    for category, count in categories.items():
        logger.info(f"  - {category}: {count} markets")
    
    return filtered_markets

def save_filtered_markets(markets: List[Dict[str, Any]], filename: str = "active_markets.json"):
    """
    Save filtered market data to a JSON file.
    
    Args:
        markets: List of filtered market data dictionaries
        filename: Name of the file to save to
    """
    # Create a simplified representation for saving
    simplified = [
        {
            "id": market.get("id"),
            "conditionId": market.get("conditionId"),
            "question": market.get("question"),
            "endDate": market.get("endDate"),
            "category": market.get("fetched_category"),
            "image": market.get("image"),
            "icon": market.get("icon")
        }
        for market in markets
    ]
    
    try:
        with open(filename, "w") as f:
            json.dump(simplified, f, indent=2)
            
        logger.info(f"Saved {len(markets)} filtered markets to {filename}")
    except Exception as e:
        logger.error(f"Error saving filtered markets: {str(e)}")

def display_active_markets(markets: List[Dict[str, Any]], max_display: int = 5):
    """
    Display active markets in a readable format.
    
    Args:
        markets: List of filtered market data dictionaries
        max_display: Maximum number of markets to display
    """
    if not markets:
        print("No active markets found.")
        return
        
    print(f"\nFound {len(markets)} active markets. Displaying first {min(max_display, len(markets))}:\n")
    
    for i, market in enumerate(markets[:max_display]):
        print(f"Market {i+1}:")
        print(f"  Question: {market.get('question', 'Unknown')}")
        print(f"  Category: {market.get('fetched_category', 'general')}")
        print(f"  End Date: {market.get('endDate', 'Unknown')}")
        print(f"  Image: {market.get('image', 'None')}")
        print(f"  Icon: {market.get('icon', 'None')}")
        print()

def main():
    """
    Main function to run the market filtering.
    """
    # Fetch markets from Polymarket API
    logger.info("Fetching markets from Polymarket API")
    markets = fetch_markets()
    
    if not markets:
        logger.error("Failed to fetch any markets from API")
        return 1
        
    logger.info(f"Successfully fetched {len(markets)} markets from API")
    
    # Filter active markets
    logger.info("Filtering active markets")
    active_markets = filter_active_markets(markets)
    
    if not active_markets:
        logger.error("No active markets found after filtering")
        return 1
        
    logger.info(f"Successfully filtered to {len(active_markets)} active markets")
    
    # Save filtered markets
    save_filtered_markets(active_markets)
    
    # Display results
    display_active_markets(active_markets)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())