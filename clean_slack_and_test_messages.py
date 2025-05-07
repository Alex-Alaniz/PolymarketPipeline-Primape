"""
Clean Slack channel and post test messages with proper formatting.

This script:
1. Cleans the Slack channel by deleting recent messages
2. Posts test messages with the correct format for both binary and event markets
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

from utils.slack import post_message_with_blocks
from utils.messaging import format_market_with_images

def clean_slack_channel(max_messages=10):
    """Clean recent messages from the Slack channel."""
    try:
        from utils.slack import slack_client, SLACK_CHANNEL_ID
        
        # Get channel history
        response = slack_client.conversations_history(
            channel=SLACK_CHANNEL_ID,
            limit=max_messages
        )
        
        if not response.get('ok'):
            logger.error(f"Failed to get channel history: {response.get('error')}")
            return False
            
        messages = response.get('messages', [])
        logger.info(f"Found {len(messages)} messages to clean")
        
        # Delete each message
        deleted_count = 0
        for message in messages:
            try:
                result = slack_client.chat_delete(
                    channel=SLACK_CHANNEL_ID,
                    ts=message['ts']
                )
                
                if result.get('ok'):
                    deleted_count += 1
                    logger.info(f"Deleted message {message['ts']}")
                else:
                    logger.warning(f"Failed to delete message {message['ts']}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error deleting message: {str(e)}")
        
        logger.info(f"Successfully cleaned {deleted_count} messages from Slack channel")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning Slack channel: {str(e)}")
        return False

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
    # Create an event market with valid images for each option
    market_data = {
        "question": "Which team will win the Champions League 2025?",
        "category": "sports",
        "endDate": "2025-05-31T23:59:59Z",
        "image": "https://blog.replit.com/images/site/logo.png",  # Event banner image
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
            # First clean the channel
            logger.info("Cleaning Slack channel...")
            clean_success = clean_slack_channel()
            if not clean_success:
                logger.warning("Failed to clean Slack channel, continuing with tests")
            
            # Test binary market
            binary_success = test_binary_market()
            logger.info(f"Binary market test: {'SUCCESS' if binary_success else 'FAILED'}")
            
            # Test event market
            event_success = test_event_market()
            logger.info(f"Event market test: {'SUCCESS' if event_success else 'FAILED'}")
            
            return 0 if binary_success and event_success else 1
    except ImportError:
        # If we can't import app, just run without context
        # First clean the channel
        logger.info("Cleaning Slack channel...")
        clean_success = clean_slack_channel()
        if not clean_success:
            logger.warning("Failed to clean Slack channel, continuing with tests")
        
        # Test binary market
        binary_success = test_binary_market()
        logger.info(f"Binary market test: {'SUCCESS' if binary_success else 'FAILED'}")
        
        # Test event market
        event_success = test_event_market()
        logger.info(f"Event market test: {'SUCCESS' if event_success else 'FAILED'}")
        
        return 0 if binary_success and event_success else 1

if __name__ == "__main__":
    sys.exit(main())