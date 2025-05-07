#!/usr/bin/env python3
"""
Direct Test Script for Polymarket Pipeline

This script tests the core functionality of the pipeline directly,
bypassing the Flask web interface. It focuses on:

1. Fetching markets from Polymarket API
2. Categorizing markets with GPT-4o-mini
3. Posting a sample market to Slack
"""

import os
import sys
import json
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline_direct_test.log")
    ]
)
logger = logging.getLogger('pipeline_test')

# Flask context for database operations
from models import db, PendingMarket, Market
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Import pipeline components
from utils.market_categorizer import categorize_markets
from utils.messaging import post_market_to_slack
from utils.market_transformer import MarketTransformer
from utils.option_image_fixer import apply_image_fixes, verify_option_images

# Constants
MARKET_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100 "
MARKETS_QUERY = """
query FetchMarkets($first: Int!, $skip: Int!) {
  markets(
    input: {
      first: $first,
      skip: $skip,
      where: {
        or: [
          { settlement_status: { not_equals: "2" } },
          { settlement_status: { not_exists: true } }
        ],
      },
      order_by: { created_at: DESC }
    }
  ) {
    items {
      id
      question
      description
      base_asset
      meta_type
      mechanism
      settlement_status
      settlement_value
      settlement_data
      settlement_type
      expires_at
      created_at
      type
      image_url
      author {
        id
        username
      }
      outcomes
      assets {
        id
        token_address
        image_url
        ticker
        price_category {
          id
          label
        }
      }
      outcomes_metadata {
        title
        pool_liquidity
        price
        total_volume
        outcome_id
        pool_id
        image_url
      }
    }
  }
}
"""

def fetch_markets(limit=10):
    """
    Fetch markets from Polymarket API
    
    Args:
        limit: Maximum number of markets to fetch
        
    Returns:
        List of market data dictionaries
    """
    logger.info(f"Fetching up to {limit} markets from Polymarket API")
    
    # Make GraphQL request to API
    response = requests.post(
        MARKET_API_URL,
        json={
            "query": MARKETS_QUERY,
            "variables": {
                "first": limit,
                "skip": 0
            }
        }
    )
    
    # Check response
    if response.status_code != 200:
        logger.error(f"API request failed with status {response.status_code}: {response.text}")
        return []
    
    # Parse response
    try:
        data = response.json()
        markets = data.get("data", {}).get("markets", {}).get("items", [])
        
        logger.info(f"Fetched {len(markets)} markets from API")
        
        return markets
    except Exception as e:
        logger.error(f"Error parsing API response: {str(e)}")
        return []

def filter_active_markets(markets):
    """
    Filter active and non-expired markets
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List of filtered market data dictionaries
    """
    logger.info(f"Filtering {len(markets)} markets for active, non-expired ones")
    
    active_markets = []
    now = datetime.now()
    
    for market in markets:
        try:
            # Skip markets with no expiry
            if not market.get("expires_at"):
                logger.debug(f"Skipping market with no expiry: {market.get('id')}")
                continue
            
            # Convert expiry to datetime
            expiry = datetime.fromisoformat(market.get("expires_at").replace("Z", "+00:00"))
            
            # Skip expired markets
            if expiry < now:
                logger.debug(f"Skipping expired market: {market.get('id')}")
                continue
            
            # Skip markets with no outcomes
            if not market.get("outcomes") or len(market.get("outcomes")) == 0:
                logger.debug(f"Skipping market with no outcomes: {market.get('id')}")
                continue
            
            # Skip markets with no outcomes metadata
            if not market.get("outcomes_metadata") or len(market.get("outcomes_metadata")) == 0:
                logger.debug(f"Skipping market with no outcomes metadata: {market.get('id')}")
                continue
            
            # Check if market has valid image assets
            valid_images = verify_option_images(market)
            if not valid_images:
                logger.debug(f"Skipping market with invalid image assets: {market.get('id')}")
                continue
            
            # Market is valid
            active_markets.append(market)
            
        except Exception as e:
            logger.error(f"Error filtering market {market.get('id')}: {str(e)}")
    
    logger.info(f"Found {len(active_markets)} active, non-expired markets")
    
    return active_markets

def store_pending_markets(categorized_markets):
    """
    Store categorized markets as pending markets in the database
    
    Args:
        categorized_markets: List of categorized market data dictionaries
        
    Returns:
        Number of markets stored
    """
    logger.info(f"Storing {len(categorized_markets)} categorized markets as pending markets")
    
    stored_count = 0
    transformer = MarketTransformer()
    
    with app.app_context():
        for market in categorized_markets:
            try:
                # Skip already processed markets
                existing = PendingMarket.query.filter_by(id=market.get("id")).first()
                if existing:
                    logger.debug(f"Market {market.get('id')} already exists in pending_markets table")
                    continue
                
                # Transform market data for storage
                category = market.get("ai_category", "news")
                needs_manual = market.get("needs_manual_categorization", True)
                transformed_data = transformer.transform(market)
                
                # Create PendingMarket entry
                pending_market = PendingMarket(
                    id=market.get("id"),
                    question=market.get("question"),
                    category=category,
                    needs_manual_categorization=needs_manual,
                    expiry=datetime.fromisoformat(market.get("expires_at").replace("Z", "+00:00")),
                    raw_data=json.dumps(market),
                    transformed_data=json.dumps(transformed_data),
                    created_at=datetime.now(),
                    posted=False
                )
                
                # Add to database
                db.session.add(pending_market)
                db.session.commit()
                
                stored_count += 1
                
            except Exception as e:
                logger.error(f"Error storing market {market.get('id')}: {str(e)}")
                db.session.rollback()
    
    logger.info(f"Stored {stored_count} pending markets")
    
    return stored_count

def post_test_market():
    """
    Post a test market to Slack for verification
    
    Returns:
        True if successful, False otherwise
    """
    logger.info("Posting a test market to Slack for verification")
    
    with app.app_context():
        # Find a pending market
        pending_market = PendingMarket.query.filter_by(posted=False).first()
        
        if not pending_market:
            logger.error("No pending markets found to post")
            return False
        
        try:
            # Post to Slack
            message_ts, thread_ts = post_market_to_slack(pending_market)
            
            # Update pending market
            pending_market.slack_message_ts = message_ts
            pending_market.slack_thread_ts = thread_ts
            pending_market.posted = True
            pending_market.posted_at = datetime.now()
            
            db.session.commit()
            
            logger.info(f"Successfully posted market {pending_market.id} to Slack")
            return True
            
        except Exception as e:
            logger.error(f"Error posting market to Slack: {str(e)}")
            db.session.rollback()
            return False

def main():
    """
    Main function to test the pipeline directly
    """
    logger.info("Starting direct pipeline test")
    
    # Step 1: Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY environment variable not set")
        return 1
    
    # Step 2: Check for Slack configuration
    if not os.environ.get("SLACK_BOT_TOKEN") or not os.environ.get("SLACK_CHANNEL_ID"):
        logger.error("SLACK_BOT_TOKEN and/or SLACK_CHANNEL_ID environment variables not set")
        return 1
    
    try:
        # Step 3: Fetch markets from Polymarket API
        markets = fetch_markets(limit=5)
        if not markets:
            logger.error("Failed to fetch markets from API")
            return 1
        
        # Step 4: Filter active markets
        active_markets = filter_active_markets(markets)
        if not active_markets:
            logger.error("No active markets found")
            return 1
        
        # Step 5: Categorize markets with GPT-4o-mini
        categorized_markets = categorize_markets(active_markets)
        if not categorized_markets:
            logger.error("Failed to categorize markets")
            return 1
        
        # Step 6: Store categorized markets in database
        stored_count = store_pending_markets(categorized_markets)
        if stored_count == 0:
            logger.warning("No new markets stored in database")
        
        # Step 7: Post a test market to Slack
        if not post_test_market():
            logger.error("Failed to post test market to Slack")
            return 1
        
        logger.info("Pipeline test completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline test failed with exception: {str(e)}")
        return 1

if __name__ == "__main__":
    # Make sure to import requests at the top level for the script
    import requests
    
    sys.exit(main())