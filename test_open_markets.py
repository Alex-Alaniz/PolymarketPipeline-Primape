#!/usr/bin/env python3

"""
Test script for fetching truly open markets from Polymarket API.

This script specifically attempts to find markets that are still accepting orders
but not yet expired, using additional parameters beyond the standard API filters.
"""

import requests
import json
import logging
import sys
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("open_markets_test")

def fetch_open_markets_by_time():
    """
    Fetch markets that have end dates in the future, checking date strings.
    """
    logger.info("Fetching markets with future end dates...")
    
    # Endpoint for fetching markets
    endpoint = "https://clob.polymarket.com/markets"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        # Get current time in ISO format
        now = datetime.now()
        one_month_future = now + timedelta(days=30)
        
        # Make the request
        response = requests.get(endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "data" in data and isinstance(data["data"], list):
                markets = data["data"]
                logger.info(f"Total markets: {len(markets)}")
                
                # Markets with future game_start_time
                markets_with_future_start = []
                # Markets with future end_date_iso
                markets_with_future_end = []
                # Markets accepting orders
                markets_accepting_orders = []
                
                for market in markets:
                    # Check accepting_orders flag
                    if market.get("accepting_orders", False):
                        markets_accepting_orders.append(market)
                    
                    # Check game_start_time if present
                    if "game_start_time" in market and market["game_start_time"]:
                        try:
                            start_time = market["game_start_time"].replace("Z", "+00:00")
                            start_dt = datetime.fromisoformat(start_time)
                            if start_dt > now:
                                markets_with_future_start.append(market)
                        except Exception as e:
                            logger.debug(f"Error parsing game_start_time: {e}")
                    
                    # Check end_date_iso if present
                    if "end_date_iso" in market and market["end_date_iso"]:
                        try:
                            end_time = market["end_date_iso"].replace("Z", "+00:00")
                            end_dt = datetime.fromisoformat(end_time)
                            if end_dt > now:
                                markets_with_future_end.append(market)
                        except Exception as e:
                            logger.debug(f"Error parsing end_date_iso: {e}")
                
                logger.info(f"Markets accepting orders: {len(markets_accepting_orders)}")
                logger.info(f"Markets with future game start time: {len(markets_with_future_start)}")
                logger.info(f"Markets with future end date: {len(markets_with_future_end)}")
                
                # Find markets that are both accepting orders AND have future dates
                accepting_and_future_start = [m for m in markets_accepting_orders if m in markets_with_future_start]
                accepting_and_future_end = [m for m in markets_accepting_orders if m in markets_with_future_end]
                
                logger.info(f"Markets accepting orders AND with future start: {len(accepting_and_future_start)}")
                logger.info(f"Markets accepting orders AND with future end: {len(accepting_and_future_end)}")
                
                # Show some examples of markets accepting orders
                if markets_accepting_orders:
                    logger.info("\nExamples of markets accepting orders:")
                    for i, market in enumerate(markets_accepting_orders[:5]):
                        print(f"{i+1}. {market.get('question', 'No question')}")
                        print(f"   - Condition ID: {market.get('condition_id', 'N/A')}")
                        print(f"   - Game start: {market.get('game_start_time', 'N/A')}")
                        print(f"   - End date: {market.get('end_date_iso', 'N/A')}")
                
                # Return markets accepting orders for further use
                return markets_accepting_orders
            
            else:
                logger.error("No 'data' field in response")
        else:
            logger.error(f"Failed to fetch markets: HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
    
    return []

def generate_curl_for_open_markets():
    """
    Generate curl commands that are more likely to return only open markets.
    """
    logger.info("\n\nCURL COMMANDS FOR FETCHING OPEN MARKETS:")
    logger.info("==========================================")
    
    # Generate current timestamp in ISO format
    now = datetime.now().isoformat().replace('+00:00', 'Z')
    
    # Define endpoints with different filtering parameters
    endpoints = [
        # Filter with accepting_orders=true
        "https://clob.polymarket.com/markets?accepting_orders=true",
        # Filter by active and accepting orders
        "https://clob.polymarket.com/markets?active=true&accepting_orders=true",
        # Limiting to 50 markets
        "https://clob.polymarket.com/markets?accepting_orders=true&limit=50"
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
    logger.info("Starting Polymarket open markets test")
    
    # Fetch truly open markets by analyzing timestamps
    open_markets = fetch_open_markets_by_time()
    
    # Generate curl commands for open markets
    generate_curl_for_open_markets()
    
    # Final recommendation
    logger.info(f"\n\nBased on testing, the recommended approach is:")
    logger.info(f"1. Use the 'accepting_orders=true' parameter to get markets still accepting orders")
    logger.info(f"2. Further filter the results in your code for:")
    logger.info(f"   - active=true")
    logger.info(f"   - game_start_time is in the future")
    logger.info(f"   - end_date_iso is in the future (if available)")
    
    logger.info("\nCompleted open markets test")

if __name__ == "__main__":
    main()
