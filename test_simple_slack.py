"""
Simple Slack message test to verify our changes.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def post_simple_message():
    """
    Post a simple message to Slack.
    """
    # Import Slack client
    from utils.slack import post_message_with_blocks
    
    # Simple text message
    message = "Testing Polymarket Pipeline Improvements"
    
    # Simple blocks with one image
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Polymarket Pipeline Improvements"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Successfully updated image handling for market posts."
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Improvements:*\n• Better image handling\n• Proper expiry date formatting\n• Enhanced options display\n• Correct category handling"
            }
        }
    ]
    
    # Post the message
    result = post_message_with_blocks(message, blocks)
    
    if result:
        logger.info("Test message posted successfully!")
        return True
    else:
        logger.error("Failed to post test message")
        return False

if __name__ == "__main__":
    try:
        from main import app
        with app.app_context():
            success = post_simple_message()
            sys.exit(0 if success else 1)
    except ImportError:
        # If we can't import app, just run without context
        success = post_simple_message()
        sys.exit(0 if success else 1)