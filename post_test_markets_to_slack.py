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
from utils.messaging import format_market_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_market_poster")

# Slack API imports
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

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
                
                # Update market with Slack message ID
                market.slack_message_id = response['ts']
                market.posted = True
                db.session.commit()
                
                logger.info(f"Posted market '{market.question[:40]}...' to Slack (ts: {response['ts']})")
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