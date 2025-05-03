#!/usr/bin/env python3
"""
Test script for Polymarket API connectivity.
"""
import requests
import json

def main():
    """Test connectivity to Polymarket API"""
    # Try different base URLs
    base_urls = [
        "https://polymarket.com/api",
        "https://api.polymarket.com",
        "https://clob-api.polymarket.com"
    ]
    
    for base_url in base_urls:
        print(f"\nTesting API endpoint: {base_url}")
        
        # Test endpoints
        endpoints = [
            "/markets",
            "/v0/markets",
            "/markets/popular"
        ]
        
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            print(f"  Requesting: {url}")
            
            try:
                response = requests.get(url, timeout=5)
                print(f"  Status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if "markets" in data:
                        markets = data["markets"]
                        print(f"  SUCCESS! Found {len(markets)} markets")
                        # Print the first market as sample
                        if markets:
                            print(f"  Sample market: {json.dumps(markets[0], indent=2)[:200]}...")
                    elif "data" in data:
                        markets = data["data"]
                        print(f"  SUCCESS! Found {len(markets)} markets in data field")
                        # Print the first market as sample
                        if markets:
                            print(f"  Sample market: {json.dumps(markets[0], indent=2)[:200]}...")
                    else:
                        print(f"  Response structure: {list(data.keys())}")
                else:
                    print(f"  Error response: {response.text[:100]}")
            
            except Exception as e:
                print(f"  ERROR: {str(e)}")

if __name__ == "__main__":
    main()