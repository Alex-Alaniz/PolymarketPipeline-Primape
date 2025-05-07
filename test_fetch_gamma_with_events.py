#!/usr/bin/env python3
"""
Test Gamma API Fetch with Event Grouping

This script tests fetching markets from the Gamma API and transforming them 
with proper event grouping, but with a smaller batch size for testing purposes.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fetch_events_test.log")
    ]
)
logger = logging.getLogger('test_gamma_events')

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Local imports
from models import db, Market, PendingMarket, ProcessedMarket
from utils.transform_market_with_events import transform_markets_batch

# Initialize app
db.init_app(app)

# Constants
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"

def fetch_limited_markets(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch a limited number of markets for testing"""
    import requests
    
    params = {
        "closed": "false",
        "archived": "false",
        "active": "true",
        "limit": str(limit)
    }
    
    logger.info(f"Fetching {limit} markets from Gamma API")
    
    try:
        response = requests.get(GAMMA_API_URL, params=params)
        response.raise_for_status()
        
        markets = response.json()
        
        if not isinstance(markets, list):
            raise ValueError(f"Expected list response, got {type(markets)}")
            
        logger.info(f"Successfully fetched {len(markets)} markets")
        
        return markets
    
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        raise

def filter_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out expired markets"""
    # Get current time with timezone info
    now = datetime.now(timezone.utc)
    
    filtered_markets = []
    for market in markets:
        end_date_str = market.get("endDate")
        
        if end_date_str:
            try:
                # Parse ISO format date
                from dateutil import parser
                end_date = parser.parse(end_date_str)
                
                # Ensure timezone info
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                
                # Check if expired
                if end_date < now:
                    logger.info(f"Market expired: {market.get('question', '')[:30]}... (End: {end_date_str})")
                    continue
            except Exception as e:
                logger.warning(f"Invalid end date '{end_date_str}': {str(e)}")
        
        # Add to filtered list
        filtered_markets.append(market)
    
    logger.info(f"Filtered to {len(filtered_markets)} non-expired markets")
    return filtered_markets

def test_market_transformation(markets: List[Dict[str, Any]]):
    """Test the transformation of markets with event extraction"""
    logger.info("Testing market transformation with event extraction...")
    
    try:
        # Transform markets, extracting events
        events, transformed_markets = transform_markets_batch(markets)
        
        # Log results
        logger.info(f"Extracted {len(events)} events from {len(transformed_markets)} markets")
        
        # Show events found
        for i, event in enumerate(events):
            logger.info(f"Event {i+1}: {event['name']} (ID: {event['id']})")
            
            # Count markets in this event
            event_markets = [m for m in transformed_markets if m['event_id'] == event['id']]
            logger.info(f"  - Contains {len(event_markets)} markets")
            
            # Show markets in this event
            for j, market in enumerate(event_markets[:3]):  # Show max 3 per event
                logger.info(f"    Market {j+1}: {market['question'][:40]}...")
        
        return events, transformed_markets
        
    except Exception as e:
        logger.error(f"Error in market transformation: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        return [], []

def test_store_in_database(events, transformed_markets):
    """Test storing the transformed markets in the database"""
    logger.info("Testing database storage...")
    
    stored_count = 0
    event_count = 0
    
    with app.app_context():
        try:
            # First, store events
            for event in events:
                # Check if event already exists
                existing_event = db.session.query(Market).filter_by(id=event['id']).first()
                if existing_event:
                    logger.info(f"Event {event['name']} already exists, skipping")
                    continue
                
                logger.info(f"Storing event: {event['name']}")
                
                # Create database record
                event_record = PendingMarket(
                    poly_id=f"event_{event['id']}",
                    question=f"Event: {event['name']}",
                    category=event['category'],
                    banner_url=event.get('banner_url'),
                    icon_url=event.get('icon_url'),
                    event_id=event['id'],
                    event_name=event['name'],
                    raw_data=event,
                    posted=False
                )
                
                db.session.add(event_record)
                event_count += 1
            
            # Then store markets
            for market in transformed_markets:
                market_id = market.get('id')
                
                # Skip if already in database
                existing = db.session.query(PendingMarket).filter_by(poly_id=market_id).first()
                if existing:
                    logger.info(f"Market {market_id} already exists, skipping")
                    continue
                
                logger.info(f"Storing market: {market['question'][:40]}...")
                
                # Create database record
                market_record = PendingMarket(
                    poly_id=market_id,
                    question=market['question'],
                    category=market.get('category', 'news'),
                    banner_url=market.get('banner_uri'),
                    icon_url=market.get('icon_url'),
                    options=market.get('options', []),
                    option_images=market.get('option_images', {}),
                    event_id=market.get('event_id'),
                    event_name=market.get('event_name'),
                    raw_data=market.get('raw_data', {}),
                    posted=False
                )
                
                db.session.add(market_record)
                stored_count += 1
                
                # Add to processed_markets to prevent re-processing
                processed = ProcessedMarket(
                    condition_id=market_id,
                    question=market['question'],
                    category=market.get('category', 'news'),
                    raw_data=market.get('raw_data', {}),
                    posted=False
                )
                
                db.session.add(processed)
            
            # Commit changes
            db.session.commit()
            logger.info(f"Successfully stored {event_count} events and {stored_count} markets")
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing data: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
    
    return stored_count, event_count

def main():
    """Main test function"""
    try:
        # Step 1: Fetch markets from API
        markets = fetch_limited_markets(limit=10)
        
        # Step 2: Filter out expired markets
        active_markets = filter_non_expired_markets(markets)
        
        # Step 3: Transform markets with event extraction
        events, transformed_markets = test_market_transformation(active_markets)
        
        # Step 4: Test storing in database (if requested)
        if len(sys.argv) > 1 and sys.argv[1] == '--store':
            logger.info("Testing database storage...")
            stored_markets, stored_events = test_store_in_database(events, transformed_markets)
            logger.info(f"Stored {stored_events} events and {stored_markets} markets in database")
        
        logger.info("Test completed successfully")
        return 0
    
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())