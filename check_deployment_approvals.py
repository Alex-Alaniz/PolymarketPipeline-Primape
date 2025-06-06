#!/usr/bin/env python3

"""
Check deployment approvals in Slack and update the database.

This script checks Slack messages for approval or rejection reactions,
updates the database accordingly, and prepares approved markets for
deployment to Apechain after the final QA check.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

from models import db, Market, ProcessedMarket, ApprovalEvent
from utils.messaging import get_channel_messages, get_message_reactions, post_formatted_message_to_slack as post_message_to_slack, add_reaction_to_message as add_reaction
# We'll create the apechain module later
from utils.apechain import deploy_market_to_apechain

# Bot user ID to ignore its reactions (this is the ID that's adding the initial reactions)
BOT_USER_ID = "U08QJHCKABG"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deployment_approvals")

def post_markets_for_deployment_approval() -> List[Market]:
    """
    Post approved markets to Slack for final deployment approval.
    
    This function finds all markets that have been approved but not yet
    posted for deployment approval, and posts them to Slack.
    
    Returns:
        List[Market]: List of markets posted for deployment approval
    """
    # Import the new deployment formatter
    from utils.deployment_formatter import format_deployment_message as new_format_message
    
    # Find markets that are approved but not yet posted for deployment
    markets_to_deploy = Market.query.filter(
        Market.status == "new",  # New status means approved but not yet deployed
        Market.apechain_market_id == None  # Not yet deployed to Apechain
    ).all()
    
    logger.info(f"Found {len(markets_to_deploy)} markets to post for deployment approval")
    
    posted_markets = []
    
    for market in markets_to_deploy:
        try:
            # Format message with market details using the new formatter
            # Prepare options
            options = []
            if market.options:
                try:
                    if isinstance(market.options, str):
                        options_data = json.loads(market.options)
                        for opt in options_data:
                            if isinstance(opt, dict) and 'value' in opt:
                                options.append(opt['value'])
                            else:
                                options.append(str(opt))
                    elif isinstance(market.options, list):
                        for opt in market.options:
                            if isinstance(opt, dict) and 'value' in opt:
                                options.append(opt['value'])
                            else:
                                options.append(str(opt))
                except Exception as e:
                    logger.error(f"Error parsing options for market {market.id}: {str(e)}")
                    options = ["Yes", "No"]  # Fallback
            
            # Prepare expiry date in human-readable format
            if market.expiry:
                try:
                    expiry_str = datetime.fromtimestamp(market.expiry).strftime('%Y-%m-%d %H:%M:%S UTC')
                except:
                    expiry_str = str(market.expiry)
            else:
                expiry_str = "Unknown"
            
            # Determine market type
            market_type = "Multiple-Choice Market" if market.type == "multiple" else "Binary Market (Yes/No)"
            
            # Format the message with the new formatter
            message_text, blocks = new_format_message(
                market_id=market.id,
                question=market.question,
                category=market.category or "News",
                market_type=market_type,
                options=options or ["Yes", "No"],
                expiry=expiry_str,
                banner_uri=market.banner_uri,
                event_name=getattr(market, 'event_name', None),
                event_id=getattr(market, 'event_id', None)
            )
            
            # Post to Slack
            message_id = post_message_to_slack(message_text, blocks=blocks)
            
            if message_id:
                # Add initial reactions (✅ and ❌) for easier voting
                # These will be ignored in the approval count since they're from the bot
                add_reaction(message_id, "white_check_mark")
                add_reaction(message_id, "x")
                
                # Small delay to ensure reactions are added
                import time
                time.sleep(0.5)
                # Create approval event
                event = ApprovalEvent(
                    market_id=market.id,
                    stage="final",
                    status="pending",
                    message_id=message_id
                )
                db.session.add(event)
                
                # Update market status
                market.status = "pending_deployment"
                
                posted_markets.append(market)
                logger.info(f"Posted market {market.id} for deployment approval")
            else:
                logger.error(f"Failed to post market {market.id} for deployment approval")
        
        except Exception as e:
            logger.error(f"Error posting market {market.id} for deployment: {str(e)}")
    
    # Save all changes
    if posted_markets:
        db.session.commit()
    
    return posted_markets

def format_deployment_message(market: Market) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for deployment approval with rich formatting.
    
    Args:
        market: Market model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Default text for fallback
    message_text = f"*Market for Deployment Approval*\n\n*Question:* {market.question}"
    
    # Market type
    market_type_text = "Multiple-Choice Market" if market.type == "multiple" else "Binary Market (Yes/No)"
    
    # Parse options from JSON
    options = []
    try:
        if market.options:
            raw_options = str(market.options)
            logger.info(f"Raw options for market {market.id}: {raw_options}")
            
            # Clean up the string for parsing
            clean_str = raw_options.replace('\\"', '"').replace('\\\\', '\\')
            # Remove any surrounding quotes
            while clean_str.startswith('"') and clean_str.endswith('"'):
                clean_str = clean_str[1:-1]
                
            # Parse the options
            try:
                options_parsed = json.loads(clean_str)
                if isinstance(options_parsed, list):
                    options = options_parsed
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse options JSON for market {market.id}")
    except Exception as e:
        logger.error(f"Error parsing options for market {market.id}: {str(e)}")
    
    # Parse banner_uri from JSON to extract images
    event_image = None
    market_image = None
    event_icon = None
    option_images = {}
    
    try:
        if market.banner_uri:
            # Try to parse the banner_uri as JSON
            banner_data = json.loads(market.banner_uri) if isinstance(market.banner_uri, str) else market.banner_uri
            
            # Extract image URLs
            event_image = banner_data.get("event_image")
            market_image = banner_data.get("market_image")
            event_icon = banner_data.get("event_icon")
            
            logger.info(f"Extracted images for market {market.id}: event_image={event_image}, market_image={market_image}")
    except Exception as e:
        logger.error(f"Error parsing banner_uri for market {market.id}: {str(e)}")
    
    # Similarly for option_images
    try:
        if market.option_images:
            option_images = json.loads(market.option_images) if isinstance(market.option_images, str) else market.option_images
            logger.info(f"Parsed option images for {len(option_images)} options")
    except Exception as e:
        logger.error(f"Error parsing option_images for market {market.id}: {str(e)}")
    
    # Create rich message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Market for Deployment Approval"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {market.question}"
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Category:* {market.category or 'Uncategorized'}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Expiry:* {datetime.fromtimestamp(market.expiry).strftime('%Y-%m-%d %H:%M:%S UTC')}"
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
                    "text": f"*ID:* {market.id}"
                }
            ]
        }
    ]
    
    # Add options section
    if options:
        options_text = "*Options:*\n"
        for i, option in enumerate(options):
            options_text += f"  {i+1}. {option}\n"
        
        logger.info(f"Adding options section with {len(options)} options")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": options_text
            }
        })
    
    # Add event image as banner if available
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
    # Add market image if available and it's different from event image
    elif market_image:
        logger.info(f"Adding market image as banner: {market_image}")
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Market Banner*"
            },
            "accessory": {
                "type": "image",
                "image_url": market_image,
                "alt_text": "Market Banner"
            }
        })
    
    # Add option-specific images if this is a multi-option market
    if market.type == "multiple" and options and option_images:
        for option in options:
            if option in option_images:
                option_image_url = option_images[option]
                if option_image_url:
                    logger.info(f"Adding image for option '{option}': {option_image_url}")
                    
                    # Add image block for this option
                    option_block = {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Option:* {option}"
                        },
                        "accessory": {
                            "type": "image",
                            "image_url": option_image_url,
                            "alt_text": f"Image for {option}"
                        }
                    }
                    blocks.append(option_block)
    
    # Add instructions for approval/rejection
    blocks.append(
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please review this market carefully before deployment to Apechain.\nReact with :white_check_mark: to approve or :x: to reject."
            }
        }
    )
    
    return message_text, blocks

def check_deployment_approvals() -> Tuple[int, int, int]:
    """
    Check for deployment approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) markets
    """
    # Get markets pending deployment approval
    pending_markets = Market.query.filter(
        Market.status == "pending_deployment"
    ).all()
    
    # Find the corresponding approval events to get message IDs
    pending_events = {}
    for market in pending_markets:
        event = ApprovalEvent.query.filter(
            ApprovalEvent.market_id == market.id,
            ApprovalEvent.stage == "final",
            ApprovalEvent.status == "pending"
        ).order_by(ApprovalEvent.created_at.desc()).first()
        
        if event and event.message_id:
            pending_events[market.id] = event
    
    logger.info(f"Checking deployment approvals for {len(pending_events)} pending markets")
    
    # Define timeout period (7 days)
    timeout_days = 7
    timeout_date = datetime.utcnow() - timedelta(days=timeout_days)
    
    # Track counts
    still_pending = 0
    approved = 0
    rejected = 0
    
    for market_id, event in pending_events.items():
        market = Market.query.get(market_id)
        if not market:
            logger.warning(f"Market {market_id} not found")
            continue
            
        # Get reactions for this message
        reactions = get_message_reactions(event.message_id)
        
        # Debug logging
        logger.info(f"Processing reactions for market {market_id} (message {event.message_id})")
        logger.info(f"Got {len(reactions)} reactions: {reactions}")
        
        # Check for approval (white_check_mark) or rejection (x) reactions
        has_approval = False
        has_rejection = False
        approver = None
        
        # Reactions are returned as a dict {reaction_name: [user_ids]}
        for reaction_name, users in reactions.items():
            logger.info(f"Processing reaction: {reaction_name}")
            
            # Ensure users is a list
            if not isinstance(users, list):
                logger.warning(f"Expected list of users for reaction {reaction_name}, but got {type(users)}")
                continue
                
            # Filter out bot user
            non_bot_users = [user for user in users if user != BOT_USER_ID]
            
            # If only the bot reacted, skip this reaction
            if not non_bot_users:
                logger.info(f"Skipping reaction '{reaction_name}' - only from bot user {BOT_USER_ID}")
                continue
                
            logger.info(f"Non-bot users who reacted with '{reaction_name}': {non_bot_users}")
            
            if reaction_name == "white_check_mark" or reaction_name == "+1" or reaction_name == "thumbsup":
                has_approval = True
                # Get first non-bot user who reacted as approver
                approver = non_bot_users[0]
                logger.info(f"Found approval reaction from user {approver}")
            elif reaction_name == "x" or reaction_name == "-1" or reaction_name == "thumbsdown":
                has_rejection = True
                # Get first non-bot user who reacted as rejector
                approver = non_bot_users[0]
                logger.info(f"Found rejection reaction from user {approver}")
                
        logger.info(f"Final result: has_approval={has_approval}, has_rejection={has_rejection}, approver={approver}")
        
        # Process based on reactions
        if has_approval and not has_rejection:
            # Market is approved for deployment
            event.status = "approved"
            market.status = "deploying"
            
            # Attempt to deploy to Apechain
            try:
                # Deploy market to Apechain
                apechain_id, tx_hash = deploy_market_to_apechain(market)
                
                if apechain_id:
                    # Update market with deployment info
                    market.apechain_market_id = apechain_id
                    market.blockchain_tx = tx_hash
                    market.status = "deployed"
                    
                    logger.info(f"Market {market_id} deployed to Apechain with ID {apechain_id}")
                    approved += 1
                else:
                    # Deployment failed
                    market.status = "deployment_failed"
                    event.reason = "Deployment to Apechain failed"
                    
                    logger.error(f"Failed to deploy market {market_id} to Apechain")
                    rejected += 1
            except Exception as e:
                # Deployment error
                market.status = "deployment_failed"
                event.reason = f"Deployment error: {str(e)}"
                
                logger.error(f"Error deploying market {market_id} to Apechain: {str(e)}")
                rejected += 1
                
        elif has_rejection:
            # Market is rejected for deployment
            event.status = "rejected"
            market.status = "deployment_rejected"
            
            logger.info(f"Market {market_id} deployment rejected by {approver}")
            rejected += 1
            
        else:
            # Check if market has timed out (posted more than 7 days ago)
            if event.created_at and event.created_at < timeout_date:
                # Market has timed out, auto-reject
                event.status = "timeout"
                market.status = "deployment_timeout"
                event.reason = f"Auto-rejected after {timeout_days} days"
                
                logger.info(f"Market {market_id} deployment auto-rejected due to {timeout_days}-day timeout")
                rejected += 1
            else:
                # Still pending and within timeout period
                still_pending += 1
    
    # Save all changes
    db.session.commit()
    
    logger.info(f"Deployment approval results: {still_pending} still pending, {approved} approved, {rejected} rejected")
    return (still_pending, approved, rejected)

def main():
    """
    Main function to check deployment approvals.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # First post any new markets for deployment approval
        posted = post_markets_for_deployment_approval()
        print(f"Posted {len(posted)} markets for deployment approval")
        
        # Then check for approvals
        pending, approved, rejected = check_deployment_approvals()
        
        # Log results
        print(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
    
    return 0

if __name__ == "__main__":
    main()