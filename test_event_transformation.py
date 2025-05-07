#!/usr/bin/env python3

"""
Test Event Transformation

This script tests the event transformation functionality by:
1. Creating test market data
2. Transforming it into event-based format
3. Posting it to Slack for testing
4. Storing it in the database
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

from models import db, PendingMarket
from main import app
from utils.transform_markets_with_events import transform_markets_with_events
from utils.messaging import post_slack_message

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("event_test")

def create_test_markets():
    """
    Create test market data for transformation.
    
    Returns:
        list: List of test market data
    """
    # Create test markets for a Champions League event
    ucl_event = {
        "id": "ucl_test",
        "name": "UEFA Champions League 2025",
        "image": "https://i.imgur.com/Ux7r6Fp.png",
        "icon": "https://i.imgur.com/Ux7r6Fp.png"
    }
    
    test_markets = [
        {
            "id": "market_inter",
            "question": "Will Inter Milan win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=60)).isoformat(),
            "events": [ucl_event],
            "icon": "https://i.imgur.com/5fiT0XE.png"
        },
        {
            "id": "market_real",
            "question": "Will Real Madrid win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=60)).isoformat(),
            "events": [ucl_event],
            "icon": "https://i.imgur.com/vvL5yfp.png"
        },
        {
            "id": "market_arsenal",
            "question": "Will Arsenal win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=60)).isoformat(),
            "events": [ucl_event],
            "icon": "https://i.imgur.com/yBzwzFM.png"
        },
        {
            "id": "market_psg",
            "question": "Will Paris Saint-Germain win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=60)).isoformat(),
            "events": [ucl_event],
            "icon": "https://i.imgur.com/B8Zmr1v.png"
        },
        {
            "id": "market_manu",
            "question": "Will Manchester United win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=60)).isoformat(),
            "events": [ucl_event],
            "icon": "https://i.imgur.com/OTDjOce.png"
        },
        # Add a standalone market (not part of an event)
        {
            "id": "market_btc",
            "question": "Will Bitcoin exceed $100,000 in 2025?",
            "category": "crypto",
            "expiry_time": (datetime.now() + timedelta(days=300)).isoformat(),
            "events": [],
            "icon": "https://i.imgur.com/3GhBLj5.png"
        }
    ]
    
    return test_markets

def test_transform_and_post():
    """
    Transform test markets to event-based format and post to Slack.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Step 1: Create test market data
        raw_markets = create_test_markets()
        logger.info(f"Created {len(raw_markets)} test markets")
        
        # Step 2: Transform markets to event-based format
        transformed_markets = transform_markets_with_events(raw_markets)
        logger.info(f"Transformed into {len(transformed_markets)} markets/events")
        
        post_count = 0
        store_count = 0

        with app.app_context():
            # Step 3: Store and post transformed markets
            for market in transformed_markets:
                # Store in database
                try:
                    # Handle options based on whether this is an event or regular market
                    is_event = market.get('is_event', False)
                    
                    if is_event:
                        # For events, options are team names
                        options = market.get('options', [])
                    else:
                        # For regular markets, use binary Yes/No options if not specified
                        options = market.get('options', ["Yes", "No"])
                    
                    # Store option images as JSON if available
                    option_images = market.get('option_images', {})
                    option_images_json = json.dumps(option_images) if option_images else None
                    
                    # Store option market IDs for events
                    option_market_ids = market.get('option_market_ids', {})
                    option_market_ids_json = json.dumps(option_market_ids) if option_market_ids else None
                    
                    # Create a PendingMarket record
                    pending_market = PendingMarket(
                        poly_id=market.get('id'),
                        question=market.get('question'),
                        category=market.get('category'),
                        options=json.dumps(options),
                        expiry=None,  # No numeric expiry in test data
                        event_id=market.get('event_id'),
                        event_name=market.get('event_name'),
                        posted=False,
                        event_image=market.get('event_image'),
                        event_icon=market.get('event_icon'),
                        option_images=option_images_json,
                        is_event=is_event,
                        option_market_ids=option_market_ids_json
                    )
                    
                    # Add to database
                    db.session.add(pending_market)
                    db.session.commit()
                    store_count += 1
                    logger.info(f"Stored market in database: {market.get('question')[:50]}...")
                    
                    # Post to Slack
                    response = post_slack_message("", market_data=market)
                    
                    if response and response.get('ok'):
                        # Update the PendingMarket record with Slack message info
                        pending_market.slack_message_id = response.get('ts')
                        pending_market.posted = True
                        db.session.commit()
                        
                        logger.info(f"Posted market to Slack: {market.get('question')[:50]}...")
                        post_count += 1
                    else:
                        logger.error(f"Failed to post market to Slack: {response}")
                        
                except Exception as e:
                    logger.error(f"Error storing/posting market: {str(e)}")
                    db.session.rollback()
        
        logger.info(f"Successfully stored {store_count} markets in database")
        logger.info(f"Successfully posted {post_count} markets to Slack")
        return True
        
    except Exception as e:
        logger.error(f"Error in transform and post test: {str(e)}")
        return False

def main():
    """
    Main function to run the event transformation test.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting event transformation test")
    
    success = test_transform_and_post()
    
    if success:
        logger.info("Successfully completed event transformation test")
        return 0
    else:
        logger.error("Failed to complete event transformation test")
        return 1

if __name__ == "__main__":
    sys.exit(main())