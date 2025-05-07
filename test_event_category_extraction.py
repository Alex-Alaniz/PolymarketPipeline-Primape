#!/usr/bin/env python3

"""
Test script to verify event category extraction 
"""

import requests
import json
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_event_category")

def fetch_sample_markets():
    """Fetch a few sample markets to test event category extraction"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    
    # Parameters for sample markets
    params = {
        "closed": "false",
        "archived": "false",
        "active": "true",
        "limit": "10"
    }
    
    logger.info("Fetching sample markets...")
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch markets: Status {response.status_code}")
        return []
    
    markets = response.json()
    logger.info(f"Successfully fetched {len(markets)} markets")
    
    return markets

def extract_event_categories(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract event categories from markets"""
    processed_markets = []
    
    for market in markets:
        # Store original category for comparison
        market["fetched_category"] = "api_query_category"
        
        # Extract event category if available
        events = market.get("events", [])
        event_category = None
        event_image = None
        event_icon = None
        
        if events:
            # Get the first event (typically only one per market)
            event = events[0]
            if "category" in event:
                event_category = event["category"]
                logger.info(f"Found event category: {event_category}")
            else:
                logger.info("Event does not have category field")
                
            # Get event images
            event_image = event.get("image")
            event_icon = event.get("icon")
            
        # Store extracted data
        market["event_category"] = event_category
        market["event_image"] = event_image
        market["event_icon"] = event_icon
        
        # Add to processed list
        processed_markets.append(market)
    
    return processed_markets

def main():
    """Main test function"""
    # Fetch sample markets
    markets = fetch_sample_markets()
    
    if not markets:
        logger.error("No markets fetched, cannot proceed with test")
        return 1
    
    # Process markets to extract event categories
    processed_markets = extract_event_categories(markets)
    
    # Count markets with event categories
    markets_with_event_category = sum(1 for m in processed_markets if m.get("event_category"))
    
    logger.info(f"Found {markets_with_event_category} out of {len(processed_markets)} markets with event categories")
    
    # Print summary of each market
    print("\nMarket Category Summary:")
    print("=" * 50)
    
    for i, market in enumerate(processed_markets):
        print(f"Market {i+1}: {market.get('question', 'Unknown')}")
        
        # Print category information
        event_category = market.get("event_category")
        if event_category:
            print(f"  Event Category: {event_category}")
        else:
            print("  No Event Category Found")
            
        # Print image information
        print(f"  Market Image: {market.get('image', 'None')}")
        event_image = market.get("event_image")
        if event_image:
            print(f"  Event Image: {event_image}")
            
            # Check if images match
            if market.get("image") == event_image:
                print("  ✓ Market image matches event image")
            else:
                print("  ✗ Market image differs from event image")
        else:
            print("  No Event Image Available")
            
        print("-" * 50)
    
    return 0

if __name__ == "__main__":
    main()