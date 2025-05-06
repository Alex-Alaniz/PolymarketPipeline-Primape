#!/usr/bin/env python3
"""
Test Full Updated Pipeline with Gamma API

This script tests the entire pipeline using the updated Gamma API integration:
1. Fetching markets from the new Gamma API
2. Categorizing them with GPT-4o-mini
3. Storing them in the pending_markets table
4. Simulating the Slack approval process
5. Verifying deployment workflow

Use this script to check if all components are working correctly together.
"""

import json
import os
import sys
import logging
from datetime import datetime, timedelta

from loguru import logger

# Set up logging
logging.basicConfig(level=logging.INFO)
logger.remove()
logger.add(sys.stderr, level="INFO")

# Import Flask app to get application context
from main import app
from models import db, PendingMarket, Market, ApprovalEvent
from utils.market_categorizer import categorize_markets
from fetch_and_categorize_markets import fetch_markets, filter_active_non_expired_markets

# Constants
MAX_MARKETS_TO_FETCH = 10  # Limit for testing

def test_fetch_markets():
    """Test fetching markets from the updated Gamma API"""
    logger.info("Testing market fetching from Gamma API...")
    markets = fetch_markets(limit=MAX_MARKETS_TO_FETCH)
    
    if not markets:
        logger.error("Failed to fetch markets from API")
        return False
        
    logger.info(f"Successfully fetched {len(markets)} markets from Gamma API")
    logger.info(f"Sample market: {json.dumps(markets[0], indent=2)[:200]}...")
    
    # Test filtering
    active_markets = filter_active_non_expired_markets(markets)
    logger.info(f"Filtered to {len(active_markets)} active markets")
    
    return active_markets

def test_categorization(markets):
    """Test market categorization with GPT-4o-mini"""
    logger.info("Testing market categorization with GPT-4o-mini...")
    
    if not markets:
        logger.error("No markets to categorize")
        return False
        
    # Categorize a small sample
    sample = markets[:3]
    categorized = categorize_markets(sample)
    
    if not categorized:
        logger.error("Failed to categorize markets")
        return False
        
    for market in categorized:
        category = market.get("ai_category", "unknown")
        logger.info(f"Market '{market.get('question')}' categorized as: {category}")
        
        # Verify the category is valid
        if category not in ["politics", "crypto", "sports", "business", "culture", "news", "tech"]:
            logger.warning(f"Invalid category: {category}")
    
    return categorized

def create_test_pending_market(categorized_market):
    """Create a test entry in the pending_markets table"""
    logger.info("Creating test pending market entry...")
    
    try:
        # Use a unique ID for testing to avoid duplicates
        test_id = f"test_{int(datetime.utcnow().timestamp())}"
        
        pending_market = PendingMarket(
            poly_id=test_id,
            question=categorized_market.get("question", "Test market question"),
            category=categorized_market.get("ai_category", "news"),
            banner_url=categorized_market.get("image", ""),
            icon_url=categorized_market.get("icon", ""),
            options=json.dumps(categorized_market.get("outcomes", ["Yes", "No"])),
            expiry=int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            needs_manual_categorization=False,
            raw_data=categorized_market
        )
        
        db.session.add(pending_market)
        db.session.commit()
        
        logger.info(f"Created pending market with ID {pending_market.id}, poly_id {pending_market.poly_id}")
        return pending_market
    except Exception as e:
        logger.error(f"Error creating pending market: {str(e)}")
        db.session.rollback()
        return None

def simulate_approval_process(pending_market):
    """Simulate the Slack approval process"""
    logger.info("Simulating Slack approval process...")
    
    if not pending_market:
        logger.error("No pending market to approve")
        return None
        
    try:
        # Create a regular market entry (simulating approval)
        market = Market(
            id=pending_market.poly_id,
            question=pending_market.question,
            type="binary",
            category=pending_market.category,
            options=pending_market.options,
            expiry=pending_market.expiry,
            status="pending_deployment",
            banner_uri=pending_market.banner_url,
            icon_uri=pending_market.icon_url
        )
        
        # Create an approval event
        approval_event = ApprovalEvent(
            market_id=market.id,
            event_type="market_approval",
            status="approved",
            approver="test_user",
            message_id="test_message_123",
            created_at=datetime.utcnow()
        )
        
        db.session.add(market)
        db.session.add(approval_event)
        db.session.commit()
        
        logger.info(f"Created market with ID {market.id} and approval event")
        return market
    except Exception as e:
        logger.error(f"Error simulating approval: {str(e)}")
        db.session.rollback()
        return None

def cleanup_test_data(pending_market, market):
    """Clean up test data"""
    logger.info("Cleaning up test data...")
    
    try:
        if pending_market:
            db.session.delete(pending_market)
            
        if market:
            # Delete approval events
            ApprovalEvent.query.filter_by(market_id=market.id).delete()
            db.session.delete(market)
            
        db.session.commit()
        logger.info("Test data cleaned up successfully")
        return True
    except Exception as e:
        logger.error(f"Error cleaning up test data: {str(e)}")
        db.session.rollback()
        return False

def main():
    """Main test function"""
    # Use application context for database operations
    with app.app_context():
        try:
            # Step 1: Test fetching markets
            markets = test_fetch_markets()
            if not markets:
                logger.error("Market fetching test failed")
                return 1
                
            # Step 2: Test categorization
            categorized = test_categorization(markets)
            if not categorized:
                logger.error("Categorization test failed")
                return 1
                
            # Step 3: Create test pending market
            pending_market = create_test_pending_market(categorized[0])
            if not pending_market:
                logger.error("Pending market creation failed")
                return 1
                
            # Step 4: Simulate approval process
            market = simulate_approval_process(pending_market)
            if not market:
                logger.error("Approval process simulation failed")
                cleanup_test_data(pending_market, None)
                return 1
                
            # Step 5: Clean up test data
            if not cleanup_test_data(pending_market, market):
                logger.error("Cleanup failed")
                return 1
                
            logger.info("✅ Full pipeline test successful!")
            
        except Exception as e:
            logger.error(f"Error in test process: {str(e)}")
            return 1
            
    return 0

if __name__ == "__main__":
    sys.exit(main())