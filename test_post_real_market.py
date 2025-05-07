"""
Test posting real market data with our updated formatting.

This script uses real market data to test our Slack message formatting.
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

def test_binary_market_from_json():
    """Test a binary market with real data from JSON file."""
    # Load sample market data from file
    try:
        with open('market_sample.json', 'r') as f:
            market_data = json.load(f)
            
        # Make sure it's a binary market
        market_data['is_event'] = False
        market_data['is_multiple_option'] = False
        
        # Format the market
        message, blocks = format_market_with_images(market_data)
        
        # Post to Slack
        result = post_message_with_blocks(message, blocks)
        
        if result:
            logger.info("Binary market from JSON posted successfully")
            return True
        else:
            logger.error("Failed to post binary market from JSON")
            return False
    except Exception as e:
        logger.error(f"Error testing binary market from JSON: {str(e)}")
        return False

def test_multiple_choice_market_from_json():
    """Test a multiple choice market with real data from JSON file."""
    # Load sample market data from file
    try:
        with open('multiple_choice_market.json', 'r') as f:
            market_data = json.load(f)
            
        # Make sure it's an event market
        market_data['is_event'] = True
        market_data['is_multiple_option'] = True
        
        # Format the market
        message, blocks = format_market_with_images(market_data)
        
        # Post to Slack
        result = post_message_with_blocks(message, blocks)
        
        if result:
            logger.info("Multiple choice market from JSON posted successfully")
            return True
        else:
            logger.error("Failed to post multiple choice market from JSON")
            return False
    except Exception as e:
        logger.error(f"Error testing multiple choice market from JSON: {str(e)}")
        return False

def main():
    """Main test function."""
    try:
        from main import app
        with app.app_context():
            # Test binary market first
            binary_success = test_binary_market_from_json()
            logger.info(f"Binary market test: {'SUCCESS' if binary_success else 'FAILED'}")
            
            # Then test multiple choice market
            multi_success = test_multiple_choice_market_from_json()
            logger.info(f"Multiple choice market test: {'SUCCESS' if multi_success else 'FAILED'}")
            
            return 0 if binary_success and multi_success else 1
    except ImportError:
        # If we can't import app, just run without context
        binary_success = test_binary_market_from_json()
        logger.info(f"Binary market test: {'SUCCESS' if binary_success else 'FAILED'}")
        
        multi_success = test_multiple_choice_market_from_json()
        logger.info(f"Multiple choice market test: {'SUCCESS' if multi_success else 'FAILED'}")
        
        return 0 if binary_success and multi_success else 1

if __name__ == "__main__":
    sys.exit(main())