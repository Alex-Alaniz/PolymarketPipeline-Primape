#!/usr/bin/env python3

"""
Check market approvals in Slack and update the database.

This script checks Slack messages for approval or rejection reactions,
updates the database accordingly, and adds approved markets to the main
Market table for processing by the pipeline.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from models import db, ProcessedMarket, Market
from utils.messaging import check_message_reactions

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("market_approvals")

def check_market_approvals() -> Tuple[int, int, int]:
    """
    Check for market approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) markets
    """
    # Initialize counters
    pending_count = 0
    approved_count = 0
    rejected_count = 0
    
    # Get all markets that have been posted to Slack but don't have approval status yet
    pending_markets = ProcessedMarket.query.filter(
        ProcessedMarket.posted == True,
        ProcessedMarket.message_id.isnot(None),
        ProcessedMarket.approved.is_(None)
    ).all()
    
    logger.info(f"Checking approval status for {len(pending_markets)} pending markets")
    
    for market in pending_markets:
        if not market.message_id:
            continue
            
        # Check the reaction status on the Slack message
        status, user_id = check_message_reactions(market.message_id)
        
        # Update the market based on the reaction status
        if status == "approved":
            market.approved = True
            market.approval_date = datetime.utcnow()
            market.approver = user_id
            approved_count += 1
            
            # Create entry in the main Market table
            if market.raw_data and create_market_entry(market.raw_data):
                logger.info(f"Created Market entry for approved market {market.condition_id}")
            else:
                logger.warning(f"Failed to create Market entry for {market.condition_id}")
                
        elif status == "rejected":
            market.approved = False
            market.approval_date = datetime.utcnow()
            market.approver = user_id
            rejected_count += 1
            
        elif status == "timeout":
            # Handle timeout as rejection
            market.approved = False
            market.approval_date = datetime.utcnow()
            market.approver = "TIMEOUT"
            rejected_count += 1
            
        else:  # still pending
            pending_count += 1
    
    # Commit all changes to the database
    db.session.commit()
    
    logger.info(f"Market approval status: {approved_count} approved, {rejected_count} rejected, {pending_count} still pending")
    return pending_count, approved_count, rejected_count

def create_market_entry(raw_data: Dict[str, Any]) -> bool:
    """
    Create an entry in the Market table for an approved market.
    
    Args:
        raw_data: Raw market data from Polymarket API
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if this market already exists
        existing = Market.query.filter_by(id=raw_data.get("id")).first()
        if existing:
            logger.info(f"Market {raw_data.get('id')} already exists in Market table")
            return True
            
        # Parse options from string representation to list
        options_str = raw_data.get("outcomes", "[]")
        try:
            options = json.loads(options_str)
        except:
            # Default to binary Yes/No if cannot parse
            options = ["Yes", "No"]
            
        # Create a new Market entry
        market = Market(
            id=raw_data.get("id"),
            question=raw_data.get("question"),
            type="binary" if options == ["Yes", "No"] else "multiple",
            category=raw_data.get("events", [{}])[0].get("slug") if raw_data.get("events") else None,
            sub_category=None,  # No subcategory in the API data
            expiry=int(datetime.fromisoformat(raw_data.get("endDate", "").replace('Z', '+00:00')).timestamp()) if raw_data.get("endDate") else None,
            original_market_id=raw_data.get("conditionId"),
            options=options_str,
            status="new",
            banner_path=raw_data.get("image"),  # Store the original Polymarket image URL
            banner_uri=raw_data.get("image"),  # Store the same URL as URI for frontend use
            icon_url=raw_data.get("icon"),  # Store the icon URL for frontend use
        )
        
        db.session.add(market)
        db.session.commit()
        logger.info(f"Created new market in Market table: {market.id}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating market entry: {str(e)}")
        db.session.rollback()
        return False

def main():
    """
    Main function to check market approvals.
    """
    logger.info("Starting market approval check")
    
    # Import Flask app to get application context
    from main import app
    
    try:
        # Use application context for database operations
        with app.app_context():
            # Check for approvals/rejections
            pending, approved, rejected = check_market_approvals()
        
        logger.info(f"Completed market approval check: {approved} approved, {rejected} rejected, {pending} pending")
        return 0
        
    except Exception as e:
        logger.error(f"Error checking market approvals: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
