#!/usr/bin/env python3

"""
Test the image handling with real Polymarket API data.

This test script verifies that our image handling logic correctly processes
real market data from the Polymarket API, focusing on multi-option markets
and ensuring that:
1. Banner images use events[0].image
2. Option icons come from option_markets[].icon and events[0].outcomes[].icon
"""

import os
import sys
import json
import logging
import traceback
import requests
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Polymarket API endpoint for active markets
POLYMARKET_API = "https://clob.polymarket.com/markets"

def fetch_real_markets():
    """
    Fetch real market data from the Polymarket API.
    
    Returns:
        dict: JSON response containing markets data
    """
    try:
        logger.info(f"Fetching real market data from {POLYMARKET_API}")
        response = requests.get(POLYMARKET_API)
        
        if response.status_code == 200:
            data = response.json()
            markets = data.get('data', [])
            logger.info(f"Successfully fetched {len(markets)} markets from API")
            return markets
        else:
            logger.error(f"Failed to fetch markets. Status code: {response.status_code}")
            return []
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        traceback.print_exc()
        return []

def find_multi_option_markets(markets):
    """
    Find multi-option markets with events array from real data.
    
    Args:
        markets: List of markets from API
        
    Returns:
        list: Multi-option markets with events array
    """
    multi_option_markets = []
    
    for market in markets:
        # Check if this is a multi-option market
        has_events = (
            'events' in market and 
            isinstance(market['events'], list) and 
            len(market['events']) > 0
        )
        
        # Check if this is not a binary market
        is_not_binary = True
        outcomes = market.get('outcomes', [])
        if isinstance(outcomes, list) and sorted(outcomes) == ["No", "Yes"]:
            is_not_binary = False
        
        # This is a multi-option market if it has events and is not binary
        if has_events and is_not_binary:
            # Check if it has option_markets array
            has_option_markets = (
                'option_markets' in market and 
                isinstance(market['option_markets'], list) and 
                len(market['option_markets']) > 0
            )
            
            if has_option_markets:
                logger.info(f"Found multi-option market with events and option_markets: {market.get('question', 'Unknown')}")
                multi_option_markets.append(market)
                
                # Log the event structure
                events = market.get('events', [])
                first_event = events[0] if events else {}
                logger.info(f"First event: {first_event.get('title', 'Unknown')}")
                logger.info(f"Event image URL: {first_event.get('image', 'None')}")
                
                # Log option markets
                option_markets = market.get('option_markets', [])
                logger.info(f"Found {len(option_markets)} option markets")
                for i, option in enumerate(option_markets[:3]):  # Show first 3
                    logger.info(f"Option {i+1}: {option.get('question', 'Unknown')}")
                    logger.info(f"Option icon: {option.get('icon', 'None')}")
    
    logger.info(f"Found {len(multi_option_markets)} multi-option markets with events array")
    return multi_option_markets

def test_image_extraction(market_data):
    """Test the image extraction with real market data."""
    from utils.event_filter import process_event_images
    
    print("\n==== TESTING REAL MARKET DATA ====\n")
    print(f"Market: {market_data.get('question', 'Unknown')}")
    
    # Process the market data
    processed = process_event_images(market_data)
    
    # Print the extracted images
    print("\nExtracted Images:")
    print(f"Event Banner: {processed.get('event_image', 'None')}")
    print(f"Event Icon: {processed.get('event_icon', 'None')}")
    print("Option Images:")
    for option_id, image_url in processed.get('option_images', {}).items():
        print(f"  - {option_id}: {image_url}")
    
    # Verify the results
    events = market_data.get('events', [])
    if events and isinstance(events, list) and len(events) > 0:
        expected_banner = events[0].get('image')
        banner_correct = processed.get('event_image') == expected_banner
    else:
        banner_correct = False
        expected_banner = None
    
    # Print the verdict
    print("\nResults:")
    if banner_correct:
        print("✅ Event banner image is correct")
    else:
        print("❌ Event banner image is INCORRECT")
        print(f"  Expected: {expected_banner}")
        print(f"  Actual: {processed.get('event_image', 'None')}")
    
    # Count option images
    option_count = len(processed.get('option_images', {}))
    print(f"Extracted {option_count} option images")
    
    return banner_correct and option_count > 0

def test_slack_formatting(market_data):
    """Test the slack message formatting with real market data."""
    from utils.messaging import format_market_with_images
    
    print("\n==== TESTING SLACK FORMATTING WITH REAL MARKET DATA ====\n")
    
    # Process the data first with our image extraction
    from utils.event_filter import process_event_images
    processed = process_event_images(market_data)
    
    # Format for Slack
    message, blocks = format_market_with_images(processed)
    
    # Print the formatted message
    print("\nFormatted Slack Message:")
    print(message)
    
    # Verify banner image in blocks
    banner_found = False
    option_images_found = 0
    
    for block in blocks:
        if block.get('type') == 'image':
            image_url = block.get('image_url', '')
            if image_url == processed.get('event_image'):
                banner_found = True
                print(f"✅ Found correct banner image in blocks: {image_url}")
        
        # Check for option images in fields
        if block.get('type') == 'section' and 'fields' in block:
            for field in block['fields']:
                field_text = field.get('text', '')
                # Look for option images (format: "*Option Name* : <image_url>")
                if '*' in field_text and ' : http' in field_text:
                    option_images_found += 1
                    print(f"Found option image in field #{option_images_found}")
    
    # Final verdict
    print("\nResults:")
    if banner_found:
        print("✅ Banner image found in blocks")
    else:
        print("❌ Banner image NOT found in blocks")
    
    expected_option_count = len(processed.get('option_images', {}))
    if option_images_found == expected_option_count:
        print(f"✅ All {expected_option_count} option images found in blocks")
    else:
        print(f"❌ Only {option_images_found} of {expected_option_count} option images found in blocks")
    
    # Try to post to Slack for visual verification
    try:
        import os
        from utils.slack import post_message_with_blocks
        
        # Check if Slack credentials are available
        if os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'):
            print("\nAttempting to post to Slack for visual verification...")
            timestamp = post_message_with_blocks(message, blocks)
            
            if timestamp:
                print(f"✅ Successfully posted to Slack with timestamp: {timestamp}")
                print("Please check your Slack channel to visually verify the formatting")
            else:
                print("❌ Failed to post to Slack")
        else:
            print("\nSlack credentials not available - skipping visual verification")
    except Exception as e:
        print(f"❌ Error posting to Slack: {str(e)}")
    
    return banner_found and option_images_found > 0

def main():
    """Main function to run tests with real API data."""
    # Step 1: Fetch real market data
    markets = fetch_real_markets()
    if not markets:
        print("❌ Failed to fetch real market data. Aborting test.")
        return 1
    
    # Step 2: Find multi-option markets with events array
    multi_option_markets = find_multi_option_markets(markets)
    if not multi_option_markets:
        print("❌ No multi-option markets found with events array. Aborting test.")
        return 1
    
    # Step 3: Test with a real multi-option market
    test_market = multi_option_markets[0]  # Use the first one
    
    # Save the real data for reference
    with open("real_market_sample.json", "w") as f:
        json.dump(test_market, f, indent=2)
        print(f"Saved real market data to real_market_sample.json")
    
    # Run the tests
    extraction_success = test_image_extraction(test_market)
    formatting_success = test_slack_formatting(test_market)
    
    print("\n==== OVERALL TEST RESULTS ====")
    if extraction_success and formatting_success:
        print("✅ All tests PASSED with real API data")
        return 0
    else:
        print("❌ Some tests FAILED with real API data")
        return 1

if __name__ == "__main__":
    sys.exit(main())