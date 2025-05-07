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

def format_market_with_images(market_data):
    """
    Format a market message for Slack with event banner and option images.
    
    Args:
        market_data: Market data dictionary with images
        
    Returns:
        Tuple of (text_message, blocks_array)
    """
    # Basic market information
    question = market_data.get('question', 'Unknown Market')
    category = market_data.get('category', 'uncategorized')
    expiry = market_data.get('expiry', 'Unknown')
    event_name = market_data.get('event_name', '')
    event_id = market_data.get('event_id', '')
    
    # Start with a text fallback message
    text_message = f"*New Market for Approval*\n"
    text_message += f"*Question:* {question}\n"
    text_message += f"*Category:* {category}\n"
    text_message += f"*Expiry:* {expiry}\n"
    
    if event_name:
        text_message += f"*Event:* {event_name}\n"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "New Market for Approval"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {question}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Category:* {category}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Expiry:* {expiry}"
                }
            ]
        }
    ]
    
    # Add event information if available
    if event_name:
        event_block = {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event:* {event_name}\n*Event ID:* {event_id}"
            }
        }
        blocks.append(event_block)
    
    # Add event banner image if available
    event_image = market_data.get('event_image')
    if event_image and is_valid_url(event_image):
        blocks.append(
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Event Banner Image"
                },
                "image_url": event_image,
                "alt_text": "Event Banner"
            }
        )
    
    # Add option images if available
    option_images = market_data.get('option_images', {})
    if option_images and isinstance(option_images, dict) and len(option_images) > 0:
        for option_name, image_url in option_images.items():
            if image_url and is_valid_url(image_url):
                blocks.append(
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Option:* {option_name}"
                        }
                    }
                )
                blocks.append(
                    {
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": f"Option Image: {option_name}"
                        },
                        "image_url": image_url,
                        "alt_text": f"Option {option_name}"
                    }
                )
    
    # Add reminder for approval reactions
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "React with 👍 to approve or 👎 to reject"
            }
        }
    )
    
    return text_message, blocks

def is_valid_url(url):
    """
    Check if a string is a valid URL.
    
    Args:
        url: URL string to check
        
    Returns:
        Boolean indicating if the URL is valid
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def post_test_market():
    """Post a test market to Slack for approval."""
    # Create a test event market (not a binary market)
    test_market = {
        "id": f"event_test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "question": "UEFA Champions League Winner 2025",
        "category": "sports",
        "event_id": "event_champions_league_2025",
        "event_name": "UEFA Champions League 2025",
        "expiry": (datetime.now() + timedelta(days=60)).isoformat(),
        "event_image": "https://i.imgur.com/Ux7r6Fp.png",
        "is_event": True,
        "options": [
            "Manchester United",
            "Paris Saint-Germain",
            "Arsenal",
            "Inter Milan",
            "Real Madrid"
        ],
        "option_images": {
            "Manchester United": "https://i.imgur.com/OTDjOce.png",
            "Paris Saint-Germain": "https://i.imgur.com/B8Zmr1v.png",
            "Arsenal": "https://i.imgur.com/yBzwzFM.png",
            "Inter Milan": "https://i.imgur.com/5fiT0XE.png",
            "Real Madrid": "https://i.imgur.com/vvL5yfp.png"
        },
        "option_market_ids": {
            "Manchester United": "market_id_1234",
            "Paris Saint-Germain": "market_id_2345",
            "Arsenal": "market_id_3456",
            "Inter Milan": "market_id_4567",
            "Real Madrid": "market_id_5678"
        }
    }
    
    # Format the message for Slack with images
    text_message, blocks = format_market_with_images(test_market)
    
    try:
        # Post to Slack with rich formatting
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=text_message,
            blocks=blocks
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