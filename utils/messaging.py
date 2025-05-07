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
    
    # RULE 1 & 2: Different image handling based on market type
    # Determine if this is a binary market (Yes/No outcomes) or multi-option market
    # Determine market type from flags in the data
    is_binary = market_data.get('is_binary', False)
    is_multiple_option = market_data.get('is_multiple_option', False)
    
    # If flags aren't set, check outcomes manually
    if not is_binary and not is_multiple_option:
        # Check for binary Yes/No outcomes
        outcomes_raw = market_data.get("outcomes", "[]")
        try:
            if isinstance(outcomes_raw, str):
                outcomes = json.loads(outcomes_raw)
            else:
                outcomes = outcomes_raw
                
            # Check if outcomes are exactly ["Yes", "No"]
            if isinstance(outcomes, list) and sorted(outcomes) == ["No", "Yes"]:
                is_binary = True
                logger.info("Detected binary Yes/No market from outcomes")
        except Exception as e:
            logger.error(f"Error checking binary market status: {str(e)}")
        
        # Check for multiple options / events
        if market_data.get('is_multiple_choice', False) or market_data.get('is_event', False):
            is_multiple_option = True
            logger.info("Detected multi-option market from is_multiple_choice or is_event flag")
    
    # Parse events data if it's a string
    events_data = market_data.get('events')
    if isinstance(events_data, str):
        try:
            if events_data.startswith('[') or events_data.startswith('{'):
                events_data = json.loads(events_data)
                logger.info(f"Successfully parsed events data from JSON string")
        except Exception as e:
            logger.error(f"Error parsing events string data: {str(e)}")
    
    # Debug log the events data structure
    if events_data:
        if isinstance(events_data, list):
            logger.info(f"Events data is a list with {len(events_data)} items")
            if len(events_data) > 0 and isinstance(events_data[0], dict):
                logger.info(f"First event keys: {list(events_data[0].keys())}")
                if 'image' in events_data[0]:
                    logger.info(f"Found first event image: {events_data[0]['image'][:30]}...")
        else:
            logger.info(f"Events data is not a list: {type(events_data)}")
        
        # If we have events array but no market type determined, assume it's a multi-option market
        if not is_binary and not is_multiple_option:
            is_multiple_option = True
            logger.info("Detected multi-option market from presence of events array")
    
    # Get banner image based on market type
    banner_image = None
    
    # RULE 1: Binary Markets (Yes/No outcomes)
    if is_binary:
        # Get banner image from 'event_image' field first (processed by our filter)
        if 'event_image' in market_data:
            banner_image = market_data.get('event_image')
            logger.info(f"Binary market: Using pre-processed event_image: {banner_image}")
        else:
            # Fall back to market-level image URL (not icon)
            banner_image = market_data.get('image')
            logger.info(f"Binary market: Using market-level image: {banner_image}")
    
    # RULE 2: Multi-option Markets
    elif is_multiple_option:
        # First try 'event_image' field (set by our filter)
        if 'event_image' in market_data:
            banner_image = market_data.get('event_image')
            logger.info(f"Multi-option market: Using pre-processed event_image: {banner_image}")
        else:
            # RULE 2: For multi-option markets, MUST use market["events"][0]["image"]
            try:
                if isinstance(events_data, list) and len(events_data) > 0:
                    first_event = events_data[0]
                    if isinstance(first_event, dict) and 'image' in first_event:
                        banner_image = first_event.get('image')
                        logger.info(f"Multi-option market: Using events[0].image: {banner_image}")
                        logger.info(f"SUCCESS: Found event banner from events[0].image")
            except Exception as e:
                logger.error(f"Error getting event banner image: {str(e)}")
    
    # Only use fallbacks if we absolutely couldn't find the banner image
    if not banner_image:
        logger.warning("Could not find preferred banner image, trying fallbacks")
        # Try other possible fields
        for field in ['image', 'banner_image', 'bannerImage']:
            if field in market_data and market_data[field]:
                banner_image = market_data[field]
                logger.info(f"Using fallback banner image from {field}: {banner_image}")
                break
    
    # Display the banner image if available and accessible to Slack
    if banner_image and is_valid_url(banner_image) and is_slack_accessible_url(banner_image):
        blocks.append(
            {
                "type": "image",
                "image_url": banner_image,
                "alt_text": "Event banner"
            }
        )
    
    # Handle options based on whether this is an event or regular market
    if is_event:
        # For events, use main event image and icon plus individual option images
        # Try to extract options from events structure first (best source)
        options = []
        option_info = {}  # Dictionary to store option_id -> option_name mapping
        
        # Try to get event outcomes from events array (best source for multiple-choice markets)
        if events_data:
            try:
                if isinstance(events_data, list) and len(events_data) > 0:
                    for event_obj in events_data:
                        if isinstance(event_obj, dict) and 'outcomes' in event_obj:
                            event_outcomes = event_obj.get('outcomes', [])
                            
                            # Process outcomes
                            for outcome in event_outcomes:
                                if isinstance(outcome, dict):
                                    # For events data, we have IDs and names/titles
                                    outcome_id = outcome.get('id', '')
                                    # Support both name and title fields
                                    outcome_name = outcome.get('title', '')
                                    if not outcome_name:
                                        outcome_name = outcome.get('name', '')
                                    
                                    if outcome_id and outcome_name:
                                        options.append(outcome_id)  # Store the ID as the option
                                        option_info[outcome_id] = outcome_name  # Map ID to name
                                        logger.info(f"Found outcome from events: {outcome_id} -> {outcome_name}")
            except Exception as e:
                logger.error(f"Error extracting options from events: {str(e)}")
        
        # If no options found in events, try the outcomes field
        if not options:
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
        
        # If still no options, try the options field
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
        
        # RULE 2: For multi-option markets, get option icons
        option_images = {}  # Dict to store option_id -> option_icon mapping
        
        # Look for option images - Need to extract icon for each option
        # From the example: For "Option: Real Madrid", we want its specific market's icon URL 
        # Not from nested outcomes, but from the option markets themselves
        
        # For each option (like "Real Madrid"), we need to find the corresponding market data
        option_markets = market_data.get('option_markets', [])
        
        # If option_markets isn't populated, check the raw response
        if not option_markets and isinstance(market_data.get('response'), dict):
            option_markets = market_data.get('response', {}).get('option_markets', [])
            
        # Log what we're working with
        logger.info(f"Checking option markets array with {len(option_markets) if option_markets else 0} items")
        
        # First process option_markets if available (direct market references)
        if option_markets:
            try:
                for option_market in option_markets:
                    if isinstance(option_market, dict):
                        # Get market ID and icon
                        market_id = option_market.get('id', '')
                        market_icon = option_market.get('icon', '')
                        market_question = option_market.get('question', '')
                        
                        # Use the question as the display name for this option
                        if market_id and market_question:
                            # Store the icon URL indexed by market ID
                            if market_icon and is_valid_url(market_icon):
                                option_images[market_id] = market_icon
                                logger.info(f"Found icon for market ID {market_id} ({market_question}): {market_icon[:30]}...")
                                # Also set the display name in our option_info mapping
                                option_info[market_id] = market_question
            except Exception as e:
                logger.error(f"Error processing option_markets: {str(e)}")
        
        # If we didn't find icons from option_markets, fall back to events structure
        if not option_images and events_data:
            try:
                logger.info("Falling back to events.outcomes for option icons...")
                if isinstance(events_data, list) and len(events_data) > 0:
                    for event_obj in events_data:
                        if isinstance(event_obj, dict) and 'outcomes' in event_obj:
                            outcomes_data = event_obj.get('outcomes', [])
                            
                            # Process each outcome for icons
                            for outcome in outcomes_data:
                                if isinstance(outcome, dict):
                                    outcome_id = outcome.get('id', '')
                                    
                                    # First check for option_market_id field
                                    option_market_id = outcome.get('option_market_id', '')
                                    if option_market_id:
                                        # This links to the market, use that ID
                                        outcome_id = option_market_id
                                    
                                    # Try to get the icon specifically (preferred)
                                    outcome_icon = outcome.get('icon', '')
                                    
                                    # If no icon, try image as fallback
                                    if not outcome_icon or not is_valid_url(outcome_icon):
                                        outcome_icon = outcome.get('image', '')
                                    
                                    # Store in our option_images dict with outcome ID as key
                                    if outcome_id and outcome_icon and is_valid_url(outcome_icon):
                                        option_images[outcome_id] = outcome_icon
                                        logger.info(f"Found option icon from events for {outcome_id}: {outcome_icon[:30]}...")
            except Exception as e:
                logger.error(f"Error extracting option icons from events data: {str(e)}")
                
        # Also look for option_info directly in the data (for testing or pre-processed data)
        if isinstance(market_data.get('option_info'), dict) and market_data['option_info']:
            direct_option_info = market_data['option_info']
            for option_id, option_name in direct_option_info.items():
                option_info[option_id] = option_name
                if option_id not in options:
                    options.append(option_id)
                logger.info(f"Using provided option info: {option_id} -> {option_name}")
        
        # Also check for direct option_images field (for testing or pre-processed data)
        if isinstance(market_data.get('option_images'), dict) and market_data['option_images']:
            direct_option_images = market_data['option_images'] 
            for option_id, option_url in direct_option_images.items():
                option_images[option_id] = option_url
                if option_id not in options:
                    options.append(option_id)
                logger.info(f"Using provided option image: {option_id} -> {option_url[:30]}...")
        
        # Log what we found
        logger.info(f"Found {len(option_images)} option icons and {len(option_info)} option names")
        logger.info(f"Options to display: {options}")
        
        # Prepare the fields list for the section - following Rule 2 structure for Slack payload
        option_fields = []
        
        for option in options:
            # Use the option name from our mapping if available, otherwise use ID
            display_name = option_info.get(option, option) if option_info else option
            
            # Get option icon URL
            icon_url = option_images.get(option, '')
            
            # Only include valid image URLs, don't show the raw JSON
            if icon_url and is_valid_url(icon_url):
                # Format option with both name and icon URL for proper display in Slack
                # Using the format "*Name* : url" to ensure Slack displays it correctly
                option_field = {
                    "type": "mrkdwn",
                    "text": f"*{display_name}*"
                }
                option_fields.append(option_field)
                
                # Add the image as a separate block for better rendering
                # Only add if the URL is accessible to Slack
                if is_slack_accessible_url(icon_url):
                    blocks.append({
                        "type": "image",
                        "image_url": icon_url,
                        "alt_text": f"Option icon for {display_name}"
                    })
                
                logger.info(f"Added option field with separate image block: {display_name}")
            else:
                # No icon available, just show the name
                option_field = {
                    "type": "mrkdwn",
                    "text": f"*{display_name}*"
                }
                option_fields.append(option_field)
                logger.info(f"Added option field without image: {display_name}")
        
        # Add all option fields in a single section
        if option_fields:
            logger.info(f"Adding {len(option_fields)} option fields to message")
            blocks.append({
                "type": "section",
                "fields": option_fields
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

def is_slack_accessible_url(url):
    """
    Check if a URL is likely to be accessible by Slack for image rendering.
    
    Slack has restrictions on which URLs it can access. This function 
    checks if the URL is from a known domain that Slack can access.
    
    Args:
        url: URL string to check
        
    Returns:
        Boolean indicating if the URL is likely accessible to Slack
    """
    if not url or not isinstance(url, str):
        return False
        
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        
        # List of domains known to work with Slack
        slack_accessible_domains = [
            'polymarket-upload.s3.us-east-2.amazonaws.com',
            's3.amazonaws.com',
            'amazonaws.com',
            'polymarket.co',
            'slack.com',
            'slack-edge.com',
            'pbs.twimg.com',
            'twimg.com',
            'imgur.com',
            'i.imgur.com',
            'cdn.discordapp.com',
            'media.discordapp.net',
            'giphy.com',
            'media.giphy.com',
            'unsplash.com',
            'images.unsplash.com',
            'img.youtube.com'
        ]
        
        # Check if domain is in the whitelist
        domain = result.netloc.lower()
        for accessible_domain in slack_accessible_domains:
            if accessible_domain in domain:
                return True
                
        # For testing, we'll allow certain other domains
        # that have been confirmed to work
        testing_domains = [
            'upload.wikimedia.org'
        ]
        
        for test_domain in testing_domains:
            if test_domain in domain:
                return True
                
        # By default, assume other domains may not be accessible by Slack
        logger.warning(f"URL may not be accessible to Slack: {url[:50]}...")
        return False
        
    except Exception as e:
        logger.warning(f"Error checking Slack URL accessibility: {str(e)} - {url[:30]}...")
        return False

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
    
    # Common invalid URL patterns to filter out
    invalid_patterns = [
        "undefined", "null", "N/A", "none", "[]", "{}", 
        "false", "true", "<", ">", "data:image"
    ]
    
    # Quickly check for common invalid patterns
    for pattern in invalid_patterns:
        if pattern in url.lower():
            logger.warning(f"Invalid URL detected containing '{pattern}': {url[:30]}...")
            return False
    
    # Only accept http/https URLs
    if not (url.startswith('http://') or url.startswith('https://')):
        logger.warning(f"Invalid URL scheme (not http/https): {url[:30]}...")
        return False
        
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        
        # URL must have scheme (http/https) and netloc (domain)
        valid = all([result.scheme, result.netloc])
        if not valid:
            logger.warning(f"Invalid URL structure: {url[:30]}...")
            return False
            
        # Check for common image domains we know are valid
        known_valid_domains = [
            'polymarket-upload.s3.us-east-2.amazonaws.com',
            'upload.wikimedia.org',
            's3.amazonaws.com',
            'amazonaws.com',
            'images.theabcdn.com',
            'pbs.twimg.com',
            'cdn.pixabay.com',
            'i.imgur.com',
            'upload.wikimedia.org'
        ]
        
        domain = result.netloc.lower()
        for valid_domain in known_valid_domains:
            if valid_domain in domain:
                return True
                
        # For other domains, check file extension
        path = result.path.lower()
        valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        
        for ext in valid_extensions:
            if path.endswith(ext):
                return True
                
        # If we can't confirm it's an image URL, log and return cautiously
        logger.warning(f"URL doesn't match known image patterns: {url[:50]}...")
        # Still return True for non-standard URLs to allow them through if they pass basic validation
        return True
        
    except Exception as e:
        logger.warning(f"Error validating URL: {str(e)} - {url[:30]}...")
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