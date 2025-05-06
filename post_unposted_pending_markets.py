#!/usr/bin/env python3

"""
Post Unposted Pending Markets to Slack

This script looks for markets in PendingMarket table with:
- posted = FALSE
- slack_message_id = NULL

It posts up to 20 of these markets to Slack for initial approval
and sets their 'posted' flag to TRUE and stores the slack_message_id.

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
from models import db, PendingMarket
from utils.messaging import post_message_to_slack, add_reaction

# Constants
MAX_MARKETS_TO_POST = 20

def get_unposted_markets() -> List[PendingMarket]:
    """
    Get pending markets that haven't been posted to Slack yet.
    
    Returns:
        List[PendingMarket]: List of unposted market entries
    """
    unposted_markets = PendingMarket.query.filter_by(
        posted=False,
        slack_message_id=None
    ).limit(MAX_MARKETS_TO_POST).all()
    
    return unposted_markets

def format_market_message(market: PendingMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge.
    
    Args:
        market: PendingMarket model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Get category and emoji
    category = market.category
    if not category or category == 'all':
        category = 'news'  # Ensure fallback to news, not all
    
    # Define emoji mapping for categories
    emoji_map = {
        'politics': ':ballot_box:',
        'crypto': ':money_with_wings:',
        'sports': ':basketball:',
        'business': ':chart_with_upwards_trend:',
        'culture': ':performing_arts:',
        'news': ':newspaper:',
        'tech': ':computer:',
    }
    
    emoji = emoji_map.get(category.lower(), ":globe_with_meridians:")
    
    # Format expiry date if available
    expiry_text = ""
    if market.expiry:
        try:
            expiry_timestamp = int(market.expiry)
            expiry_date = datetime.fromtimestamp(expiry_timestamp)
            expiry_text = f"Expires: {expiry_date.strftime('%Y-%m-%d %H:%M')} UTC"
        except Exception as e:
            logger.error(f"Error formatting expiry date: {str(e)}")
    
    # Parse options
    options_text = "Options: Yes/No"
    try:
        if market.options:
            options = market.options
            if isinstance(options, str):
                options = json.loads(options)
            
            if options and len(options) > 0:
                options_text = "Options: " + ", ".join(options)
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
    if market.banner_url:
        blocks.append({
            "type": "image",
            "image_url": market.banner_url,
            "alt_text": "Market banner"
        })
    elif market.icon_url:
        blocks.append({
            "type": "image",
            "image_url": market.icon_url,
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
    
    # Add manual category flag if needed
    if market.needs_manual_categorization:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "⚠️ *This market may need manual categorization*"
                }
            ]
        })
    
    return message_text, blocks

def post_markets_to_slack(markets: List[PendingMarket]) -> int:
    """
    Post markets to Slack for approval and update the database.
    
    Args:
        markets: List of PendingMarket model instances
        
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
                market.slack_message_id = message_ts
                db.session.commit()
                
                logger.info(f"Posted market {market.poly_id} to Slack with message ID {market.slack_message_id}")
                posted_count += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
            else:
                logger.error(f"Failed to post market {market.poly_id} to Slack: No response")
        
        except Exception as e:
            logger.error(f"Error posting market {market.poly_id} to Slack: {str(e)}")
    
    logger.info(f"Posted {posted_count} markets to Slack for approval")
    return posted_count

def main():
    """
    Main function to post unposted pending markets to Slack.
    """
    with app.app_context():
        try:
            # Get markets that haven't been posted yet
            unposted_markets = get_unposted_markets()
            
            if not unposted_markets:
                logger.info("No unposted pending markets found")
                return 0
            
            # Log the number of unposted markets found
            logger.info(f"Found {len(unposted_markets)} unposted pending markets")
            
            # Post markets to Slack
            posted_count = post_markets_to_slack(unposted_markets)
            
            if posted_count > 0:
                logger.info(f"Successfully posted {posted_count} pending markets to Slack")
            else:
                logger.warning("No pending markets were posted to Slack")
                
            return 0
            
        except Exception as e:
            logger.error(f"Error in process: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())