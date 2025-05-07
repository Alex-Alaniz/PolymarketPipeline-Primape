#!/usr/bin/env python3
"""
Fetch, categorize, and post markets to Slack with event tracking.

This script fetches markets from the Polymarket API, categorizes them using GPT-4o-mini,
extracts event information, stores them in the pending_markets table, and posts them 
to Slack with category badges. It properly tracks events and their associated markets.
"""

import os
import sys
import json
import uuid
import logging
import requests
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import required modules
import config
from models_updated import db, Event, Market, PendingMarket
from utils.transform_market_with_events import transform_market_for_apechain, transform_markets_batch
from utils.market_categorizer import categorize_market
from utils.batch_categorizer import batch_categorize_markets
from utils.messaging import post_formatted_message_to_slack, add_reaction_to_message
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('fetch_categorize_markets')

# Flask app for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Constants
MARKET_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=200"
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

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_markets(limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API using the Gamma Markets endpoint.
    
    Args:
        limit: Maximum number of markets to fetch
        
    Returns:
        List of market data dictionaries
    """
    try:
        # Define GraphQL query
        payload = {
            "query": MARKETS_QUERY,
            "variables": {
                "first": limit,
                "skip": 0
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
        logger.info(f"Fetched {len(markets)} markets from Gamma API")
        
        return markets
    
    except Exception as e:
        logger.error(f"Error fetching markets from API: {str(e)}")
        raise

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include truly active, non-expired ones with banner/icon URLs.
    
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
        
        # Filter out markets that are already in the database
        new_markets = [m for m in markets if m.get('conditionId') not in existing_market_ids and m.get('id') not in existing_market_ids]
        
        logger.info(f"Found {len(new_markets)} new markets not yet in the database")
        
        return new_markets

def store_pending_markets_with_events(markets: List[Dict[str, Any]]) -> Tuple[List[PendingMarket], List[Dict]]:
    """
    Store markets and their events in the pending_markets table.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        Tuple of (List[PendingMarket], List[Dict]): List of created database entries and events
    """
    with app.app_context():
        # Transform markets to extract events
        events_data, transformed_markets = transform_markets_batch(markets)
        
        # List to store created PendingMarket objects
        pending_markets = []
        
        # Filter out markets already in the database
        filtered_markets = []
        market_data_map = {}  # Map to store market data by ID for later use
        
        for market_data in transformed_markets:
            market_id = market_data.get('id')
            
            # Skip if market is already in the database
            if db.session.query(PendingMarket).filter_by(poly_id=market_id).first():
                continue
                
            # Prepare for batch categorization
            filtered_markets.append({
                'id': market_id,
                'question': market_data.get('question', ''),
                'description': market_data.get('description', '')
            })
            
            # Store market data for later use
            market_data_map[market_id] = market_data
        
        # Skip if no markets to process
        if not filtered_markets:
            logger.info("No new markets to store")
            return [], events_data
            
        # Batch categorize all markets at once
        logger.info(f"Batch categorizing {len(filtered_markets)} markets")
        categorized_markets = batch_categorize_markets(filtered_markets)
        
        # Create a map for quick category lookup
        category_map = {}
        for market in categorized_markets:
            market_id = market.get('id')
            category_map[market_id] = {
                'category': market.get('ai_category', 'news'),
                'needs_manual': market.get('needs_manual_categorization', True)
            }
        
        # Create PendingMarket entries with categorized data
        for market_data in filtered_markets:
            market_id = market_data.get('id')
            original_data = market_data_map.get(market_id, {})
            
            # Get category from the batch results or fallback to news
            category_info = category_map.get(market_id, {'category': 'news', 'needs_manual': True})
            category = category_info.get('category', 'news')
            needs_manual = category_info.get('needs_manual', True)
            
            question = original_data.get('question', '')
            
            # Create pending market entry
            pending_market = PendingMarket(
                poly_id=market_id,
                question=question,
                event_name=original_data.get('event_name'),
                event_id=original_data.get('event_id'),
                category=category,
                banner_url=original_data.get('banner_uri'),
                icon_url=original_data.get('icon_url'),
                options=original_data.get('options'),
                option_images=original_data.get('option_images'),
                expiry=original_data.get('expiry'),
                raw_data=original_data.get('raw_data'),
                needs_manual_categorization=needs_manual,
                posted=False
            )
            
            db.session.add(pending_market)
            logger.info(f"Added pending market {market_id}: {question} [Category: {category}]")
            pending_markets.append(pending_market)
        
        # Commit all changes at once
        db.session.commit()
        logger.info(f"Successfully stored {len(pending_markets)} pending markets")
        
        return pending_markets, events_data

def format_market_message(market: PendingMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge, event images and option images.
    
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
        }
    ]
    
    # Add event info and banner if available
    if market.event_name:
        # First add the event banner if available
        if market.banner_url:
            blocks.append({
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": f"Event: {market.event_name}",
                    "emoji": True
                },
                "image_url": market.banner_url,
                "alt_text": market.event_name
            })
        
        # Then add the event information
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event:* {market.event_name} · ID: `{market.event_id or 'N/A'}`"
            }
        })
    
    # Add the market question
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Market Question:* {market.question}"
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
    
    # Add market options with images if available
    if market.options:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Options:*"
            }
        })
        
        # Get option images if available
        option_images = market.option_images or {}
        
        # Add each option with its image if available
        for option in market.options:
            option_value = option.get('value', 'Unknown')
            option_id = option.get('id', '')
            
            # Create option section
            option_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {option_value}"
                }
            }
            
            # Add icon image if available (either from option_images or directly from option)
            icon_url = None
            if option_value in option_images:
                icon_url = option_images[option_value]
            elif 'image_url' in option and option['image_url']:
                icon_url = option['image_url']
            elif 'image' in option and option['image']:
                icon_url = option['image']
                
            if icon_url:
                option_block["accessory"] = {
                    "type": "image",
                    "image_url": icon_url,
                    "alt_text": option_value
                }
                
            blocks.append(option_block)
    
    # Show market icon URL if available
    if market.icon_url:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Market Icon:*"
            },
            "accessory": {
                "type": "image",
                "image_url": market.icon_url,
                "alt_text": "Market Icon"
            }
        })
    
    # Add divider
    blocks.append({"type": "divider"})
    
    # Add market ID and metadata
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Market ID: `{market.poly_id}` · Posted: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            }
        ]
    })
    
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

def post_markets_to_slack(markets: List[PendingMarket], max_to_post: int = 20) -> int:
    """
    Post markets to Slack for approval and update the database.
    
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

def main():
    """
    Main function to run the market fetching, categorizing, and posting process.
    """
    try:
        # Fetch markets from API (use 200 instead of 30)
        markets = fetch_markets(limit=200)
        
        # Filter markets
        filtered_markets = filter_active_non_expired_markets(markets)
        new_markets = filter_new_markets(filtered_markets)
        
        if not new_markets:
            logger.info("No new markets to process")
            return 0
        
        # Store markets in database with event tracking
        pending_markets, events_data = store_pending_markets_with_events(new_markets)
        
        # Post markets to Slack (max 20 at a time)
        posted_count = post_markets_to_slack(pending_markets, max_to_post=20)
        
        logger.info(f"Posted {posted_count} markets to Slack")
        logger.info(f"Extracted {len(events_data)} events from markets")
        
        return 0
    
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())