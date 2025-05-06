#!/usr/bin/env python3

"""
Post Test Pending Market to Slack

This script posts a test pending market to Slack for testing
the auto-categorization approval flow.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from models import db, PendingMarket
from utils.messaging import post_message_to_slack, add_reaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("post_test_market")

# Category emoji mapping
CATEGORY_EMOJI = {
    "politics": ":ballot_box:",
    "crypto": ":coin:",
    "sports": ":sports_medal:",
    "business": ":chart_with_upwards_trend:",
    "culture": ":performing_arts:",
    "news": ":newspaper:",
    "tech": ":computer:",
    "all": ":globe_with_meridians:"
}

def format_market_message(market: PendingMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge.
    
    Args:
        market: PendingMarket model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Get category emoji
    category = market.category.lower()
    emoji = CATEGORY_EMOJI.get(category, ":globe_with_meridians:")
    
    # Format expiry date if available
    expiry_text = ""
    if market.expiry:
        try:
            expiry_date = datetime.fromtimestamp(market.expiry)
            expiry_text = f"Expires: {expiry_date.strftime('%Y-%m-%d %H:%M')} UTC"
        except Exception as e:
            logger.error(f"Error formatting expiry date: {str(e)}")
            
    # Parse options
    options_text = "Options: Yes/No"
    try:
        options = json.loads(market.options)
        if options and len(options) > 0:
            options_text = "Options: " + ", ".join(options)
    except Exception as e:
        logger.error(f"Error parsing options: {str(e)}")
        
    # Create the message
    message_text = f"*New Market for Review*\n*Category:* {emoji} {market.category.capitalize()}\n\n*Question:* {market.question}\n\n{options_text}\n{expiry_text}"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*New Market for Review*\n*Category:* {emoji} {market.category.capitalize()}"
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
        
    # Add image if available and not empty
    if market.banner_url and market.banner_url.strip():
        blocks.append({
            "type": "image",
            "image_url": market.banner_url,
            "alt_text": "Market banner"
        })
    elif market.icon_url and market.icon_url.strip():
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
    
    return message_text, blocks

def post_pending_market_to_slack(market_id: str) -> bool:
    """
    Post a pending market to Slack for approval.
    
    Args:
        market_id: ID of the pending market to post
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get the pending market
        market = PendingMarket.query.get(market_id)
        
        if not market:
            logger.error(f"Pending market {market_id} not found")
            return False
            
        # Format the message
        message_text, blocks = format_market_message(market)
        
        # Post to Slack
        message_ts = post_message_to_slack((message_text, blocks))
        
        # Add initial reactions if posted successfully
        if message_ts:
            add_reaction(message_ts, "white_check_mark")
            add_reaction(message_ts, "x")
            
            # Update the market with the message ID
            market.slack_message_id = message_ts
            db.session.commit()
            
            logger.info(f"Posted market {market.poly_id} to Slack with message ID {message_ts}")
            return True
        else:
            logger.error(f"Failed to post market {market.poly_id} to Slack: No message ID returned")
            return False
            
    except Exception as e:
        logger.error(f"Error posting pending market to Slack: {str(e)}")
        return False

def main():
    """
    Main function to post a test market to Slack.
    """
    # Import Flask app to get application context
    from main import app
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Post a test pending market to Slack")
    parser.add_argument("--market-id", dest="market_id", default="test_market_001", help="ID of the pending market to post")
    args = parser.parse_args()
    
    # Use application context for database operations
    with app.app_context():
        success = post_pending_market_to_slack(args.market_id)
        
        if success:
            print(f"Successfully posted market {args.market_id} to Slack")
            return 0
        else:
            print(f"Failed to post market {args.market_id} to Slack")
            return 1

if __name__ == "__main__":
    sys.exit(main())