#!/usr/bin/env python3

"""
Inspect the Gamma API response to understand its structure.
"""

import json
import requests

# Gamma API endpoint
API_URL = "https://gamma.polymarket.com/api/v1/markets"

print(f"Fetching data from {API_URL}")
response = requests.get(API_URL)

if response.status_code == 200:
    data = response.json()
    print(f"Response status: {response.status_code}")
    
    # Look at response structure
    if isinstance(data, list):
        print(f"Found {len(data)} markets in response array")
        
        # Look at first few markets
        for i, market in enumerate(data[:5]):
            print(f"\nMarket {i+1} keys: {list(market.keys())}")
            
            # Check for events and option_markets
            if 'events' in market and market['events']:
                print(f"Market {i+1} has events array with {len(market['events'])} events")
                
                # Examine first event
                if market['events']:
                    first_event = market['events'][0]
                    print(f"  Event keys: {list(first_event.keys())}")
                    
                    # Check for image
                    if 'image' in first_event:
                        print(f"  Event has image: {first_event['image'][:50]}...")
                    
                    # Check for outcomes
                    if 'outcomes' in first_event and first_event['outcomes']:
                        print(f"  Event has {len(first_event['outcomes'])} outcomes")
                        if first_event['outcomes']:
                            outcome = first_event['outcomes'][0]
                            print(f"  Outcome keys: {list(outcome.keys())}")
                            
                            # Check for icon
                            if 'icon' in outcome:
                                print(f"  Outcome has icon: {outcome['icon'][:50]}...")
            else:
                print(f"Market {i+1} does NOT have events")
                
            if 'option_markets' in market and market['option_markets']:
                print(f"Market {i+1} has option_markets array with {len(market['option_markets'])} option markets")
                
                # Examine first option market
                if market['option_markets']:
                    option_market = market['option_markets'][0]
                    print(f"  Option market keys: {list(option_market.keys())}")
                    
                    # Check for icon
                    if 'icon' in option_market:
                        print(f"  Option market has icon: {option_market['icon'][:50]}...")
            else:
                print(f"Market {i+1} does NOT have option_markets")
                
            # If this is a multi-option market with both arrays, save it as an example
            if ('events' in market and market['events'] and 
                'option_markets' in market and market['option_markets']):
                with open(f"gamma_market_example_{i+1}.json", "w") as f:
                    json.dump(market, f, indent=2)
                print(f"Saved multi-option market example to gamma_market_example_{i+1}.json")
    
    # Save full response for examination
    with open("gamma_api_response.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved raw API response to gamma_api_response.json")
else:
    print(f"Failed to fetch data. Status code: {response.status_code}")