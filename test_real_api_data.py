#!/usr/bin/env python3
"""
Test script for option deduplication using real API data.

This script tests the deduplication logic with real data from the 
Polymarket API to ensure we correctly handle duplicate options
in real-world scenarios.
"""

import json
import logging
import os
import sys
from pprint import pprint

from utils.event_filter import process_event_images
from utils.messaging import format_market_with_images, is_slack_accessible_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_api_sample():
    """Load a sample market from stored JSON data."""
    # Try to load real API data from one of the sample files
    sample_files = [
        "gamma_markets_response.json",
        "market_sample.json",
        "multiple_choice_market.json",
    ]
    
    for file_path in sample_files:
        if os.path.exists(file_path):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # For multiple_choice_market.json, we can use directly
                if file_path == "multiple_choice_market.json":
                    return data
                    
                # For other files, extract the first market
                if isinstance(data, list) and len(data) > 0:
                    return data[0]
                elif "markets" in data and len(data["markets"]) > 0:
                    return data["markets"][0]
                    
                print(f"Loaded sample from {file_path}")
                return data
            except Exception as e:
                print(f"Error loading {file_path}: {str(e)}")
    
    # If no file found, return error
    print("ERROR: No sample data found. Please run 'fetch_small_batch.py' first.")
    return None

def test_with_real_data():
    """Test deduplication with real API data."""
    print("\n==== TESTING OPTION DEDUPLICATION WITH REAL API DATA ====\n")
    
    # Load data
    market_data = load_api_sample()
    if not market_data:
        return False
        
    print(f"Loaded market: {market_data.get('question', 'Unknown')}")
    
    # Process market data through our image filtering
    processed_data = process_event_images(market_data)
    
    # Format the message
    message, blocks = format_market_with_images(processed_data)
    
    # Count image blocks (first one is banner)
    image_blocks = [b for b in blocks if b.get("type") == "image"]
    banner_image = image_blocks[0] if image_blocks else None
    option_images = image_blocks[1:] if len(image_blocks) > 1 else []
    
    # Count unique options
    option_sections = [b for b in blocks if b.get("type") == "section" and b.get("fields")]
    option_fields = []
    for section in option_sections:
        option_fields.extend(section.get("fields", []))
    
    # Filter out non-option fields like category, expiry
    option_fields = [f for f in option_fields if not f.get("text", "").startswith("*Category:*") and
                     not f.get("text", "").startswith("*Expiry:*")]
    
    # Print results
    print(f"\nMarket type: {'Multi-option' if processed_data.get('is_multiple_option') else 'Binary'}")
    if banner_image:
        print(f"Banner image: {banner_image.get('image_url')}")
    
    print(f"\nOption count:")
    print(f"- Total options displayed: {len(option_fields)}")
    print(f"- Option images: {len(option_images)}")
    
    # Show options displayed
    print("\nOptions displayed:")
    for field in option_fields:
        print(f"- {field.get('text')}")
    
    # Show images
    if option_images:
        print("\nOption images:")
        for i, img in enumerate(option_images):
            print(f"- Image {i+1}: {img.get('image_url')} - {img.get('alt_text')}")
    
    # For multiple-option markets, verify deduplication worked
    if processed_data.get('is_multiple_option'):
        # Success if we have the same number of option fields and option images
        success = len(option_fields) == len(option_images)
        result = f"{'✅ PASSED' if success else '❌ FAILED'} - Options: {len(option_fields)}, Images: {len(option_images)}"
    else:
        # For binary markets, we should only have the banner image
        success = len(option_images) == 0
        result = f"{'✅ PASSED' if success else '❌ FAILED'} - Binary market with {len(option_images)} option images"
    
    print(f"\nTest result: {result}")
    return success

def main():
    """Run the test."""
    success = test_with_real_data()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())