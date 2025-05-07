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
import traceback
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
from models_updated import db, Event, Market, PendingMarket, ProcessedMarket
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
# API configuration - Polymarket Gamma API is public and doesn't require an API key
MARKETS_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
EVENTS_API_URL = "https://gamma-api.polymarket.com/events?closed=false&archived=false&active=true&limit=100"
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

def fetch_binary_markets(limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch binary markets from Polymarket Markets API.
    These are markets that are not part of event groups.
    
    Args:
        limit: Maximum number of markets to fetch
        skip: Number of markets to skip (for pagination)
        
    Returns:
        List of binary market data dictionaries
    """
    try:
        # Polymarket Gamma API is public and doesn't require authentication
        headers = {}
        
        # Try with REST API endpoint first (markets endpoint)
        try:
            logger.info(f"Fetching binary markets from Markets REST API endpoint")
            rest_response = requests.get(MARKETS_API_URL, headers=headers)
            rest_response.raise_for_status()
            
            rest_data = rest_response.json()
            # If we have valid data, use it
            if rest_data and isinstance(rest_data, list):
                logger.info(f"Successfully fetched {len(rest_data)} binary markets from REST API")
                
                # Filter markets to only include those not part of events
                standalone_markets = [m for m in rest_data if not m.get('events')]
                logger.info(f"Filtered to {len(standalone_markets)} standalone binary markets")
                
                return standalone_markets
            else:
                logger.warning(f"Markets REST API returned invalid data format")
                return []
        except Exception as e:
            logger.warning(f"Markets REST API request failed: {str(e)}")
            return []
        
    except Exception as e:
        logger.error(f"Error fetching binary markets from API: {str(e)}")
        return []

def fetch_event_markets(limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch event markets from Polymarket Events API.
    These are events that contain grouped markets to be transformed into a single market with options.
    
    Args:
        limit: Maximum number of events to fetch
        skip: Number of events to skip (for pagination)
        
    Returns:
        List of event data dictionaries
    """
    try:
        # Polymarket Gamma API is public and doesn't require authentication
        headers = {}
        
        # Try with REST API endpoint (events endpoint)
        try:
            logger.info(f"Fetching events from Events REST API endpoint")
            rest_response = requests.get(EVENTS_API_URL, headers=headers)
            rest_response.raise_for_status()
            
            rest_data = rest_response.json()
            # If we have valid data, use it
            if rest_data and isinstance(rest_data, list):
                # Filter events that have markets
                valid_events = [evt for evt in rest_data if evt.get('markets') and len(evt.get('markets', [])) > 0]
                logger.info(f"Successfully fetched {len(valid_events)} events with markets from Events API")
                return valid_events
            else:
                logger.warning(f"Events REST API returned invalid data format")
                return []
        except Exception as e:
            logger.warning(f"Events REST API request failed: {str(e)}")
            return []
        
    except Exception as e:
        logger.error(f"Error fetching events from API: {str(e)}")
        return []

def fetch_all_market_data(limit: int = 100) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Fetch both binary markets and event markets from Polymarket API.
    
    Args:
        limit: Maximum number of markets/events to fetch per type
        
    Returns:
        Tuple of (binary_markets, event_markets)
    """
    # Fetch both types of market data
    binary_markets = fetch_binary_markets(limit=limit)
    event_markets = fetch_event_markets(limit=limit)
    
    logger.info(f"Fetched {len(binary_markets)} binary markets and {len(event_markets)} events")
    
    return binary_markets, event_markets

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

def process_binary_markets(binary_markets: List[Dict[str, Any]], max_markets: int = 20) -> Tuple[List[Event], List[PendingMarket]]:
    """
    Process binary markets (non-event markets).
    
    Args:
        binary_markets: List of binary market data
        max_markets: Maximum number of markets to process
        
    Returns:
        Tuple of (events, pending_markets)
    """
    # Step 1: Filter binary markets
    active_markets = filter_active_non_expired_markets(binary_markets)
    new_markets = filter_new_markets(active_markets)
    
    if not new_markets:
        logger.info("No new binary markets to process")
        return [], []
    
    # Step 2: Store in database
    # Note: For binary markets, each market gets its own "event" (1:1 relationship)
    events, pending_markets = store_events_and_markets(new_markets[:max_markets])
    
    logger.info(f"Processed {len(events)} events and {len(pending_markets)} binary markets")
    
    return events, pending_markets

def process_event_markets(event_data: List[Dict[str, Any]], max_events: int = 10) -> Tuple[List[Event], List[PendingMarket]]:
    """
    Process event markets (transform event with multiple markets into single market with options).
    
    Args:
        event_data: List of event data from Polymarket Events API
        max_events: Maximum number of events to process
        
    Returns:
        Tuple of (events, pending_markets)
    """
    # First filter events to active, non-expired ones
    now = datetime.now().timestamp() * 1000  # Current time in milliseconds
    
    active_events = []
    for event in event_data:
        # Skip if event is closed, archived, or inactive
        if event.get('closed') or event.get('archived') or not event.get('active', True):
            continue
        
        # Skip if event has already expired
        end_date = event.get('endDate')
        if end_date and int(end_date) < now:
            continue
        
        # Skip if event doesn't have image or icon URLs
        if not event.get('image') or not event.get('icon'):
            continue
        
        # Skip events without markets
        markets = event.get('markets', [])
        if not markets or len(markets) == 0:
            continue
        
        # Add to filtered list
        active_events.append(event)
    
    logger.info(f"Filtered down to {len(active_events)} active, non-expired events")
    
    # Filter events not already in database
    with app.app_context():
        # Get IDs of events already in the database
        existing_event_ids = set()
        
        # Check events table
        event_ids = db.session.query(Event.source_id).all()
        existing_event_ids.update([e[0] for e in event_ids if e[0]])
        
        # Filter out events that are already in the database
        new_events = [e for e in active_events if e.get('id') not in existing_event_ids]
        
        logger.info(f"Found {len(new_events)} new events not yet in the database")
    
    if not new_events:
        logger.info("No new event markets to process")
        return [], []
    
    # Transform events into our format and store in database
    # We'll use utils/transform_market_with_events.py for this
    events = []
    pending_markets = []
    
    for event in new_events[:max_events]:
        try:
            # Transform the event into our format
            event_id = event.get('id')
            event_name = event.get('title')
            event_banner = event.get('image')
            event_icon = event.get('icon')
            event_category = event.get('category', 'sports').lower()
            event_description = event.get('description', '')
            
            # Create an event object
            event_obj = Event(
                id=generate_event_id(event_name),
                name=event_name,
                description=event_description,
                category=event_category,
                banner_url=event_banner,
                icon_url=event_icon,
                source_id=event_id,
                raw_data=json.dumps(event)
            )
            
            with app.app_context():
                db.session.add(event_obj)
                db.session.commit()
                events.append(event_obj)
            
            # Transform event markets into a single market with options
            market_options = []
            option_images = {}
            
            for market in event.get('markets', []):
                market_id = market.get('id')
                market_question = market.get('question')
                market_icon = market.get('icon')
                
                # Skip markets without proper data
                if not all([market_id, market_question]):
                    continue
                
                # Add as an option
                market_options.append(market_question)
                if market_icon:
                    option_images[market_question] = market_icon
            
            # Create a pending market for the whole event
            if market_options:
                # Categorize the market using GPT-4o-mini
                question = f"Event: {event_name}"
                category, needs_manual = categorize_market(question, event_description)
                
                # Use event category if categorization returns unknown
                if category.lower() == 'unknown':
                    category = event_category
                
                # Create pending market entry
                pending_market = PendingMarket(
                    poly_id=event_id,
                    question=question,
                    event_name=event_name,
                    event_id=event_obj.id,
                    category=category,
                    banner_url=event_banner,
                    icon_url=event_icon,
                    options=market_options,
                    option_images=option_images,
                    expiry=event.get('endDate'),
                    raw_data=json.dumps(event),
                    needs_manual_categorization=needs_manual,
                    posted=False,
                    is_event=True
                )
                
                with app.app_context():
                    db.session.add(pending_market)
                    
                    # Also add to processed_markets table to prevent duplicates
                    processed_market = ProcessedMarket(
                        condition_id=event_id,
                        question=question,
                        event_name=event_name,
                        event_id=event_obj.id,
                        raw_data=json.dumps(event),
                        posted=False,
                        approved=None  # None means pending
                    )
                    
                    db.session.add(processed_market)
                    db.session.commit()
                    
                    pending_markets.append(pending_market)
                    
                    logger.info(f"Created event market {event_id}: {question} with {len(market_options)} options")
        
        except Exception as e:
            logger.error(f"Error processing event {event.get('id')}: {str(e)}")
            continue
    
    return events, pending_markets

def run_pipeline(max_markets: int = 20, max_events: int = 10) -> int:
    """
    Run the full pipeline with both binary markets and event markets.
    
    Args:
        max_markets: Maximum number of binary markets to process
        max_events: Maximum number of events to process
        
    Returns:
        int: Exit code (0 for success, non-zero for failure)
    """
    try:
        # Step 1: Fetch both binary markets and events from Polymarket API
        binary_markets, event_data = fetch_all_market_data(limit=max_markets*2)  # Fetch more than we need to account for filtering
        
        # Step 2: Process binary markets
        binary_events, binary_pending_markets = process_binary_markets(binary_markets, max_markets)
        
        # Step 3: Process event markets
        event_events, event_pending_markets = process_event_markets(event_data, max_events)
        
        # Combine the results
        all_events = binary_events + event_events
        all_pending_markets = binary_pending_markets + event_pending_markets
        
        if not all_pending_markets:
            logger.info("No new markets to process")
            return 0
        
        # Step 4: Post pending markets to Slack for approval
        posted_count = post_pending_markets_to_slack(all_pending_markets)
        
        logger.info(f"Pipeline completed successfully")
        logger.info(f"Created {len(all_events)} events")
        logger.info(f"Created {len(all_pending_markets)} pending markets")
        logger.info(f"Posted {posted_count} markets to Slack")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in pipeline: {str(e)}")
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run the Polymarket pipeline with event support.')
    parser.add_argument('--max-markets', type=int, default=20, help='Maximum number of binary markets to process')
    parser.add_argument('--max-events', type=int, default=10, help='Maximum number of events to process')
    args = parser.parse_args()
    
    with app.app_context():
        # Check if database has necessary tables
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'events' not in inspector.get_table_names():
            logger.error("Database schema is not initialized. Run reset_and_setup_events_model.py first.")
            sys.exit(1)
    
    logger.info(f"Starting pipeline with max_markets={args.max_markets}, max_events={args.max_events}")
    sys.exit(run_pipeline(max_markets=args.max_markets, max_events=args.max_events))