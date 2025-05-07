#!/usr/bin/env python3

"""
Check for market approvals in Slack

This script checks Slack messages for reactions (thumbs up/down)
and updates the approval status in the database.

It handles the following steps in the pipeline:
1. Checks all pending markets posted to Slack
2. Marks them as approved/rejected based on reactions
3. Moves approved markets to the main Market table
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple

from flask import Flask
from utils.messaging import get_message_reactions
from models import db, PendingMarket, ApprovalLog, Market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("approval_checker")

# Import Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

def check_market_approvals() -> Tuple[int, int, int]:
    """
    Check for market approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) markets
    """
    # Find all pending markets that have been posted to Slack
    pending_markets = PendingMarket.query.filter(
        PendingMarket.posted == True,
        PendingMarket.slack_message_id.isnot(None)
        # No approved field in the model, we'll use ApprovalLog to track decisions
    ).all()
    
    if not pending_markets:
        logger.info("No pending markets found for approval check")
        return 0, 0, 0
    
    logger.info(f"Checking {len(pending_markets)} pending markets for approvals")
    
    approved_count = 0
    rejected_count = 0
    
    for market in pending_markets:
        # Skip if no Slack message ID
        if not market.slack_message_id:
            continue
        
        # Get reactions on the Slack message
        reactions = get_message_reactions(market.slack_message_id)
        
        # Check for approval (thumbsup)
        approved = any(
            reaction in reactions 
            for reaction in ['thumbsup', '+1']
        )
        
        # Check for rejection (thumbsdown)
        rejected = any(
            reaction in reactions 
            for reaction in ['thumbsdown', '-1']
        )
        
        # Skip if no decision yet
        if not approved and not rejected:
            continue
        
        # Create approval log entry
        approval_log = ApprovalLog(
            poly_id=market.poly_id,
            slack_msg_id=market.slack_message_id,
            decision="approved" if approved else "rejected",
            created_at=datetime.utcnow()
        )
        db.session.add(approval_log)
        
        # For approved markets, create entry in main Market table
        if approved:
            # Create market entry
            create_market_entry(market)
            approved_count += 1
            logger.info(f"Market approved: {market.question[:50]}...")
        else:
            rejected_count += 1
            logger.info(f"Market rejected: {market.question[:50]}...")
        
        # Commit changes
        db.session.commit()
    
    return len(pending_markets), approved_count, rejected_count

def create_market_entry(pending_market: PendingMarket) -> bool:
    """
    Create an entry in the Market table for an approved market.
    
    Args:
        pending_market: PendingMarket model instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if this market already exists (to prevent duplicate key errors)
        existing_market = Market.query.filter_by(id=pending_market.poly_id).first()
        if existing_market:
            logger.warning(f"Market with ID {pending_market.poly_id} already exists, skipping creation")
            return True
        
        # For event markets, also check if the event already exists to avoid duplicate event error
        is_event = pending_market.is_event
        if is_event and pending_market.event_id:
            # If this is an event and the event already exists, skip it
            existing_event = Market.query.filter_by(event_id=pending_market.event_id, is_event=True).first()
            if existing_event:
                logger.warning(f"Event with ID {pending_market.event_id} already exists, skipping creation")
                return True
        
        # Generate a market ID (use poly_id for now, but consider using a UUID in production)
        market_id = pending_market.poly_id
        
        # Create Market entry with all the new event fields
        market = Market(
            id=market_id,  # Use id, not poly_id for the Market table
            question=pending_market.question,
            category=pending_market.category,
            options=pending_market.options,  # Keep as JSON string
            expiry=pending_market.expiry,
            original_market_id=pending_market.poly_id,  # Store the original poly_id
            event_id=pending_market.event_id,
            event_name=pending_market.event_name,
            event_image=pending_market.event_image,
            event_icon=pending_market.event_icon,
            is_event=pending_market.is_event,
            icon_url=pending_market.icon_url, 
            option_images=pending_market.option_images,
            option_market_ids=pending_market.option_market_ids,
            status="approved"  # Set initial status
        )
        
        # Add to database
        db.session.add(market)
        logger.info(f"Created market entry: {pending_market.question[:50]}...")
        
        return True
    except Exception as e:
        logger.error(f"Error creating market entry: {str(e)}")
        db.session.rollback()
        return False

def main():
    """
    Main function to check market approvals.
    """
    with app.app_context():
        pending_count, approved_count, rejected_count = check_market_approvals()
        logger.info(f"Approval check complete: {pending_count} pending, {approved_count} approved, {rejected_count} rejected")

if __name__ == "__main__":
    main()