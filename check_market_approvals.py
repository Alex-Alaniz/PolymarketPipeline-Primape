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
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

# Set up path to find project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("check_approvals")

# Create Flask app context for database operations
from flask import Flask
from models import db, ProcessedMarket, Market, ApprovalEvent
from utils.market_tracker import MarketTracker
from utils.messaging import MessagingClient
from config import TMP_DIR

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def check_market_approvals() -> Tuple[int, int, int]:
    """
    Check for market approvals or rejections in Slack.
    
    Returns:
        Tuple[int, int, int]: Count of (pending, approved, rejected) markets
    """
    with app.app_context():
        try:
            # Initialize market tracker
            market_tracker = MarketTracker()
            
            # Get pending markets
            pending_markets = market_tracker.get_pending_markets()
            logger.info(f"Found {len(pending_markets)} pending markets")
            
            if not pending_markets:
                return 0, 0, 0
            
            # Initialize messaging client
            messaging_client = MessagingClient(platform="slack")
            
            # Counters
            approved_count = 0
            rejected_count = 0
            still_pending_count = 0
            
            # Check each pending market
            for market_info in pending_markets:
                condition_id = market_info.get("condition_id")
                message_id = market_info.get("message_id")
                
                if not message_id:
                    logger.warning(f"Market {condition_id} has no message_id, skipping")
                    still_pending_count += 1
                    continue
                
                # Get reactions for this message
                reactions = messaging_client.get_reactions(message_id)
                logger.info(f"Reactions for market {condition_id}: {reactions}")
                
                # Check for approval or rejection
                approved = False
                rejected = False
                
                # Check ✅ reaction (approval)
                if "white_check_mark" in reactions and reactions["white_check_mark"] > 1:
                    approved = True
                
                # Check ❌ reaction (rejection)
                if "x" in reactions and reactions["x"] > 1:
                    rejected = True
                
                # If both approved and rejected, consider it rejected
                if approved and rejected:
                    logger.warning(f"Market {condition_id} has both approval and rejection reactions, considering as rejected")
                    approved = False
                    rejected = True
                
                # Update database based on reactions
                if approved or rejected:
                    # Mark in the ProcessedMarket table
                    market_tracker.mark_market_approval(
                        condition_id=condition_id,
                        approved=approved,
                        approver="slack_user"  # Ideally would get the actual user ID
                    )
                    
                    # If approved, create an entry in the Market table for the pipeline
                    if approved:
                        # Get raw data for this market
                        raw_data = market_tracker.get_market_raw_data(condition_id)
                        
                        if raw_data:
                            # Create new Market entry
                            create_market_entry(raw_data)
                            
                            # Create ApprovalEvent
                            approval_event = ApprovalEvent(
                                market_id=condition_id,
                                stage="initial",
                                status="approved",
                                message_id=message_id
                            )
                            db.session.add(approval_event)
                            db.session.commit()
                            
                            logger.info(f"Market {condition_id} approved and added to Markets table")
                            approved_count += 1
                        else:
                            logger.error(f"Cannot find raw data for approved market {condition_id}")
                            still_pending_count += 1
                    else:  # rejected
                        # Create ApprovalEvent
                        approval_event = ApprovalEvent(
                            market_id=condition_id,
                            stage="initial",
                            status="rejected",
                            message_id=message_id
                        )
                        db.session.add(approval_event)
                        db.session.commit()
                        
                        logger.info(f"Market {condition_id} rejected")
                        rejected_count += 1
                else:
                    logger.info(f"Market {condition_id} still pending approval")
                    still_pending_count += 1
            
            # Log summary
            logger.info(f"Approval check complete: {approved_count} approved, {rejected_count} rejected, {still_pending_count} still pending")
            
            return still_pending_count, approved_count, rejected_count
            
        except Exception as e:
            logger.error(f"Error checking market approvals: {str(e)}")
            return 0, 0, 0

def create_market_entry(raw_data: Dict[str, Any]) -> bool:
    """
    Create an entry in the Market table for an approved market.
    
    Args:
        raw_data: Raw market data from Polymarket API
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Extract necessary data from raw_data
        condition_id = raw_data.get("condition_id")
        question = raw_data.get("question", "Unknown question")
        
        # Check if this market already exists
        existing_market = Market.query.filter_by(id=condition_id).first()
        if existing_market:
            logger.info(f"Market {condition_id} already exists in Markets table")
            return True
        
        # Determine market type (binary or multiple choice)
        tokens = raw_data.get("tokens", [])
        market_type = "binary" if len(tokens) <= 2 else "multiple"
        
        # Extract options
        options = []
        for token in tokens:
            option_name = token.get("outcome")
            if option_name:
                options.append({"name": option_name})
        
        # If no options found, default to binary Yes/No
        if not options:
            options = [{"name": "Yes"}, {"name": "No"}]
        
        # Extract category and subcategory
        tags = raw_data.get("tags", [])
        category = tags[0] if tags and len(tags) > 0 else "Other"
        sub_category = tags[1] if tags and len(tags) > 1 else ""
        
        # Extract expiry timestamp
        end_date_iso = raw_data.get("end_date_iso")
        expiry = None
        if end_date_iso:
            try:
                dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                expiry = int(dt.timestamp())
            except Exception as e:
                logger.warning(f"Error parsing end_date_iso: {e}")
        
        # Create new Market
        new_market = Market(
            id=condition_id,
            question=question,
            type=market_type,
            category=category,
            sub_category=sub_category,
            expiry=expiry,
            original_market_id=condition_id,
            options=options,
            status="approved_initial"  # Initial approval stage
        )
        
        db.session.add(new_market)
        db.session.commit()
        
        logger.info(f"Created new Market entry for {condition_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating Market entry: {str(e)}")
        return False

def main():
    """
    Main function to check market approvals.
    """
    logger.info("Starting market approval check")
    
    pending, approved, rejected = check_market_approvals()
    
    logger.info("\nSummary:")
    logger.info(f"- Markets still pending: {pending}")
    logger.info(f"- Markets approved: {approved}")
    logger.info(f"- Markets rejected: {rejected}")
    
    # Return success if we processed at least one market
    return (approved + rejected) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
