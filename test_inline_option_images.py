"""
Test inline option images for multi-option markets.

This script tests our updated market formatting with options displayed
inline with their icons.
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

def test_event_market_with_inline_images():
    """Test an event market with inline option images."""
    # Create an event market with valid images for each option
    market_data = {
        "question": "Which team will win the Champions League 2025?",
        "category": "sports",
        "endDate": "2025-05-31T23:59:59Z",
        "image": "https://blog.replit.com/images/site/logo.png",  # Banner image
        "icon": "https://blog.replit.com/images/site/logo.png",
        "outcomes": json.dumps(["Real Madrid", "Manchester City", "Bayern Munich", "PSG"]),
        "is_event": True,
        "is_multiple_option": True,
        # Individual option images displayed inline
        "option_images": {
            "Real Madrid": "https://blog.replit.com/images/site/logo.png",
            "Manchester City": "https://blog.replit.com/images/site/logo.png",
            "Bayern Munich": "https://blog.replit.com/images/site/logo.png",
            "PSG": "https://blog.replit.com/images/site/logo.png"
        },
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
        logger.info("Event market with inline option images posted successfully")
        return True
    else:
        logger.error("Failed to post event market with inline option images")
        return False

def main():
    """Main test function."""
    try:
        from main import app
        with app.app_context():
            # Test event market with inline option images
            event_success = test_event_market_with_inline_images()
            logger.info(f"Event market with inline images test: {'SUCCESS' if event_success else 'FAILED'}")
            
            return 0 if event_success else 1
    except ImportError:
        # If we can't import app, just run without context
        event_success = test_event_market_with_inline_images()
        logger.info(f"Event market with inline images test: {'SUCCESS' if event_success else 'FAILED'}")
        
        return 0 if event_success else 1

if __name__ == "__main__":
    sys.exit(main())