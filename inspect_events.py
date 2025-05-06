#!/usr/bin/env python3

"""
Simple script to inspect the events structure from the Polymarket API
"""

import requests
import json

def inspect_events():
    """Inspect events from a few markets"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets"
    
    # Simple request to get a few markets
    params = {
        "limit": "3"  # Just get 3 markets
    }
    
    print("Fetching markets from Polymarket API...")
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        print(f"Failed to fetch markets: Status {response.status_code}")
        return
    
    markets = response.json()
    print(f"Successfully fetched {len(markets)} markets")
    
    # Check if any markets have events
    markets_with_events = [m for m in markets if "events" in m and m["events"]]
    
    if not markets_with_events:
        print("None of the markets have events, trying more markets...")
        
        # Try with more markets
        params = {
            "limit": "20"  # Get 20 markets this time
        }
        
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            print(f"Failed to fetch more markets: Status {response.status_code}")
            return
        
        markets = response.json()
        markets_with_events = [m for m in markets if "events" in m and m["events"]]
        
        if not markets_with_events:
            print("Still couldn't find any markets with events")
            return
    
    print(f"\nFound {len(markets_with_events)} markets with events")
    
    # Examine the first market with events
    sample_market = markets_with_events[0]
    print(f"\n--- Sample Market ---")
    print(f"ID: {sample_market.get('id')}")
    print(f"Question: {sample_market.get('question')}")
    
    # Examine its events
    events = sample_market.get("events", [])
    print(f"\nThis market has {len(events)} events")
    
    for i, event in enumerate(events):
        print(f"\n--- Event {i+1} ---")
        # Print all fields of the event
        print("Event Fields:")
        for key, value in event.items():
            if key not in ["description"]:  # Skip long fields
                print(f"  {key}: {value}")
        
        # Check if the event has a category
        if "category" in event:
            print(f"\nEvent has a category: {event['category']}")
        else:
            print("\nEvent does NOT have a category field")
        
        # Print image and icon
        print(f"Image: {event.get('image', 'None')}")
        print(f"Icon: {event.get('icon', 'None')}")
    
    # Now check the market's image and icon
    print(f"\n--- Market Image/Icon ---")
    print(f"Market Image: {sample_market.get('image', 'None')}")
    print(f"Market Icon: {sample_market.get('icon', 'None')}")
    
    # Check if the market's image/icon matches the event's image/icon
    if events and sample_market.get('image') == events[0].get('image'):
        print("\nMarket image matches event image")
    else:
        print("\nMarket image is different from event image")
    
    # Check if any other markets share the same event
    event_id = events[0].get('id') if events else None
    if event_id:
        shared_markets = [
            m['id'] for m in markets 
            if "events" in m and m["events"] and 
            any(e.get('id') == event_id for e in m["events"])
        ]
        
        if len(shared_markets) > 1:
            print(f"\nFound {len(shared_markets)} markets sharing the same event (ID: {event_id}):")
            for m_id in shared_markets:
                print(f"  - Market ID: {m_id}")

if __name__ == "__main__":
    inspect_events()