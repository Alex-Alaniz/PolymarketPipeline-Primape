#!/usr/bin/env python3

"""
Messaging utilities for Polymarket pipeline.

This module provides functions for posting messages to messaging platforms 
(Slack/Discord) and checking for reactions.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger("messaging")

# Initialize the Slack client using the bot token
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

slack_client = WebClient(token=SLACK_BOT_TOKEN) if SLACK_BOT_TOKEN else None

# Reaction emojis for approval/rejection
APPROVE_EMOJI = "white_check_mark"
REJECT_EMOJI = "x"

def post_market_for_approval(market: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Post a market to Slack for approval.
    
    Args:
        market: Market data dictionary
        
    Returns:
        Tuple of (success, message_id) where message_id is the Slack timestamp
    """
    if not slack_client or not SLACK_CHANNEL_ID:
        logger.error("Slack client or channel ID not configured.")
        return False, None
    
    try:
        # Format the message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🏦 New Market for Approval",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Question:* {market.get('question', 'N/A')}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*ID:* {market.get('id', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Condition ID:* {market.get('conditionId', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*End Date:* {market.get('endDate', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Outcomes:* {market.get('outcomes', 'N/A')}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Description:* {market.get('description', 'N/A')[:200]}..."
                }
            }
        ]
        
        # Add image if available
        image_url = market.get("image")
        if image_url and isinstance(image_url, str):
            blocks.append({
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Market Image",
                    "emoji": True
                },
                "image_url": image_url,
                "alt_text": "Market image"
            })
        
        # Add instructions for approval/rejection
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"React with :{APPROVE_EMOJI}: to approve or :{REJECT_EMOJI}: to reject this market."
                }
            ]
        })
        
        # Post the message to Slack
        response = slack_client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            blocks=blocks,
            text=f"New market for approval: {market.get('question', 'N/A')}"
        )
        
        # Return the timestamp (used as message ID in Slack)
        message_id = response.get("ts")
        logger.info(f"Posted market {market.get('id')} to Slack, message ID: {message_id}")
        return True, message_id
        
    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error posting to Slack: {e}")
        return False, None

def check_message_reactions(message_id: str, timeout_minutes: int = 30) -> Tuple[str, Optional[str]]:
    """
    Check for approval/rejection reactions on a Slack message.
    
    Args:
        message_id: Slack message timestamp ID
        timeout_minutes: Minutes after which the approval times out
        
    Returns:
        Tuple of (status, user_id) where:
            status is one of: "approved", "rejected", "pending", "timeout"
            user_id is the ID of the user who approved/rejected (or None)
    """
    if not slack_client or not SLACK_CHANNEL_ID:
        logger.error("Slack client or channel ID not configured.")
        return "pending", None
    
    try:
        # Check if message has timed out
        message_response = slack_client.conversations_history(
            channel=SLACK_CHANNEL_ID,
            latest=message_id,
            limit=1,
            inclusive=True
        )
        
        if not message_response.get("messages"):
            logger.warning(f"Message {message_id} not found in channel.")
            return "pending", None
            
        message = message_response["messages"][0]
        message_time = float(message_id)
        current_time = datetime.now().timestamp()
        
        # Check if the message has timed out
        if current_time - message_time > timeout_minutes * 60:
            logger.info(f"Message {message_id} has timed out after {timeout_minutes} minutes.")
            return "timeout", None
        
        # Check for reactions
        reactions = message.get("reactions", [])
        
        for reaction in reactions:
            # Check for approval emoji
            if reaction.get("name") == APPROVE_EMOJI:
                # Get the first user who reacted with approval
                approver = reaction.get("users", [])[0] if reaction.get("users") else None
                return "approved", approver
            
            # Check for rejection emoji
            if reaction.get("name") == REJECT_EMOJI:
                # Get the first user who reacted with rejection
                rejecter = reaction.get("users", [])[0] if reaction.get("users") else None
                return "rejected", rejecter
        
        # No approval/rejection reactions found
        return "pending", None
        
    except SlackApiError as e:
        logger.error(f"Error checking reactions in Slack: {e}")
        return "pending", None
    except Exception as e:
        logger.error(f"Unexpected error checking reactions: {e}")
        return "pending", None

def post_markets_to_slack(markets: List[Dict[str, Any]], max_to_post: int = 5) -> List[Dict[str, Any]]:
    """
    Post multiple markets to Slack for approval.
    
    Args:
        markets: List of market data dictionaries
        max_to_post: Maximum number of markets to post
        
    Returns:
        List of posted markets with message IDs
    """
    posted_markets = []
    count = 0
    
    for market in markets:
        if count >= max_to_post:
            break
            
        success, message_id = post_market_for_approval(market)
        
        if success and message_id:
            # Add message ID to market data
            market_with_msg = market.copy()
            market_with_msg["message_id"] = message_id
            posted_markets.append(market_with_msg)
            count += 1
            
            # Add a small delay between posts to avoid rate limiting
            import time
            time.sleep(1)
    
    logger.info(f"Posted {count} markets to Slack for approval.")
    return posted_markets
