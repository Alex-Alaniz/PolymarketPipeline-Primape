#!/usr/bin/env python3

"""
Check for Test Market Approvals in Slack

This script checks for approval/rejection reactions on the test market
message in Slack, without using the database.
"""

import os
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("approval_checker")

# Initialize Slack client with bot token
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
    logger.error("Missing Slack configuration. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables.")
    exit(1)

slack_client = WebClient(token=SLACK_BOT_TOKEN)

def get_recent_messages(limit: int = 10):
    """
    Get recent messages from the Slack channel.
    
    Args:
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries
    """
    try:
        # Get history
        response = slack_client.conversations_history(
            channel=SLACK_CHANNEL_ID,
            limit=limit
        )
        
        messages = response.get("messages", [])
        return messages
    
    except SlackApiError as e:
        logger.error(f"Error getting channel history: {str(e)}")
        return []

def get_message_reactions(message_ts: str) -> Dict[str, List[str]]:
    """
    Get reactions on a Slack message.
    
    Args:
        message_ts: Message timestamp (ID)
        
    Returns:
        Dictionary mapping reaction names to lists of users who reacted
    """
    try:
        # Get message details
        response = slack_client.reactions_get(
            channel=SLACK_CHANNEL_ID,
            timestamp=message_ts
        )
        
        message = response.get("message", {})
        reactions = message.get("reactions", [])
        
        # Format reactions as {name: [users]}
        result = {}
        for reaction in reactions:
            name = reaction.get("name", "")
            users = reaction.get("users", [])
            result[name] = users
        
        return result
    
    except SlackApiError as e:
        logger.error(f"Error getting message reactions: {str(e)}")
        return {}

def extract_market_details(message_text):
    """
    Extract market details from message text.
    
    Args:
        message_text: Text content of the Slack message
        
    Returns:
        Dictionary with market details
    """
    lines = message_text.split('\n')
    details = {
        'question': '',
        'category': '',
        'expiry': '',
        'event': '',
        'has_banner_image': False,
        'has_option_images': False
    }
    
    for line in lines:
        if line.startswith('*Question:*'):
            details['question'] = line.replace('*Question:*', '').strip()
        elif line.startswith('*Category:*'):
            details['category'] = line.replace('*Category:*', '').strip()
        elif line.startswith('*Expiry:*'):
            details['expiry'] = line.replace('*Expiry:*', '').strip()
        elif line.startswith('*Event:*'):
            details['event'] = line.replace('*Event:*', '').strip()
    
    return details

def check_market_approvals():
    """
    Check for market approvals or rejections in Slack.
    """
    # Get recent messages
    messages = get_recent_messages(10)
    
    if not messages:
        logger.info("No messages found in channel")
        return 0
    
    approved_count = 0
    rejected_count = 0
    pending_count = 0
    
    for message in messages:
        # Check if this is a market message (contains "New Market for Approval")
        if "New Market for Approval" in message.get("text", ""):
            message_ts = message.get("ts")
            message_text = message.get("text", "")
            
            # Get reactions
            reactions = get_message_reactions(message_ts)
            
            # Check for approval (thumbsup)
            approved = any(
                reaction in reactions 
                for reaction in ['thumbsup', '+1']
            )
            
            # Check for rejection (thumbsdown)
            rejected = any(
                reaction in reactions 
                for reaction in ['thumbsdown', '-1']
            )
            
            # Extract market details
            details = extract_market_details(message_text)
            
            # Check for images in blocks (if available)
            has_images = False
            has_event_banner = False
            has_option_images = False
            
            if 'blocks' in message:
                for block in message.get('blocks', []):
                    if block.get('type') == 'image':
                        has_images = True
                        if 'Event Banner' in block.get('alt_text', ''):
                            has_event_banner = True
                        elif 'Option' in block.get('alt_text', ''):
                            has_option_images = True
            
            # Status indicator
            status = "✅ APPROVED" if approved else "❌ REJECTED" if rejected else "⏳ PENDING"
            
            # Print market details with additional event information
            logger.info(f"{status} - {details['question']}")
            logger.info(f"  Category: {details['category']}")
            
            if details['event']:
                logger.info(f"  Event: {details['event']}")
                logger.info(f"  Event banner image: {'Yes' if has_event_banner else 'No'}")
            
            if has_option_images:
                logger.info(f"  Has option images: Yes")
            
            if approved:
                approved_count += 1
            elif rejected:
                rejected_count += 1
            else:
                pending_count += 1
    
    logger.info(f"Market status: {pending_count} pending, {approved_count} approved, {rejected_count} rejected")
    return approved_count + rejected_count

def main():
    """
    Main function to check market approvals.
    """
    logger.info("Checking for market approvals in Slack")
    count = check_market_approvals()
    
    if count == 0:
        logger.warning("No market decisions found. Please react to the messages in Slack.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())