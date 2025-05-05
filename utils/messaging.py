"""
Slack messaging utilities.

This module provides functions for posting messages to Slack and handling reactions.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# Check if we're in test mode
def is_test_environment():
    """Check if we're in test environment."""
    return os.environ.get("TESTING") == "true"

# Initialize Slack client
slack_token = os.environ.get("SLACK_BOT_TOKEN")
slack_channel_id = os.environ.get("SLACK_CHANNEL_ID")

if slack_token and not is_test_environment():
    slack_client = WebClient(token=slack_token)
else:
    # In test mode, we'll use mock functions
    slack_client = None
    logger.info("Running in test mode, Slack client not initialized")


def post_message(channel_id: Optional[str], text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Post a message to a Slack channel.
    
    Args:
        channel_id: The Slack channel ID to post to
        text: Plain text message content
        blocks: Rich layout blocks (optional)
        
    Returns:
        Dict with response containing the message timestamp (ts)
    """
    # If in test mode, use mock implementation
    if is_test_environment():
        from test_utils.mock_slack import post_message as mock_post_message
        return mock_post_message(channel_id, text, blocks)
    
    try:
        # Default to configured channel if none provided
        if not channel_id and slack_channel_id:
            channel_id = slack_channel_id
            
        if not channel_id:
            logger.error("No Slack channel ID provided")
            return {"ok": False, "error": "No channel ID provided"}
            
        # Post message to Slack
        response = slack_client.chat_postMessage(
            channel=channel_id,
            text=text,
            blocks=blocks if blocks else None
        )
        
        logger.info(f"Posted message to Slack channel {channel_id}, ts: {response.get('ts')}")
        return response.data
        
    except SlackApiError as e:
        logger.error(f"Error posting message to Slack: {str(e)}")
        return {"ok": False, "error": str(e)}


def get_message_reactions(message_id: str) -> List[Dict[str, Any]]:
    """
    Get reactions for a message.
    
    Args:
        message_id: The message timestamp (ts)
        
    Returns:
        List of reaction objects with name and users
    """
    # If in test mode, use mock implementation
    if is_test_environment():
        from test_utils.mock_slack import get_message_reactions as mock_get_reactions
        return mock_get_reactions(message_id)
    
    try:
        # Get reactions
        response = slack_client.reactions_get(
            channel=slack_channel_id,
            timestamp=message_id
        )
        
        if response.get("ok") and response.get("message"):
            return response.get("message", {}).get("reactions", [])
        else:
            logger.warning(f"No reactions found for message {message_id}")
            return []
            
    except SlackApiError as e:
        logger.error(f"Error checking reactions in Slack: {str(e)}")
        return []


def get_channel_messages(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent messages from the configured channel.
    
    Args:
        limit: Maximum number of messages to return
        
    Returns:
        List of message objects
    """
    # If in test mode, use mock implementation
    if is_test_environment():
        from test_utils.mock_slack import get_channel_messages as mock_get_messages
        return mock_get_messages(limit)
    
    try:
        # Get channel history
        response = slack_client.conversations_history(
            channel=slack_channel_id,
            limit=limit
        )
        
        if response.get("ok") and response.get("messages"):
            return response.get("messages", [])
        else:
            logger.warning("No messages found in channel history")
            return []
            
    except SlackApiError as e:
        logger.error(f"Error checking reactions in Slack: {str(e)}")
        return []


def post_markets_to_slack(markets: List[Dict[str, Any]], max_to_post: int = 5) -> List[Tuple[Dict[str, Any], Optional[str]]]:
    """
    Post multiple markets to Slack for approval.
    
    Args:
        markets: List of market data dictionaries
        max_to_post: Maximum number of markets to post
        
    Returns:
        List of tuples with (market_data, message_id) pairs
    """
    if not markets:
        logger.warning("No markets to post")
        return []
        
    posted = []
    count = 0
    
    for market in markets:
        if count >= max_to_post:
            break
            
        message_id = post_market_for_approval(market)
        
        if message_id:
            posted.append((market, message_id))
            count += 1
            
    logger.info(f"Posted {len(posted)} markets to Slack for approval")
    return posted


def post_market_for_approval(market_data: Dict[str, Any]) -> Optional[str]:
    """
    Post a market to Slack for approval.
    
    Args:
        market_data: The market data dictionary
        
    Returns:
        Message timestamp (ts) if successful, None otherwise
    """
    if not market_data:
        logger.error("No market data provided")
        return None
    
    # Deep debugging of market data to understand the structure
    logger.info(f"DEBUG: Full market data keys: {list(market_data.keys())}")
    
    # Check if this is a multi-option market
    is_multiple = market_data.get('is_multiple_option', False)
    
    # Log details for debugging
    logger.info(f"Posting market for approval: {market_data.get('question', 'Unknown')}")
    logger.info(f"  - Type: {('Multiple-choice' if is_multiple else 'Binary')}")
    
    # Output debug info for multi-option market
    if is_multiple:
        logger.info(f"  - ID: {market_data.get('id')}")
        logger.info(f"  - Is multiple? {is_multiple}")
        logger.info(f"  - Original market IDs: {market_data.get('original_market_ids', [])}")
        
        # Parse outcomes to ensure we're handling them correctly
        outcomes_raw = market_data.get("outcomes", "[]")
        logger.info(f"  - Raw outcomes type: {type(outcomes_raw)}")
        logger.info(f"  - Raw outcomes value: {outcomes_raw}")
        
        outcomes = []
        try:
            if isinstance(outcomes_raw, str):
                import json
                outcomes = json.loads(outcomes_raw)
                logger.info(f"  - Parsed outcomes from JSON string: {outcomes}")
            else:
                outcomes = outcomes_raw
                logger.info(f"  - Using outcomes directly: {outcomes}")
            
            # Verify unique outcomes
            unique_outcomes = list(dict.fromkeys(outcomes))
            logger.info(f"  - Options after deduplication ({len(unique_outcomes)}): {unique_outcomes}")
        except Exception as e:
            logger.error(f"Error parsing outcomes: {str(e)}")
    else:
        logger.info(f"  - Condition ID: {market_data.get('conditionId')}")
    
    # Market ID to track in the message - CRITICAL PART
    market_id = ""
    if is_multiple:
        market_id = market_data.get('id', 'unknown-multiple')
        logger.info(f"  - Using ID for multi-option market: {market_id}")
    else:
        market_id = market_data.get('conditionId', 'unknown-binary')
        logger.info(f"  - Using conditionId for binary market: {market_id}")

    # Format message text - include market type in the header for clarity
    market_type_text = "Multiple-Choice Market" if is_multiple else "Binary Market (Yes/No)"
    text = f"*New {market_type_text} for Approval*\n\n*Question:* {market_data.get('question', 'N/A')}"
    
    # Create rich message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"New {market_type_text} for Approval"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {market_data.get('question', 'N/A')}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Category:* {market_data.get('fetched_category', 'general')}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*End Date:* {market_data.get('endDate', 'N/A')}"
                }
            ]
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Type:* {market_type_text}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*ID:* {market_id}"
                }
            ]
        }
    ]
    
    # Add options section - CRITICAL PART
    outcomes_raw = market_data.get("outcomes", "[]")
    outcomes = []
    
    # Parse outcomes which come as a JSON string
    try:
        if isinstance(outcomes_raw, str):
            outcomes = json.loads(outcomes_raw)
            logger.info(f"Parsed {len(outcomes)} outcomes from JSON string")
        else:
            outcomes = outcomes_raw
            logger.info(f"Using {len(outcomes)} outcomes directly")
            
        # For multiple-option markets, ensure we have unique options
        if is_multiple and outcomes:
            # Remove duplicates while preserving order
            unique_outcomes = []
            seen = set()
            for outcome in outcomes:
                if outcome not in seen:
                    seen.add(outcome)
                    unique_outcomes.append(outcome)
            
            outcomes = unique_outcomes
            logger.info(f"Deduplicated to {len(outcomes)} unique outcomes")
            
            # Update the market data for downstream processing
            market_data["outcomes"] = json.dumps(outcomes)
    except Exception as e:
        logger.error(f"Error parsing outcomes: {str(e)}")
        # Default to Yes/No for binary markets if we can't parse outcomes
        if not is_multiple:
            outcomes = ["Yes", "No"]
            logger.info("Defaulting to Yes/No options for binary market")
    
    # Add options to blocks
    if outcomes:
        options_text = "*Options:*\n"
        for i, option in enumerate(outcomes):
            options_text += f"  {i+1}. {option}\n"
        
        logger.info(f"Adding options section with {len(outcomes)} options")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": options_text
            }
        })
    else:
        logger.warning("No options found for market")
    
    # Add note about original market IDs for multiple-option markets
    original_ids = market_data.get('original_market_ids', [])
    if is_multiple and original_ids:
        unique_ids = list(dict.fromkeys(original_ids))
        logger.info(f"Adding section for {len(unique_ids)} original market IDs")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Original Markets:* {len(unique_ids)} markets combined"
            }
        })
    
    # Add image if available
    if market_data.get("image"):
        logger.info(f"Adding image URL: {market_data.get('image')}")
        blocks.append(
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Market Image"
                },
                "image_url": market_data.get("image"),
                "alt_text": "Market Image"
            }
        )
    
    # Add icon if available and different from image
    if market_data.get("icon") and market_data.get("icon") != market_data.get("image"):
        logger.info(f"Adding icon URL: {market_data.get('icon')}")
        blocks.append(
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Market Icon"
                },
                "image_url": market_data.get("icon"),
                "alt_text": "Market Icon"
            }
        )
    
    # Add approval instructions
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "React with :white_check_mark: to approve or :x: to reject."
            }
        }
    )
    
    # Post message to Slack
    logger.info(f"Posting {market_type_text} to Slack channel: {slack_channel_id}")
    response = post_message(slack_channel_id, text, blocks)
    
    if response.get("ok"):
        logger.info(f"Successfully posted {market_type_text} to Slack, ts: {response.get('ts')}")
        return response.get("ts")
    else:
        logger.error(f"Failed to post market for approval: {response.get('error')}")
        return None


def post_message_to_slack(message: str) -> Optional[str]:
    """
    Post a simple text message to Slack.
    
    Args:
        message: Message text to post
        
    Returns:
        Message timestamp (ts) if successful, None otherwise
    """
    response = post_message(slack_channel_id, message)
    
    if response.get("ok"):
        return response.get("ts")
    else:
        logger.error(f"Failed to post message to Slack: {response.get('error')}")
        return None