"""
Slack messaging utilities.

This module provides functions and classes for posting messages to Slack and handling reactions.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    # For testing environments
    WebClient = None
    SlackApiError = Exception

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


class MessagingClient:
    """
    Wrapper class for Slack client with additional functionality.
    
    This class provides a convenient interface for working with Slack,
    including methods for posting messages, checking reactions, and
    updating message formatting.
    """
    
    def __init__(self, token: Optional[str] = None, channel_id: Optional[str] = None):
        """
        Initialize the messaging client.
        
        Args:
            token: Slack bot token (defaults to environment variable)
            channel_id: Slack channel ID (defaults to environment variable)
        """
        self.token = token or slack_token
        self.channel_id = channel_id or slack_channel_id
        
        # Initialize the client if we have a token and not in test mode
        if self.token and not is_test_environment():
            self.client = WebClient(token=self.token)
        else:
            # In test mode, we'll use mock functions
            self.client = None
            logger.info("Running in test mode, Slack client not initialized")
    
    def post_message(self, text: str, blocks: Optional[List[Dict[str, Any]]] = None, 
                    channel_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Post a message to a Slack channel.
        
        Args:
            text: Plain text message content
            blocks: Rich layout blocks (optional)
            channel_id: Channel to post to (defaults to configured channel)
            
        Returns:
            Dict with response containing the message timestamp (ts)
        """
        # If in test mode, use mock implementation
        if is_test_environment():
            from test_utils.mock_slack import post_message as mock_post_message
            return mock_post_message(channel_id or self.channel_id, text, blocks)
        
        try:
            # Use provided channel or default
            channel = channel_id or self.channel_id
                
            if not channel:
                logger.error("No Slack channel ID provided")
                return {"ok": False, "error": "No channel ID provided"}
                
            # Post message to Slack
            response = self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks if blocks else None
            )
            
            logger.info(f"Posted message to Slack channel {channel}, ts: {response.get('ts')}")
            return response.data
            
        except SlackApiError as e:
            logger.error(f"Error posting message to Slack: {str(e)}")
            return {"ok": False, "error": str(e)}
    
    def get_channel_history(self, limit: int = 100, 
                           oldest: Optional[str] = None, 
                           latest: Optional[str] = None,
                           cursor: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Get message history from the Slack channel with pagination support.
        
        Args:
            limit: Maximum number of messages to retrieve per page
            oldest: Start of time range (Unix timestamp)
            latest: End of time range (Unix timestamp)
            cursor: Pagination cursor for subsequent calls
            
        Returns:
            Tuple of (messages, next_cursor)
        """
        # If in test mode, use mock implementation
        if is_test_environment():
            from test_utils.mock_slack import get_channel_messages as mock_get_messages
            return mock_get_messages(limit), None
        
        try:
            # Build params
            params = {
                "channel": self.channel_id,
                "limit": limit
            }
            
            if oldest:
                params["oldest"] = oldest
            if latest:
                params["latest"] = latest
            if cursor:
                params["cursor"] = cursor
            
            # Get channel history
            response = self.client.conversations_history(**params)
            
            messages = response.get("messages", [])
            next_cursor = response.get("response_metadata", {}).get("next_cursor")
            
            logger.info(f"Got {len(messages)} messages from Slack channel")
            logger.debug(f"Has more: {bool(next_cursor)}")
            
            return messages, next_cursor
            
        except SlackApiError as e:
            logger.error(f"Error getting channel history from Slack: {str(e)}")
            return [], None
            
    def update_message(self, message_id: str, text: str, 
                      attachments: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Update an existing message in Slack.
        
        Args:
            message_id: The message timestamp (ts) to update
            text: New message text
            attachments: New message attachments
            
        Returns:
            True if successful, False otherwise
        """
        # If in test mode, just log and return
        if is_test_environment():
            logger.info(f"[TEST MODE] Would update message {message_id}")
            return True
        
        # Ensure client is initialized
        if not self.client:
            logger.error("Slack client not initialized")
            return False
            
        try:
            # Build update parameters
            params = {
                "channel": self.channel_id,
                "ts": message_id,
                "text": text
            }
            
            # Convert attachments to JSON string for Slack API
            if attachments:
                import json
                # Slack API expects attachments as a JSON string
                params["attachments"] = json.dumps(attachments)
                
            # Update the message with proper debug logging
            logger.debug(f"Updating message {message_id} with params: {params}")
            response = self.client.chat_update(**params)
            
            if response and response.get("ok"):
                logger.info(f"Successfully updated message {message_id}")
                return True
            else:
                logger.warning(f"Failed to update message {message_id}: {response.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating message in Slack: {str(e)}")
            return False


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
            reactions = response.get("message", {}).get("reactions", [])
            logger.info(f"Got {len(reactions)} reactions for message {message_id}: {reactions}")
            return reactions
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
        
        
def add_reaction(message_id: str, reaction_name: str) -> bool:
    """
    Add a reaction to a message.
    
    Args:
        message_id: The message timestamp (ts)
        reaction_name: The name of the reaction emoji (without colons)
        
    Returns:
        True if successful, False otherwise
    """
    # If in test mode, use mock implementation
    if is_test_environment():
        from test_utils.mock_slack import add_reaction as mock_add_reaction
        return mock_add_reaction(message_id, reaction_name)
    
    try:
        # Add reaction
        response = slack_client.reactions_add(
            channel=slack_channel_id,
            timestamp=message_id,
            name=reaction_name
        )
        
        if response.get("ok"):
            logger.info(f"Added reaction :{reaction_name}: to message {message_id}")
            return True
        else:
            logger.warning(f"Failed to add reaction :{reaction_name}: to message {message_id}")
            return False
            
    except SlackApiError as e:
        # Check if the error is because the reaction already exists
        if "already_reacted" in str(e):
            logger.info(f"Reaction :{reaction_name}: already exists on message {message_id}")
            return True
        else:
            logger.error(f"Error adding reaction to Slack message: {str(e)}")
            return False


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
                # json is already imported at the top of the file
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
                    "text": f"*Category:* {market_data.get('event_category') or 'Uncategorized'}"
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
            # json is already imported at the top of the file
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
    
    # Add event image as banner if available (using accessory in section for inline display)
    event_image = market_data.get("event_image")
    if event_image:
        logger.info(f"Adding event image as banner: {event_image}")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Event Banner*"
            },
            "accessory": {
                "type": "image",
                "image_url": event_image,
                "alt_text": "Event Banner"
            }
        })
    
    # For multi-option markets, display options with their respective images
    if is_multiple:
        # Get option-specific images
        option_images = {}
        try:
            option_images_raw = market_data.get("option_images", "{}")
            if isinstance(option_images_raw, str):
                option_images = json.loads(option_images_raw)
            else:
                option_images = option_images_raw
            logger.info(f"Parsed option images for {len(option_images)} options")
        except Exception as e:
            logger.error(f"Error parsing option images: {str(e)}")
            
        # Get outcomes again to ensure we have the same order
        options = []
        try:
            outcomes_raw = market_data.get("outcomes", "[]")
            if isinstance(outcomes_raw, str):
                options = json.loads(outcomes_raw)
            else:
                options = outcomes_raw
        except Exception as e:
            logger.error(f"Error re-parsing outcomes for images: {str(e)}")
            
        # Add each option with its image
        for i, option in enumerate(options):
            # Option text section with numbering and inline image if available
            option_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Option {i+1}:* {option}"
                }
            }
            
            # Add image as an accessory if available (this makes it inline)
            if option in option_images and option_images[option]:
                logger.info(f"Adding inline image for option '{option}': {option_images[option]}")
                option_block["accessory"] = {
                    "type": "image",
                    "image_url": option_images[option],
                    "alt_text": f"Image for {option}"
                }
            
            # Add the option block to the message
            blocks.append(option_block)
    else:
        # For binary markets, add the main market image as an inline accessory
        if market_data.get("image"):
            logger.info(f"Adding market image URL: {market_data.get('image')}")
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Market Image*"
                },
                "accessory": {
                    "type": "image",
                    "image_url": market_data.get("image"),
                    "alt_text": "Market Image"
                }
            })
    
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
        message_id = response.get("ts")
        logger.info(f"Successfully posted {market_type_text} to Slack, ts: {message_id}")
        
        # Automatically add approval/rejection reactions to message
        try:
            # Add white_check_mark for approval
            add_reaction(message_id, "white_check_mark")
            # Add x for rejection
            add_reaction(message_id, "x")
            logger.info(f"Successfully added approval/rejection reactions to message {message_id}")
        except Exception as e:
            logger.error(f"Error adding reactions to message: {str(e)}")
        
        return message_id
    else:
        logger.error(f"Failed to post market for approval: {response.get('error')}")
        return None


def post_message_to_slack(message: Union[str, Tuple[str, List[Dict[str, Any]]]]) -> Optional[str]:
    """
    Post a message to Slack, supporting both simple text and rich blocks formatting.
    
    Args:
        message: Either a simple string or a tuple of (text, blocks)
        
    Returns:
        Message timestamp (ts) if successful, None otherwise
    """
    # Check if we have rich blocks formatting
    if isinstance(message, tuple) and len(message) == 2:
        text, blocks = message
        response = post_message(slack_channel_id, text, blocks)
    else:
        # Simple text message
        response = post_message(slack_channel_id, message)
    
    if response.get("ok"):
        return response.get("ts")
    else:
        logger.error(f"Failed to post message to Slack: {response.get('error')}")
        return None