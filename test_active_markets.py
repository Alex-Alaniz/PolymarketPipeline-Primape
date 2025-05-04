#!/usr/bin/env python3

"""
Test script for fetching only active, non-expired markets from Polymarket API.

This script focuses on filtering active markets and showing clear curl commands
for reproducing the requests in Postman or other API tools.
"""

import requests
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("active_markets_test")

def fetch_active_markets():
    """
    Fetch only active, non-expired markets from Polymarket API.
    """
    logger.info("Fetching active non-expired markets from Polymarket API...")
    
    # Define endpoints with different filtering parameters
    endpoints = [
        # Base endpoint - all markets (default is 500 per page)
        "https://clob.polymarket.com/markets",
        # Active=true filter - should get only active markets
        "https://clob.polymarket.com/markets?active=true",
        # Smaller result set for detailed testing
        "https://clob.polymarket.com/markets?limit=10&active=true",
        # Additional parameter: accepting_orders=true
        "https://clob.polymarket.com/markets?accepting_orders=true",
        # Combined filtering - this is likely the most useful
        "https://clob.polymarket.com/markets?active=true&accepting_orders=true"
    ]
    
    # Track most successful endpoint
    best_endpoint = None
    most_active_markets = 0
    
    # Try each endpoint
    for endpoint in endpoints:
        try:
            logger.info(f"\nTesting endpoint: {endpoint}")
            
            # Set headers for the request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            # Make the request
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            # Check response
            if response.status_code == 200:
                data = response.json()
                
                # Check if we got markets
                if "data" in data and isinstance(data["data"], list):
                    markets = data["data"]
                    
                    # Count active markets
                    active_markets = [m for m in markets if m.get("active", False)]
                    # Count accepting_orders markets
                    accepting_orders_markets = [m for m in markets if m.get("accepting_orders", False)]
                    # Count neither closed nor archived markets
                    open_markets = [m for m in markets if not m.get("closed", False) and not m.get("archived", False)]
                    # Count markets with future end dates
                    current_time = datetime.now().isoformat()
                    future_markets = []
                    for m in markets:
                        if "end_date_iso" in m and m["end_date_iso"]:
                            try:
                                # Standardize format: convert Z to +00:00 for parsing
                                end_date = m["end_date_iso"].replace("Z", "+00:00")
                                if end_date > current_time:
                                    future_markets.append(m)
                            except Exception:
                                pass
                    
                    # Print detailed stats
                    logger.info(f"Total markets: {len(markets)}")
                    logger.info(f"Active markets: {len(active_markets)}")
                    logger.info(f"Accepting orders: {len(accepting_orders_markets)}")
                    logger.info(f"Not closed/archived: {len(open_markets)}")
                    logger.info(f"Future end dates: {len(future_markets)}")
                    
                    # Count truly active markets (active + accepting orders + not expired)
                    truly_active = [m for m in markets if 
                                    m.get("active", False) and 
                                    m.get("accepting_orders", False) and 
                                    not m.get("closed", False) and 
                                    not m.get("archived", False)]
                    
                    logger.info(f"Truly active markets (active + accepting orders + not closed/archived): {len(truly_active)}")
                    
                    # Track best endpoint
                    if len(truly_active) > most_active_markets:
                        most_active_markets = len(truly_active)
                        best_endpoint = endpoint
                    
                    # For the smallest result set, print first market detail
                    if endpoint.endswith("limit=10&active=true") and markets:
                        logger.info("\nSample market details:")
                        sample = markets[0]
                        print(json.dumps(sample, indent=2))
                    
                    # For the best combined filter, list first 5 market questions
                    if endpoint.endswith("active=true&accepting_orders=true") and truly_active:
                        logger.info("\nTop 5 truly active markets:")
                        for i, market in enumerate(truly_active[:5]):
                            print(f"{i+1}. {market.get('question', 'No question')}")
                else:
                    logger.warning(f"No markets data found in response from {endpoint}")
            else:
                logger.error(f"Failed to connect to {endpoint}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
        
        except Exception as e:
            logger.error(f"Error testing {endpoint}: {str(e)}")
    
    # Return the best endpoint
    return best_endpoint, most_active_markets

def generate_curl_commands():
    """
    Generate curl commands for fetching active markets.
    """
    logger.info("\n\nCURL COMMANDS FOR POSTMAN/TESTING:")
    logger.info("==================================")
    
    # Define endpoints with different filtering parameters
    endpoints = [
        # The most useful endpoints for active markets
        "https://clob.polymarket.com/markets?active=true",
        "https://clob.polymarket.com/markets?active=true&accepting_orders=true",
        # Limit results
        "https://clob.polymarket.com/markets?active=true&accepting_orders=true&limit=10"
    ]
    
    # Generate curl commands
    for endpoint in endpoints:
        curl_cmd = f'''curl -X GET \
  "{endpoint}" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" \
  -H "Accept: application/json"'''
        
        print("\n" + "-"*80)
        print(f"Curl command for {endpoint}:")
        print("-"*80)
        print(curl_cmd)

def main():
    """
    Main function to run the tests.
    """
    logger.info("Starting Polymarket active markets test")
    
    # Fetch active markets
    best_endpoint, count = fetch_active_markets()
    
    # Generate curl commands
    generate_curl_commands()
    
    # Final recommendation
    if best_endpoint:
        logger.info(f"\n\nRECOMMENDED ENDPOINT: {best_endpoint}")
        logger.info(f"This endpoint returned {count} truly active markets")
    
    logger.info("Completed active markets test")

if __name__ == "__main__":
    main()
