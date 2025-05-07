#!/usr/bin/env python3

"""
Test script for event image handling.

This script tests the new event image handling logic with sample data
to ensure it correctly follows the image handling rules.
"""

import json
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our event filter
from utils.event_filter import process_event_images

def create_binary_market():
    """
    Create a sample binary market.
    """
    return {
        "id": "binary-123",
        "question": "Will Bitcoin exceed $100,000 by the end of 2024?",
        "outcomes": ["Yes", "No"],
        "image": "https://example.com/bitcoin-banner.jpg",
        "icon": "https://example.com/bitcoin-icon.jpg"
    }

def create_multi_option_market():
    """
    Create a sample multi-option market with events.
    """
    return {
        "id": "multi-123",
        "question": "Which team will win the Champions League 2025?",
        "is_multiple_choice": True,
        "events": [
            {
                "id": "event-123",
                "title": "Champions League 2025",
                "image": "https://example.com/champions-league-banner.jpg",
                "icon": "https://example.com/champions-league-icon.jpg",
                "active": True,
                "closed": False,
                "outcomes": [
                    {
                        "id": "real-madrid",
                        "title": "Real Madrid",
                        "image": "https://example.com/real-madrid-image.jpg",
                        "icon": "https://example.com/real-madrid-icon.jpg"
                    },
                    {
                        "id": "manchester-city",
                        "title": "Manchester City",
                        "image": "https://example.com/man-city-image.jpg",
                        "icon": "https://example.com/man-city-icon.jpg"
                    },
                    {
                        "id": "bayern-munich",
                        "title": "Bayern Munich",
                        "image": "https://example.com/bayern-image.jpg",
                        "icon": "https://example.com/bayern-icon.jpg"
                    },
                    {
                        "id": "psg",
                        "title": "PSG",
                        "image": "https://example.com/psg-image.jpg",
                        "icon": "https://example.com/psg-icon.jpg"
                    }
                ]
            }
        ]
    }

def test_binary_market():
    """
    Test image handling for binary markets.
    """
    print("\n\n===== Testing Binary Market =====")
    market = create_binary_market()
    
    # Process the market
    processed = process_event_images(market)
    
    # Check the results
    print("\nBinary Market Results:")
    print(f"Is Binary: {processed.get('is_binary', False)}")
    print(f"Is Multiple Option: {processed.get('is_multiple_option', False)}")
    print(f"Event Image: {processed.get('event_image')}")
    print(f"Option Images: {len(processed.get('option_images', {}))}")
    
    # Verify rules
    if processed.get('event_image') == market['image']:
        print("✅ PASS: Binary market uses market-level image as banner")
    else:
        print("❌ FAIL: Binary market does not use market-level image as banner")
    
    if len(processed.get('option_images', {})) == 0:
        print("✅ PASS: Binary market has no option images")
    else:
        print("❌ FAIL: Binary market has option images, but should not")

def test_multi_option_market():
    """
    Test image handling for multi-option markets with events.
    """
    print("\n\n===== Testing Multi-Option Market =====")
    market = create_multi_option_market()
    
    # Process the market
    processed = process_event_images(market)
    
    # Check the results
    print("\nMulti-Option Market Results:")
    print(f"Is Binary: {processed.get('is_binary', False)}")
    print(f"Is Multiple Option: {processed.get('is_multiple_option', False)}")
    print(f"Event Image: {processed.get('event_image')}")
    print(f"Event Icon: {processed.get('event_icon')}")
    print(f"Option Images: {len(processed.get('option_images', {}))}")
    for name, url in processed.get('option_images', {}).items():
        print(f"  - {name}: {url}")
    
    # Verify rules
    if processed.get('event_image') == market['events'][0]['image']:
        print("✅ PASS: Multi-option market uses events[0].image as banner")
    else:
        print("❌ FAIL: Multi-option market does not use events[0].image as banner")
    
    if processed.get('event_icon') == market['events'][0]['icon']:
        print("✅ PASS: Multi-option market uses events[0].icon")
    else:
        print("❌ FAIL: Multi-option market does not use events[0].icon")
    
    # Check that we have one icon per outcome
    outcome_count = len(market['events'][0]['outcomes'])
    if len(processed.get('option_images', {})) == outcome_count:
        print(f"✅ PASS: Multi-option market has {outcome_count} option images")
    else:
        print(f"❌ FAIL: Multi-option market has {len(processed.get('option_images', {}))} option images, should have {outcome_count}")

def main():
    """
    Main function to run the tests.
    """
    # Test binary market
    test_binary_market()
    
    # Test multi-option market
    test_multi_option_market()
    
    print("\n\n✅ Tests completed")
    return 0

if __name__ == "__main__":
    main()