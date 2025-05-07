#!/usr/bin/env python3

"""
Test End-to-End Event Pipeline

This script runs a complete test of the event-based market pipeline:
1. Creates test market data for events
2. Transforms markets into event-based format
3. Posts markets to Slack
4. Checks for approvals
5. Creates approved markets in the database

This is meant to be run after cleaning the database for a fresh test.
"""

import os
import sys
import json
import logging
import time
from datetime import datetime, timedelta

from models import db, PendingMarket, Market
from main import app
from utils.transform_markets_with_events import transform_markets_with_events
from utils.messaging import post_slack_message, add_reaction_to_message

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("event_pipeline_test")

def create_test_markets():
    """
    Create test market data for transformation.
    
    Returns:
        list: List of test market data
    """
    # Create test markets for Champions League event
    ucl_event = {
        "id": "ucl_test",
        "name": "UEFA Champions League 2025",
        "image": "https://i.imgur.com/Ux7r6Fp.png",
        "icon": "https://i.imgur.com/Ux7r6Fp.png"
    }
    
    champions_league_markets = [
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
        }
    ]
    
    # Create test markets for La Liga event
    laliga_event = {
        "id": "laliga_test",
        "name": "La Liga Winner 2025",
        "image": "https://i.imgur.com/2YLWh6Z.png",
        "icon": "https://i.imgur.com/2YLWh6Z.png"
    }
    
    laliga_markets = [
        {
            "id": "market_real_laliga",
            "question": "Will Real Madrid win La Liga?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=120)).isoformat(),
            "events": [laliga_event],
            "icon": "https://i.imgur.com/vvL5yfp.png"
        },
        {
            "id": "market_barca",
            "question": "Will Barcelona win La Liga?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=120)).isoformat(),
            "events": [laliga_event],
            "icon": "https://i.imgur.com/7kLZZSQ.png"
        },
        {
            "id": "market_atletico",
            "question": "Will Atletico Madrid win La Liga?",
            "category": "sports",
            "expiry_time": (datetime.now() + timedelta(days=120)).isoformat(),
            "events": [laliga_event],
            "icon": "https://i.imgur.com/8D5KjfG.png"
        }
    ]
    
    # Add some standalone markets (not part of events)
    standalone_markets = [
        {
            "id": "market_btc",
            "question": "Will Bitcoin exceed $100,000 in 2025?",
            "category": "crypto",
            "expiry_time": (datetime.now() + timedelta(days=300)).isoformat(),
            "events": [],
            "icon": "https://i.imgur.com/3GhBLj5.png"
        },
        {
            "id": "market_election",
            "question": "Will Donald Trump win the 2025 presidential election?",
            "category": "politics",
            "expiry_time": (datetime.now() + timedelta(days=180)).isoformat(),
            "events": [],
            "icon": "https://i.imgur.com/KmVLZ9B.png"
        }
    ]
    
    # Combine all test markets
    all_markets = champions_league_markets + laliga_markets + standalone_markets
    logger.info(f"Created {len(all_markets)} test markets for pipeline testing")
    return all_markets

def run_event_pipeline_test():
    """
    Run the complete event pipeline test.
    
    Returns:
        tuple: (original_count, transformed_count, posted_count, approved_count)
    """
    try:
        message_ids = []
        
        # Step 1: Create test market data
        raw_markets = create_test_markets()
        original_count = len(raw_markets)
        logger.info(f"Step 1: Created {original_count} test markets")
        
        # Step 2: Transform markets to event-based format
        transformed_markets = transform_markets_with_events(raw_markets)
        transformed_count = len(transformed_markets)
        logger.info(f"Step 2: Transformed into {transformed_count} markets/events")
        
        # Calculate how many events were created
        event_count = sum(1 for m in transformed_markets if m.get('is_event', False))
        logger.info(f"Created {event_count} event markets and {transformed_count - event_count} standalone markets")
        
        posted_count = 0
        with app.app_context():
            # Step 3: Store and post transformed markets
            for market in transformed_markets:
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
                    logger.info(f"Stored market in database: {market.get('question')[:50]}...")
                    
                    # Post to Slack
                    response = post_slack_message("", market_data=market)
                    
                    if response and response.get('ok'):
                        message_id = response.get('ts')
                        message_ids.append(message_id)
                        
                        # Update the PendingMarket record with Slack message info
                        pending_market.slack_message_id = message_id
                        pending_market.posted = True
                        db.session.commit()
                        
                        logger.info(f"Posted market to Slack: {market.get('question')[:50]}...")
                        posted_count += 1
                        
                        # Auto-approve the market with a thumbs up reaction
                        add_reaction_to_message(message_id, "thumbsup")
                    else:
                        logger.error(f"Failed to post market to Slack: {response}")
                        
                except Exception as e:
                    logger.error(f"Error storing/posting market: {str(e)}")
                    db.session.rollback()
        
            logger.info(f"Step 3: Posted {posted_count} markets to Slack")
            
            # Step 4: Wait a bit for reactions to be processed
            logger.info("Step 4: Waiting for reactions to be processed...")
            time.sleep(3)
            
            # Step 5: Run the approval check
            from check_pending_approvals import check_market_approvals
            pending_count, approved_count, rejected_count = check_market_approvals()
            logger.info(f"Step 5: Approval results: {pending_count} pending, {approved_count} approved, {rejected_count} rejected")
            
            # Step 6: Verify markets were created in the Market table
            market_count = Market.query.count()
            logger.info(f"Step 6: Verified {market_count} markets created in the Market table")
            
            # Check for event markets specifically
            event_market_count = Market.query.filter_by(is_event=True).count()
            logger.info(f"Found {event_market_count} event markets in the Market table")
            
            return original_count, transformed_count, posted_count, approved_count
            
    except Exception as e:
        logger.error(f"Error in event pipeline test: {str(e)}")
        return 0, 0, 0, 0

def main():
    """
    Main function to run the event pipeline test.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting end-to-end event pipeline test")
    
    original_count, transformed_count, posted_count, approved_count = run_event_pipeline_test()
    
    if original_count > 0 and transformed_count > 0 and posted_count > 0 and approved_count > 0:
        logger.info("Successfully completed event pipeline test")
        logger.info(f"Results: {original_count} original markets → {transformed_count} transformed → {posted_count} posted → {approved_count} approved")
        return 0
    else:
        logger.error("Failed to complete event pipeline test")
        return 1

if __name__ == "__main__":
    sys.exit(main())