#!/usr/bin/env python3

"""
Inspect the raw API response from Polymarket to understand its structure.
"""

import json
import requests

# API endpoint 
API_URL = "https://clob.polymarket.com/markets"

print(f"Fetching data from {API_URL}")
response = requests.get(API_URL)

if response.status_code == 200:
    data = response.json()
    print(f"Response status: {response.status_code}")
    print(f"Response keys: {list(data.keys())}")
    
    # If there's a data key, look at its structure
    if 'data' in data:
        items = data['data']
        print(f"Found {len(items)} items in data array")
        
        # Look at first few items
        for i, item in enumerate(items[:3]):
            print(f"\nItem {i+1} keys: {list(item.keys())}")
            
            # Check if this item has events or option_markets
            if 'events' in item:
                print(f"Item {i+1} has events: {item['events']}")
            else:
                print(f"Item {i+1} does NOT have events")
                
            if 'option_markets' in item:
                print(f"Item {i+1} has option_markets: {item['option_markets']}")
            else:
                print(f"Item {i+1} does NOT have option_markets")
    
    # Save the raw response for examination
    with open("raw_api_response.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved raw API response to raw_api_response.json")
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")