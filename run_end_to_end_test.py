#!/usr/bin/env python3

"""
End-to-End Test for Market Pipeline

This script demonstrates the complete market pipeline workflow from insertion to approval
to deployment while preserving event relationships. It runs each step of the pipeline
in sequence with test data, showing all the state transitions.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta

from main import app
from models import db, PendingMarket, Market, ApprovalLog

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('pipeline_test')

# Test data with event relationships
TEST_MARKETS = [
    # Event 1: World Cup 2026
    {
        "poly_id": "test_wc_001",
        "question": "Will Brazil win the 2026 World Cup?",
        "category": "sports",
        "event_id": "event_worldcup_2026",
        "event_name": "FIFA World Cup 2026",
        "options": ["Yes", "No"],
        "expiry": int((datetime.now() + timedelta(days=365)).timestamp())
    },
    {
        "poly_id": "test_wc_002",
        "question": "Will France reach the semi-finals of the 2026 World Cup?",
        "category": "sports",
        "event_id": "event_worldcup_2026",
        "event_name": "FIFA World Cup 2026",
        "options": ["Yes", "No"],
        "expiry": int((datetime.now() + timedelta(days=365)).timestamp())
    },
    # Event 2: US Election 2028
    {
        "poly_id": "test_election_001",
        "question": "Will a Democrat win the 2028 US Presidential Election?",
        "category": "politics",
        "event_id": "event_uselection_2028",
        "event_name": "US Presidential Election 2028",
        "options": ["Yes", "No"],
        "expiry": int((datetime.now() + timedelta(days=730)).timestamp())
    }
]

def reset_test_data():
    """Reset the database for testing by removing previous test markets."""
    logger.info("Resetting test data...")
    
    # Delete test markets from the Market table
    for market in TEST_MARKETS:
        existing = Market.query.filter_by(id=market["poly_id"]).first()
        if existing:
            db.session.delete(existing)
    
    # Delete test markets from the PendingMarket table
    for market in TEST_MARKETS:
        existing = PendingMarket.query.filter_by(poly_id=market["poly_id"]).first()
        if existing:
            db.session.delete(existing)
    
    # Delete approval logs for test markets
    for market in TEST_MARKETS:
        logs = ApprovalLog.query.filter_by(poly_id=market["poly_id"]).all()
        for log in logs:
            db.session.delete(log)
    
    db.session.commit()
    logger.info("Test data reset complete")

def create_pending_markets():
    """Create pending markets with event relationships."""
    logger.info("Creating pending markets...")
    
    for market_data in TEST_MARKETS:
        pending_market = PendingMarket(
            poly_id=market_data["poly_id"],
            question=market_data["question"],
            category=market_data["category"],
            event_id=market_data["event_id"],
            event_name=market_data["event_name"],
            options=json.dumps(market_data["options"]),
            expiry=market_data["expiry"],
            posted=False
        )
        db.session.add(pending_market)
    
    db.session.commit()
    logger.info(f"Created {len(TEST_MARKETS)} pending markets")

def simulate_posting_to_slack():
    """Simulate posting markets to Slack and updating message IDs."""
    logger.info("Simulating posting to Slack...")
    
    # In a real scenario, this would call the Slack API
    for i, market_data in enumerate(TEST_MARKETS):
        pending_market = PendingMarket.query.filter_by(poly_id=market_data["poly_id"]).first()
        if pending_market:
            # Simulate a Slack message ID (timestamp format)
            slack_msg_id = f"{int(time.time())}.{i+1000}"
            pending_market.slack_message_id = slack_msg_id
            pending_market.posted = True
    
    db.session.commit()
    logger.info("Markets posted to Slack (simulated)")

def simulate_market_approvals():
    """Simulate market approvals and create Market entries."""
    logger.info("Simulating market approvals...")
    
    for market_data in TEST_MARKETS:
        pending_market = PendingMarket.query.filter_by(poly_id=market_data["poly_id"]).first()
        if pending_market:
            # Create approval log
            approval = ApprovalLog(
                poly_id=pending_market.poly_id,
                slack_msg_id=pending_market.slack_message_id,
                reviewer="TEST_USER",
                decision="approved",
                created_at=datetime.utcnow()
            )
            db.session.add(approval)
            
            # Create Market entry
            market = Market(
                id=pending_market.poly_id,
                question=pending_market.question,
                category=pending_market.category,
                event_id=pending_market.event_id,
                event_name=pending_market.event_name,
                options=pending_market.options,
                expiry=pending_market.expiry,
                status="approved"
            )
            db.session.add(market)
    
    db.session.commit()
    logger.info("Markets approved and created in main table")

def simulate_market_deployment():
    """Simulate market deployment with Apechain IDs."""
    logger.info("Simulating market deployment...")
    
    for i, market_data in enumerate(TEST_MARKETS):
        market = Market.query.filter_by(id=market_data["poly_id"]).first()
        if market:
            # Simulate an Apechain market ID
            market.apechain_market_id = str(1000 + i)
            market.status = "deployed"
            market.blockchain_tx = f"0xabcdef{i}123456789"
    
    db.session.commit()
    logger.info("Markets deployed with Apechain IDs (simulated)")

def check_results():
    """Check the results of the pipeline execution."""
    logger.info("Checking pipeline results...")
    
    # Check all markets in the main table
    markets = Market.query.all()
    logger.info(f"Found {len(markets)} markets in the main table")
    
    for market in markets:
        logger.info(f"Market: {market.question}")
        logger.info(f"  ID: {market.id}")
        logger.info(f"  Category: {market.category}")
        logger.info(f"  Event ID: {market.event_id}")
        logger.info(f"  Event Name: {market.event_name}")
        logger.info(f"  Status: {market.status}")
        logger.info(f"  Apechain ID: {market.apechain_market_id}")
    
    # Check events
    events = db.session.query(Market.event_id, Market.event_name).distinct().all()
    logger.info(f"\nFound {len(events)} unique events:")
    
    for event_id, event_name in events:
        event_markets = Market.query.filter_by(event_id=event_id).all()
        logger.info(f"Event: {event_name} (ID: {event_id})")
        logger.info(f"Has {len(event_markets)} markets:")
        
        for market in event_markets:
            logger.info(f"  - {market.question}")

def run_test():
    """Run the end-to-end test of the pipeline."""
    logger.info("Starting end-to-end pipeline test")
    
    reset_test_data()
    create_pending_markets()
    simulate_posting_to_slack()
    simulate_market_approvals()
    simulate_market_deployment()
    check_results()
    
    logger.info("End-to-end test completed successfully")

if __name__ == "__main__":
    with app.app_context():
        run_test()