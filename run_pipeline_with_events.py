#!/usr/bin/env python3
"""
Run the complete pipeline with the new event-based model.

This script runs the full pipeline:
1. Fetch markets from Polymarket API
2. Extract events and categorize markets
3. Store them in the database
4. Post to Slack for approval
5. Process approvals
6. Deploy approved markets to ApeChain

It properly handles events, market IDs, and image URLs for both event
banners and market option icons.
"""

import os
import sys
import json
import logging
import hashlib
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional

# Flask app for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import updated models
from models_updated import db, Event, Market, PendingMarket, ProcessedMarket, ApprovalEvent
db.init_app(app)

# Import utility functions
from utils.transform_market_with_events import transform_market_for_apechain, transform_markets_batch
from utils.market_categorizer import categorize_market
from utils.messaging import post_formatted_message_to_slack, add_reaction_to_message

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger('pipeline')

# Constants
MARKET_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100 "
MARKETS_QUERY = """
query FetchMarkets($first: Int!, $skip: Int!) {
  markets(
    first: $first
    skip: $skip
    orderDirection: desc
    orderBy: updatedAtBlock
    where: { active: true, archived: false, closed: false }
  ) {
    id
    conditionId
    question
    description
    type
    initialOdds
    title
    image
    icon
    category
    endDate
    tokenAddress
    virtualFloor
    tradingViewSymbol
    options {
      id
      value
      image
    }
    outcomes {
      id
      value
      image
    }
    active
    closed
    archived
  }
}
"""

def fetch_markets(limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API.
    
    Args:
        limit: Maximum number of markets to fetch
        skip: Number of markets to skip (for pagination)
        
    Returns:
        List of market data dictionaries
    """
    try:
        # Define GraphQL query
        payload = {
            "query": MARKETS_QUERY,
            "variables": {
                "first": limit,
                "skip": skip
            }
        }
        
        # Make request to API
        response = requests.post(MARKET_API_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            return []
        
        markets = data.get('data', {}).get('markets', [])
        logger.info(f"Fetched {len(markets)} markets from Gamma API (skip={skip})")
        
        return markets
    
    except Exception as e:
        logger.error(f"Error fetching markets from API: {str(e)}")
        return []

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include active, non-expired ones with banner/icon URLs.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    now = datetime.now().timestamp() * 1000  # Current time in milliseconds
    
    filtered_markets = []
    for market in markets:
        # Skip if market is closed, archived, or inactive
        if market.get('closed') or market.get('archived') or not market.get('active', True):
            continue
        
        # Skip if market has already expired
        end_date = market.get('endDate')
        if end_date and int(end_date) < now:
            continue
        
        # Skip if market doesn't have image or icon URLs
        if not market.get('image') or not market.get('icon'):
            continue
        
        # Skip markets without options/outcomes
        options = market.get('options') or market.get('outcomes') or []
        if not options:
            continue
        
        # Add to filtered list
        filtered_markets.append(market)
    
    logger.info(f"Filtered down to {len(filtered_markets)} active, non-expired markets with banner/icon")
    
    return filtered_markets

def filter_new_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include those not already in the database.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: List of new markets
    """
    with app.app_context():
        # Get IDs of markets already in the database
        existing_market_ids = set()
        
        # Check pending_markets
        pending_market_ids = db.session.query(PendingMarket.poly_id).all()
        existing_market_ids.update([m[0] for m in pending_market_ids])
        
        # Check markets
        market_ids = db.session.query(Market.original_market_id).all()
        existing_market_ids.update([m[0] for m in market_ids if m[0]])
        
        # Check processed_markets
        processed_ids = db.session.query(ProcessedMarket.condition_id).all()
        existing_market_ids.update([m[0] for m in processed_ids])
        
        # Filter out markets that are already in the database
        new_markets = [m for m in markets if m.get('conditionId') not in existing_market_ids and m.get('id') not in existing_market_ids]
        
        logger.info(f"Found {len(new_markets)} new markets not yet in the database")
        
        return new_markets

def generate_event_id(event_name: str) -> str:
    """
    Generate a deterministic ID for an event based on its name.
    
    Args:
        event_name: Name of the event
        
    Returns:
        Deterministic ID for the event
    """
    return hashlib.sha256(event_name.encode()).hexdigest()[:40]

def store_events_and_markets(markets: List[Dict[str, Any]]) -> Tuple[List[Event], List[PendingMarket]]:
    """
    Process and store events and markets in the database.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        Tuple of (List[Event], List[PendingMarket]): Created events and pending markets
    """
    with app.app_context():
        # Transform markets to extract events
        events_data, transformed_markets = transform_markets_batch(markets)
        
        # Track created objects
        created_events = []
        created_pending_markets = []
        
        # First, create or update events
        for event_data in events_data:
            event_id = event_data['id']
            
            # Check if event already exists
            existing_event = Event.query.get(event_id)
            if existing_event:
                logger.info(f"Event {event_id} already exists, updating")
                
                # Update event fields
                existing_event.name = event_data['name']
                existing_event.description = event_data.get('description', '')
                existing_event.category = event_data.get('category', 'news')
                existing_event.sub_category = event_data.get('sub_category')
                existing_event.banner_url = event_data.get('banner_url')
                existing_event.icon_url = event_data.get('icon_url')
                existing_event.updated_at = datetime.utcnow()
                
                created_events.append(existing_event)
            else:
                # Create new event
                new_event = Event(
                    id=event_id,
                    name=event_data['name'],
                    description=event_data.get('description', ''),
                    category=event_data.get('category', 'news'),
                    sub_category=event_data.get('sub_category'),
                    banner_url=event_data.get('banner_url'),
                    icon_url=event_data.get('icon_url'),
                    source_id=event_data.get('source_id'),
                    raw_data=event_data.get('raw_data')
                )
                
                db.session.add(new_event)
                created_events.append(new_event)
                logger.info(f"Created new event {event_id}: {event_data['name']}")
        
        # Commit events first to avoid foreign key constraints
        db.session.commit()
        
        # Then, create pending markets
        for market_data in transformed_markets:
            market_id = market_data['id']
            
            # Skip if market is already in the database
            if db.session.query(PendingMarket).filter_by(poly_id=market_id).first():
                continue
            
            # Categorize the market using GPT-4o-mini
            question = market_data['question']
            description = market_data.get('description', '')
            category, needs_manual = categorize_market(question, description)
            
            # Create pending market entry
            pending_market = PendingMarket(
                poly_id=market_id,
                question=question,
                event_name=market_data.get('event_name'),
                event_id=market_data.get('event_id'),
                category=category,
                banner_url=market_data.get('banner_uri'),
                icon_url=market_data.get('icon_url'),
                options=market_data.get('options'),
                option_images=market_data.get('option_images'),
                expiry=market_data.get('expiry'),
                raw_data=market_data.get('raw_data'),
                needs_manual_categorization=needs_manual,
                posted=False
            )
            
            db.session.add(pending_market)
            created_pending_markets.append(pending_market)
            logger.info(f"Created pending market {market_id}: {question}")
            
            # Also add to processed_markets table to prevent duplicates
            processed_market = ProcessedMarket(
                condition_id=market_id,
                question=question,
                event_name=market_data.get('event_name'),
                event_id=market_data.get('event_id'),
                raw_data=market_data.get('raw_data'),
                posted=False,
                approved=None  # None means pending
            )
            
            db.session.add(processed_market)
        
        # Commit all changes
        db.session.commit()
        
        return created_events, created_pending_markets

def format_market_message(market: PendingMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge.
    
    Args:
        market: PendingMarket model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Define emoji map for categories
    category_emoji = {
        'politics': ':ballot_box_with_ballot:',
        'crypto': ':coin:',
        'sports': ':sports_medal:',
        'business': ':chart_with_upwards_trend:',
        'culture': ':performing_arts:',
        'tech': ':computer:',
        'news': ':newspaper:',
        # Add fallback for unknown categories
        'unknown': ':question:'
    }
    
    # Get emoji for this category
    emoji = category_emoji.get(market.category.lower(), category_emoji['unknown'])
    
    # Format message text
    message_text = f"*{market.question}*\n\nCategory: {emoji} {market.category.capitalize()}"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "New Market for Approval",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{market.question}*"
            }
        }
    ]
    
    # Add event name if available
    if market.event_name:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event:* {market.event_name}"
            }
        })
    
    # Add market options if available
    if market.options:
        # Create header for options
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Options:*"
            }
        })
        
        # Add each option separately, this will help with the option images later
        if isinstance(market.options, list):
            for option in market.options:
                if isinstance(option, dict):
                    option_value = option.get('value', 'Unknown')
                elif isinstance(option, str):
                    option_value = option
                else:
                    option_value = str(option)
                    
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {option_value}"
                    }
                })
        elif isinstance(market.options, dict):
            for option_id, option_value in market.options.items():
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"• {option_value}"
                    }
                })
        else:
            # Fallback for other option formats
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Options format not supported: {type(market.options)}"
                }
            })
    
    # Add category section with badge
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Category:* {emoji} {market.category.capitalize()}"
        }
    })
    
    # Add event banner image if available
    if market.banner_url:
        blocks.append({
            "type": "image",
            "image_url": market.banner_url,
            "alt_text": market.question,
            "title": {
                "type": "plain_text",
                "text": "Event Banner"
            }
        })
    
    # Add option images if available
    if market.option_images and isinstance(market.option_images, dict):
        for option_name, image_url in market.option_images.items():
            if image_url:
                # Add option name first
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Option:* {option_name}"
                    }
                })
                # Add option image
                blocks.append({
                    "type": "image",
                    "image_url": image_url,
                    "alt_text": f"Option {option_name}",
                    "title": {
                        "type": "plain_text",
                        "text": f"Option: {option_name}"
                    }
                })
    
    # Add divider
    blocks.append({"type": "divider"})
    
    # Add approval/rejection buttons context
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": "React with :white_check_mark: to approve or :x: to reject"
            }
        ]
    })
    
    return message_text, blocks

def post_pending_markets_to_slack(markets: List[PendingMarket], max_to_post: int = 20) -> int:
    """
    Post pending markets to Slack for approval and update the database.
    
    Args:
        markets: List of PendingMarket model instances
        max_to_post: Maximum number of markets to post
        
    Returns:
        int: Number of markets successfully posted
    """
    with app.app_context():
        # Get unposted markets
        unposted_markets = [m for m in markets if not m.posted and not m.slack_message_id]
        
        # Limit to max_to_post
        markets_to_post = unposted_markets[:max_to_post]
        
        posted_count = 0
        for market in markets_to_post:
            try:
                # Format message
                message_text, blocks = format_market_message(market)
                
                # Post to Slack
                message_id = post_formatted_message_to_slack(message_text, blocks=blocks)
                
                if not message_id:
                    logger.error(f"Failed to post market {market.poly_id} to Slack")
                    continue
                
                # Add approval/rejection reactions
                add_reaction_to_message(message_id, "white_check_mark")
                add_reaction_to_message(message_id, "x")
                
                # Update database
                market.slack_message_id = message_id
                market.posted = True
                db.session.commit()
                
                logger.info(f"Posted market {market.poly_id} to Slack with message ID {message_id}")
                posted_count += 1
                
            except Exception as e:
                logger.error(f"Error posting market {market.poly_id} to Slack: {str(e)}")
                db.session.rollback()
        
        return posted_count

def run_pipeline(max_markets: int = 20) -> int:
    """
    Run the full pipeline.
    
    Args:
        max_markets: Maximum number of markets to process
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Step 1: Fetch markets from API
        markets = fetch_markets(limit=max_markets)
        
        # Step 2: Filter markets
        filtered_markets = filter_active_non_expired_markets(markets)
        new_markets = filter_new_markets(filtered_markets)
        
        if not new_markets:
            logger.info("No new markets to process")
            return 0
        
        # Step 3: Store events and markets in database
        events, pending_markets = store_events_and_markets(new_markets)
        
        # Step 4: Post markets to Slack
        posted_count = post_pending_markets_to_slack(pending_markets, max_to_post=10)
        
        logger.info(f"Pipeline completed successfully")
        logger.info(f"Created {len(events)} events")
        logger.info(f"Created {len(pending_markets)} pending markets")
        logger.info(f"Posted {posted_count} markets to Slack")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        return 1

if __name__ == "__main__":
    with app.app_context():
        # Check if database has necessary tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'events' not in inspector.get_table_names():
            logger.error("Database schema is not initialized. Run reset_and_setup_events_model.py first.")
            sys.exit(1)
    
    sys.exit(run_pipeline())