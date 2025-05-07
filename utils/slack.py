"""
Slack utilities for posting messages and checking reactions.

This module provides simplified functions for posting messages to Slack
and handling reactions without the full complexity of utils.messaging.
"""

import os
import logging
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import Slack SDK if available
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_SDK_AVAILABLE = True
except ImportError:
    logger.warning("Slack SDK not available, using fallback mock implementation")
    SLACK_SDK_AVAILABLE = False

# Initialize Slack client with bot token
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
    logger.warning("Missing Slack configuration. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables.")

# Initialize Slack client if SDK is available
slack_client = None
if SLACK_SDK_AVAILABLE and SLACK_BOT_TOKEN:
    slack_client = WebClient(token=SLACK_BOT_TOKEN)
    logger.info("Slack client initialized successfully")

def post_message_with_blocks(message: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Optional[str]:
    """
    Post a message to Slack with optional formatting blocks.
    
    Args:
        message: Text message (used as fallback for clients that don't support blocks)
        blocks: Optional rich formatting blocks
        
    Returns:
        Message timestamp (ID) if successful, None otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token or SDK")
        return None
    
    try:
        # Prepare payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message
        }
        
        # Add blocks if provided
        if blocks:
            payload["blocks"] = blocks
        
        # Post message
        response = slack_client.chat_postMessage(**payload)
        
        if response and response.get('ok'):
            message_id = response['ts']
            
            # Add standard approval/rejection reactions
            add_reaction(message_id, "thumbsup")
            add_reaction(message_id, "thumbsdown")
            
            logger.info(f"Posted message to Slack with ID {message_id}")
            return message_id
        else:
            logger.error(f"Failed to post message to Slack: {response.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        logger.error(f"Error posting message to Slack: {str(e)}")
        return None

def add_reaction(message_id: str, reaction: str) -> bool:
    """
    Add a reaction emoji to a Slack message.
    
    Args:
        message_id: Message timestamp (ID)
        reaction: Reaction emoji name (without colons)
        
    Returns:
        True if successful, False otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token or SDK")
        return False
    
    try:
        # Add reaction
        response = slack_client.reactions_add(
            channel=SLACK_CHANNEL_ID,
            timestamp=message_id,
            name=reaction
        )
        
        return response.get('ok', False)
    
    except SlackApiError as e:
        # Ignore "already_reacted" error
        if "already_reacted" in str(e):
            return True
        
        logger.error(f"Error adding reaction to message: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error adding reaction: {str(e)}")
        return False