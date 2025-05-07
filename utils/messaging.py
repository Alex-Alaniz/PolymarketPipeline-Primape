"""
Messaging utilities for Slack integration.

This module provides functions for sending messages to Slack,
including rich message formatting, file uploads, and reaction handling.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Slack client with bot token
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
    logger.warning("Missing Slack configuration. Set SLACK_BOT_TOKEN and SLACK_CHANNEL_ID environment variables.")

slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

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
        # Prepare message payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message
        }
        
        # Add thread_ts if provided
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Post message
        response = slack_client.chat_postMessage(**payload)
        
        # Return message timestamp (ID)
        return response["ts"]
    
    except SlackApiError as e:
        logger.error(f"Error posting message to Slack: {str(e)}")
        return None

def post_formatted_message_to_slack(
    message: str, 
    blocks: Optional[List[Dict[str, Any]]] = None,
    thread_ts: Optional[str] = None
) -> Optional[str]:
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
        # Prepare message payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message
        }
        
        # Add blocks if provided
        if blocks:
            payload["blocks"] = blocks
        
        # Add thread_ts if provided
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Post message
        response = slack_client.chat_postMessage(**payload)
        
        # Return message timestamp (ID)
        return response["ts"]
    
    except SlackApiError as e:
        logger.error(f"Error posting formatted message to Slack: {str(e)}")
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
        # Prepare file upload payload
        payload = {
            "channels": SLACK_CHANNEL_ID,
            "file": file_path
        }
        
        # Add optional parameters
        if title:
            payload["title"] = title
        
        if initial_comment:
            payload["initial_comment"] = initial_comment
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        # Upload file
        response = slack_client.files_upload_v2(**payload)
        
        # Return file ID
        return response.get("file", {}).get("id")
    
    except SlackApiError as e:
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
        
        return response["ok"]
    
    except SlackApiError as e:
        # Ignore "already_reacted" error
        if "already_reacted" in str(e):
            return True
        
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
        
        # Add cursor if provided
        if cursor:
            payload["cursor"] = cursor
        
        # Get history
        response = slack_client.conversations_history(**payload)
        
        messages = response.get("messages", [])
        next_cursor = response.get("response_metadata", {}).get("next_cursor")
        
        return messages, next_cursor
    
    except SlackApiError as e:
        logger.error(f"Error getting channel history: {str(e)}")
        return [], None

# Alias for backward compatibility
get_channel_messages = get_channel_history

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
        
        return response["ok"]
    
    except SlackApiError as e:
        logger.error(f"Error deleting message: {str(e)}")
        return False

def format_market_with_images(market_data):
    """
    Format a market message for Slack with event banner and option images.
    
    Args:
        market_data: Market data dictionary with images
        
    Returns:
        Tuple of (text_message, blocks_array)
    """
    # Check if this is an event or regular market
    is_event = market_data.get('is_event', False)
    
    # Basic market information
    question = market_data.get('question', 'Unknown Market')
    category = market_data.get('category', 'uncategorized')
    
    # Look for expiry date in all possible fields
    expiry = "Unknown"
    if 'expiry_time' in market_data:
        expiry = market_data.get('expiry_time')
    elif 'endDate' in market_data:
        expiry = market_data.get('endDate')
    elif 'end_date' in market_data:
        expiry = market_data.get('end_date')
    elif 'expiryTime' in market_data:
        expiry = market_data.get('expiryTime')
    
    event_name = market_data.get('event_name', '')
    event_id = market_data.get('event_id', '')
    
    # Format expiry date nicely if it's a timestamp or ISO format
    try:
        from datetime import datetime
        import dateutil.parser
        
        if isinstance(expiry, int) or (isinstance(expiry, str) and expiry.isdigit()):
            # Handle numeric timestamp (milliseconds or seconds)
            expiry_date = datetime.fromtimestamp(int(expiry) / 1000 if int(expiry) > 1000000000000 else int(expiry))
            expiry = expiry_date.strftime('%Y-%m-%d %H:%M UTC')
        elif isinstance(expiry, str) and ('T' in expiry or '-' in expiry):
            # Handle ISO format date string (YYYY-MM-DDTHH:MM:SS)
            try:
                expiry_date = dateutil.parser.parse(expiry)
                expiry = expiry_date.strftime('%Y-%m-%d %H:%M UTC')
                logger.info(f"Parsed ISO date format: {expiry}")
            except Exception as date_e:
                logger.error(f"Error parsing ISO date format: {date_e}")
    except Exception as e:
        logger.error(f"Error formatting expiry date: {e}")
    
    # Start with a text fallback message
    text_message = f"*New {'Event' if is_event else 'Market'} for Approval*\n"
    text_message += f"*{'Event' if is_event else 'Question'}:* {question}\n"
    text_message += f"*Category:* {category}\n"
    text_message += f"*Expiry:* {expiry}\n"
    
    if event_name and not is_event:
        text_message += f"*Event:* {event_name}\n"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"New {'Event' if is_event else 'Market'} for Approval"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{'Event' if is_event else 'Question'}:* {question}"
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
    
    # For regular markets, add event info
    if event_name and not is_event:
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
    
    # Handle options based on whether this is an event or regular market
    if is_event:
        # For events, use main event image and icon - no individual option images
        # First try to get options from outcomes field (proper API format)
        options = []
        outcomes_raw = market_data.get("outcomes", "[]")
        try:
            if isinstance(outcomes_raw, str):
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
                
            if isinstance(outcomes, list):
                options = outcomes
                logger.info(f"Extracted {len(options)} options from outcomes field")
        except Exception as e:
            logger.error(f"Error parsing outcomes field: {str(e)}")
            
        # If no options found in outcomes, try the options field
        if not options:
            options = market_data.get('options', [])
            logger.info(f"Using {len(options)} options from options field")
            
        option_market_ids = market_data.get('option_market_ids', {})
        
        # Add option divider
        blocks.append({
            "type": "divider"
        })
        
        # Add heading for options
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Options:*"
            }
        })
        
        # For each option, show the option name with its icon INLINE
        option_images = market_data.get('option_images', {})
        for option in options:
            option_text = f"*{option}*"
            
            # Get option image if available
            option_image_url = None
            if option in option_images and option_images[option]:
                option_image_url = option_images[option]
            
            # If we have an image, display it inline with the option
            if option_image_url and is_valid_url(option_image_url):
                # Create a section with both text and image
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": option_text
                    },
                    "accessory": {
                        "type": "image",
                        "image_url": option_image_url,
                        "alt_text": f"Option: {option}"
                    }
                })
            else:
                # If no image, just show the option text
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": option_text
                    }
                })
    else:
        # Regular market (binary Yes/No) - only show one banner image
        outcomes = []
        try:
            # Try to extract from outcomes field first
            outcomes_raw = market_data.get("outcomes", "[]")
            if isinstance(outcomes_raw, str):
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
            
            if isinstance(outcomes, list) and outcomes:
                logger.info(f"Binary market with {len(outcomes)} outcomes from outcomes field")
                # Add outcomes as options section
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Options:* " + ", ".join(outcomes)
                    }
                })
        except Exception as e:
            logger.error(f"Error extracting outcomes for binary market: {str(e)}")
        
        # For binary markets, we DON'T add individual option images
        # The event banner image is already added above for all markets
    
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

def post_slack_message(message, blocks=None, market_data=None):
    """
    Post a message to Slack and add approval reactions.
    
    Args:
        message: Message text to post
        blocks: Optional blocks for rich formatting
        market_data: Optional market data dictionary for auto-formatting with images
        
    Returns:
        Response dictionary if successful, None otherwise
    """
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return None
    
    try:
        # If market data is provided, format the message with images
        if market_data:
            message, blocks = format_market_with_images(market_data)
        
        # Prepare payload
        payload = {
            "channel": SLACK_CHANNEL_ID,
            "text": message
        }
        
        # Add blocks if provided
        if blocks:
            payload["blocks"] = blocks
        
        # Post to Slack
        response = slack_client.chat_postMessage(**payload)
        
        if response and response.get('ok'):
            message_id = response['ts']
            
            # Add standard approval/rejection reactions
            add_reaction_to_message(message_id, "thumbsup")
            add_reaction_to_message(message_id, "thumbsdown")
            
            logger.info(f"Posted message to Slack with ID {message_id}")
            return response
        else:
            logger.error(f"Failed to post message to Slack: {response.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        logger.error(f"Error posting message to Slack: {str(e)}")
        return None

def post_markets_to_slack(markets, format_market_message_func=None):
    """
    Post a batch of markets to Slack.
    
    Args:
        markets: List of market model instances
        format_market_message_func: Optional function to format the market message
        
    Returns:
        Number of markets successfully posted
    """
    posted_count = 0
    
    if not slack_client:
        logger.error("Slack client not initialized - missing token")
        return posted_count
    
    # Default format function if none provided
    if format_market_message_func is None:
        def default_format(market):
            """Default formatting for markets"""
            message = f"*{market.question}*"
            return message, None
        format_market_message_func = default_format
    
    for market in markets:
        try:
            # Format message
            message_text, blocks = format_market_message_func(market)
            
            # Post to Slack
            response = slack_client.chat_postMessage(
                channel=SLACK_CHANNEL_ID,
                text=message_text,
                blocks=blocks
            )
            
            if response and response.get('ok'):
                message_id = response['ts']
                
                # Add approval/rejection reactions
                add_reaction_to_message(message_id, "thumbsup")
                add_reaction_to_message(message_id, "thumbsdown")
                
                # Set the message ID on the market
                if hasattr(market, 'message_id'):
                    market.message_id = message_id
                if hasattr(market, 'slack_message_id'):
                    market.slack_message_id = message_id
                if hasattr(market, 'posted'):
                    market.posted = True
                
                posted_count += 1
                logger.info(f"Posted market to Slack with message ID {message_id}")
            else:
                logger.error(f"Failed to post market to Slack: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error posting market to Slack: {str(e)}")
    
    return posted_count