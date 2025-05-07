#!/usr/bin/env python3

"""
Test the image handling for the specific La Liga example structure.

This test script verifies that our image handling logic correctly processes
the La Liga event structure with the event banner from events[0].image and 
option icons from each option market's icon field.
"""

import json
import logging
from pprint import pprint

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data based on La Liga structure provided
SAMPLE_DATA = {
    "events": [
        {
            "id": "12672",
            "ticker": "la-liga-winner",
            "slug": "la-liga-winner",
            "title": "La Liga Winner",
            "description": "This is a market on predicting the winner of the La Liga football league for the current season.",
            "resolutionSource": "",
            "startDate": "2024-09-18T16:52:55.612547Z",
            "creationDate": "2024-09-18T16:52:55.612533Z",
            "endDate": "2025-05-25T12:00:00Z",
            "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/la-liga-winner-0Gd3D1MaSklO.png",
            # Add option_markets or outcomes here if they exist in the event
            "outcomes": [
                {
                    "id": "real-madrid",
                    "title": "Real Madrid",
                    "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/real-madrid-icon.png",
                },
                {
                    "id": "barcelona",
                    "title": "Barcelona",
                    "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/barcelona-icon.png",
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
            "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-la-liga-vCC-C0S5sp4O.png",
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
            "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-real-madrid-win-la-liga-vCC-C0S5sp4O.png",
        }
    ],
    "question": "La Liga Winner 2024-2025",
    "category": "sports",
    "is_multiple_option": True,
    "is_binary": False,
    "is_event": True,
}

def test_image_extraction():
    """Test the image extraction from the sample data structure."""
    from utils.event_filter import process_event_images
    
    print("\n==== TESTING LA LIGA SAMPLE DATA ====\n")
    
    # Process the sample data
    processed = process_event_images(SAMPLE_DATA)
    
    # Print the extracted images
    print("\nExtracted Images:")
    print(f"Event Banner: {processed.get('event_image', 'None')}")
    print(f"Event Icon: {processed.get('event_icon', 'None')}")
    print("Option Images:")
    for option_id, image_url in processed.get('option_images', {}).items():
        print(f"  - {option_id}: {image_url}")
    
    # Verify the results
    banner_correct = processed.get('event_image') == SAMPLE_DATA['events'][0]['image']
    
    # For options, we need to check both option_markets and events.outcomes
    option_images = processed.get('option_images', {})
    
    options_correct = True
    expected_options = {}
    
    # Add expected options from option_markets
    for option_market in SAMPLE_DATA.get('option_markets', []):
        option_id = option_market.get('id', '')
        if option_id and 'icon' in option_market:
            expected_options[option_id] = option_market['icon']
    
    # Add expected options from events.outcomes if no option_markets match
    if not expected_options and 'events' in SAMPLE_DATA:
        for event in SAMPLE_DATA['events']:
            for outcome in event.get('outcomes', []):
                outcome_id = outcome.get('id', '')
                if outcome_id and 'icon' in outcome:
                    expected_options[outcome_id] = outcome['icon']
    
    # Now verify
    for option_id, expected_url in expected_options.items():
        if option_id not in option_images:
            print(f"❌ Missing option image for {option_id}")
            options_correct = False
        elif option_images[option_id] != expected_url:
            print(f"❌ Wrong URL for {option_id}:")
            print(f"  Expected: {expected_url}")
            print(f"  Actual: {option_images[option_id]}")
            options_correct = False
    
    # Print the verdict
    print("\nResults:")
    if banner_correct:
        print("✅ Event banner image is correct")
    else:
        print("❌ Event banner image is INCORRECT")
        print(f"  Expected: {SAMPLE_DATA['events'][0]['image']}")
        print(f"  Actual: {processed.get('event_image', 'None')}")
    
    if options_correct:
        print("✅ Option images are correct")
    else:
        print("❌ Some option images are INCORRECT")
    
    return banner_correct and options_correct

def test_slack_formatting():
    """Test the slack message formatting with the sample data."""
    from utils.messaging import format_market_with_images
    
    print("\n==== TESTING SLACK FORMATTING FOR LA LIGA SAMPLE ====\n")
    
    # Process the data first with our image extraction
    from utils.event_filter import process_event_images
    processed = process_event_images(SAMPLE_DATA)
    
    # Format for Slack
    message, blocks = format_market_with_images(processed)
    
    # Print the formatted message
    print("\nFormatted Slack Message:")
    print(message)
    
    print("\nBlocks Structure:")
    pprint(blocks)
    
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
                # Look for option images (format: "*Real Madrid* : <image_url>")
                if '*' in field_text and ' : http' in field_text:
                    option_images_found += 1
                    print(f"✅ Found option image in field: {field_text}")
    
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
    
    return banner_found and option_images_found == expected_option_count

def main():
    """Main function to run both tests."""
    extraction_success = test_image_extraction()
    formatting_success = test_slack_formatting()
    
    print("\n==== OVERALL TEST RESULTS ====")
    if extraction_success and formatting_success:
        print("✅ All tests PASSED")
        return 0
    else:
        print("❌ Some tests FAILED")
        return 1

if __name__ == "__main__":
    main()