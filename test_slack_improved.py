#!/usr/bin/env python3
"""
Test improved Slack image posting with better URL validation.

This script tests the enhanced Slack message formatting with:
1. URL validation for all image fields
2. Separate option icons as distinct image blocks
3. Filtering to ensure only Slack-accessible URLs are used
"""

import os
import logging
import json
from pprint import pprint

from utils.event_filter import process_event_images
from utils.messaging import format_market_with_images, is_slack_accessible_url
from utils.slack import post_message_with_blocks

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test data for Polymarket events
POLYMARKET_DATA = {
    "question": "US Presidential Election 2024 Winner",
    "category": "politics",
    "is_multiple_option": True,
    "is_binary": False,
    "is_event": True,
    "events": [
        {
            "id": "12675",
            "ticker": "us-election-2024",
            "slug": "us-election-2024-winner",
            "title": "US Presidential Election 2024",
            "description": "This market predicts the winner of the 2024 US Presidential Election.",
            "resolutionSource": "",
            "startDate": "2024-05-07T00:00:00Z",
            "creationDate": "2024-05-07T00:00:00Z",
            "endDate": "2024-11-05T23:59:59Z",
            # Using a known Slack-accessible domain
            "image": "https://i.imgur.com/us_election2024.png",
            "outcomes": [
                {
                    "id": "harris",
                    "title": "Kamala Harris",
                    "icon": "https://i.imgur.com/harris_icon.png",
                },
                {
                    "id": "trump",
                    "title": "Donald Trump",
                    "icon": "https://i.imgur.com/trump_icon.png",
                },
                {
                    "id": "other",
                    "title": "Other Candidate",
                    "icon": "https://i.imgur.com/other_candidate.png",
                }
            ]
        }
    ],
    "option_markets": [
        {
            "id": "507501",
            "question": "Will Kamala Harris win the 2024 US Presidential Election?",
            "conditionId": "0x99a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713d1",
            "slug": "will-harris-win-2024",
            "resolutionSource": "",
            "endDate": "2024-11-05T23:59:59Z",
            "liquidity": "250000.00",
            "startDate": "2024-05-07T00:00:00Z",
            "icon": "https://i.imgur.com/harris_icon.png",
        },
        {
            "id": "507502",
            "question": "Will Donald Trump win the 2024 US Presidential Election?",
            "conditionId": "0x88a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713d2",
            "slug": "will-trump-win-2024",
            "resolutionSource": "",
            "endDate": "2024-11-05T23:59:59Z",
            "liquidity": "280000.00",
            "startDate": "2024-05-07T00:00:00Z",
            "icon": "https://i.imgur.com/trump_icon.png",
        },
        {
            "id": "507503",
            "question": "Will another candidate win the 2024 US Presidential Election?",
            "conditionId": "0x77a76eb4959604e2a1b7c6dedf1f75fb19491df21deb746388a2b65c0c1713d3",
            "slug": "will-other-win-2024",
            "resolutionSource": "",
            "endDate": "2024-11-05T23:59:59Z",
            "liquidity": "50000.00",
            "startDate": "2024-05-07T00:00:00Z",
            "icon": "https://i.imgur.com/other_candidate.png",
        }
    ]
}

# Test with URLs that are definitely Slack-accessible
def update_to_real_urls(data):
    """Replace mock URLs with real, working URLs."""
    # Real URLs that should work with Slack
    real_urls = {
        "election": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/Flag_of_the_United_States_of_America.svg/1200px-Flag_of_the_United_States_of_America.svg.png",
        "harris": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/46/Kamala_Harris_2021.jpg/800px-Kamala_Harris_2021.jpg",
        "trump": "https://upload.wikimedia.org/wikipedia/commons/thumb/5/56/Donald_Trump_official_portrait.jpg/220px-Donald_Trump_official_portrait.jpg",
        "other": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b9/US_Capitol_west_side.JPG/220px-US_Capitol_west_side.JPG"
    }
    
    # Update banner image
    data["events"][0]["image"] = real_urls["election"]
    
    # Update outcome icons
    for outcome in data["events"][0]["outcomes"]:
        if "harris" in outcome["id"]:
            outcome["icon"] = real_urls["harris"]
        elif "trump" in outcome["id"]:
            outcome["icon"] = real_urls["trump"]
        else:
            outcome["icon"] = real_urls["other"]
    
    # Update option market icons
    for option in data["option_markets"]:
        if "Harris" in option["question"]:
            option["icon"] = real_urls["harris"]
        elif "Trump" in option["question"]:
            option["icon"] = real_urls["trump"]
        else:
            option["icon"] = real_urls["other"]
    
    return data

def test_multi_option_market():
    """Test formatting of multi-option market with real, accessible images."""
    print("\n==== TESTING MULTI-OPTION MARKET WITH SLACK-ACCESSIBLE IMAGES ====\n")
    
    # Update data with real URLs
    test_data = update_to_real_urls(POLYMARKET_DATA.copy())
    
    # Verify URLs are Slack-accessible
    print("Verifying URL accessibility:")
    for url_name, url in {
        "Banner": test_data["events"][0]["image"],
        "Harris Icon (events)": test_data["events"][0]["outcomes"][0]["icon"],
        "Trump Icon (events)": test_data["events"][0]["outcomes"][1]["icon"],
        "Other Icon (events)": test_data["events"][0]["outcomes"][2]["icon"],
        "Harris Icon (market)": test_data["option_markets"][0]["icon"],
        "Trump Icon (market)": test_data["option_markets"][1]["icon"],
        "Other Icon (market)": test_data["option_markets"][2]["icon"]
    }.items():
        is_accessible = is_slack_accessible_url(url)
        print(f"- {url_name}: {'✅ Accessible' if is_accessible else '❌ Not accessible'} ({url[:50]}...)")
    
    # Process with our image extraction logic
    processed_data = process_event_images(test_data)
    
    # Format for Slack
    message, blocks = format_market_with_images(processed_data)
    
    # Print the formatted message
    print("\nFormatted Message:")
    print(message)
    print("\nFormatted Blocks (first few):")
    for i, block in enumerate(blocks[:5]):
        print(f"Block {i}: {json.dumps(block, indent=2)}")
    print(f"... and {len(blocks) - 5} more blocks")
    
    # Try to post to Slack
    try:
        if os.environ.get('SLACK_BOT_TOKEN') and os.environ.get('SLACK_CHANNEL_ID'):
            print("\nAttempting to post to Slack...")
            timestamp = post_message_with_blocks(message, blocks)
            
            if timestamp:
                print(f"✅ Successfully posted to Slack with timestamp: {timestamp}")
                print("Please check Slack to verify correct image display")
                return True
            else:
                print("❌ Failed to post to Slack")
        else:
            print("\nSlack credentials not available - skipping posting")
    except Exception as e:
        print(f"❌ Error posting to Slack: {str(e)}")
    
    return False

def main():
    """Main test function."""
    success = test_multi_option_market()
    
    if success:
        print("\n✅ TEST PASSED - Successfully posted formatted message to Slack")
        return 0
    else:
        print("\n❌ TEST FAILED - Could not post formatted message to Slack")
        return 1

if __name__ == "__main__":
    main()