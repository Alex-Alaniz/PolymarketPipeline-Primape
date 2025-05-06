#!/usr/bin/env python3

"""
Post Unposted Markets to Slack

This script looks for markets in ProcessedMarkets with:
- posted = FALSE
- message_id = NULL

It posts up to 20 of these markets to Slack for initial approval
and sets their 'posted' flag to TRUE and stores the message_id.

Run this script after all previously posted markets have been
approved or rejected to process the next batch.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import flask app for database context
from main import app
from models import db, ProcessedMarket
from utils.messaging import post_message_to_slack, add_reaction
from config import SLACK_CHANNEL_ID

# Constants
MAX_MARKETS_TO_POST = 20

def get_unposted_markets() -> List[ProcessedMarket]:
    """
    Get markets that haven't been posted to Slack yet.
    
    Returns:
        List[ProcessedMarket]: List of unposted market entries
    """
    unposted_markets = ProcessedMarket.query.filter_by(
        posted=False,
        message_id=None
    ).limit(MAX_MARKETS_TO_POST).all()
    
    return unposted_markets

def format_market_message(market: ProcessedMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge.
    
    Args:
        market: ProcessedMarket model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Get category and emoji
    category = getattr(market, 'category', 'news')
    if not category or category == 'all':
        category = 'news'  # Ensure fallback to news, not all
    
    emoji = SLACK_EMOJI_MAP.get(category.lower(), ":globe_with_meridians:")
    
    # Format expiry date if available
    expiry_text = ""
    if market.raw_data and 'expiry' in market.raw_data:
        try:
            expiry_timestamp = int(market.raw_data['expiry'])
            expiry_date = datetime.fromtimestamp(expiry_timestamp)
            expiry_text = f"Expires: {expiry_date.strftime('%Y-%m-%d %H:%M')} UTC"
        except Exception as e:
            logger.error(f"Error formatting expiry date: {str(e)}")
    
    # Parse options
    options_text = "Options: Yes/No"
    try:
        if market.raw_data and 'outcomes' in market.raw_data:
            outcomes = market.raw_data['outcomes']
            if isinstance(outcomes, str):
                outcomes = json.loads(outcomes)
            
            if outcomes and len(outcomes) > 0:
                options_text = "Options: " + ", ".join(outcomes)
    except Exception as e:
        logger.error(f"Error parsing options: {str(e)}")
    
    # Create the message
    message_text = f"*New Market for Review*\n*Category:* {emoji} {category.capitalize()}\n\n*Question:* {market.question}\n\n{options_text}\n{expiry_text}"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*New Market for Review*\n*Category:* {emoji} {category.capitalize()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {market.question}"
            }
        }
    ]
    
    # Add options block
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": options_text
        }
    })
    
    # Add expiry if available
    if expiry_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": expiry_text
            }
        })
    
    # Add image if available
    if market.raw_data and 'banner_url' in market.raw_data and market.raw_data['banner_url']:
        blocks.append({
            "type": "image",
            "image_url": market.raw_data['banner_url'],
            "alt_text": "Market banner"
        })
    elif market.raw_data and 'icon_url' in market.raw_data and market.raw_data['icon_url']:
        blocks.append({
            "type": "image",
            "image_url": market.raw_data['icon_url'],
            "alt_text": "Market icon"
        })
    
    # Add instructions for review
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "React with :white_check_mark: to approve or :x: to reject"
            }
        ]
    })
    
    return message_text, blocks

def post_markets_to_slack(markets: List[ProcessedMarket]) -> int:
    """
    Post markets to Slack for approval and update the database.
    
    Args:
        markets: List of ProcessedMarket model instances
        
    Returns:
        int: Number of markets successfully posted
    """
    posted_count = 0
    
    for market in markets:
        try:
            # Format the message
            message_text, blocks = format_market_message(market)
            
            # Post to Slack
            message_ts = post_message_to_slack((message_text, blocks))
            
            # Add initial reactions if posted successfully
            if message_ts:
                add_reaction(message_ts, "white_check_mark")
                add_reaction(message_ts, "x")
                
                # Update database with message ID and posted flag
                market.posted = True
                market.message_id = message_ts
                db.session.commit()
                
                logger.info(f"Posted market {market.condition_id} to Slack with message ID {market.message_id}")
                posted_count += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
            else:
                logger.error(f"Failed to post market {market.condition_id} to Slack: No response")
        
        except Exception as e:
            logger.error(f"Error posting market {market.condition_id} to Slack: {str(e)}")
    
    logger.info(f"Posted {posted_count} markets to Slack for approval")
    return posted_count

def main():
    """
    Main function to post unposted markets to Slack.
    """
    with app.app_context():
        try:
            # Get markets that haven't been posted yet
            unposted_markets = get_unposted_markets()
            
            if not unposted_markets:
                logger.info("No unposted markets found")
                return 0
            
            # Log the number of unposted markets found
            logger.info(f"Found {len(unposted_markets)} unposted markets")
            
            # Post markets to Slack
            posted_count = post_markets_to_slack(unposted_markets)
            
            if posted_count > 0:
                logger.info(f"Successfully posted {posted_count} markets to Slack")
            else:
                logger.warning("No markets were posted to Slack")
                
            return 0
            
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())