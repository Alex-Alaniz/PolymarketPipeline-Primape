#!/usr/bin/env python3
"""
Slack utilities for posting messages and handling reactions.

This module provides functions for interacting with the Slack API,
sending messages, uploading files, and managing reactions.
"""

import os
import logging
from typing import Dict, List, Optional, Any, Tuple

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Slack
try:
    import slack_sdk
    from slack_sdk.errors import SlackApiError
    
    SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
    SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")
    
    if SLACK_BOT_TOKEN:
        slack_client = slack_sdk.WebClient(token=SLACK_BOT_TOKEN)
        logger.info("Slack client initialized")
    else:
        logger.warning("SLACK_BOT_TOKEN not set, Slack integration disabled")
        slack_client = None
        
    if not SLACK_CHANNEL_ID:
        logger.warning("SLACK_CHANNEL_ID not set, using default channel")
except ImportError:
    logger.error("slack_sdk not installed, Slack integration disabled")
    SLACK_BOT_TOKEN = None
    SLACK_CHANNEL_ID = None
    slack_client = None


def post_message_to_slack(message: str, thread_ts: Optional[str] = None) -> Optional[str]:
    """
    Post a simple text message to Slack.
    
    Args:
        message: Message text to post
        thread_ts: Optional thread timestamp to reply to
        
    Returns:
        Message timestamp (ID) if successful, None otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return None
    
    try:
        # Prepare payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message
        }
        
        # Add thread_ts if provided for threaded replies
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Post to Slack
        response = slack_client.chat_postMessage(**payload)
        
        if response["ok"]:
            logger.info(f"Posted message to Slack with ID {response['ts']}")
            return response["ts"]
        else:
            logger.error(f"Failed to post message to Slack: {response.get('error')}")
            return None
    except Exception as e:
        logger.error(f"Error posting message to Slack: {str(e)}")
        return None


def post_message_with_blocks(message: str, blocks: List[Dict[str, Any]], thread_ts: Optional[str] = None) -> Optional[str]:
    """
    Post a rich formatted message to Slack with blocks.
    
    Args:
        message: Fallback message text
        blocks: Rich message formatting blocks
        thread_ts: Optional thread timestamp to reply to
        
    Returns:
        Message timestamp (ID) if successful, None otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return None
    
    try:
        # Prepare payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message,
            "blocks": blocks
        }
        
        # Add thread_ts if provided for threaded replies
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Post to Slack
        response = slack_client.chat_postMessage(**payload)
        
        if response["ok"]:
            logger.info(f"Posted message to Slack with ID {response['ts']}")
            return response["ts"]
        else:
            logger.error(f"Error posting message to Slack: {response.get('error', 'Unknown error')}")
            return None
    except SlackApiError as e:
        logger.error(f"Error posting message to Slack: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error posting message to Slack: {str(e)}")
        return None


def upload_file_to_slack(
    file_path: str, 
    title: Optional[str] = None,
    initial_comment: Optional[str] = None,
    thread_ts: Optional[str] = None
) -> Optional[str]:
    """
    Upload a file to Slack.
    
    Args:
        file_path: Path to the file to upload
        title: Optional title for the file
        initial_comment: Optional comment to add with the file
        thread_ts: Optional thread timestamp to attach the file to
        
    Returns:
        File ID if successful, None otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return None
    
    try:
        # Prepare payload
        payload = {
            "channels": SLACK_CHANNEL_ID,
            "file": file_path
        }
        
        # Add optional parameters if provided
        if title:
            payload["title"] = title
        if initial_comment:
            payload["initial_comment"] = initial_comment
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Upload to Slack
        response = slack_client.files_upload_v2(**payload)
        
        if response["ok"]:
            file_id = response["file"]["id"]
            logger.info(f"Uploaded file to Slack with ID {file_id}")
            return file_id
        else:
            logger.error(f"Failed to upload file to Slack: {response.get('error')}")
            return None
    except Exception as e:
        logger.error(f"Error uploading file to Slack: {str(e)}")
        return None


def add_reaction_to_message(message_ts: str, reaction: str) -> bool:
    """
    Add a reaction to a Slack message.
    
    Args:
        message_ts: Message timestamp (ID)
        reaction: Reaction emoji name (without colons)
        
    Returns:
        True if successful, False otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return False
    
    try:
        # Add reaction
        response = slack_client.reactions_add(
            channel=SLACK_CHANNEL_ID,
            timestamp=message_ts,
            name=reaction
        )
        
        if response["ok"]:
            logger.info(f"Added reaction '{reaction}' to message {message_ts}")
            return True
        else:
            logger.error(f"Failed to add reaction to message: {response.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Error adding reaction to message: {str(e)}")
        return False


def get_message_reactions(message_ts: str) -> Dict[str, List[str]]:
    """
    Get reactions on a Slack message.
    
    Args:
        message_ts: Message timestamp (ID)
        
    Returns:
        Dictionary mapping reaction names to lists of users who reacted
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return {}
    
    try:
        # Get reactions
        response = slack_client.reactions_get(
            channel=SLACK_CHANNEL_ID,
            timestamp=message_ts
        )
        
        reactions = {}
        
        if response["ok"] and "message" in response and "reactions" in response["message"]:
            for reaction in response["message"]["reactions"]:
                reactions[reaction["name"]] = reaction["users"]
            
            logger.info(f"Retrieved {len(reactions)} reactions for message {message_ts}")
        else:
            logger.warning(f"No reactions found for message {message_ts}")
        
        return reactions
    except Exception as e:
        logger.error(f"Error getting message reactions: {str(e)}")
        return {}


def get_channel_history(limit: int = 100, cursor: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Get message history from the Slack channel.
    
    Args:
        limit: Maximum number of messages to retrieve
        cursor: Pagination cursor for fetching next batch
        
    Returns:
        Tuple of (messages, next_cursor)
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return [], None
    
    try:
        # Prepare payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "limit": limit
        }
        
        # Add cursor if provided for pagination
        if cursor:
            payload["cursor"] = cursor
        
        # Get history
        response = slack_client.conversations_history(**payload)
        
        if response["ok"]:
            messages = response["messages"]
            next_cursor = response.get("response_metadata", {}).get("next_cursor")
            
            logger.info(f"Retrieved {len(messages)} messages from channel")
            return messages, next_cursor
        else:
            logger.error(f"Failed to get channel history: {response.get('error')}")
            return [], None
    except Exception as e:
        logger.error(f"Error getting channel history: {str(e)}")
        return [], None


def delete_message(message_ts: str) -> bool:
    """
    Delete a message from Slack.
    
    Args:
        message_ts: Message timestamp (ID)
        
    Returns:
        True if successful, False otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return False
    
    try:
        # Delete message
        response = slack_client.chat_delete(
            channel=SLACK_CHANNEL_ID,
            ts=message_ts
        )
        
        if response["ok"]:
            logger.info(f"Deleted message {message_ts} from channel")
            return True
        else:
            logger.error(f"Failed to delete message: {response.get('error')}")
            return False
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        return False