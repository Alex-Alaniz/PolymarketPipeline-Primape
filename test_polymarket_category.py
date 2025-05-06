#!/usr/bin/env python3

"""
Test script to examine Polymarket API response and category structure
"""

import requests
import json
from pprint import pprint

def test_api_call():
    """Test API call to Polymarket"""
    # Base API URL
    base_url = "https://gamma-api.polymarket.com/markets"
    
    # Get just a few markets from 'politics' category
    params = {
        "closed": "false",
        "archived": "false",
        "active": "true",
        "limit": "5",
        "category": "politics"
    }
    
    print("Fetching politics markets from Polymarket API...")
    
    response = requests.get(base_url, params=params)
    
    if response.status_code == 200:
        markets = response.json()
        print(f"Successfully fetched {len(markets)} markets")
        
        # Print the first market's full structure
        print("\nSample market full structure:")
        first_market = markets[0]
        print(json.dumps(first_market, indent=2))
        
        # Check if 'category' field already exists in the raw API response
        print("\nChecking if 'category' exists in raw API response:")
        if "category" in first_market:
            print(f"FOUND: Market has 'category' field with value: {first_market['category']}")
        else:
            print("NOT FOUND: Market does not have a 'category' field in the raw API response")
            print("This confirms why we need to add our own 'fetched_category' field")
        
        # Print relevant fields for all fetched markets
        print("\nAll fetched markets (selected fields):")
        for i, market in enumerate(markets):
            print(f"\nMarket {i+1}:")
            print(f"  ID: {market.get('id')}")
            print(f"  Question: {market.get('question')}")
            # If category exists in raw response, show it
            if "category" in market:
                print(f"  API Category: {market.get('category')}")
    else:
        print(f"Failed to fetch markets: Status {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == "__main__":
    test_api_call()