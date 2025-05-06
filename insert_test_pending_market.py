#!/usr/bin/env python3

"""
Insert Test Pending Market

This script inserts a test pending market into the database for testing
the auto-categorization approval flow.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

from models import db, PendingMarket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("insert_test_market")

# Sample test market data
TEST_MARKET = {
    "poly_id": "test_market_001",
    "question": "Will Bitcoin exceed $100,000 by end of 2025?",
    "category": "crypto",
    "banner_url": "https://via.placeholder.com/800x400.png?text=Bitcoin+Price+Prediction",
    "icon_url": "https://via.placeholder.com/64x64.png?text=BTC",
    "options": json.dumps(["Yes", "No"]),
    "expiry": int((datetime.utcnow() + timedelta(days=365)).timestamp()),
    "needs_manual_categorization": False,
    "raw_data": {
        "question": "Will Bitcoin exceed $100,000 by end of 2025?",
        "endDate": (datetime.utcnow() + timedelta(days=365)).isoformat() + "Z",
        "outcomes": ["Yes", "No"],
        "conditionId": "test_market_001",
        "image": "https://via.placeholder.com/800x400.png?text=Bitcoin+Price+Prediction",
        "icon": "https://via.placeholder.com/64x64.png?text=BTC",
        "active": True,
        "isResolved": False,
        "ai_category": "crypto"
    }
}

def insert_test_market():
    """
    Insert a test market into the pending_markets table.
    """
    try:
        # Check if test market already exists
        existing = PendingMarket.query.get(TEST_MARKET["poly_id"])
        if existing:
            logger.info(f"Test market {TEST_MARKET['poly_id']} already exists, updating")
            
            # Update existing market
            for key, value in TEST_MARKET.items():
                setattr(existing, key, value)
        else:
            logger.info(f"Creating new test market {TEST_MARKET['poly_id']}")
            
            # Create new pending market
            market = PendingMarket(
                poly_id=TEST_MARKET["poly_id"],
                question=TEST_MARKET["question"],
                category=TEST_MARKET["category"],
                banner_url=TEST_MARKET["banner_url"],
                icon_url=TEST_MARKET["icon_url"],
                options=TEST_MARKET["options"],
                expiry=TEST_MARKET["expiry"],
                needs_manual_categorization=TEST_MARKET["needs_manual_categorization"],
                raw_data=TEST_MARKET["raw_data"]
            )
            db.session.add(market)
            
        # Commit changes
        db.session.commit()
        logger.info(f"Successfully added test market: {TEST_MARKET['question']}")
        
        return True
    except Exception as e:
        logger.error(f"Error inserting test market: {str(e)}")
        return False

def main():
    """
    Main function to insert a test market.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        success = insert_test_market()
        
        if success:
            print("Successfully inserted test market")
            
            # Show details of inserted market
            market = PendingMarket.query.get(TEST_MARKET["poly_id"])
            print(f"\nTest Market Details:")
            print(f"ID: {market.poly_id}")
            print(f"Question: {market.question}")
            print(f"Category: {market.category}")
            print(f"Options: {market.options}")
            print(f"Expiry: {datetime.fromtimestamp(market.expiry).isoformat()}")
            
            return 0
        else:
            print("Failed to insert test market")
            return 1

if __name__ == "__main__":
    sys.exit(main())