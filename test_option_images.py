#!/usr/bin/env python3

"""
Test script to verify option-specific images in multi-option markets.
"""

import sys
import json
import logging
from typing import Dict, List, Any, Optional
from utils.messaging import post_market_for_approval

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_option_images")

def create_test_market_with_option_images():
    """Create a test multi-option market with option-specific images."""
    
    # Sample options with their images
    options = [
        "Arsenal",
        "Barcelona",
        "Inter Milan",
        "Paris Saint-Germain"
    ]
    
    # Sample option-specific images
    option_images = {
        "Arsenal": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-arsenal-win-the-uefa-champions-league-uNdX5G_OD3RZ.png",
        "Barcelona": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-the-uefa-champions-league-Krl4_iYrHb5t.png",
        "Inter Milan": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-inter-milan-win-the-uefa-champions-league-qLXmECEH1IMR.png",
        "Paris Saint-Germain": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-paris-saint-germain-win-the-uefa-champions-league-NxlXl1qZffuf.png"
    }
    
    # Event image/banner
    event_image = "https://polymarket-upload.s3.us-east-2.amazonaws.com/champions-league-winner-2025-F-QYbKsrHt_E.jpg"
    
    # Create test market data
    market_data = {
        "id": "test_market_images",
        "conditionId": "test_condition_id",
        "question": "Champions League Winner 2025",
        "endDate": "2025-06-01T00:00:00Z",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/champions-league-winner-2025-F-QYbKsrHt_E.jpg",
        "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-arsenal-win-the-uefa-champions-league-uNdX5G_OD3RZ.png",
        "event_image": event_image,
        "event_category": "Sports",
        "is_multiple_option": True,
        "outcomes": json.dumps(options),
        "option_images": json.dumps(option_images),
        "original_market_ids": ["id1", "id2", "id3", "id4"],
    }
    
    return market_data

def post_test_market() -> Optional[str]:
    """Post a test market to Slack and verify option-specific images."""
    # Create test market
    market_data = create_test_market_with_option_images()
    
    # Log market details
    logger.info(f"Posting test market: {market_data['question']}")
    logger.info(f"Category: {market_data.get('event_category', '')}")
    logger.info(f"Options: {json.loads(market_data['outcomes'])}")
    logger.info(f"Option images: {json.loads(market_data['option_images'])}")
    
    # Post to Slack
    message_id = post_market_for_approval(market_data)
    
    if message_id:
        logger.info(f"Successfully posted test market with message ID: {message_id}")
        return message_id
    else:
        logger.error("Failed to post test market")
        return None

def main():
    """Main test function."""
    message_id = post_test_market()
    
    if message_id:
        logger.info("✅ Test passed: Market posted with option-specific images")
        return 0
    else:
        logger.error("❌ Test failed: Could not post market")
        return 1

if __name__ == "__main__":
    sys.exit(main())