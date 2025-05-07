#!/usr/bin/env python3

"""
Test script to check for historical events with categories
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
logger = logging.getLogger("test_historical_events")

def fetch_historical_markets():
    """Fetch some historical markets that might have event categories"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    
    # Try different parameters to find historical markets
    params_list = [
        # Include archived markets
        {
            "limit": "20",
            "archived": "true"
        },
        # Include closed markets
        {
            "limit": "20",
            "closed": "true"
        },
        # Try a specific ID that had a category in our previous test
        {
            "id": "12"
        }
    ]
    
    all_markets = []
    
    for params in params_list:
        logger.info(f"Fetching markets with params: {params}")
        
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch markets: Status {response.status_code}")
            continue
        
        markets = response.json()
        logger.info(f"Successfully fetched {len(markets)} markets")
        
        all_markets.extend(markets)
    
    # Remove duplicates
    unique_markets = []
    seen_ids = set()
    
    for market in all_markets:
        market_id = market.get("id")
        if market_id and market_id not in seen_ids:
            seen_ids.add(market_id)
            unique_markets.append(market)
    
    logger.info(f"Found {len(unique_markets)} unique markets")
    
    return unique_markets

def check_event_categories(markets: List[Dict[str, Any]]):
    """Check events for categories"""
    markets_with_events = 0
    events_with_categories = 0
    events_examined = 0
    
    # Event categories found
    categories_found = set()
    
    for market in markets:
        events = market.get("events", [])
        
        if events:
            markets_with_events += 1
            
            for event in events:
                events_examined += 1
                
                if "category" in event:
                    events_with_categories += 1
                    category = event["category"]
                    categories_found.add(category)
                    
                    logger.info(f"Found event with category: {category}")
                    logger.info(f"  Event ID: {event.get('id')}")
                    logger.info(f"  Event Title: {event.get('title')}")
                    logger.info(f"  Market Question: {market.get('question')}")
    
    # Print summary
    print("\nEvent Category Analysis:")
    print(f"Total markets examined: {len(markets)}")
    print(f"Markets with events: {markets_with_events}")
    print(f"Total events examined: {events_examined}")
    print(f"Events with categories: {events_with_categories}")
    
    if categories_found:
        print("\nCategories found:")
        for category in sorted(categories_found):
            print(f"  - {category}")
    else:
        print("\nNo categories found in any events")

def examine_single_market(market_id):
    """Examine a specific market in detail"""
    # Base API URL
    base_url = f"https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100/{market_id}"
    
    logger.info(f"Fetching market with ID: {market_id}")
    
    response = requests.get(base_url)
    
    if response.status_code != 200:
        logger.error(f"Failed to fetch market: Status {response.status_code}")
        return
    
    market = response.json()
    logger.info(f"Successfully fetched market: {market.get('question')}")
    
    # Print all fields
    print("\nMarket Detail:")
    for key, value in market.items():
        if key != "events":  # Don't print events yet
            print(f"{key}: {value}")
    
    # Examine events
    events = market.get("events", [])
    print(f"\nThis market has {len(events)} events")
    
    for i, event in enumerate(events):
        print(f"\nEvent {i+1}:")
        for key, value in event.items():
            if key not in ["description"]:  # Skip long fields
                print(f"  {key}: {value}")

def main():
    """Main test function"""
    # Fetch historical markets
    markets = fetch_historical_markets()
    
    if not markets:
        logger.error("No markets fetched, cannot proceed with test")
        return 1
    
    # Check for event categories
    check_event_categories(markets)
    
    # Examine a specific market that previously had a category
    examine_single_market("12")
    
    return 0

if __name__ == "__main__":
    main()