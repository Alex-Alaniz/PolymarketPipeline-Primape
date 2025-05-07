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
from utils.market_transformer import MarketTransformer

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

def fetch_markets(limit: int = 200, variant: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API using the gamma API endpoint.
    Fetches a diverse set of markets across different categories.
    
    Args:
        limit: Maximum number of markets to fetch per query
        variant: A variant number to diversify market fetching
                (run 0 = default, run 1, 2, etc. = different parameters)
        
    Returns:
        List of market data dictionaries
    """
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    
    # Base parameters with anti-caching timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    params = {
        "closed": "false",
        "archived": "false",
        "active": "true",
        "limit": "200",  # Always fetch 200 for maximum coverage
        "include_detailed_events": "true",  # Get more detailed event information
        "_t": timestamp  # Add timestamp to avoid caching
    }
    
    # Modify parameters based on variant to get different sets of markets
    if variant > 0:
        # On subsequent runs, we get markets with different sort parameters
        sort_options = ["newest", "oldest", "volume", "liquidity", "expiry"]
        sort_choice = sort_options[variant % len(sort_options)]
        params["sort"] = sort_choice
        logger.info(f"Using variant {variant} with sort={sort_choice}")
        
        # We can also vary the category focus for more diversity
        if variant % 3 == 1:
            # Focus on sports and entertainment
            CATEGORIES["sports"] = 100
            CATEGORIES["entertainment"] = 80
        elif variant % 3 == 2:
            # Focus on politics and crypto
            CATEGORIES["politics"] = 100
            CATEGORIES["crypto"] = 80
    
    all_markets = []
    found_event_ids = set()  # Track event IDs to group multi-option markets better
    
    # First, fetch a large batch of markets without category filtering
    try:
        # Use the base parameters without category to get a more comprehensive list
        logger.info(f"Fetching up to 200 markets from Polymarket API (all categories)")
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            all_category_markets = response.json()
            logger.info(f"Successfully fetched {len(all_category_markets)} markets (all categories)")
            
            # Process each market
            for market in all_category_markets:
                # Track event IDs to help find related markets later
                events = market.get("events", [])
                if events:
                    for event in events:
                        if "id" in event:
                            found_event_ids.add(event["id"])
                
                # Check if the market has events
                if events:
                    # Extract event category if available
                    for event in events:
                        if "category" in event:
                            # Use the event's category
                            market["event_category"] = event["category"]
                            # Also store event images for reference
                            market["event_image"] = event.get("image")
                            market["event_icon"] = event.get("icon")
                            
                            # Check if the event has related questions that we can use for extraction
                            if "questions" in event:
                                market["event_questions"] = event["questions"]
                            
                            # Check if the event has more detailed outcome data
                            if "outcomes" in event:
                                market["event_outcomes"] = event["outcomes"]
                            
                            break
            
            all_markets.extend(all_category_markets)
        else:
            logger.error(f"Failed to fetch markets: Status {response.status_code}")
            logger.error(f"Response: {response.text}")
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
    
    # Now fetch markets for each category to ensure we don't miss anything
    for category, count in CATEGORIES.items():
        try:
            category_params = params.copy()
            category_params["category"] = category
            category_params["limit"] = str(count)
            
            logger.info(f"Fetching {count} {category} markets from Polymarket API")
            
            response = requests.get(base_url, params=category_params)
            
            if response.status_code == 200:
                category_markets = response.json()
                
                # Process each market to extract event categories and images
                for market in category_markets:
                    # Check if this market is already in our list (by ID)
                    market_id = market.get("id")
                    if market_id and any(m.get("id") == market_id for m in all_markets):
                        continue  # Skip duplicate markets
                    
                    # Process event data
                    events = market.get("events", [])
                    if events:
                        # Extract event category if available
                        for event in events:
                            if "category" in event:
                                # Use the event's category
                                market["event_category"] = event["category"]
                                # Also store event images for reference
                                market["event_image"] = event.get("image")
                                market["event_icon"] = event.get("icon")
                                
                                # Check if the event has related questions that we can use for extraction
                                if "questions" in event:
                                    market["event_questions"] = event["questions"]
                                
                                # Check if the event has more detailed outcome data
                                if "outcomes" in event:
                                    market["event_outcomes"] = event["outcomes"]
                                
                                # Track event ID
                                if "id" in event:
                                    found_event_ids.add(event["id"])
                                
                                break
                    
                    # Add to our collection
                    all_markets.append(market)
                
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
            "category": market.get("event_category", market.get("fetched_category")),
            "fetched_category": market.get("fetched_category"),
            "event_category": market.get("event_category"),
            "closed": market.get("closed"),
            "archived": market.get("archived"),
            "active": market.get("active"),
            "image": market.get("image"),
            "icon": market.get("icon"),
            "event_image": market.get("event_image"),
            "event_icon": market.get("event_icon")
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
        # Use event_category when available, otherwise leave as "uncategorized"
        category = market.get("event_category", "uncategorized")
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
            "category": market.get("event_category", ""),  # Only use event category, no fallback
            "fetched_category": market.get("fetched_category"),
            "event_category": market.get("event_category"),
            "image": market.get("image"),
            "icon": market.get("icon"),
            "event_image": market.get("event_image"),
            "event_icon": market.get("event_icon"),
            "event_questions": market.get("event_questions"),  # Include event questions data
            "event_outcomes": market.get("event_outcomes")  # Include event outcomes data
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
        
        # Display category information - only show event_category if available, no fallback
        event_category = market.get('event_category')
        if event_category:
            print(f"  Category: {event_category} (from event)")
        else:
            print(f"  Category: Uncategorized")
        
        print(f"  End Date: {market.get('endDate', 'Unknown')}")
        
        # Display image information
        print(f"  Market Image: {market.get('image', 'None')}")
        print(f"  Market Icon: {market.get('icon', 'None')}")
        
        # Display event image information if available
        if market.get('event_image'):
            print(f"  Event Image: {market.get('event_image')}")
        if market.get('event_icon'):
            print(f"  Event Icon: {market.get('event_icon')}")
            
        print()

def transform_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform markets to consolidate multi-option markets.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List of transformed market dictionaries
    """
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(markets)
    
    # Check if we have any multiple-option markets
    multiple_count = sum(1 for m in transformed if m.get("is_multiple_option"))
    multiple_markets = [m for m in transformed if m.get("is_multiple_option")]
    
    logger.info(f"Transformed {len(markets)} markets into {len(transformed)} markets")
    logger.info(f"Found {multiple_count} multiple-option markets")
    
    # Save transformed markets for direct inspection
    with open("transformed_markets.json", "w") as f:
        json.dump(transformed, f, indent=2, default=str)
    
    # Debug the multiple-option markets
    if multiple_count > 0:
        logger.info("DEBUGGING MULTIPLE-OPTION MARKETS:")
        for i, market in enumerate(multiple_markets):
            logger.info(f"Multiple-option market {i+1}:")
            logger.info(f"  - ID: {market.get('id')}")
            logger.info(f"  - Question: {market.get('question')}")
            
            # Parse outcomes which come as a JSON string
            outcomes_raw = market.get("outcomes", "[]")
            outcomes = []
            try:
                if isinstance(outcomes_raw, str):
                    outcomes = json.loads(outcomes_raw)
                else:
                    outcomes = outcomes_raw
            except Exception as e:
                logger.error(f"Error parsing outcomes: {str(e)}")
                
            if outcomes:
                logger.info(f"  - Options ({len(outcomes)}):")
                for j, option in enumerate(outcomes):
                    logger.info(f"    {j+1}. {option}")
            
            logger.info(f"  - Original Market IDs: {market.get('original_market_ids', [])}")
    
    return transformed

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
    
    # Transform markets to consolidate multi-option markets
    logger.info("Transforming markets")
    transformed_markets = transform_markets(active_markets)
    
    # Save filtered markets
    save_filtered_markets(transformed_markets)
    
    # Display results
    display_active_markets(transformed_markets)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())