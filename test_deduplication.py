#!/usr/bin/env python3
"""
Test script for the option deduplication feature.

This script tests the new deduplication logic to ensure we don't display 
the same team both as a plain entity ("Real Madrid") and a question
("Will Real Madrid win?").
"""

import json
import logging
import os
from pprint import pprint

from utils.messaging import format_market_with_images, is_slack_accessible_url

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data with duplicated option representations
TEST_DATA = {
    "question": "Which team will win La Liga 2024-25?",
    "category": "sports",
    "is_multiple_option": True,
    "is_binary": False,
    "is_event": True,
    "endDate": "2025-05-31T23:59:59Z",
    "events": [
        {
            "id": "laliga-2024-25",
            "title": "La Liga Winner 2024-25",
            "image": "https://i.imgur.com/vth6y1z.jpg",  # La Liga banner
            "outcomes": [
                {
                    "id": "real-madrid",
                    "title": "Real Madrid",
                    "icon": "https://i.imgur.com/HnG0ZAw.png",  # Team logo
                },
                {
                    "id": "barcelona",
                    "title": "Barcelona",
                    "icon": "https://i.imgur.com/T14BXyP.png",  # Team logo
                },
                {
                    "id": "atletico-madrid",
                    "title": "Atletico Madrid",
                    "icon": "https://i.imgur.com/8JVdNGY.png",  # Team logo
                }
            ]
        }
    ],
    # Also add the same teams as option markets but with questions
    "option_markets": [
        {
            "id": "101",
            "question": "Will Real Madrid win La Liga?",
            "icon": "https://i.imgur.com/HnG0ZAw.png"  # Same logo
        },
        {
            "id": "102",
            "question": "Will Barcelona win La Liga?",
            "icon": "https://i.imgur.com/T14BXyP.png"  # Same logo
        },
        {
            "id": "103",
            "question": "Will Atletico Madrid win La Liga?",
            "icon": "https://i.imgur.com/8JVdNGY.png"  # Same logo
        }
    ]
}

def test_option_deduplication():
    """Test the option deduplication logic."""
    print("\n==== TESTING OPTION DEDUPLICATION FOR LA LIGA MARKET ====\n")
    
    # First, format the message
    message, blocks = format_market_with_images(TEST_DATA)
    
    # Extract option fields to see what was included
    option_sections = []
    image_blocks = []
    
    for block in blocks:
        if block.get("type") == "section" and block.get("fields"):
            option_sections.append(block)
        elif block.get("type") == "image":
            image_blocks.append(block)
    
    # Count unique options and image blocks
    image_count = len([b for b in blocks if b.get("type") == "image"])
    banner_image_count = 1  # There should be 1 banner image
    option_image_count = image_count - banner_image_count
    
    # Print summary
    print(f"Total options displayed: {len([field for section in option_sections for field in section.get('fields', [])])}")
    print(f"Total image blocks: {image_count}")
    print(f"Option image blocks: {option_image_count}")
    
    # Show the options displayed
    for section in option_sections:
        for field in section.get("fields", []):
            print(f"Option displayed: {field.get('text')}")
    
    # Show the images displayed
    for i, block in enumerate([b for b in blocks if b.get("type") == "image"]):
        if i == 0:
            print(f"Banner image: {block.get('image_url')}")
        else:
            print(f"Option image {i}: {block.get('image_url')} - {block.get('alt_text')}")
    
    # Verify deduplication worked - we should have 3 teams not 6
    success = option_image_count == 3
    print(f"\n{'✅ TEST PASSED' if success else '❌ TEST FAILED'} - Deduplicated to {option_image_count} options")
    
    return success

def main():
    """Run the tests."""
    test_option_deduplication()

if __name__ == "__main__":
    main()