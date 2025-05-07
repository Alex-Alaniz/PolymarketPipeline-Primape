#!/usr/bin/env python3

"""
Simple Test Script to Post a Market to Slack

This script posts a simple test market to Slack directly,
without using the database or the full pipeline. This is useful
for testing Slack integration and approvals independently.
"""

import os
import json
import logging
from datetime import datetime, timedelta

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_test")

# Initialize Slack client with bot token
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
    logger.error("Missing Slack configuration. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables.")
    exit(1)

slack_client = WebClient(token=SLACK_BOT_TOKEN)

def post_test_market():
    """Post a test market to Slack for approval."""
    # Create a test market
    test_market = {
        "id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "question": "Will product X release before June 2025?",
        "category": "tech",
        "event_name": "Tech Product Releases 2025",
        "event_id": "event_tech_001",
        "expiry": (datetime.now() + timedelta(days=60)).isoformat()
    }
    
    # Format the message for Slack
    message = f"*New Market for Approval*\n"
    message += f"*Question:* {test_market['question']}\n"
    message += f"*Category:* {test_market['category']}\n"
    message += f"*Expiry:* {test_market['expiry']}\n"
    
    if test_market.get('event_name'):
        message += f"*Event:* {test_market.get('event_name')}\n"
    
    message += "\nReact with 👍 to approve or 👎 to reject"
    
    try:
        # Post to Slack
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=message
        )
        
        if response and response.get('ok'):
            message_id = response['ts']
            
            # Add standard approval/rejection reactions
            add_reaction(message_id, "thumbsup")
            add_reaction(message_id, "thumbsdown")
            
            logger.info(f"Posted test market to Slack with message ID {message_id}")
            return True
        else:
            logger.error(f"Failed to post test market to Slack: {response.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error posting test market to Slack: {str(e)}")
        return False

def add_reaction(message_id, reaction):
    """Add a reaction to a Slack message."""
    try:
        slack_client.reactions_add(
            channel=SLACK_CHANNEL_ID,
            name=reaction,
            timestamp=message_id
        )
    except SlackApiError as e:
        # Ignore "already_reacted" error
        if "already_reacted" not in str(e):
            logger.error(f"Error adding reaction to message: {str(e)}")

def main():
    """Main function to run the test."""
    logger.info("Starting Slack test")
    success = post_test_market()
    
    if success:
        logger.info("Test market posted successfully to Slack")
        logger.info(f"Check Slack channel {SLACK_CHANNEL_ID} for the message")
    else:
        logger.error("Failed to post test market to Slack")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())