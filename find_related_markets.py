#!/usr/bin/env python3

"""
Script to find related markets by looking at their event associations
"""

import requests
import json

def find_related_markets():
    """Find markets that are related to each other via events"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets"
    
    # Try to find a specific type of event that might have related markets
    # Let's try fetching sports markets as they might be more likely to have related events
    categories = ["sports", "politics", "crypto"]
    
    for category in categories:
        params = {
            "limit": "20",
            "category": category
        }
        
        print(f"\nFetching {category} markets from Polymarket API...")
        
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            print(f"Failed to fetch {category} markets: Status {response.status_code}")
            continue
        
        markets = response.json()
        print(f"Successfully fetched {len(markets)} {category} markets")
        
        # Extract events from all markets
        all_events = {}
        for market in markets:
            events = market.get("events", [])
            for event in events:
                event_id = event.get("id")
                if event_id and event_id not in all_events:
                    all_events[event_id] = {
                        "title": event.get("title"),
                        "markets": []
                    }
        
        # Now check which markets reference these events
        for event_id in all_events:
            for market in markets:
                market_id = market.get("id")
                market_events = market.get("events", [])
                
                if any(e.get("id") == event_id for e in market_events):
                    all_events[event_id]["markets"].append({
                        "id": market_id,
                        "question": market.get("question")
                    })
        
        # Find events with multiple markets
        shared_events = {
            event_id: data 
            for event_id, data in all_events.items() 
            if len(data["markets"]) > 1
        }
        
        print(f"Found {len(shared_events)} events with multiple markets in {category} category")
        
        # Print details of shared events
        for event_id, data in shared_events.items():
            print(f"\nEvent: {data['title']} (ID: {event_id})")
            print("Related Markets:")
            for market in data["markets"]:
                print(f"  - {market['question']} (ID: {market['id']})")
        
        # If we found shared events, fetch one in detail to examine
        if shared_events:
            # Pick the first shared event
            first_event_id = next(iter(shared_events))
            first_market_id = shared_events[first_event_id]["markets"][0]["id"]
            
            # Fetch this market to examine its events in detail
            print(f"\nFetching detailed information for market ID: {first_market_id}")
            detail_response = requests.get(f"{base_url}/{first_market_id}")
            
            if detail_response.status_code == 200:
                market_detail = detail_response.json()
                
                # Extract the event that multiple markets share
                shared_event = next((e for e in market_detail.get("events", []) 
                                    if e.get("id") == first_event_id), None)
                
                if shared_event:
                    print("\nShared Event Details:")
                    print(f"Title: {shared_event.get('title')}")
                    
                    # Check if the event has a category
                    event_category = shared_event.get("category")
                    if event_category:
                        print(f"Category: {event_category}")
                    else:
                        print("No category field in the event")
                    
                    # Print image and icon
                    print(f"Image: {shared_event.get('image')}")
                    print(f"Icon: {shared_event.get('icon')}")
                    
                    # Compare with market's image and icon
                    print("\nMarket Image/Icon:")
                    print(f"Image: {market_detail.get('image')}")
                    print(f"Icon: {market_detail.get('icon')}")
                    
                    # Check if they match
                    if market_detail.get('image') == shared_event.get('image'):
                        print("Market image matches event image")
                    else:
                        print("Market image is different from event image")
            
            # Stop after finding one example
            if shared_events:
                break

if __name__ == "__main__":
    find_related_markets()