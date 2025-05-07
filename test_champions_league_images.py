#!/usr/bin/env python3
"""
Test script for fixing Champions League market image issues.

This script tests the image handling for Champions League market data,
focusing on the team logo issue observed in the Slack messages.
"""

import json
import logging
import os
from pprint import pprint

# Import our image processing utilities
from utils.event_filter import process_event_images
from utils.messaging import format_market_with_images, is_slack_accessible_url
from utils.slack import post_message_with_blocks

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data for Champions League market with teams
# This is based on what we observed in the failing image
CHAMPIONS_LEAGUE_DATA = {
    "question": "Which team will win the Champions League 2025?",
    "category": "sports",
    "is_multiple_option": True,
    "is_binary": False,
    "is_event": True,
    "endDate": "2025-05-31T23:59:59Z",
    "events": [
        {
            "id": "12673",
            "ticker": "champions-league-winner",
            "slug": "champions-league-winner",
            "title": "Which team will win the Champions League 2025?",
            "description": "This market is about predicting the winner of the UEFA Champions League for the 2024-2025 season.",
            "resolutionSource": "",
            "startDate": "2024-09-18T16:52:55.612547Z",
            "creationDate": "2024-09-18T16:52:55.612533Z",
            "endDate": "2025-05-31T23:59:59Z",
            # Use Imgur for Champions League banner
            "image": "https://i.imgur.com/HGFLYMJ.jpg",  # UEFA Champions League logo
            "outcomes": [
                {
                    "id": "real-madrid",
                    "title": "Real Madrid",
                    "icon": "https://i.imgur.com/HnG0ZAw.png",  # Real Madrid logo
                },
                {
                    "id": "manchester-city",
                    "title": "Manchester City",
                    "icon": "https://i.imgur.com/X7Vtf03.png",  # Man City logo
                },
                {
                    "id": "bayern-munich",
                    "title": "Bayern Munich",
                    "icon": "https://i.imgur.com/ZQKNPsW.png",  # Bayern Munich logo
                },
                {
                    "id": "psg",
                    "title": "PSG",
                    "icon": "https://i.imgur.com/c5xZGjX.png",  # PSG logo
                }
            ]
        }
    ],
    "option_markets": [
        {
            "id": "507400",
            "question": "Will Real Madrid win the Champions League?",
            "conditionId": "0x99a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713c8",
            "slug": "will-real-madrid-win-the-champions-league",
            "resolutionSource": "",
            "endDate": "2025-05-31T23:59:59Z",
            "liquidity": "149845.1908",
            "startDate": "2024-09-18T16:34:53.5892Z",
            "icon": "https://i.imgur.com/HnG0ZAw.png",  # Real Madrid logo
        },
        {
            "id": "507401",
            "question": "Will Manchester City win the Champions League?",
            "conditionId": "0x88a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713c9",
            "slug": "will-manchester-city-win-the-champions-league",
            "resolutionSource": "",
            "endDate": "2025-05-31T23:59:59Z",
            "liquidity": "159845.1908",
            "startDate": "2024-09-18T16:34:53.5892Z",
            "icon": "https://i.imgur.com/X7Vtf03.png",  # Man City logo
        },
        {
            "id": "507402",
            "question": "Will Bayern Munich win the Champions League?",
            "conditionId": "0x88a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713d0",
            "slug": "will-bayern-munich-win-the-champions-league",
            "resolutionSource": "",
            "endDate": "2025-05-31T23:59:59Z",
            "liquidity": "129845.1908",
            "startDate": "2024-09-18T16:34:53.5892Z",
            "icon": "https://i.imgur.com/ZQKNPsW.png",  # Bayern Munich logo
        },
        {
            "id": "507403",
            "question": "Will PSG win the Champions League?",
            "conditionId": "0x88a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713d1",
            "slug": "will-psg-win-the-champions-league",
            "resolutionSource": "",
            "endDate": "2025-05-31T23:59:59Z",
            "liquidity": "119845.1908",
            "startDate": "2024-09-18T16:34:53.5892Z",
            "icon": "https://i.imgur.com/c5xZGjX.png",  # PSG logo
        }
    ]
}

def test_champions_league_market():
    """Test formatting of Champions League multi-option market with team icons."""
    print("\n==== TESTING CHAMPIONS LEAGUE MARKET WITH TEAM ICONS ====\n")
    
    # Verify URLs are Slack-accessible
    print("Verifying URL accessibility:")
    for url_name, url in {
        "Banner": CHAMPIONS_LEAGUE_DATA["events"][0]["image"],
        "Real Madrid Icon": CHAMPIONS_LEAGUE_DATA["events"][0]["outcomes"][0]["icon"],
        "Man City Icon": CHAMPIONS_LEAGUE_DATA["events"][0]["outcomes"][1]["icon"],
        "Bayern Munich Icon": CHAMPIONS_LEAGUE_DATA["events"][0]["outcomes"][2]["icon"],
        "PSG Icon": CHAMPIONS_LEAGUE_DATA["events"][0]["outcomes"][3]["icon"],
    }.items():
        is_accessible = is_slack_accessible_url(url)
        print(f"- {url_name}: {'✅ Accessible' if is_accessible else '❌ Not accessible'} ({url})")
    
    # Process the data with our image extraction logic
    processed_data = process_event_images(CHAMPIONS_LEAGUE_DATA)
    
    # Format for Slack
    message, blocks = format_market_with_images(processed_data)
    
    # Print the formatted message
    print("\nFormatted Message:")
    print(message)
    print("\nFormatted Blocks (first few):")
    for i, block in enumerate(blocks[:8]):
        print(f"Block {i}: {json.dumps(block, indent=2)}")
    print(f"... and {len(blocks) - 8} more blocks")
    
    # Try to post to Slack
    try:
        if os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'):
            print("\nAttempting to post to Slack...")
            timestamp = post_message_with_blocks(message, blocks)
            
            if timestamp:
                print(f"✅ Successfully posted to Slack with timestamp: {timestamp}")
                print("Please check Slack to verify correct image display")
                
                # Count image blocks
                image_blocks = [b for b in blocks if b.get('type') == 'image']
                print(f"Total image blocks sent: {len(image_blocks)}")
                for i, img in enumerate(image_blocks):
                    print(f"Image {i+1}: {img.get('alt_text')} - {img.get('image_url')}")
                
                return True
            else:
                print("❌ Failed to post to Slack")
        else:
            print("\nSlack credentials not available - skipping posting")
    except Exception as e:
        print(f"❌ Error posting to Slack: {str(e)}")
    
    return False

def simulate_broken_icons():
    """
    Simulate the issue observed in polyp.png where team icons don't load.
    
    This function replaces Imgur URLs with non-Slack-accessible URLs to 
    reproduce the error condition for debugging.
    """
    # Make a deep copy of the data first
    import copy
    broken_data = copy.deepcopy(CHAMPIONS_LEAGUE_DATA)
    
    # Replace icon URLs with ones we know will fail
    broken_domain = "https://example.org/non-slack-accessible"
    
    # Replace in events outcomes
    for outcome in broken_data["events"][0]["outcomes"]:
        outcome["icon"] = f"{broken_domain}/{outcome['id']}.png"
    
    # Replace in option markets
    for option in broken_data["option_markets"]:
        option["icon"] = f"{broken_domain}/{option['id']}.png"
    
    # Process and format with broken URLs
    processed_data = process_event_images(broken_data)
    message, blocks = format_market_with_images(processed_data)
    
    # Log the blocks with broken image URLs
    print("\n==== SIMULATING BROKEN TEAM ICONS ====\n")
    print("This simulates the issue seen in the screenshot.")
    
    # Count image blocks
    image_blocks = [b for b in blocks if b.get('type') == 'image']
    print(f"Total image blocks with broken URLs: {len(image_blocks)}")
    for i, img in enumerate(image_blocks):
        url = img.get('image_url')
        is_accessible = is_slack_accessible_url(url)
        print(f"Image {i+1}: {img.get('alt_text')} - {'✅' if is_accessible else '❌'} {url}")
    
    # Print the formatted blocks
    print("\nFormatted Message with broken URLs:")
    print(message)
    
    return processed_data

def main():
    """Main test function."""
    # Test with working Imgur URLs
    success = test_champions_league_market()
    
    # Simulate the broken icons issue for debugging
    broken_data = simulate_broken_icons()
    
    if success:
        print("\n✅ TEST PASSED - Successfully posted formatted message to Slack")
        print("Please verify all team logos appear correctly in Slack")
        return 0
    else:
        print("\n❌ TEST FAILED - Could not post formatted message to Slack")
        return 1

if __name__ == "__main__":
    main()