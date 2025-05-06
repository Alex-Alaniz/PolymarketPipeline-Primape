#!/usr/bin/env python3
"""
Debug Database State

This script examines the current state of the database to help
diagnose issues with the market posting process.
"""

import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("db_debug")

# Import Flask app to get application context
from main import app
from models import db, ProcessedMarket, PendingMarket, Market, ApprovalEvent

def check_processed_markets():
    """Check the state of the ProcessedMarket table"""
    logger.info("Checking ProcessedMarket table...")
    
    # Get total count
    total_count = ProcessedMarket.query.count()
    logger.info(f"Total ProcessedMarket entries: {total_count}")
    
    # Count posted vs. unposted
    posted_count = ProcessedMarket.query.filter_by(posted=True).count()
    unposted_count = ProcessedMarket.query.filter_by(posted=False).count()
    logger.info(f"Posted markets: {posted_count}")
    logger.info(f"Unposted markets: {unposted_count}")
    
    # Check for markets with message_id = None
    no_message_id_count = ProcessedMarket.query.filter_by(message_id=None).count()
    logger.info(f"Markets with no message_id: {no_message_id_count}")
    
    # Check for anomalies
    posted_no_message = ProcessedMarket.query.filter_by(posted=True, message_id=None).count()
    unposted_with_message = ProcessedMarket.query.filter_by(posted=False).filter(ProcessedMarket.message_id != None).count()
    logger.info(f"Anomaly - Posted markets with no message_id: {posted_no_message}")
    logger.info(f"Anomaly - Unposted markets with message_id: {unposted_with_message}")
    
    # Check a sample of unposted markets
    unposted_markets = ProcessedMarket.query.filter_by(posted=False).limit(5).all()
    logger.info(f"Sample of unposted markets ({len(unposted_markets)} of {unposted_count}):")
    for market in unposted_markets:
        logger.info(f"Condition ID: {market.condition_id}")
        logger.info(f"  - Question: {market.question}")
        # Only log attributes that we know exist
        logger.info(f"  - Is raw data stored: {'Yes' if market.raw_data else 'No'}")
    
    # Check if the model has an error field
    try:
        if hasattr(ProcessedMarket, 'error'):
            error_markets = ProcessedMarket.query.filter(ProcessedMarket.error != None).count()
            logger.info(f"Markets with error field populated: {error_markets}")
        else:
            logger.info("ProcessedMarket model does not have an 'error' field")
    except Exception as e:
        logger.warning(f"Error checking for error field: {str(e)}")
    
    return total_count, posted_count, unposted_count

def check_pending_markets():
    """Check the state of the PendingMarket table"""
    logger.info("\nChecking PendingMarket table...")
    
    # Get total count
    total_count = PendingMarket.query.count()
    logger.info(f"Total PendingMarket entries: {total_count}")
    
    # Count posted vs. unposted
    posted_count = PendingMarket.query.filter(PendingMarket.slack_message_id != None).count()
    unposted_count = PendingMarket.query.filter_by(slack_message_id=None).count()
    logger.info(f"Posted pending markets: {posted_count}")
    logger.info(f"Unposted pending markets: {unposted_count}")
    
    # Check a sample of pending markets
    pending_markets = PendingMarket.query.limit(5).all()
    logger.info(f"Sample of pending markets ({len(pending_markets)} of {total_count}):")
    for market in pending_markets:
        logger.info(f"ID: {market.id}, Poly ID: {market.poly_id}")
        logger.info(f"  - Question: {market.question}")
        logger.info(f"  - Created: {market.created_at}")
        logger.info(f"  - Category: {market.category}")
        logger.info(f"  - Slack message ID: {market.slack_message_id or 'None'}")
        logger.info(f"  - Needs manual categorization: {market.needs_manual_categorization}")
    
    return total_count, posted_count, unposted_count

def check_markets_table():
    """Check the state of the Market table"""
    logger.info("\nChecking Market table...")
    
    # Get total count
    total_count = Market.query.count()
    logger.info(f"Total Market entries: {total_count}")
    
    # Count by status
    status_counts = {}
    for market in Market.query.all():
        status_counts[market.status] = status_counts.get(market.status, 0) + 1
    
    logger.info("Status breakdown:")
    for status, count in status_counts.items():
        logger.info(f"  - {status}: {count}")
    
    # Check markets with ApeChain IDs
    apechain_count = Market.query.filter(Market.apechain_market_id != None).count()
    logger.info(f"Markets with ApeChain IDs: {apechain_count}")
    
    return total_count, status_counts

def check_approval_events():
    """Check the state of the ApprovalEvent table"""
    logger.info("\nChecking ApprovalEvent table...")
    
    # Get total count
    total_count = ApprovalEvent.query.count()
    logger.info(f"Total ApprovalEvent entries: {total_count}")
    
    # Count by stage (instead of event_type which doesn't exist)
    stage_counts = {}
    for event in ApprovalEvent.query.all():
        stage_counts[event.stage] = stage_counts.get(event.stage, 0) + 1
    
    logger.info("Stage breakdown:")
    for stage, count in stage_counts.items():
        logger.info(f"  - {stage}: {count}")
    
    # Count by status
    status_counts = {}
    for event in ApprovalEvent.query.all():
        status_counts[event.status] = status_counts.get(event.status, 0) + 1
    
    logger.info("Status breakdown:")
    for status, count in status_counts.items():
        logger.info(f"  - {status}: {count}")
    
    return total_count, stage_counts, status_counts

def main():
    """Main function"""
    with app.app_context():
        try:
            logger.info("Running database state diagnostic...")
            
            # Check each table
            processed_stats = check_processed_markets()
            pending_stats = check_pending_markets()
            market_stats = check_markets_table()
            approval_stats = check_approval_events()
            
            # Summary
            logger.info("\n========== SUMMARY ==========")
            logger.info(f"ProcessedMarket: {processed_stats[0]} total, {processed_stats[1]} posted, {processed_stats[2]} unposted")
            logger.info(f"PendingMarket: {pending_stats[0]} total, {pending_stats[1]} posted, {pending_stats[2]} unposted")
            logger.info(f"Market: {market_stats[0]} total")
            logger.info(f"ApprovalEvent: {approval_stats[0]} total")
            
            logger.info("\nDiagnostic complete!")
            
        except Exception as e:
            logger.error(f"Error during diagnostic: {str(e)}")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())