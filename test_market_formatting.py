"""
Test Market Formatting with Updated Image and Date Handling

This script tests the updated image and date handling in Slack market messages.
It takes a market sample and processes it with the enhanced formatter.
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

# Import the messaging utilities
from utils.messaging import format_market_with_images
from utils.slack import post_message_with_blocks

def load_test_market():
    """
    Load a test market from multiple_choice_market.json or create a sample one.
    
    Returns:
        dict: Market data dictionary
    """
    try:
        if os.path.exists("multiple_choice_market.json"):
            with open("multiple_choice_market.json", "r") as f:
                market_data = json.load(f)
                logger.info("Loaded test market from multiple_choice_market.json")
                return market_data
    except Exception as e:
        logger.error(f"Error loading multiple_choice_market.json: {e}")
    
    # Create a sample market with proper fields
    market_data = {
        "question": "Test Market with Updated Image Handling",
        "category": "uncategorized",
        "endDate": datetime.now().isoformat(),  # ISO format date for testing
        "image": "https://www.polymarket.com/event-images/test-banner.jpg",
        "icon": "https://www.polymarket.com/event-icons/test-icon.jpg",
        "outcomes": json.dumps(["Yes", "No"]),  # JSON string format
        "is_event": False,
        "is_multiple_option": False
    }
    
    logger.info("Created sample test market")
    return market_data

def load_test_event_market():
    """
    Create a sample event (multiple-choice) market.
    
    Returns:
        dict: Event market data dictionary
    """
    # Create a sample event market with proper fields
    market_data = {
        "question": "Test Event Market with Multiple Options",
        "category": "sports",
        "endDate": datetime.now().isoformat(),  # ISO format date for testing
        "image": "https://www.polymarket.com/event-images/sports-banner.jpg",
        "icon": "https://www.polymarket.com/event-icons/sports-icon.jpg",
        "outcomes": json.dumps(["Team A", "Team B", "Team C", "Draw"]),  # Multiple options
        "is_event": True,
        "is_multiple_option": True,
        "option_images": {
            "Team A": "https://www.polymarket.com/team-icons/team-a.jpg",
            "Team B": "https://www.polymarket.com/team-icons/team-b.jpg",
            "Team C": "https://www.polymarket.com/team-icons/team-c.jpg",
            "Draw": "https://www.polymarket.com/team-icons/draw.jpg"
        }
    }
    
    logger.info("Created sample test event market")
    return market_data

def test_market_formatting():
    """
    Test market formatting with enhanced image and date handling.
    """
    # Load test markets
    binary_market = load_test_market()
    event_market = load_test_event_market()
    
    # Format binary market
    logger.info("Formatting binary market...")
    binary_message, binary_blocks = format_market_with_images(binary_market)
    logger.info(f"Binary market formatted with {len(binary_blocks)} blocks")
    
    # Format event market
    logger.info("Formatting event market...")
    event_message, event_blocks = format_market_with_images(event_market)
    logger.info(f"Event market formatted with {len(event_blocks)} blocks")
    
    # Post to Slack for visual inspection
    logger.info("Posting markets to Slack for visual inspection...")
    
    # Post binary market
    binary_result = post_message_with_blocks(binary_message, binary_blocks)
    if binary_result:
        logger.info("Binary market posted successfully")
    else:
        logger.error("Failed to post binary market")
    
    # Post event market
    event_result = post_message_with_blocks(event_message, event_blocks)
    if event_result:
        logger.info("Event market posted successfully")
    else:
        logger.error("Failed to post event market")
    
    return binary_result and event_result

if __name__ == "__main__":
    # Use context for database operations
    try:
        from main import app
        with app.app_context():
            success = test_market_formatting()
            sys.exit(0 if success else 1)
    except ImportError:
        # If we can't import app, just run without context
        success = test_market_formatting()
        sys.exit(0 if success else 1)