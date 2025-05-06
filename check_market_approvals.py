#!/usr/bin/env python3

"""
Check market approvals in Slack and update the database.

This script checks Slack messages for approval or rejection reactions,
updates the database accordingly, and adds approved markets to the main
Market table for processing by the pipeline.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

from models import db, Market, ProcessedMarket, ApprovalEvent
from utils.messaging import get_channel_messages, get_message_reactions

# Bot user ID to ignore its reactions (this is the ID that's adding the initial reactions)
BOT_USER_ID = "U08QJHCKABG"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_approvals")

def check_market_approvals() -> Tuple[int, int, int]:
    """
    Check for market approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) markets
    """
    # Get markets that have been posted to Slack but not yet approved/rejected
    pending_markets = ProcessedMarket.query.filter(
        ProcessedMarket.posted == True,
        ProcessedMarket.approved == None
    ).all()
    
    # Define timeout period (7 days)
    timeout_days = 7
    timeout_date = datetime.utcnow() - timedelta(days=timeout_days)
    
    logger.info(f"Checking approvals for {len(pending_markets)} pending markets")
    
    # Track counts
    still_pending = 0
    approved = 0
    rejected = 0
    
    for market in pending_markets:
        # Skip if no message ID (shouldn't happen)
        if not market.message_id:
            logger.warning(f"Market {market.condition_id} has no message ID")
            still_pending += 1
            continue
            
        # Get reactions for this message
        reactions = get_message_reactions(market.message_id)
        
        # Debug reactions
        logger.info(f"Processing reactions for market {market.condition_id} (message {market.message_id})")
        logger.info(f"Got {len(reactions)} reactions: {reactions}")
        
        # Check for approval (white_check_mark) or rejection (x) reactions
        has_approval = False
        has_rejection = False
        approver = None
        
        for reaction in reactions:
            logger.info(f"Processing reaction: {reaction}")
            reaction_name = reaction.get("name", "")
            logger.info(f"Reaction name: '{reaction_name}'")
            
            # Get users who reacted (excluding the bot)
            users = [user for user in reaction.get("users", []) if user != BOT_USER_ID]
            
            # If only the bot reacted, skip this reaction
            if not users:
                logger.info(f"Skipping reaction '{reaction_name}' - only from bot user {BOT_USER_ID}")
                continue
                
            logger.info(f"Non-bot users who reacted with '{reaction_name}': {users}")
            
            if reaction_name == "white_check_mark" or reaction_name == "+1" or reaction_name == "thumbsup":
                has_approval = True
                # Get first non-bot user who reacted as approver
                approver = users[0]
                logger.info(f"Found approval reaction from user {approver}")
            elif reaction_name == "x" or reaction_name == "-1" or reaction_name == "thumbsdown":
                has_rejection = True
                # Get first non-bot user who reacted as rejector
                approver = users[0]
                logger.info(f"Found rejection reaction from user {approver}")
                
        logger.info(f"Final result: has_approval={has_approval}, has_rejection={has_rejection}, approver={approver}")
        
        # Process based on reactions
        if has_approval and not has_rejection:
            # Market is approved
            market.approved = True
            market.approval_date = datetime.utcnow()
            market.approver = approver
            
            # Create entry in main Market table
            success = create_market_entry(market.raw_data)
            
            # Create approval event
            event = ApprovalEvent(
                market_id=market.condition_id,
                stage="initial",
                status="approved",
                message_id=market.message_id
            )
            db.session.add(event)
            
            # Log result
            if success:
                logger.info(f"Market {market.condition_id} approved by {approver}")
                approved += 1
            else:
                logger.error(f"Failed to create Market entry for {market.condition_id}")
                still_pending += 1
                
        elif has_rejection:
            # Market is rejected
            market.approved = False
            market.approval_date = datetime.utcnow()
            market.approver = approver
            
            # For rejected markets, we need to create a placeholder Market entry
            # to maintain foreign key relationships for ApprovalEvent
            if not Market.query.get(market.condition_id):
                end_date_timestamp = None
                if market.raw_data and 'endDate' in market.raw_data:
                    try:
                        end_date_str = market.raw_data.get('endDate')
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        end_date_timestamp = int(end_date.timestamp())
                    except:
                        pass
                
                placeholder = Market(
                    id=market.condition_id,
                    question=market.question,
                    expiry=end_date_timestamp,
                    status="rejected",
                    category=market.raw_data.get('event_category', '') if market.raw_data else '',
                    icon_url=market.raw_data.get('icon') if market.raw_data else None
                )
                db.session.add(placeholder)
                db.session.flush()  # Flush to generate ID
            
            # Create rejection event
            event = ApprovalEvent(
                market_id=market.condition_id,
                stage="initial",
                status="rejected",
                message_id=market.message_id
            )
            db.session.add(event)
            
            logger.info(f"Market {market.condition_id} rejected by {approver}")
            rejected += 1
            
        else:
            # Check if market has timed out (posted more than 7 days ago)
            if market.last_processed and market.last_processed < timeout_date:
                # Market has timed out, auto-reject
                market.approved = False
                market.approval_date = datetime.utcnow()
                market.approver = "SYSTEM_TIMEOUT"
                
                # Create a placeholder Market entry for the rejected market
                if not Market.query.get(market.condition_id):
                    end_date_timestamp = None
                    if market.raw_data and 'endDate' in market.raw_data:
                        try:
                            end_date_str = market.raw_data.get('endDate')
                            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                            end_date_timestamp = int(end_date.timestamp())
                        except:
                            pass
                    
                    placeholder = Market(
                        id=market.condition_id,
                        question=market.question,
                        expiry=end_date_timestamp,
                        status="rejected",
                        category=market.raw_data.get('event_category', '') if market.raw_data else '',
                        icon_url=market.raw_data.get('icon') if market.raw_data else None
                    )
                    db.session.add(placeholder)
                    db.session.flush()  # Flush to generate ID
                
                # Create timeout rejection event
                event = ApprovalEvent(
                    market_id=market.condition_id,
                    stage="initial",
                    status="timeout",
                    message_id=market.message_id,
                    reason=f"Auto-rejected after {timeout_days} days"
                )
                db.session.add(event)
                
                logger.info(f"Market {market.condition_id} auto-rejected due to {timeout_days}-day timeout")
                rejected += 1
            else:
                # Still pending and within timeout period
                still_pending += 1
    
    # Save all changes
    db.session.commit()
    
    logger.info(f"Approval results: {still_pending} still pending, {approved} approved, {rejected} rejected")
    return (still_pending, approved, rejected)


def create_market_entry(raw_data: Dict[str, Any]) -> bool:
    """
    Create an entry in the Market table for an approved market.
    
    Args:
        raw_data: Raw market data from Polymarket API
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
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
            
        # Get the expiry timestamp
        expiry_timestamp = None
        try:
            if raw_data.get("endDate"):
                expiry_timestamp = int(datetime.fromisoformat(
                    raw_data.get("endDate", "").replace("Z", "+00:00")
                ).timestamp())
        except Exception as e:
            logger.error(f"Error parsing endDate: {str(e)}")
            
        # Create new market entry
        # Use event_category ONLY when available, otherwise leave blank (no fallback to fetched_category)
        category = raw_data.get("event_category", "")
        
        # Get images from both market and event
        market_image = raw_data.get("image")
        market_icon = raw_data.get("icon")
        event_image = raw_data.get("event_image")
        event_icon = raw_data.get("event_icon")
        
        # Create debugging info for tracing
        debug_info = {
            "is_multiple": is_multiple,
            "source": "polymarket",
            "options_count": len(options),
            "category_source": "event" if raw_data.get("event_category") else "api_query",
            "has_event_image": bool(event_image),
            "has_event_icon": bool(event_icon)
        }
        
        market = Market(
            id=market_id,
            question=raw_data.get("question"),
            type="multiple" if is_multiple else "binary",
            category=category,
            sub_category=raw_data.get("subCategory"),
            expiry=expiry_timestamp,
            original_market_id=raw_data.get("id") if not is_multiple else json.dumps(raw_data.get("original_market_ids", [])),
            options=json.dumps(options),
            status="new",
            icon_url=market_icon,
            # Store event images for reference
            banner_uri=json.dumps({
                "market_image": market_image,
                "event_image": event_image,
                "event_icon": event_icon
            }),
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
    Main function to check market approvals.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        pending, approved, rejected = check_market_approvals()
        
        # Log results
        print(f"Market approval results: {pending} pending, {approved} approved, {rejected} rejected")
    
    return 0


if __name__ == "__main__":
    main()