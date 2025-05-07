#!/usr/bin/env python3

"""
Insert Multiple Test Pending Markets

This script inserts several test pending markets into the database for testing
the approval flow, including markets that share the same event.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta

from models import db, PendingMarket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("insert_test_markets")

# Multiple test markets with event relationships
TEST_MARKETS = [
    {
        "poly_id": "test_market_001",
        "question": "Will Bitcoin exceed $100,000 by end of 2025?",
        "category": "crypto",
        "banner_url": "",
        "icon_url": "",
        "options": json.dumps(["Yes", "No"]),
        "expiry": int((datetime.utcnow() + timedelta(days=365)).timestamp()),
        "needs_manual_categorization": False,
        "posted": False,
        "event_id": "event_crypto_001",
        "event_name": "Bitcoin Price Predictions",
        "raw_data": {
            "question": "Will Bitcoin exceed $100,000 by end of 2025?",
            "endDate": (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z",
            "outcomes": ["Yes", "No"],
            "conditionId": "test_market_001",
            "image": "",
            "icon": "",
            "active": True,
            "isResolved": False,
            "eventId": "event_crypto_001",
            "eventName": "Bitcoin Price Predictions"
        }
    },
    {
        "poly_id": "test_market_002",
        "question": "Will Ethereum reach $10,000 by end of 2025?",
        "category": "crypto",
        "banner_url": "",
        "icon_url": "",
        "options": json.dumps(["Yes", "No"]),
        "expiry": int((datetime.utcnow() + timedelta(days=365)).timestamp()),
        "needs_manual_categorization": False,
        "posted": False,
        "event_id": "event_crypto_001",
        "event_name": "Bitcoin Price Predictions",
        "raw_data": {
            "question": "Will Ethereum reach $10,000 by end of 2025?",
            "endDate": (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z",
            "outcomes": ["Yes", "No"],
            "conditionId": "test_market_002",
            "image": "",
            "icon": "",
            "active": True,
            "isResolved": False,
            "eventId": "event_crypto_001",
            "eventName": "Bitcoin Price Predictions"
        }
    },
    {
        "poly_id": "test_market_003",
        "question": "Will Manchester City win the 2025-2026 Champions League?",
        "category": "sports",
        "banner_url": "",
        "icon_url": "",
        "options": json.dumps(["Yes", "No"]),
        "expiry": int((datetime.utcnow() + timedelta(days=300)).timestamp()),
        "needs_manual_categorization": False,
        "posted": False,
        "event_id": "event_sports_001",
        "event_name": "Champions League 2025-2026",
        "raw_data": {
            "question": "Will Manchester City win the 2025-2026 Champions League?",
            "endDate": (datetime.utcnow() + timedelta(days=300)).isoformat() + "Z",
            "outcomes": ["Yes", "No"],
            "conditionId": "test_market_003",
            "image": "",
            "icon": "",
            "active": True,
            "isResolved": False,
            "eventId": "event_sports_001",
            "eventName": "Champions League 2025-2026"
        }
    },
    {
        "poly_id": "test_market_004",
        "question": "Will Real Madrid reach the final of the 2025-2026 Champions League?",
        "category": "sports",
        "banner_url": "",
        "icon_url": "",
        "options": json.dumps(["Yes", "No"]),
        "expiry": int((datetime.utcnow() + timedelta(days=280)).timestamp()),
        "needs_manual_categorization": False,
        "posted": False,
        "event_id": "event_sports_001",
        "event_name": "Champions League 2025-2026",
        "raw_data": {
            "question": "Will Real Madrid reach the final of the 2025-2026 Champions League?",
            "endDate": (datetime.utcnow() + timedelta(days=280)).isoformat() + "Z",
            "outcomes": ["Yes", "No"],
            "conditionId": "test_market_004",
            "image": "",
            "icon": "",
            "active": True,
            "isResolved": False,
            "eventId": "event_sports_001",
            "eventName": "Champions League 2025-2026"
        }
    },
    {
        "poly_id": "test_market_005",
        "question": "Will Democrats win the US election in 2028?",
        "category": "politics",
        "banner_url": "",
        "icon_url": "",
        "options": json.dumps(["Yes", "No"]),
        "expiry": int((datetime.utcnow() + timedelta(days=730)).timestamp()),
        "needs_manual_categorization": False,
        "posted": False,
        "event_id": "event_politics_001",
        "event_name": "US Election 2028",
        "raw_data": {
            "question": "Will Democrats win the US election in 2028?",
            "endDate": (datetime.utcnow() + timedelta(days=730)).isoformat() + "Z",
            "outcomes": ["Yes", "No"],
            "conditionId": "test_market_005",
            "image": "",
            "icon": "",
            "active": True,
            "isResolved": False,
            "eventId": "event_politics_001",
            "eventName": "US Election 2028"
        }
    }
]

def insert_test_markets(clear_existing=False):
    """
    Insert test markets into the pending_markets table.
    
    Args:
        clear_existing: If True, clear existing test markets before inserting new ones
    
    Returns:
        int: Number of markets successfully inserted
    """
    try:
        # Optionally clear existing test markets
        if clear_existing:
            test_ids = [market["poly_id"] for market in TEST_MARKETS]
            PendingMarket.query.filter(PendingMarket.poly_id.in_(test_ids)).delete(synchronize_session=False)
            logger.info(f"Cleared {len(test_ids)} existing test markets")
        
        # Insert each test market
        count = 0
        for market_data in TEST_MARKETS:
            try:
                # Check if test market already exists
                existing = PendingMarket.query.filter_by(poly_id=market_data["poly_id"]).first()
                if existing:
                    logger.info(f"Test market {market_data['poly_id']} already exists, updating")
                    
                    # Update existing market
                    for key, value in market_data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                else:
                    logger.info(f"Creating new test market {market_data['poly_id']}")
                    
                    # Create new pending market
                    market = PendingMarket(
                        poly_id=market_data["poly_id"],
                        question=market_data["question"],
                        category=market_data["category"],
                        banner_url=market_data.get("banner_url", ""),
                        icon_url=market_data.get("icon_url", ""),
                        options=market_data["options"],
                        expiry=market_data["expiry"],
                        needs_manual_categorization=market_data.get("needs_manual_categorization", False),
                        raw_data=market_data["raw_data"],
                        posted=market_data.get("posted", False),
                        event_id=market_data.get("event_id"),
                        event_name=market_data.get("event_name")
                    )
                    db.session.add(market)
                
                count += 1
                logger.info(f"Processed market: {market_data['question']}")
                
            except Exception as e:
                logger.error(f"Error processing market {market_data.get('poly_id')}: {str(e)}")
        
        # Commit all changes at once
        db.session.commit()
        logger.info(f"Successfully added {count} test markets")
        
        return count
    except Exception as e:
        logger.error(f"Error inserting test markets: {str(e)}")
        return 0

def display_test_markets():
    """
    Display details of all test markets in the database.
    """
    test_ids = [market["poly_id"] for market in TEST_MARKETS]
    markets = PendingMarket.query.filter(PendingMarket.poly_id.in_(test_ids)).all()
    
    print(f"\nTest Markets in Database ({len(markets)}):")
    for market in markets:
        print(f"ID: {market.poly_id}")
        print(f"Question: {market.question}")
        print(f"Category: {market.category}")
        print(f"Event ID: {market.event_id}")
        print(f"Event Name: {market.event_name}")
        print(f"Options: {market.options}")
        print(f"Expiry: {datetime.fromtimestamp(market.expiry).isoformat()}")
        print(f"Posted: {market.posted}")
        print("---")

def main():
    """
    Main function to insert test markets.
    """
    parser = argparse.ArgumentParser(description='Insert test markets into the database')
    parser.add_argument('--clear', action='store_true', help='Clear existing test markets before inserting')
    args = parser.parse_args()
    
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        count = insert_test_markets(clear_existing=args.clear)
        
        if count > 0:
            print(f"Successfully inserted {count} test markets")
            display_test_markets()
            return 0
        else:
            print("Failed to insert test markets")
            return 1

if __name__ == "__main__":
    sys.exit(main())