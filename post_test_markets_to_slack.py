"""
Post test markets to Slack for approval.
"""
import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask
from models import db, PendingMarket, Market, ProcessedMarket, ApprovalEvent
from main import app
from utils.messaging import add_reaction_to_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_market_poster")

# Slack API imports
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

def format_market_message(market):
    """
    Format a market message for posting to Slack with category badge and event information.
    This is a simplified version of the function in post_unposted_pending_markets.py
    that handles string-formatted options.
    
    Args:
        market: PendingMarket model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Define emoji map for categories
    category_emoji = {
        'politics': ':ballot_box_with_ballot:',
        'crypto': ':coin:',
        'sports': ':sports_medal:',
        'business': ':chart_with_upwards_trend:',
        'culture': ':performing_arts:',
        'tech': ':computer:',
        'news': ':newspaper:',
        # Add fallback for unknown categories
        'unknown': ':question:'
    }
    
    # Get emoji for this category
    category = market.category.lower() if market.category else 'news'
    emoji = category_emoji.get(category, category_emoji['unknown'])
    
    # Parse options if they're stored as a string
    options_list = []
    if market.options:
        if isinstance(market.options, str):
            try:
                options_list = json.loads(market.options)
            except json.JSONDecodeError:
                options_list = []
        else:
            options_list = market.options
    
    # Format options list for display
    option_values = []
    for option in options_list:
        if isinstance(option, dict):
            option_value = option.get('value', 'Unknown')
            option_values.append(option_value)
        elif isinstance(option, str):
            option_values.append(option)
    
    options_str = ', '.join(option_values) if option_values else 'Yes, No'
    
    # Determine if this market is part of an event
    has_event = market.event_id and market.event_name
    event_text = f"Event: {market.event_name}" if has_event else ""
    
    # Format message text including event information if available
    message_text = f"*New Market for Review* *Category:* {emoji} {category.capitalize()}  *Question:* {market.question}  Options: {options_str} {event_text}"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*New Market for Review*\n*Category:* {emoji} {category.capitalize()}"
            }
        }
    ]
    
    # Add event information if available
    if has_event:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event:* {market.event_name}"
            }
        })
    
    blocks.extend([
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {market.question}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Options: {options_str}"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "React with :white_check_mark: to approve or :x: to reject"
                }
            ]
        }
    ])
    
    return message_text, blocks

def post_markets_to_slack():
    """Post existing test markets to Slack for approval."""
    
    # Get environment variables
    slack_token = os.environ.get('SLACK_BOT_TOKEN')
    slack_channel_id = os.environ.get('SLACK_CHANNEL_ID')
    
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN not found in environment variables")
        return 1
    
    if not slack_channel_id:
        logger.error("SLACK_CHANNEL_ID not found in environment variables")
        return 1
    
    # Initialize Slack client
    client = WebClient(token=slack_token)
    
    with app.app_context():
        # Get markets from database
        pending_markets = db.session.query(PendingMarket).filter_by(posted=False).all()
        
        if not pending_markets:
            logger.info("No pending markets to post to Slack")
            return 0
        
        logger.info(f"Found {len(pending_markets)} pending markets to post to Slack")
        
        # Post markets to Slack
        posted_count = 0
        for market in pending_markets:
            try:
                # Format message for Slack
                message_text, blocks = format_market_message(market)
                
                # Post to Slack
                response = client.chat_postMessage(
                    channel=slack_channel_id,
                    text=message_text,
                    blocks=blocks
                )
                
                # Add approval/rejection reactions
                message_id = response['ts']
                add_reaction = client.reactions_add(
                    channel=slack_channel_id,
                    timestamp=message_id,
                    name="white_check_mark"
                )
                add_rejection = client.reactions_add(
                    channel=slack_channel_id,
                    timestamp=message_id,
                    name="x"
                )
                
                # Update market with Slack message ID
                market.slack_message_id = message_id
                market.posted = True
                db.session.commit()
                
                logger.info(f"Posted market '{market.question[:40]}...' to Slack (ts: {message_id})")
                posted_count += 1
                
            except SlackApiError as e:
                logger.error(f"Slack API error: {e.response['error']}")
                db.session.rollback()
            except Exception as e:
                logger.error(f"Error posting market to Slack: {str(e)}")
                db.session.rollback()
        
        logger.info(f"Successfully posted {posted_count} markets to Slack")
        return 0

if __name__ == "__main__":
    sys.exit(post_markets_to_slack())