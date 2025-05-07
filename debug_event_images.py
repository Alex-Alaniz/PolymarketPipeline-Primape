#!/usr/bin/env python3

"""
Debug Event Image Handling

This script analyzes a sample of markets from the API to help debug
our image handling logic for event-based markets.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List
import requests
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our event filter module
from utils.event_filter import filter_inactive_events, process_event_images

def fetch_sample_markets():
    """
    Fetch a sample of markets from the Polymarket API.
    
    Returns:
        List[Dict]: List of market data dictionaries
    """
    logger.info("Fetching sample markets from Polymarket API...")
    
    # Try to load from cache first for faster testing
    cache_file = "market_sample_cache.json"
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                markets = json.load(f)
                logger.info(f"Loaded {len(markets)} markets from cache")
                return markets
        except Exception as e:
            logger.warning(f"Error loading cache: {str(e)}")
    
    # Fallback to API call
    try:
        # Use the gamma API endpoint
        url = "https://gamma-api.polymarket.com/markets"
        params = {
            "sort": "volume",
            "limit": 50,
            "filter": "open",
            "outcome": "unresolved"
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            data = response.json()
            # The API might return data directly or in a 'data' field
            if isinstance(data, dict) and 'data' in data:
                markets = data['data']
            else:
                markets = data
            
            # Cache for future runs
            with open(cache_file, 'w') as f:
                json.dump(markets, f)
                
            logger.info(f"Fetched {len(markets)} markets from API")
            return markets
        else:
            logger.error(f"API error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        return []

def analyze_market_images(market_data: Dict[str, Any]):
    """
    Analyze the image structure of a market.
    
    Args:
        market_data: Raw market data dictionary
    """
    market_id = market_data.get('id', 'Unknown')
    question = market_data.get('question', 'Unknown question')
    
    # Log market info
    logger.info(f"\n\n======= MARKET: {market_id} =======")
    logger.info(f"Question: {question}")
    logger.info(f"Is multiple choice: {market_data.get('is_multiple_choice', False)}")
    
    # Check if market has events
    has_events = 'events' in market_data and isinstance(market_data['events'], list) and len(market_data['events']) > 0
    logger.info(f"Has events array: {has_events}")
    
    # Is this a binary market? (Yes/No outcomes)
    outcomes_raw = market_data.get("outcomes", "[]")
    is_binary = False
    try:
        if isinstance(outcomes_raw, str):
            outcomes = json.loads(outcomes_raw)
        else:
            outcomes = outcomes_raw
            
        # Check if outcomes are exactly ["Yes", "No"]
        if isinstance(outcomes, list) and sorted(outcomes) == ["No", "Yes"]:
            is_binary = True
    except Exception as e:
        logger.error(f"Error checking binary market: {str(e)}")
    
    logger.info(f"Is binary market (Yes/No): {is_binary}")
    
    # Market-level image
    logger.info(f"Market-level image: {market_data.get('image', 'None')[:50]}...")
    
    # Go through event array if exists
    if has_events:
        logger.info("\nEvents:")
        for i, event in enumerate(market_data['events']):
            event_id = event.get('id', 'Unknown')
            event_title = event.get('title', 'Untitled event')
            event_image = event.get('image', 'None')
            event_icon = event.get('icon', 'None')
            
            logger.info(f"\nEvent #{i+1}: {event_id}")
            logger.info(f"  Title: {event_title}")
            logger.info(f"  Image: {event_image[:50]}...")
            logger.info(f"  Icon: {event_icon[:50]}...")
            
            # Check outcomes for this event
            if 'outcomes' in event and isinstance(event['outcomes'], list):
                logger.info(f"  Outcomes:")
                for j, outcome in enumerate(event['outcomes']):
                    if not isinstance(outcome, dict):
                        continue
                        
                    outcome_id = outcome.get('id', 'Unknown')
                    outcome_title = outcome.get('title') or outcome.get('name', 'Untitled')
                    outcome_image = outcome.get('image', 'None')
                    outcome_icon = outcome.get('icon', 'None')
                    
                    logger.info(f"    Outcome #{j+1}: {outcome_id}")
                    logger.info(f"      Title: {outcome_title}")
                    logger.info(f"      Image: {outcome_image[:50]}...")
                    logger.info(f"      Icon: {outcome_icon[:50]}...")

def process_test_market(market_data: Dict[str, Any]):
    """
    Process a test market with our image handling logic.
    
    Args:
        market_data: Raw market data dictionary
    """
    # First do basic market analysis
    analyze_market_images(market_data)
    
    # Now apply our processing logic
    logger.info("\n----- PROCESSING WITH OUR LOGIC -----")
    
    # Step 1: Filter inactive events
    filtered_market = filter_inactive_events(market_data)
    logger.info(f"Events after filtering: {len(filtered_market.get('events', []))}")
    
    # Step 2: Process images
    processed_market = process_event_images(filtered_market)
    
    # Show results
    logger.info("\n----- RESULTS -----")
    logger.info(f"Is binary: {processed_market.get('is_binary', False)}")
    logger.info(f"Is multiple: {processed_market.get('is_multiple_option', False)}")
    logger.info(f"Event image: {processed_market.get('event_image', 'None')[:50]}...")
    logger.info(f"Event icon: {processed_market.get('event_icon', 'None')[:50]}...")
    
    # Show option images
    option_images = processed_market.get('option_images', {})
    if option_images:
        logger.info(f"Option images: {len(option_images)}")
        for name, url in option_images.items():
            logger.info(f"  {name}: {url[:50]}...")
    else:
        logger.info("No option images found")
    
    return processed_market

def main():
    """
    Main function to debug event image handling.
    """
    # Step 1: Fetch sample markets
    markets = fetch_sample_markets()
    if not markets:
        logger.error("Failed to fetch markets")
        return 1
    
    # Step 2: Find a good example of a multi-option market
    multi_option_market = None
    binary_market = None
    
    for market in markets:
        if market.get('is_multiple_choice', False) and 'events' in market:
            multi_option_market = market
            logger.info(f"Found multi-option market: {market.get('question', 'Unknown')}")
            
        outcomes_raw = market.get("outcomes", "[]")
        try:
            if isinstance(outcomes_raw, str):
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
                
            if isinstance(outcomes, list) and sorted(outcomes) == ["No", "Yes"]:
                binary_market = market
                logger.info(f"Found binary market: {market.get('question', 'Unknown')}")
        except:
            pass
            
        # If we found both types, we can stop
        if multi_option_market and binary_market:
            break
    
    # Step 3: Process each example
    if binary_market:
        logger.info("\n\n============ BINARY MARKET ============")
        process_test_market(binary_market)
    else:
        logger.warning("No binary market found")
    
    if multi_option_market:
        logger.info("\n\n============ MULTI-OPTION MARKET ============")
        process_test_market(multi_option_market)
    else:
        logger.warning("No multi-option market found")
    
    logger.info("\n✅ Debug complete")
    return 0

if __name__ == "__main__":
    sys.exit(main())