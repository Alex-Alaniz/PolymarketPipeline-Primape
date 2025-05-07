#!/usr/bin/env python3

"""
Examine the Polymarket API data structure to understand the market and event relationships.
"""

import json
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# API endpoint
API_URL = "https://clob.polymarket.com/markets"

def fetch_markets():
    """Fetch market data from the API."""
    logger.info(f"Fetching market data from {API_URL}")
    response = requests.get(API_URL)
    
    if response.status_code == 200:
        data = response.json()
        markets = data.get('data', [])
        logger.info(f"Successfully fetched {len(markets)} markets")
        return markets
    else:
        logger.error(f"Failed to fetch data: {response.status_code}")
        return []

def examine_market_structure(markets):
    """Examine the structure of markets to understand events and option markets."""
    has_events_count = 0
    has_option_markets_count = 0
    has_both_count = 0
    
    for idx, market in enumerate(markets[:50]):  # Look at first 50 markets only
        has_events = 'events' in market and isinstance(market['events'], list) and len(market['events']) > 0
        has_option_markets = 'option_markets' in market and isinstance(market['option_markets'], list) and len(market['option_markets']) > 0
        
        if has_events:
            has_events_count += 1
            logger.info(f"Market {idx+1} has events array with {len(market['events'])} events")
            
            # Look at first event structure
            if market['events']:
                first_event = market['events'][0]
                logger.info(f"First event keys: {list(first_event.keys())}")
                
                # Check if event has image
                if 'image' in first_event:
                    logger.info(f"Event has image URL: {first_event['image']}")
                
                # Check if event has outcomes
                if 'outcomes' in first_event and first_event['outcomes']:
                    logger.info(f"Event has {len(first_event['outcomes'])} outcomes")
                    
                    # Look at first outcome
                    first_outcome = first_event['outcomes'][0]
                    logger.info(f"First outcome keys: {list(first_outcome.keys())}")
                    
                    # Check if outcome has icon
                    if 'icon' in first_outcome:
                        logger.info(f"Outcome has icon URL: {first_outcome['icon']}")
        
        if has_option_markets:
            has_option_markets_count += 1
            logger.info(f"Market {idx+1} has option_markets array with {len(market['option_markets'])} option markets")
            
            # Look at first option market structure
            if market['option_markets']:
                first_option = market['option_markets'][0]
                logger.info(f"First option market keys: {list(first_option.keys())}")
                
                # Check if option market has icon
                if 'icon' in first_option:
                    logger.info(f"Option market has icon URL: {first_option['icon']}")
                
                if 'image' in first_option:
                    logger.info(f"Option market has image URL: {first_option['image']}")
        
        if has_events and has_option_markets:
            has_both_count += 1
            logger.info(f"Market {idx+1} has BOTH events AND option_markets arrays")
            
            # Save this market as an example
            with open(f"market_example_{idx+1}.json", "w") as f:
                json.dump(market, f, indent=2)
            logger.info(f"Saved market {idx+1} as example to market_example_{idx+1}.json")
            
            # Stop after finding first example with both arrays
            logger.info("Found market with both arrays - saving as example")
            break
    
    logger.info(f"Summary: {has_events_count} markets have events, {has_option_markets_count} have option_markets, {has_both_count} have both")

def main():
    """Main function to examine market data."""
    markets = fetch_markets()
    if not markets:
        logger.error("Failed to fetch markets")
        return 1
    
    examine_market_structure(markets)
    return 0

if __name__ == "__main__":
    main()