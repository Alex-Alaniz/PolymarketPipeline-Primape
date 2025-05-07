#!/usr/bin/env python3

"""
Testing approval and rejection of pending markets.

This script is a modified version of check_pending_market_approvals.py that
allows bot user reactions for testing purposes.
"""

import os
import logging
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

from models import db, Market, PendingMarket, ApprovalLog, PipelineRun
from utils.messaging import get_channel_messages, get_message_reactions

# Initialize app
db.init_app(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_approvals")

def approve_pending_markets(market_ids=None, approve_all=False):
    """
    Approve specific pending markets or all pending markets.
    
    Args:
        market_ids: List of poly_ids to approve
        approve_all: If True, approve all pending markets
        
    Returns:
        Tuple[int, int]: Count of (approved, failed) markets
    """
    approved = 0
    failed = 0
    
    # Determine which markets to approve
    if approve_all:
        pending_markets = PendingMarket.query.filter(
            PendingMarket.slack_message_id.isnot(None)
        ).all()
    elif market_ids:
        pending_markets = PendingMarket.query.filter(
            PendingMarket.poly_id.in_(market_ids),
            PendingMarket.slack_message_id.isnot(None)
        ).all()
    else:
        logger.error("No markets specified to approve")
        return 0, 0
    
    logger.info(f"Processing approvals for {len(pending_markets)} pending markets")
    
    # Track pipeline run
    pipeline_run = PipelineRun(
        start_time=datetime.utcnow(),
        status="running"
    )
    db.session.add(pipeline_run)
    db.session.commit()
    
    for market in pending_markets:
        try:
            logger.info(f"Approving market {market.poly_id}: {market.question}")
            
            # Record approval in log
            approval_log = ApprovalLog(
                poly_id=market.poly_id,
                slack_msg_id=market.slack_message_id,
                reviewer="TEST_USER",
                decision='approved'
            )
            db.session.add(approval_log)
            
            # Create entry in Market table
            success = create_market_entry(market)
            
            if success:
                logger.info(f"Successfully approved market {market.poly_id}")
                approved += 1
            else:
                logger.error(f"Failed to create Market entry for {market.poly_id}")
                failed += 1
                
        except Exception as e:
            logger.error(f"Error approving market {market.poly_id}: {str(e)}")
            failed += 1
            db.session.rollback()
    
    # Save all changes
    db.session.commit()
    
    # Update pipeline run
    pipeline_run.end_time = datetime.utcnow()
    pipeline_run.status = "completed"
    pipeline_run.markets_processed = len(pending_markets)
    pipeline_run.markets_approved = approved
    db.session.commit()
    
    logger.info(f"Approval results: {approved} approved, {failed} failed")
    return (approved, failed)


def create_market_entry(pending_market: PendingMarket) -> bool:
    """
    Create an entry in the Market table for an approved market.
    
    Args:
        pending_market: PendingMarket model instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Parse options if stored as string
        options = pending_market.options
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except:
                options = ["Yes", "No"]  # Default fallback
        
        # Create market entry
        market = Market(
            id=pending_market.poly_id,  # Market uses id, not poly_id as primary key
            question=pending_market.question,
            category=pending_market.category,
            options=json.dumps(options) if isinstance(options, list) else options,
            expiry=pending_market.expiry,
            status="approved",
            event_id=pending_market.event_id,
            event_name=pending_market.event_name
        )
        
        db.session.add(market)
        logger.info(f"Created Market entry for {pending_market.poly_id}")
        
        return True
    
    except Exception as e:
        logger.error(f"Error creating Market entry: {str(e)}")
        db.session.rollback()
        return False


def reject_pending_markets(market_ids=None, reject_all=False):
    """
    Reject specific pending markets or all pending markets.
    
    Args:
        market_ids: List of poly_ids to reject
        reject_all: If True, reject all pending markets
        
    Returns:
        int: Count of rejected markets
    """
    rejected = 0
    
    # Determine which markets to reject
    if reject_all:
        pending_markets = PendingMarket.query.filter(
            PendingMarket.slack_message_id.isnot(None)
        ).all()
    elif market_ids:
        pending_markets = PendingMarket.query.filter(
            PendingMarket.poly_id.in_(market_ids),
            PendingMarket.slack_message_id.isnot(None)
        ).all()
    else:
        logger.error("No markets specified to reject")
        return 0
    
    logger.info(f"Processing rejections for {len(pending_markets)} pending markets")
    
    # Track pipeline run
    pipeline_run = PipelineRun(
        start_time=datetime.utcnow(),
        status="running"
    )
    db.session.add(pipeline_run)
    db.session.commit()
    
    for market in pending_markets:
        try:
            logger.info(f"Rejecting market {market.poly_id}: {market.question}")
            
            # Record rejection in log
            approval_log = ApprovalLog(
                poly_id=market.poly_id,
                slack_msg_id=market.slack_message_id,
                reviewer="TEST_USER",
                decision='rejected'
            )
            db.session.add(approval_log)
            
            # Remove from pending markets
            db.session.delete(market)
            rejected += 1
            
        except Exception as e:
            logger.error(f"Error rejecting market {market.poly_id}: {str(e)}")
            db.session.rollback()
    
    # Save all changes
    db.session.commit()
    
    # Update pipeline run
    pipeline_run.end_time = datetime.utcnow()
    pipeline_run.status = "completed"
    pipeline_run.markets_processed = len(pending_markets)
    pipeline_run.markets_rejected = rejected
    db.session.commit()
    
    logger.info(f"Rejection results: {rejected} rejected")
    return rejected


def list_pending_markets():
    """
    List all pending markets that have been posted to Slack.
    
    Returns:
        List[PendingMarket]: List of pending markets
    """
    pending_markets = PendingMarket.query.filter(
        PendingMarket.slack_message_id.isnot(None)
    ).all()
    
    print(f"\nFound {len(pending_markets)} pending markets:")
    for market in pending_markets:
        print(f"ID: {market.poly_id}")
        print(f"Question: {market.question}")
        print(f"Category: {market.category}")
        print(f"Event ID: {market.event_id or 'None'}")
        print(f"Event Name: {market.event_name or 'None'}")
        print("---")
    
    return pending_markets


def main():
    """
    Main function to test market approvals/rejections.
    """
    parser = argparse.ArgumentParser(description='Test market approvals and rejections')
    parser.add_argument('--list', action='store_true', help='List all pending markets')
    parser.add_argument('--approve-all', action='store_true', help='Approve all pending markets')
    parser.add_argument('--reject-all', action='store_true', help='Reject all pending markets')
    parser.add_argument('--approve', nargs='+', help='Approve specific markets by ID')
    parser.add_argument('--reject', nargs='+', help='Reject specific markets by ID')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.list:
            list_pending_markets()
            return 0
        
        if args.approve_all:
            approved, failed = approve_pending_markets(approve_all=True)
            print(f"Approved {approved} markets, {failed} failed")
            
        elif args.approve:
            approved, failed = approve_pending_markets(market_ids=args.approve)
            print(f"Approved {approved} markets, {failed} failed")
            
        elif args.reject_all:
            rejected = reject_pending_markets(reject_all=True)
            print(f"Rejected {rejected} markets")
            
        elif args.reject:
            rejected = reject_pending_markets(market_ids=args.reject)
            print(f"Rejected {rejected} markets")
            
        else:
            parser.print_help()
            
        return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())