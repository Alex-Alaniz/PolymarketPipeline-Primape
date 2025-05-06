#!/usr/bin/env python3

"""
Fetch, categorize, and post markets to Slack.

This script fetches markets from the Polymarket API, categorizes them using GPT-4o-mini,
stores them in the pending_markets table, and posts them to Slack with category badges.
"""

import os
import sys
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from models import db, PendingMarket, ProcessedMarket
from utils.market_categorizer import categorize_markets
from utils.messaging import post_message_to_slack, add_reaction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("fetch_categorize_markets")

# Polymarket API base URL
POLYMARKET_API_BASE = "https://strapi-matic.poly.market/api"

# Number of markets to fetch and post per run
MAX_MARKETS_TO_FETCH = 100  # Fetch a large batch to filter down
MAX_MARKETS_TO_POST = 20   # Limit posting to avoid spam

# Category emoji mapping
CATEGORY_EMOJI = {
    "politics": ":ballot_box:",
    "crypto": ":coin:",
    "sports": ":sports_medal:",
    "business": ":chart_with_upwards_trend:",
    "culture": ":performing_arts:",
    "news": ":newspaper:",
    "tech": ":computer:",
    "all": ":globe_with_meridians:"
}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_markets(page: int = 1, page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API.
    
    Args:
        page: Page number for pagination
        page_size: Number of markets per page
        
    Returns:
        List of market data dictionaries
    """
    url = f"{POLYMARKET_API_BASE}/markets"
    params = {
        "page": page,
        "pageSize": page_size,
        "sortBy": "creationDate",
        "sortDirection": "desc"
    }
    
    try:
        logger.info(f"Fetching page {page} with page size {page_size}")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        markets = data.get("markets", [])
        logger.info(f"Fetched {len(markets)} markets from page {page}")
        
        return markets
        
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        raise

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include truly active, non-expired ones with banner/icon URLs.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    now = datetime.utcnow()
    filtered_markets = []
    
    for market in markets:
        # Check if market is active
        if market.get("active") != True:
            logger.debug(f"Skipping inactive market: {market.get('question')}")
            continue
            
        # Check if market is resolved
        if market.get("isResolved") == True:
            logger.debug(f"Skipping resolved market: {market.get('question')}")
            continue
            
        # Check if market has an end date and if it's expired
        end_date_str = market.get("endDate")
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
                if end_date < now:
                    logger.debug(f"Skipping expired market: {market.get('question')}")
                    continue
            except Exception as e:
                logger.warning(f"Error parsing end date: {str(e)}")
                # Continue without filtering if we can't parse the date
                
        # Ensure market has a question
        if not market.get("question"):
            logger.debug("Skipping market without question")
            continue
            
        # Make sure we have banner or icon URL
        has_banner = bool(market.get("image") or market.get("event_image"))
        has_icon = bool(market.get("icon") or market.get("event_icon"))
        
        if not (has_banner or has_icon):
            logger.debug(f"Skipping market without banner/icon: {market.get('question')}")
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
    new_markets = []
    existing_market_ids = set()
    
    # Get all condition IDs that are already in the processed_markets table
    existing_condition_ids = {m.condition_id for m in ProcessedMarket.query.all()}
    
    # Get all poly_ids that are already in the pending_markets table
    existing_poly_ids = {m.poly_id for m in PendingMarket.query.all()}
    
    # Combine all existing IDs
    all_existing_ids = existing_condition_ids.union(existing_poly_ids)
    
    for market in markets:
        # For multiple-option markets, check group ID
        if market.get("is_multiple_option", False):
            market_id = market.get("id")
        else:
            market_id = market.get("conditionId")
            
        if not market_id:
            logger.warning(f"Market missing ID, skipping: {market.get('question', 'Unknown')}")
            continue
            
        if market_id in all_existing_ids:
            logger.debug(f"Market {market_id} already in database, skipping")
            continue
            
        # Check if already added to our new markets list (can happen with duplicates from API)
        if market_id in existing_market_ids:
            logger.debug(f"Market {market_id} already in new markets list, skipping")
            continue
            
        new_markets.append(market)
        existing_market_ids.add(market_id)
        
    logger.info(f"Found {len(new_markets)} new markets not in database")
    return new_markets

def store_pending_markets(markets: List[Dict[str, Any]]) -> List[PendingMarket]:
    """
    Store markets in the pending_markets table.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[PendingMarket]: List of created database entries
    """
    pending_markets = []
    
    for market in markets:
        try:
            # Determine the ID based on market type
            if market.get("is_multiple_option", False):
                poly_id = market.get("id")
            else:
                poly_id = market.get("conditionId")
                
            if not poly_id:
                logger.warning(f"Market missing ID, skipping: {market.get('question', 'Unknown')}")
                continue
                
            # Extract banner and icon URLs
            banner_url = market.get("image") or market.get("event_image", "")
            icon_url = market.get("icon") or market.get("event_icon", "")
            
            # Extract expiry timestamp
            expiry_timestamp = None
            if market.get("endDate"):
                try:
                    expiry_timestamp = int(datetime.fromisoformat(
                        market.get("endDate").replace("Z", "+00:00")
                    ).timestamp())
                except Exception as e:
                    logger.error(f"Error parsing endDate for {poly_id}: {str(e)}")
                    
            # Get options/outcomes
            options = []
            outcomes_raw = market.get("outcomes", "[]")
            
            # Parse outcomes which come as a JSON string
            try:
                if isinstance(outcomes_raw, str):
                    outcomes = json.loads(outcomes_raw)
                else:
                    outcomes = outcomes_raw
                    
                # For multiple-option markets, remove duplicates
                if market.get("is_multiple_option", False) and outcomes:
                    outcomes = list(dict.fromkeys(outcomes))
                    options = outcomes
                else:
                    # Binary market defaults to Yes/No
                    options = outcomes if outcomes else ["Yes", "No"]
            except Exception as e:
                logger.error(f"Error parsing outcomes for {poly_id}: {str(e)}")
                options = ["Yes", "No"]  # Default fallback
                
            # Create PendingMarket entry
            pending_market = PendingMarket(
                poly_id=poly_id,
                question=market.get("question", ""),
                category=market.get("ai_category", "all"),
                banner_url=banner_url,
                icon_url=icon_url,
                options=json.dumps(options),
                expiry=expiry_timestamp,
                needs_manual_categorization=market.get("needs_manual_categorization", False),
                raw_data=market
            )
            
            db.session.add(pending_market)
            pending_markets.append(pending_market)
            
            logger.info(f"Added pending market {poly_id}: {pending_market.question}")
            
        except Exception as e:
            logger.error(f"Error storing pending market: {str(e)}")
            continue
            
    # Commit all changes
    db.session.commit()
    
    logger.info(f"Successfully stored {len(pending_markets)} pending markets")
    return pending_markets

def format_market_message(market: PendingMarket) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for posting to Slack with category badge.
    
    Args:
        market: PendingMarket model instance
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Get category emoji
    category = market.category.lower()
    emoji = CATEGORY_EMOJI.get(category, ":globe_with_meridians:")
    
    # Format expiry date if available
    expiry_text = ""
    if market.expiry:
        try:
            expiry_date = datetime.fromtimestamp(market.expiry)
            expiry_text = f"Expires: {expiry_date.strftime('%Y-%m-%d %H:%M')} UTC"
        except Exception as e:
            logger.error(f"Error formatting expiry date: {str(e)}")
            
    # Parse options
    options_text = "Options: Yes/No"
    try:
        options = json.loads(market.options)
        if options and len(options) > 0:
            options_text = "Options: " + ", ".join(options)
    except Exception as e:
        logger.error(f"Error parsing options: {str(e)}")
        
    # Create the message
    message_text = f"*New Market for Review*\n*Category:* {emoji} {market.category.capitalize()}\n\n*Question:* {market.question}\n\n{options_text}\n{expiry_text}"
    
    # Create blocks for rich formatting
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*New Market for Review*\n*Category:* {emoji} {market.category.capitalize()}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {market.question}"
            }
        }
    ]
    
    # Add options block
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": options_text
        }
    })
    
    # Add expiry if available
    if expiry_text:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": expiry_text
            }
        })
        
    # Add image if available and not empty
    if market.banner_url and market.banner_url.strip():
        blocks.append({
            "type": "image",
            "image_url": market.banner_url,
            "alt_text": "Market banner"
        })
    elif market.icon_url and market.icon_url.strip():
        blocks.append({
            "type": "image",
            "image_url": market.icon_url,
            "alt_text": "Market icon"
        })
        
    # Add instructions for review
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
    posted_count = 0
    
    # Limit to max_to_post
    markets = markets[:max_to_post]
    
    for market in markets:
        try:
            # Format the message
            message_text, blocks = format_market_message(market)
            
            # Post to Slack
            message_ts = post_message_to_slack((message_text, blocks))
            
            # Add initial reactions if posted successfully
            if message_ts:
                add_reaction(message_ts, "white_check_mark")
                add_reaction(message_ts, "x")
                response = {"ts": message_ts}
            else:
                response = None
            
            # Update database with message ID
            if response and response.get("ts"):
                market.slack_message_id = response["ts"]
                db.session.commit()
                
                logger.info(f"Posted market {market.poly_id} to Slack with message ID {market.slack_message_id}")
                posted_count += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
            else:
                logger.error(f"Failed to post market {market.poly_id} to Slack: No response")
                
        except Exception as e:
            logger.error(f"Error posting market {market.poly_id} to Slack: {str(e)}")
            
    logger.info(f"Posted {posted_count} markets to Slack for approval")
    return posted_count

def main():
    """
    Main function to run the market fetching, categorizing, and posting process.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        try:
            # 1. Fetch markets from API
            markets = fetch_markets(page=1, page_size=MAX_MARKETS_TO_FETCH)
            
            # 2. Filter markets
            active_markets = filter_active_non_expired_markets(markets)
            new_markets = filter_new_markets(active_markets)
            
            if not new_markets:
                logger.info("No new markets to process")
                return 0
                
            # 3. Categorize markets with GPT-4o-mini
            categorized_markets = categorize_markets(new_markets)
            
            # 4. Store in pending_markets table
            pending_markets = store_pending_markets(categorized_markets)
            
            # 5. Post to Slack with category badges
            posted_count = post_markets_to_slack(pending_markets, max_to_post=MAX_MARKETS_TO_POST)
            
            logger.info(f"Successfully fetched, categorized, and posted {posted_count} markets to Slack")
            
        except Exception as e:
            logger.error(f"Error in market fetching process: {str(e)}")
            return 1
            
    return 0

if __name__ == "__main__":
    sys.exit(main())