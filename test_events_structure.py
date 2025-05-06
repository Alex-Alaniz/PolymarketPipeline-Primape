#!/usr/bin/env python3

"""
Test script to examine Polymarket API events structure
"""

import requests
import json
from pprint import pprint

def test_events_structure():
    """Test API call to Polymarket focusing on events"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets"
    
    # Get markets from multiple categories to check event structures
    categories = ["sports", "politics", "crypto", "entertainment"]
    
    all_events = {}
    
    for category in categories:
        params = {
            "closed": "false",
            "archived": "false",
            "active": "true",
            "limit": "10",
            "category": category
        }
        
        print(f"\nFetching {category} markets from Polymarket API...")
        
        response = requests.get(base_url, params=params)
        
        if response.status_code == 200:
            markets = response.json()
            print(f"Successfully fetched {len(markets)} {category} markets")
            
            for market in markets:
                # Check if the market has events
                events = market.get("events", [])
                
                # If the market has events, analyze them
                if events:
                    for event in events:
                        event_id = event.get("id")
                        
                        # Store unique events
                        if event_id not in all_events:
                            all_events[event_id] = {
                                "id": event_id,
                                "title": event.get("title"),
                                "description": event.get("description"),
                                "image": event.get("image"),
                                "icon": event.get("icon"),
                                "category": category,  # We'll assign the market's category for now
                                "markets": []
                            }
                        
                        # Add this market to the event's markets list
                        market_id = market.get("id")
                        if market_id not in all_events[event_id]["markets"]:
                            all_events[event_id]["markets"].append(market_id)
        else:
            print(f"Failed to fetch {category} markets: Status {response.status_code}")
    
    # Print the events we've found
    print(f"\nFound {len(all_events)} unique events across all markets")
    
    # Print a few sample events with their markets
    print("\nSample Events:")
    count = 0
    for event_id, event in all_events.items():
        if count >= 3:  # Limit to 3 samples
            break
            
        print(f"\nEvent ID: {event_id}")
        print(f"Title: {event['title']}")
        print(f"Assigned Category: {event['category']}")
        print(f"Image: {event['image']}")
        print(f"Icon: {event['icon']}")
        print(f"Markets Count: {len(event['markets'])}")
        print("Market IDs:")
        for market_id in event['markets']:
            print(f"  - {market_id}")
            
        count += 1
    
    # Check if events have their own category field
    print("\nChecking if events have their own category field:")
    has_category = False
    
    # Get a fresh sample market to check its events
    sample_response = requests.get(base_url, params={"limit": "1"})
    if sample_response.status_code == 200:
        sample_markets = sample_response.json()
        if sample_markets and sample_markets[0].get("events"):
            sample_event = sample_markets[0]["events"][0]
            if "category" in sample_event:
                has_category = True
                print(f"Found event with category: {sample_event['category']}")
    
    if not has_category:
        print("None of the events have their own category field")

if __name__ == "__main__":
    test_events_structure()