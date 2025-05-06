#!/usr/bin/env python3

"""
Script to check for markets sharing the same events and analyze event categories
"""

import requests
import json

def check_shared_events():
    """Check for markets sharing the same events"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets"
    
    # Get a larger sample of markets
    params = {
        "limit": "50"  # Get 50 markets
    }
    
    print("Fetching markets from Polymarket API...")
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        print(f"Failed to fetch markets: Status {response.status_code}")
        return
    
    markets = response.json()
    print(f"Successfully fetched {len(markets)} markets")
    
    # Group markets by event
    events_to_markets = {}
    markets_with_events = 0
    
    for market in markets:
        events = market.get("events", [])
        if events:
            markets_with_events += 1
            
            for event in events:
                event_id = event.get("id")
                if event_id:
                    if event_id not in events_to_markets:
                        events_to_markets[event_id] = {
                            "event": event,
                            "markets": []
                        }
                    
                    events_to_markets[event_id]["markets"].append({
                        "id": market.get("id"),
                        "question": market.get("question"),
                        "image": market.get("image"),
                        "icon": market.get("icon")
                    })
    
    print(f"\nFound {markets_with_events} markets with events")
    print(f"Found {len(events_to_markets)} unique events")
    
    # Find events with multiple markets
    shared_events = {
        event_id: data 
        for event_id, data in events_to_markets.items() 
        if len(data["markets"]) > 1
    }
    
    print(f"Found {len(shared_events)} events shared by multiple markets")
    
    # Print some information about shared events
    for i, (event_id, data) in enumerate(shared_events.items()):
        if i >= 3:  # Limit to 3 examples
            break
            
        event = data["event"]
        markets_list = data["markets"]
        
        print(f"\n--- Shared Event {i+1} ---")
        print(f"Event ID: {event_id}")
        print(f"Event Title: {event.get('title')}")
        
        # Check if the event has a category
        if "category" in event:
            print(f"Event Category: {event['category']}")
        else:
            print("Event does NOT have a category field")
        
        print(f"Event Image: {event.get('image')}")
        print(f"Event Icon: {event.get('icon')}")
        
        print(f"\nThis event is shared by {len(markets_list)} markets:")
        for j, market in enumerate(markets_list):
            print(f"  Market {j+1}:")
            print(f"    ID: {market['id']}")
            print(f"    Question: {market['question']}")
            print(f"    Image: {market['image']}")
            print(f"    Icon: {market['icon']}")
            
            # Check if market image matches event image
            if market['image'] == event.get('image'):
                print("    Market image matches event image: Yes")
            else:
                print("    Market image matches event image: No")
    
    # Analyze event categories
    events_with_categories = [
        data["event"] for data in events_to_markets.values()
        if "category" in data["event"]
    ]
    
    print(f"\n--- Event Categories Analysis ---")
    print(f"Found {len(events_with_categories)} events with categories out of {len(events_to_markets)} total events")
    
    if events_with_categories:
        # Count occurrences of each category
        category_counts = {}
        for event in events_with_categories:
            category = event["category"]
            if category not in category_counts:
                category_counts[category] = 0
            category_counts[category] += 1
        
        # Sort categories by frequency
        sorted_categories = sorted(
            category_counts.items(),
            key=lambda item: item[1],
            reverse=True
        )
        
        print("\nMost common event categories:")
        for category, count in sorted_categories[:10]:  # Top 10
            print(f"  {category}: {count} events")

if __name__ == "__main__":
    check_shared_events()