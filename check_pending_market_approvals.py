#!/usr/bin/env python3

"""
Check pending market approvals in Slack and update the database.

This script checks Slack messages for approval or rejection reactions on pending markets,
records the decisions in the approvals_log table, and moves approved markets to the
Market table for further processing.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

from models import db, Market, PendingMarket, ApprovalLog
from utils.messaging import get_channel_messages, get_message_reactions

# Bot user ID to ignore its reactions (this is the ID that's adding the initial reactions)
BOT_USER_ID = "U08QJHCKABG"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pending_market_approvals")

def check_pending_market_approvals() -> Tuple[int, int, int]:
    """
    Check for pending market approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) markets
    """
    # Get markets that have been posted to Slack but not yet approved/rejected
    pending_markets = PendingMarket.query.filter(
        PendingMarket.slack_message_id.isnot(None)
    ).all()
    
    logger.info(f"Checking approvals for {len(pending_markets)} pending markets")
    
    # Track counts
    still_pending = 0
    approved = 0
    rejected = 0
    
    for market in pending_markets:
        # Skip if no message ID (shouldn't happen)
        if not market.slack_message_id:
            logger.warning(f"Market {market.poly_id} has no message ID")
            still_pending += 1
            continue
            
        # Check if market has already been processed
        existing_approval = ApprovalLog.query.filter_by(poly_id=market.poly_id).first()
        if existing_approval:
            logger.info(f"Market {market.poly_id} already has approval decision: {existing_approval.decision}")
            # Remove from pending markets if already decided
            db.session.delete(market)
            continue
            
        # Get reactions for this message
        reactions = get_message_reactions(market.slack_message_id)
        
        # Debug reactions
        logger.info(f"Processing reactions for market {market.poly_id} (message {market.slack_message_id})")
        logger.info(f"Got {len(reactions)} reactions: {reactions}")
        
        # Check for approval (white_check_mark) or rejection (x) reactions
        has_approval = False
        has_rejection = False
        reviewer = None
        
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
                reviewer = non_bot_users[0]
                logger.info(f"Found approval reaction from user {reviewer}")
            elif reaction_name == "x" or reaction_name == "-1" or reaction_name == "thumbsdown":
                has_rejection = True
                # Get first non-bot user who reacted as rejector
                reviewer = non_bot_users[0]
                logger.info(f"Found rejection reaction from user {reviewer}")
                
        logger.info(f"Final result: has_approval={has_approval}, has_rejection={has_rejection}, reviewer={reviewer}")
        
        # Process based on reactions
        if has_approval and not has_rejection:
            # Market is approved
            approval_log = ApprovalLog(
                poly_id=market.poly_id,
                slack_msg_id=market.slack_message_id,
                reviewer=reviewer,
                decision='approved'
            )
            db.session.add(approval_log)
            
            # Create entry in main Market table
            success = create_market_entry(market)
            
            # Log result
            if success:
                logger.info(f"Market {market.poly_id} approved by {reviewer}")
                approved += 1
            else:
                logger.error(f"Failed to create Market entry for {market.poly_id}")
                still_pending += 1
                
        elif has_rejection:
            # Market is rejected
            approval_log = ApprovalLog(
                poly_id=market.poly_id,
                slack_msg_id=market.slack_message_id,
                reviewer=reviewer,
                decision='rejected'
            )
            db.session.add(approval_log)
            
            logger.info(f"Market {market.poly_id} rejected by {reviewer}")
            rejected += 1
            
            # Remove from pending markets
            db.session.delete(market)
            
        else:
            # Check if market has timed out
            if market.is_expired():
                # Market has timed out, auto-reject
                approval_log = ApprovalLog(
                    poly_id=market.poly_id,
                    slack_msg_id=market.slack_message_id,
                    reviewer="SYSTEM_TIMEOUT",
                    decision='timeout'
                )
                db.session.add(approval_log)
                
                logger.info(f"Market {market.poly_id} auto-rejected due to timeout")
                rejected += 1
                
                # Remove from pending markets
                db.session.delete(market)
            else:
                # Still pending and within timeout period
                still_pending += 1
    
    # Save all changes
    db.session.commit()
    
    logger.info(f"Approval results: {still_pending} still pending, {approved} approved, {rejected} rejected")
    return (still_pending, approved, rejected)


def create_market_entry(pending_market: PendingMarket) -> bool:
    """
    Create an entry in the Market table for an approved market.
    
    Args:
        pending_market: PendingMarket model instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract data from pending market and raw data
        raw_data = pending_market.raw_data or {}
        
        # Check if this is a multi-option market
        is_multiple = raw_data.get('is_multiple_option', False)
        
        # For multiple-option markets, use the group ID (id field)
        # For binary markets, use the conditionId
        if is_multiple:
            market_id = raw_data.get("id")
            if not market_id:
                logger.error("Multi-option market missing id field")
                return False
                
            logger.info(f"Processing multi-option market with ID: {market_id}")
        else:
            market_id = raw_data.get("conditionId")
            if not market_id:
                logger.error("Binary market missing conditionId")
                return False
                
            logger.info(f"Processing binary market with ID: {market_id}")
            
        # Check if market already exists
        existing = Market.query.get(market_id)
        if existing:
            logger.info(f"Market {market_id} already exists in Markets table")
            return True
        
        # Extract options for the market
        options = []
        
        # First check if we have options from the pending market
        if pending_market.options:
            logger.info(f"Using options from pending_market: {pending_market.options}")
            if isinstance(pending_market.options, str):
                try:
                    options_data = json.loads(pending_market.options)
                    # Handle options that might be in [{"id": "...", "value": "..."}, ...] format
                    if isinstance(options_data, list) and options_data and isinstance(options_data[0], dict):
                        options = [opt.get("value", "Unknown") for opt in options_data]
                    else:
                        options = options_data
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse options JSON: {pending_market.options}")
                    options = []
            else:
                options = pending_market.options
        
        # Fallback to raw_data if no options found in pending_market
        if not options:
            logger.info("No valid options in pending_market, falling back to raw_data")
            outcomes_raw = raw_data.get("outcomes", "[]")
            
            # Parse outcomes which come as a JSON string
            try:
                if isinstance(outcomes_raw, str):
                    outcomes = json.loads(outcomes_raw)
                else:
                    outcomes = outcomes_raw
                    
                # For multiple-option markets, remove duplicates
                if is_multiple and outcomes:
                    outcomes = list(dict.fromkeys(outcomes))
                    options = outcomes
                else:
                    # Binary market defaults to Yes/No
                    options = outcomes if outcomes else ["Yes", "No"]
            except Exception as e:
                logger.error(f"Error parsing outcomes: {str(e)}")
                options = ["Yes", "No"]  # Default fallback
        
        logger.info(f"Final options for market: {options}")
            
        # Get the expiry timestamp
        expiry_timestamp = pending_market.expiry
        if not expiry_timestamp and raw_data.get("endDate"):
            try:
                expiry_timestamp = int(datetime.fromisoformat(
                    raw_data.get("endDate", "").replace("Z", "+00:00")
                ).timestamp())
            except Exception as e:
                logger.error(f"Error parsing endDate: {str(e)}")
                
        # Create new market entry
        # Use the AI-assigned category from pending_market
        category = pending_market.category
        
        # Get images
        banner_url = pending_market.banner_url
        icon_url = pending_market.icon_url
        
        # Create debugging info for tracing
        debug_info = {
            "is_multiple": is_multiple,
            "source": "polymarket",
            "options_count": len(options),
            "category_source": "ai_categorization",
            "has_banner_url": bool(banner_url),
            "has_icon_url": bool(icon_url)
        }
        
        market = Market(
            id=market_id,
            question=pending_market.question,
            type="multiple" if is_multiple else "binary",
            category=category,
            sub_category=raw_data.get("subCategory"),
            expiry=expiry_timestamp,
            original_market_id=raw_data.get("id") if not is_multiple else json.dumps(raw_data.get("original_market_ids", [])),
            options=json.dumps(options) if isinstance(options, list) else options,
            status="new",
            icon_url=icon_url,
            # Store banner URL
            banner_uri=banner_url,
            # For debugging/tracing
            banner_path=json.dumps(debug_info)
        )
        
        db.session.add(market)
        db.session.commit()
        
        # Log details about the market we created
        if is_multiple:
            logger.info(f"Created multi-option market entry for {market_id} with {len(options)} options")
        else:
            logger.info(f"Created binary market entry for {market_id}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error creating market entry: {str(e)}")
        return False


def main():
    """
    Main function to check pending market approvals.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        pending, approved, rejected = check_pending_market_approvals()
        
        # Log results
        print(f"Pending market approval results: {pending} pending, {approved} approved, {rejected} rejected")
    
    return 0


if __name__ == "__main__":
    main()