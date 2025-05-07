#!/usr/bin/env python3

"""
Test script for Slack message formatting.

This script tests the updated Slack formatting code to ensure
it correctly follows our image handling rules.
"""

import sys
import json
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import our messaging utilities
from utils.messaging import format_market_with_images, post_formatted_message_to_slack

def test_binary_market():
    """
    Test formatting for a binary (Yes/No) market.
    """
    print("\n\n===== TESTING BINARY MARKET =====")
    market_data = {
        "id": "binary-123",
        "question": "Will Bitcoin exceed $100,000 by the end of 2024?",
        "category": "crypto",
        "end_date": "2024-12-31T23:59:59Z",
        "is_binary": True,
        "is_multiple_option": False,
        "outcomes": ["Yes", "No"],
        "image": "https://blog.replit.com/images/site/logo.png",
        "event_image": "https://blog.replit.com/images/site/logo.png"
    }
    
    # Format the market for Slack
    message, blocks = format_market_with_images(market_data)
    
    # Print out formatted message
    print("Formatted Message:")
    print(message)
    print("\nBlocks Structure:")
    pprint(blocks)
    
    # Verify banner image
    banner_found = False
    for block in blocks:
        if block.get('type') == 'image' and 'image_url' in block:
            print(f"Found banner image URL: {block['image_url']}")
            if block['image_url'] == market_data['event_image']:
                print("✅ PASS: Binary market using correct banner image")
                banner_found = True
            else:
                print("❌ FAIL: Binary market NOT using correct banner image")
    
    if not banner_found:
        print("❌ FAIL: No banner image found in blocks")
    
    # Post to Slack if configured
    if 'SLACK_BOT_TOKEN' in globals() and 'SLACK_CHANNEL_ID' in globals():
        print("Posting to Slack for visual inspection...")
        result = post_formatted_message_to_slack(message, blocks)
        if result:
            print(f"✅ Posted to Slack with timestamp: {result}")
        else:
            print("❌ Failed to post to Slack")
    else:
        print("Slack credentials not available - skipping Slack posting")
    
    return banner_found

def test_multi_option_market():
    """
    Test formatting for a multi-option event market.
    """
    print("\n\n===== TESTING MULTI-OPTION MARKET =====")
    
    # Create test market data for a multi-option event
    market_data = {
        "id": "multi-123",
        "question": "Which team will win the Champions League 2025?",
        "category": "sports",
        "end_date": "2025-05-31T23:59:59Z",
        "is_binary": False,
        "is_multiple_option": True,
        "is_event": True,
        
        # These are the key fields for multi-option markets
        # The events array with outcomes is critical for option images
        "events": [
            {
                "id": "event-456",
                "title": "Champions League 2025",
                "image": "https://blog.replit.com/images/site/logo.png",
                "icon": "https://blog.replit.com/images/site/logo.png",
                "outcomes": [
                    {
                        "id": "real-madrid",
                        "title": "Real Madrid",
                        "icon": "https://blog.replit.com/images/site/logo.png"
                    },
                    {
                        "id": "manchester-city",
                        "title": "Manchester City",
                        "icon": "https://blog.replit.com/images/site/logo.png"
                    },
                    {
                        "id": "bayern-munich",
                        "title": "Bayern Munich",
                        "icon": "https://blog.replit.com/images/site/logo.png"
                    },
                    {
                        "id": "psg",
                        "title": "PSG",
                        "icon": "https://blog.replit.com/images/site/logo.png"
                    }
                ]
            }
        ],
        
        # These are fields set by our event filter
        "event_image": "https://blog.replit.com/images/site/logo.png",
        "event_id": "event-456",
        "event_name": "Champions League 2025",
        
        # Add options as an array so they'll be displayed
        "options": ["real-madrid", "manchester-city", "bayern-munich", "psg"],
        
        # Map option IDs to names
        "option_info": {
            "real-madrid": "Real Madrid",
            "manchester-city": "Manchester City",
            "bayern-munich": "Bayern Munich",
            "psg": "PSG"
        },
        
        # Provide the option images mapping
        "option_images": {
            "real-madrid": "https://blog.replit.com/images/site/logo.png",
            "manchester-city": "https://blog.replit.com/images/site/logo.png",
            "bayern-munich": "https://blog.replit.com/images/site/logo.png",
            "psg": "https://blog.replit.com/images/site/logo.png"
        }
    }
    
    # Format the market for Slack
    message, blocks = format_market_with_images(market_data)
    
    # Print out formatted message
    print("Formatted Message:")
    print(message)
    print("\nBlocks Structure:")
    pprint(blocks)
    
    # Verify banner image and option images
    banner_found = False
    option_image_count = 0
    
    for block in blocks:
        # Check for banner image
        if block.get('type') == 'image' and 'image_url' in block:
            print(f"Found banner image URL: {block['image_url']}")
            if block['image_url'] == market_data['event_image']:
                print("✅ PASS: Multi-option market using correct banner image")
                banner_found = True
            else:
                print("❌ FAIL: Multi-option market NOT using correct banner image")
        
        # Check for option images in fields
        if block.get('type') == 'section' and 'fields' in block:
            for field in block['fields']:
                if field.get('type') == 'mrkdwn' and 'text' in field:
                    text = field['text']
                    if 'http' in text and '://' in text:
                        print(f"Found option field with image: {text[:50]}...")
                        option_image_count += 1
    
    if not banner_found:
        print("❌ FAIL: No banner image found in blocks")
    
    print(f"Found {option_image_count} option fields with images")
    if option_image_count == len(market_data['option_images']):
        print(f"✅ PASS: All {option_image_count} option images included")
    else:
        print(f"❌ FAIL: Only {option_image_count} of {len(market_data['option_images'])} option images included")
    
    # Post to Slack if configured
    if 'SLACK_BOT_TOKEN' in globals() and 'SLACK_CHANNEL_ID' in globals():
        print("Posting to Slack for visual inspection...")
        result = post_formatted_message_to_slack(message, blocks)
        if result:
            print(f"✅ Posted to Slack with timestamp: {result}")
        else:
            print("❌ Failed to post to Slack")
    else:
        print("Slack credentials not available - skipping Slack posting")
    
    return banner_found and option_image_count == len(market_data['option_images'])

def main():
    """
    Main function to run the tests.
    """
    binary_success = test_binary_market()
    multi_option_success = test_multi_option_market()
    
    print("\n\n===== TEST SUMMARY =====")
    print(f"Binary Market Test: {'PASS' if binary_success else 'FAIL'}")
    print(f"Multi-Option Market Test: {'PASS' if multi_option_success else 'FAIL'}")
    
    if binary_success and multi_option_success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())