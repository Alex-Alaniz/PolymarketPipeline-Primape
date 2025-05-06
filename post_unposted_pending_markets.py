#!/usr/bin/env python3
"""
Post unposted pending markets to Slack.

This script finds pending markets that haven't been posted to Slack yet,
formats them with category badges, posts them to Slack for approval,
and updates the database to track which markets have been posted.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Local imports
from models import db, PendingMarket, PipelineRun
from utils.messaging import post_formatted_message_to_slack, add_reaction_to_message

# Initialize app
db.init_app(app)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("post_markets.log")
    ]
)
logger = logging.getLogger('post_markets')

def create_pipeline_run():
    """Create a new pipeline run record in the database."""
    pipeline_run = PipelineRun(
        start_time=datetime.utcnow(),
        status="running"
    )
    db.session.add(pipeline_run)
    db.session.commit()
    
    logger.info(f"Created pipeline run with ID {pipeline_run.id}")
    return pipeline_run

def update_pipeline_run(pipeline_run, status, markets_processed=0, markets_approved=0, 
                       markets_rejected=0, markets_failed=0, markets_deployed=0, error=None):
    """Update the pipeline run record with results."""
    pipeline_run.end_time = datetime.utcnow()
    pipeline_run.status = status
    pipeline_run.markets_processed = markets_processed
    pipeline_run.markets_approved = markets_approved
    pipeline_run.markets_rejected = markets_rejected
    pipeline_run.markets_failed = markets_failed
    pipeline_run.markets_deployed = markets_deployed
    pipeline_run.error = error
    
    db.session.commit()
    logger.info(f"Updated pipeline run {pipeline_run.id} with status {status}")

def format_market_message(market: PendingMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge.
    
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
    
    # Format message text
    message_text = f"*{market.question}*\n\nCategory: {emoji} {category.capitalize()}"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "New Market for Approval",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{market.question}*"
            }
        }
    ]
    
    # Add market options if available
    if market.options:
        options_text = "*Options:*\n"
        for option in market.options:
            option_value = option.get('value', 'Unknown')
            options_text += f"• {option_value}\n"
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": options_text
            }
        })
    
    # Add category section with badge
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Category:* {emoji} {category.capitalize()}"
        }
    })
    
    # Add image if available
    if market.banner_url:
        blocks.append({
            "type": "image",
            "image_url": market.banner_url,
            "alt_text": market.question
        })
    
    # Add divider
    blocks.append({"type": "divider"})
    
    # Add approval/rejection buttons context
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

def get_unposted_markets(limit: int = 10) -> List[PendingMarket]:
    """
    Get pending markets that haven't been posted to Slack yet.
    
    Args:
        limit: Maximum number of markets to retrieve
        
    Returns:
        List[PendingMarket]: List of unposted pending markets
    """
    unposted_markets = PendingMarket.query.filter_by(posted=False).limit(limit).all()
    logger.info(f"Found {len(unposted_markets)} unposted pending markets")
    return unposted_markets

def post_markets_to_slack(markets: List[PendingMarket]) -> int:
    """
    Post markets to Slack and update the database.
    
    Args:
        markets: List of markets to post
        
    Returns:
        int: Number of markets successfully posted
    """
    posted_count = 0
    
    for market in markets:
        try:
            # Format message
            message_text, blocks = format_market_message(market)
            
            # Post to Slack
            message_id = post_formatted_message_to_slack(message_text, blocks=blocks)
            
            if not message_id:
                logger.error(f"Failed to post market {market.poly_id} to Slack")
                continue
            
            # Add approval/rejection reactions
            add_reaction_to_message(message_id, "white_check_mark")
            add_reaction_to_message(message_id, "x")
            
            # Update database
            market.slack_message_id = message_id
            market.posted = True
            db.session.commit()
            
            logger.info(f"Posted market {market.poly_id} to Slack with message ID {message_id}")
            posted_count += 1
            
        except Exception as e:
            logger.error(f"Error posting market {market.poly_id} to Slack: {str(e)}")
            db.session.rollback()
    
    return posted_count

def main():
    """
    Main function to post unposted pending markets to Slack.
    """
    with app.app_context():
        try:
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Get unposted markets
            unposted_markets = get_unposted_markets(limit=10)
            
            if not unposted_markets:
                logger.info("No unposted pending markets found")
                update_pipeline_run(pipeline_run, "completed")
                return 0
            
            # Post markets to Slack
            posted_count = post_markets_to_slack(unposted_markets)
            
            logger.info(f"Posted {posted_count} out of {len(unposted_markets)} pending markets to Slack")
            update_pipeline_run(
                pipeline_run, 
                "completed", 
                markets_processed=len(unposted_markets),
                markets_approved=posted_count
            )
            
            return 0
        
        except Exception as e:
            logger.error(f"Error in main function: {str(e)}")
            if 'pipeline_run' in locals():
                update_pipeline_run(pipeline_run, "failed", error=str(e))
            return 1

if __name__ == "__main__":
    sys.exit(main())