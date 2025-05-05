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
from utils.messaging import get_channel_messages, get_message_reactions, post_message_to_slack
# We'll create the apechain module later
from utils.apechain import deploy_market_to_apechain

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
    # Find markets that are approved but not yet posted for deployment
    markets_to_deploy = Market.query.filter(
        Market.status == "new",  # New status means approved but not yet deployed
        Market.apechain_market_id == None  # Not yet deployed to Apechain
    ).all()
    
    logger.info(f"Found {len(markets_to_deploy)} markets to post for deployment approval")
    
    posted_markets = []
    
    for market in markets_to_deploy:
        try:
            # Format message with market details
            message = format_deployment_message(market)
            
            # Post to Slack
            message_id = post_message_to_slack(message)
            
            if message_id:
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

def format_deployment_message(market: Market) -> str:
    """
    Format a market message for deployment approval.
    
    Args:
        market: Market model instance
        
    Returns:
        str: Formatted message text
    """
    # Create a detailed message with all relevant market information
    message = f"*DEPLOYMENT APPROVAL NEEDED*\n\n"
    message += f"*Market ID:* {market.id}\n"
    message += f"*Question:* {market.question}\n"
    message += f"*Category:* {market.category}\n"
    message += f"*Type:* {market.type}\n"
    message += f"*Expiry:* {datetime.fromtimestamp(market.expiry).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    
    # Add options if available
    if market.options:
        try:
            # Handle the specific multi-level escaped format
            option_text = "Unknown"
            
            # First, get the raw string representation
            raw_options = str(market.options)
            logger.info(f"Raw options for market {market.id}: {raw_options}")
            
            # Get a clean, readable format for the options
            try:
                # This cleans up the escape sequences
                clean_str = raw_options.replace('\\"', '"').replace('\\\\', '\\')
                # Remove any surrounding quotes
                while clean_str.startswith('"') and clean_str.endswith('"'):
                    clean_str = clean_str[1:-1]
                    
                # Try standard JSON parsing on the cleaned string
                try:
                    options_parsed = json.loads(clean_str)
                    if isinstance(options_parsed, list):
                        option_text = ", ".join(options_parsed)
                    else:
                        option_text = str(options_parsed)
                except json.JSONDecodeError:
                    # If still not valid JSON after cleaning, display as is
                    option_text = clean_str
            except Exception as e:
                logger.warning(f"Error cleaning options: {str(e)}")
                option_text = raw_options
                
            message += f"*Options:* {option_text}\n"
            
        except Exception as e:
            logger.error(f"Error formatting options for market {market.id}: {str(e)}")
            # Add raw format for debugging
            message += f"*Options (raw):* {repr(market.options)}\n"
    
    # Add links to banner and icon if available
    if market.banner_uri:
        message += f"*Banner:* {market.banner_uri}\n"
    if market.icon_url:
        message += f"*Icon:* {market.icon_url}\n"
    
    # Add instructions for approval/rejection
    message += "\nPlease review this market carefully before deployment to Apechain.\n"
    message += "React with :white_check_mark: to approve or :x: to reject."
    
    return message

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
        
        # Check for approval (white_check_mark) or rejection (x) reactions
        has_approval = False
        has_rejection = False
        approver = None
        
        for reaction in reactions:
            if reaction.get("name") == "white_check_mark":
                has_approval = True
                # Get first user who reacted as approver
                approver = reaction.get("users", ["unknown"])[0]
            elif reaction.get("name") == "x":
                has_rejection = True
                # Get first user who reacted as rejector
                approver = reaction.get("users", ["unknown"])[0]
        
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