#!/usr/bin/env python
"""
Check image approvals in Slack and update the database.

This script checks Slack messages for approval or rejection reactions on market banner images,
updates the database accordingly, and adds image URIs to approved markets for 
integration with the frontend and blockchain.
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
import json

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from main import app
from models import db, ProcessedMarket, Market

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('image_approvals')

# Initialize Slack client
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
    logger.error("Slack environment variables are not set")
    sys.exit(1)

slack_client = WebClient(token=SLACK_BOT_TOKEN)

# Reaction emojis
APPROVAL_EMOJI = "white_check_mark"
REJECTION_EMOJI = "x"

def check_image_approvals() -> Tuple[int, int, int]:
    """
    Check for image approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) images
    """
    with app.app_context():
        # Get markets with posted images that are pending approval
        pending_markets = ProcessedMarket.query.filter(
            ProcessedMarket.approved == True,
            ProcessedMarket.image_generated == True,
            ProcessedMarket.image_message_id.isnot(None),
            ProcessedMarket.image_approved.is_(None)  # None means pending
        ).all()
        
        logger.info(f"Found {len(pending_markets)} markets with pending image approvals")
        
        approved_count = 0
        rejected_count = 0
        
        for market in pending_markets:
            try:
                # Get message from Slack
                message_id = market.image_message_id
                
                try:
                    # Get reactions for the message
                    response = slack_client.reactions_get(
                        channel=SLACK_CHANNEL_ID,
                        timestamp=message_id
                    )
                    
                    message = response.get('message', {})
                    reactions = message.get('reactions', [])
                    
                    # Check for approval/rejection reactions
                    is_approved = any(r['name'] == APPROVAL_EMOJI for r in reactions)
                    is_rejected = any(r['name'] == REJECTION_EMOJI for r in reactions)
                    
                    if is_approved and not is_rejected:
                        # Image approved
                        market.image_approved = True
                        market.image_approval_date = datetime.utcnow()
                        
                        # Get the user who approved
                        for reaction in reactions:
                            if reaction['name'] == APPROVAL_EMOJI:
                                # Just take the first user
                                market.image_approver = reaction.get('users', [None])[0]
                                break
                        
                        # Extract image URLs from the market data
                        try:
                            raw_data = market.raw_data
                            if raw_data:
                                # Get event image (banner)
                                event_image = raw_data.get("event_image")
                                market_image = raw_data.get("image")
                                
                                # Get option-specific images if it's a multi-option market
                                option_images = {}
                                if raw_data.get("is_multiple_option", False):
                                    option_images_raw = raw_data.get("option_images", "{}")
                                    if isinstance(option_images_raw, str):
                                        option_images = json.loads(option_images_raw)
                                    else:
                                        option_images = option_images_raw
                                
                                # Update the main Market table if it exists
                                main_market = Market.query.filter_by(id=market.condition_id).first()
                                if main_market:
                                    # Save event image as banner
                                    if event_image:
                                        main_market.banner_uri = event_image
                                    elif market_image:
                                        main_market.banner_uri = market_image
                                    
                                    # Save option images if it's multi-option
                                    if option_images:
                                        main_market.option_images = json.dumps(option_images)
                                    
                                    main_market.updated_at = datetime.utcnow()
                                    
                                    logger.info(f"Saved event banner and {len(option_images)} option images for market {market.condition_id}")
                                else:
                                    logger.warning(f"Main market {market.condition_id} not found, cannot update images")
                            else:
                                logger.warning(f"No raw data available for market {market.condition_id}, cannot extract images")
                        except Exception as e:
                            logger.error(f"Error extracting image data: {str(e)}")
                        
                        logger.info(f"Images for market {market.condition_id} approved")
                        approved_count += 1
                        
                        # React to the message to acknowledge
                        slack_client.reactions_add(
                            channel=SLACK_CHANNEL_ID,
                            timestamp=message_id,
                            name="heavy_check_mark"
                        )
                        
                    elif is_rejected:
                        # Image rejected
                        market.image_approved = False
                        market.image_approval_date = datetime.utcnow()
                        
                        # Get the user who rejected
                        for reaction in reactions:
                            if reaction['name'] == REJECTION_EMOJI:
                                # Just take the first user
                                market.image_approver = reaction.get('users', [None])[0]
                                break
                        
                        # Reset image generation to allow for retry
                        market.image_generated = False
                        
                        logger.info(f"Image for market {market.condition_id} rejected")
                        rejected_count += 1
                        
                        # React to the message to acknowledge
                        slack_client.reactions_add(
                            channel=SLACK_CHANNEL_ID,
                            timestamp=message_id,
                            name="octagonal_sign"
                        )
                    
                except SlackApiError as e:
                    logger.error(f"Error getting reactions: {str(e)}")
                    continue
                
                # Save changes to database
                db.session.commit()
                
            except Exception as e:
                logger.error(f"Error processing market {market.condition_id}: {str(e)}")
                db.session.rollback()
        
        pending_count = len(pending_markets) - approved_count - rejected_count
        return pending_count, approved_count, rejected_count

def main():
    """
    Main function to check image approvals.
    """
    try:
        logger.info("Starting image approval check process")
        pending, approved, rejected = check_image_approvals()
        logger.info(f"Image approval check complete: {pending} pending, {approved} approved, {rejected} rejected")
        
        return 0
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())