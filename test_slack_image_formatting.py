#!/usr/bin/env python3

"""
Test the improved Slack image formatting with La Liga event data.

This script tests the new approach for image display in Slack which:
1. Uses events[0].image for event banner image
2. Displays option icons as separate image blocks for better rendering
"""

import json
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data based on La Liga market structure
LA_LIGA_DATA = {
    "question": "La Liga Winner 2024-2025",
    "category": "sports",
    "is_multiple_option": True,
    "is_binary": False,
    "is_event": True,
    "events": [
        {
            "id": "12672",
            "ticker": "la-liga-winner",
            "slug": "la-liga-winner",
            "title": "La Liga Winner 2024-2025",
            "description": "This is a market on predicting the winner of the La Liga football league for the current season.",
            "resolutionSource": "",
            "startDate": "2024-09-18T16:52:55.612547Z",
            "creationDate": "2024-09-18T16:52:55.612533Z",
            "endDate": "2025-05-25T12:00:00Z",
            # Using imgur which is known to be Slack-accessible
            "image": "https://i.imgur.com/Yk6Vvcq.jpg",  # La Liga logo
            "outcomes": [
                {
                    "id": "real-madrid",
                    "title": "Real Madrid",
                    "icon": "https://i.imgur.com/HnG0ZAw.png",  # Madrid logo
                },
                {
                    "id": "barcelona",
                    "title": "Barcelona",
                    "icon": "https://i.imgur.com/8mSafpx.png",  # Barcelona logo
                },
            ]
        }
    ],
    "option_markets": [
        {
            "id": "507396",
            "question": "Will Barcelona win La Liga?",
            "conditionId": "0x99a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713c7",
            "slug": "will-barcelona-win-la-liga",
            "resolutionSource": "",
            "endDate": "2025-05-25T12:00:00Z",
            "liquidity": "149845.1908",
            "startDate": "2024-09-18T16:34:53.5892Z",
            "icon": "https://i.imgur.com/8mSafpx.png",  # Barcelona logo
        },
        {
            "id": "507395",
            "question": "Will Real Madrid win La Liga?",
            "conditionId": "0x88a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713c8",
            "slug": "will-real-madrid-win-la-liga",
            "resolutionSource": "",
            "endDate": "2025-05-25T12:00:00Z",
            "liquidity": "159845.1908",
            "startDate": "2024-09-18T16:34:53.5892Z",
            "icon": "https://i.imgur.com/HnG0ZAw.png",  # Madrid logo
        }
    ]
}

# Add a binary market example for completeness
BITCOIN_DATA = {
    "id": "507394",
    "question": "Will Bitcoin exceed $100,000 by end of 2025?",
    "category": "crypto",
    "outcomes": ["Yes", "No"],
    "endDate": "2025-12-31T23:59:59Z",
    "is_binary": True,
    "is_multiple_option": False,
    "image": "https://i.imgur.com/oBgMoXn.png"  # Bitcoin logo from imgur
}

def test_multi_option_market():
    """Test formatting of a multi-option market with event banner and option icons."""
    from utils.event_filter import process_event_images
    from utils.messaging import format_market_with_images
    
    print("\n==== TESTING MULTI-OPTION MARKET FORMATTING ====\n")
    
    # Process the data with our image extraction logic
    processed_data = process_event_images(LA_LIGA_DATA)
    
    # Format for Slack
    message, blocks = format_market_with_images(processed_data)
    
    # Print the formatted blocks
    print("Formatted Message:")
    print(message)
    print("\nFormatted Blocks:")
    pprint(blocks)
    
    # Verify crucial elements
    banner_block = None
    option_image_blocks = []
    option_names_section = None
    
    for block in blocks:
        # Check for banner image
        if block.get('type') == 'image' and block.get('alt_text') == 'Event banner':
            banner_block = block
            print(f"\n✅ Found event banner image: {block.get('image_url')}")
        
        # Check for option icon images (separate blocks)
        elif block.get('type') == 'image' and block.get('alt_text', '').startswith('Option icon for'):
            option_image_blocks.append(block)
            print(f"✅ Found option icon image: {block.get('image_url')}")
        
        # Check for option names section
        elif block.get('type') == 'section' and block.get('fields'):
            option_names = [
                field.get('text') for field in block.get('fields', [])
                if '*' in field.get('text', '')
            ]
            if option_names:
                option_names_section = block
                print(f"\n✅ Found option names section with {len(option_names)} options:")
                for name in option_names:
                    print(f"  - {name}")
    
    # Final verdict
    print("\nVerification Results:")
    if banner_block:
        print("✅ Event banner image correctly displayed as image block")
    else:
        print("❌ Event banner image not found")
    
    if option_image_blocks:
        print(f"✅ Option icons correctly displayed as separate image blocks ({len(option_image_blocks)} found)")
    else:
        print("❌ No option icon images found")
    
    if option_names_section:
        print("✅ Option names correctly displayed in a fields section")
    else:
        print("❌ Option names section not found")
    
    # Try to post to Slack for visual verification
    try:
        import os
        from utils.slack import post_message_with_blocks
        
        # Check if we have Slack credentials
        if os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'):
            print("\nAttempting to post to Slack for visual verification...")
            timestamp = post_message_with_blocks(message, blocks)
            
            if timestamp:
                print(f"✅ Successfully posted to Slack with timestamp: {timestamp}")
                print("Please check Slack to verify correct image display")
            else:
                print("❌ Failed to post to Slack")
        else:
            print("\nSlack credentials not available - skipping visual verification")
    except Exception as e:
        print(f"❌ Error posting to Slack: {str(e)}")
    
    return banner_block is not None and len(option_image_blocks) > 0 and option_names_section is not None

def test_binary_market():
    """Test formatting of a binary market with a single banner image."""
    from utils.event_filter import process_event_images
    from utils.messaging import format_market_with_images
    
    print("\n==== TESTING BINARY MARKET FORMATTING ====\n")
    
    # Process the data with our image extraction logic
    processed_data = process_event_images(BITCOIN_DATA)
    
    # Format for Slack
    message, blocks = format_market_with_images(processed_data)
    
    # Print the formatted blocks
    print("Formatted Message:")
    print(message)
    print("\nFormatted Blocks:")
    pprint(blocks)
    
    # Verify crucial elements
    banner_block = None
    options_section = None
    
    for block in blocks:
        # Check for banner image
        if block.get('type') == 'image' and block.get('alt_text') == 'Event banner':
            banner_block = block
            print(f"\n✅ Found banner image: {block.get('image_url')}")
        
        # Check for Yes/No options section
        elif block.get('type') == 'section' and block.get('text', {}).get('text', '').startswith('*Options:*'):
            options_text = block.get('text', {}).get('text', '')
            options_section = block
            print(f"\n✅ Found options section: {options_text}")
    
    # Final verdict
    print("\nVerification Results:")
    if banner_block:
        print("✅ Banner image correctly displayed as image block")
    else:
        print("❌ Banner image not found")
    
    if options_section:
        print("✅ Yes/No options correctly displayed as text")
    else:
        print("❌ Options section not found")
    
    # Try to post to Slack for visual verification
    try:
        import os
        from utils.slack import post_message_with_blocks
        
        # Check if we have Slack credentials
        if os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'):
            print("\nAttempting to post to Slack for visual verification...")
            timestamp = post_message_with_blocks(message, blocks)
            
            if timestamp:
                print(f"✅ Successfully posted to Slack with timestamp: {timestamp}")
                print("Please check Slack to verify correct image display")
            else:
                print("❌ Failed to post to Slack")
        else:
            print("\nSlack credentials not available - skipping visual verification")
    except Exception as e:
        print(f"❌ Error posting to Slack: {str(e)}")
    
    return banner_block is not None and options_section is not None

def main():
    """Run both tests and report overall results."""
    multi_option_success = test_multi_option_market()
    binary_success = test_binary_market()
    
    print("\n==== OVERALL TEST RESULTS ====")
    if multi_option_success and binary_success:
        print("✅ All tests PASSED")
        return 0
    else:
        print("❌ Some tests FAILED")
        return 1

if __name__ == "__main__":
    main()