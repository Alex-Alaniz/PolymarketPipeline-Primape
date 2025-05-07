"""
Test formatted market messages with simplified test data.

This script tests our market formatting with both binary and multi-option markets.
"""

import os
import sys
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add local path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import utilities
from utils.messaging import format_market_with_images
from utils.slack import post_message_with_blocks

def test_binary_market():
    """Test a binary (Yes/No) market with correct formatting."""
    # Create a binary market with valid image
    market_data = {
        "question": "Will Bitcoin exceed $100,000 by the end of 2024?",
        "category": "crypto",
        "endDate": "2024-12-31T23:59:59Z",
        "image": "https://blog.replit.com/images/site/logo.png",
        "icon": "https://blog.replit.com/images/site/logo.png",
        "outcomes": json.dumps(["Yes", "No"]),
        "is_event": False,
        "is_multiple_option": False
    }
    
    # Format the market
    message, blocks = format_market_with_images(market_data)
    
    # Post to Slack
    result = post_message_with_blocks(message, blocks)
    
    if result:
        logger.info("Binary market posted successfully")
        return True
    else:
        logger.error("Failed to post binary market")
        return False

def test_event_market():
    """Test a multi-option event market with correct formatting."""
    # Create an event market with valid image
    market_data = {
        "question": "Which team will win the Champions League 2025?",
        "category": "sports",
        "endDate": "2025-05-31T23:59:59Z",
        "image": "https://blog.replit.com/images/site/logo.png",
        "icon": "https://blog.replit.com/images/site/logo.png",
        "outcomes": json.dumps(["Real Madrid", "Manchester City", "Bayern Munich", "PSG"]),
        "is_event": True,
        "is_multiple_option": True,
        "option_market_ids": {
            "Real Madrid": "123",
            "Manchester City": "456",
            "Bayern Munich": "789",
            "PSG": "101"
        }
    }
    
    # Format the market
    message, blocks = format_market_with_images(market_data)
    
    # Post to Slack
    result = post_message_with_blocks(message, blocks)
    
    if result:
        logger.info("Event market posted successfully")
        return True
    else:
        logger.error("Failed to post event market")
        return False

def main():
    """Main test function."""
    try:
        from main import app
        with app.app_context():
            # Test binary market first
            binary_success = test_binary_market()
            logger.info(f"Binary market test: {'SUCCESS' if binary_success else 'FAILED'}")
            
            # Then test event market
            event_success = test_event_market()
            logger.info(f"Event market test: {'SUCCESS' if event_success else 'FAILED'}")
            
            return 0 if binary_success and event_success else 1
    except ImportError:
        # If we can't import app, just run without context
        binary_success = test_binary_market()
        logger.info(f"Binary market test: {'SUCCESS' if binary_success else 'FAILED'}")
        
        event_success = test_event_market()
        logger.info(f"Event market test: {'SUCCESS' if event_success else 'FAILED'}")
        
        return 0 if binary_success and event_success else 1

if __name__ == "__main__":
    sys.exit(main())