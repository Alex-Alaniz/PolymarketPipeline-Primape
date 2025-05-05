#!/usr/bin/env python3

"""
Check market approvals in Slack and update the database.

This script checks Slack messages for approval or rejection reactions,
updates the database accordingly, and adds approved markets to the main
Market table for processing by the pipeline.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import json

from models import db, Market, ProcessedMarket, ApprovalEvent
from utils.messaging import get_channel_messages, get_message_reactions

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
                    category=market.raw_data.get('fetched_category', 'general') if market.raw_data else 'general',
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
            # Still pending
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
        # Extract relevant fields from raw data
        market_id = raw_data.get("conditionId")
        
        if not market_id:
            logger.error("Raw data missing conditionId")
            return False
            
        # Check if market already exists
        existing = Market.query.get(market_id)
        if existing:
            logger.info(f"Market {market_id} already exists in Markets table")
            return True
            
        # Create new market entry
        market = Market(
            id=market_id,
            question=raw_data.get("question"),
            type="binary", # Default to binary for now
            category=raw_data.get("fetched_category", "general"),
            sub_category=raw_data.get("subCategory"),
            expiry=int(datetime.fromisoformat(raw_data.get("endDate", "").replace("Z", "+00:00")).timestamp()),
            original_market_id=raw_data.get("id"),
            options=json.dumps(raw_data.get("outcomes", ["Yes", "No"])),
            status="new",
            icon_url=raw_data.get("icon")
        )
        
        db.session.add(market)
        db.session.commit()
        
        logger.info(f"Created market entry for {market_id}")
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