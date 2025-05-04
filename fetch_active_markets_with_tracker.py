#!/usr/bin/env python3

"""
Fetch active markets from Polymarket API with database tracking.

This script fetches active markets from the Polymarket API,
tracks them in the database to avoid duplicates, and posts
only new markets to Slack for approval.

It implements pagination for efficiently processing large numbers of markets.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple

# Set up path to find project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("fetch_markets")

# Create Flask app context for database operations
from flask import Flask
from models import db, ProcessedMarket
from utils.market_tracker import MarketTracker
from utils.messaging import MessagingClient
from config import TMP_DIR

# Initialize Flask app
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

def fetch_markets_page(page_size: int = 50, next_cursor: str = None) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetch a single page of markets from Polymarket API.
    
    Args:
        page_size: Number of markets to fetch per page
        next_cursor: Cursor for pagination
        
    Returns:
        Tuple[List[Dict[str, Any]], Optional[str]]: List of markets and next_cursor
    """
    # API endpoint with pagination parameters
    url = "https://clob.polymarket.com/markets?accepting_orders=true"
    
    # Add page size
    url += f"&limit={page_size}"
    
    # Add cursor if provided
    if next_cursor:
        url += f"&next_cursor={next_cursor}"
    
    logger.info(f"Fetching markets from: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # Check if data contains markets
            if "data" in data and isinstance(data["data"], list):
                markets = data["data"]
                logger.info(f"Fetched {len(markets)} markets from API")
                
                # Get next cursor if available
                cursor = data.get("next_cursor")
                if cursor and cursor != "LTE=":
                    next_cursor = cursor
                    logger.info(f"Next cursor: {next_cursor}")
                else:
                    next_cursor = None
                    logger.info("No more pages available")
                
                return markets, next_cursor
            else:
                logger.error("No 'data' field found in response")
        else:
            logger.error(f"Failed to fetch markets: HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching markets page: {str(e)}")
    
    return [], None

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include truly active, non-expired ones.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    
    filtered_markets = []
    for market in markets:
        # Skip if market is closed or not active
        if market.get("closed", False) or not market.get("active", True):
            continue
        
        # Skip if game_start_time is in the past (if available)
        game_start_iso = market.get("game_start_time")
        if game_start_iso and game_start_iso.replace("Z", "+00:00") < now_iso:
            continue
        
        # Skip if end_date_iso is in the past (if available)
        end_date_iso = market.get("end_date_iso")
        if end_date_iso and end_date_iso.replace("Z", "+00:00") < now_iso:
            continue
        
        # Check question for keywords suggesting expired markets
        question = market.get("question", "").lower()
        
        # Skip if question contains past year references (and not future years)
        past_years = ["2020", "2021", "2022", "2023"]
        future_years = ["2024", "2025", "2026"]
        
        if any(year in question for year in past_years) and not any(year in question for year in future_years):
            continue
        
        # This market passes all filters - add it to our list
        filtered_markets.append(market)
    
    logger.info(f"Filtered {len(markets)} markets to {len(filtered_markets)} active, non-expired markets")
    return filtered_markets

def format_market_message(market: Dict[str, Any]) -> str:
    """
    Format a market message for posting to Slack/Discord
    
    Args:
        market: Raw market data from Polymarket API
        
    Returns:
        str: Formatted message text
    """
    # Get basic market info
    market_id = market.get("condition_id", "unknown")
    question = market.get("question", "Unknown question")
    description = market.get("description", "")
    
    # Extract tags for categories
    tags = market.get("tags", [])
    category = tags[0] if tags and len(tags) > 0 else "Uncategorized"
    sub_category = tags[1] if tags and len(tags) > 1 else ""
    
    # Get dates
    end_date_iso = market.get("end_date_iso")
    game_start_time = market.get("game_start_time")
    
    # Format dates if available
    expiry_date = ""
    if end_date_iso:
        try:
            dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
            expiry_date = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception as e:
            logger.warning(f"Error parsing end_date_iso: {e}")
    
    # Format start time if available
    start_time = ""
    if game_start_time:
        try:
            dt = datetime.fromisoformat(game_start_time.replace("Z", "+00:00"))
            start_time = dt.strftime("%Y-%m-%d %H:%M UTC")
        except Exception as e:
            logger.warning(f"Error parsing game_start_time: {e}")
    
    # Get options (outcomes)
    tokens = market.get("tokens", [])
    options_str = ", ".join([token.get("outcome", "Unknown") for token in tokens])
    
    # Format the message with all available information
    message = (
        f"*ACTIVE MARKET - APPROVAL NEEDED*\n\n"
        f"*Question:* {question}\n"
        f"*Market ID:* {market_id}\n"
        f"*Category:* {category}"
    )
    
    if sub_category:
        message += f" > {sub_category}"
    
    message += f"\n*Options:* {options_str}"
    
    if expiry_date:
        message += f"\n*Expiry:* {expiry_date}"
    
    if start_time:
        message += f"\n*Start Time:* {start_time}"
    
    # Add description if available (truncated if too long)
    if description:
        # Truncate if too long
        if len(description) > 300:
            description = description[:297] + "..."
        message += f"\n\n*Description:*\n{description}"
    
    # Add polymarket URL if a slug exists
    slug = market.get("market_slug")
    if slug:
        message += f"\n\n*Polymarket Link:* https://polymarket.com/market/{slug}"
    
    message += "\n\n:white_check_mark: Approve | :x: Reject"
    
    return message

def post_markets_to_slack(markets: List[Dict[str, Any]], max_to_post: int = 5) -> List[Dict[str, Any]]:
    """
    Post markets to Slack for approval.
    
    Args:
        markets: List of market data dictionaries
        max_to_post: Maximum number of markets to post
        
    Returns:
        List[Dict[str, Any]]: List of posted markets with message IDs
    """
    logger.info(f"Posting up to {max_to_post} markets to Slack...")
    
    # Initialize messaging client for Slack
    try:
        messaging_client = MessagingClient(platform="slack")
    except Exception as e:
        logger.error(f"Error initializing messaging client: {str(e)}")
        return []
    
    # Store posted markets with message IDs
    posted_markets = []
    
    # Limit the number of markets to post
    markets_to_post = markets[:max_to_post]
    
    # Post each market to Slack
    for idx, market in enumerate(markets_to_post):
        try:
            # Get market ID and question
            market_id = market.get("condition_id", f"unknown-{idx}")
            question = market.get("question", "Unknown question")
            
            # Format message
            message = format_market_message(market)
            
            # Post to Slack
            message_id = messaging_client.post_message(message)
            
            if message_id:
                # Add reactions for approval/rejection
                messaging_client.add_reactions(message_id, ["white_check_mark", "x"])
                
                # Add to posted markets list
                posted_markets.append({
                    "market_id": market_id,
                    "question": question,
                    "message_id": message_id,
                    "raw_data": market
                })
                
                logger.info(f"Posted market {market_id} to Slack (message ID: {message_id})")
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
            else:
                logger.error(f"Failed to post market {market_id} to Slack")
            
        except Exception as e:
            logger.error(f"Error posting market {idx+1}: {str(e)}")
    
    # Save posted markets to file
    if posted_markets:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(TMP_DIR, f"posted_markets_{timestamp}.json")
        
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "markets_posted": len(posted_markets),
                "markets": [{
                    "market_id": m["market_id"],
                    "question": m["question"],
                    "message_id": m["message_id"]
                } for m in posted_markets]
            }, f, indent=2)
        
        logger.info(f"Saved posted markets to {output_file}")
    
    return posted_markets

def main():
    """
    Main function to run the market fetching process with database tracking.
    """
    logger.info("Starting market fetching with database tracking")
    
    # Create tmp directory if it doesn't exist
    os.makedirs(TMP_DIR, exist_ok=True)
    
    # Initialize the market tracker
    market_tracker = MarketTracker()
    
    # Parameters
    page_size = 50          # Number of markets per page
    max_pages = 4           # Maximum number of pages to fetch
    max_to_post = 5         # Maximum number of new markets to post to Slack
    
    with app.app_context():
        try:
            # Get all processed market IDs from database
            processed_ids = market_tracker.get_processed_market_ids()
            logger.info(f"Found {len(processed_ids)} already processed markets in database")
            
            # Fetch markets with pagination
            all_markets = []
            new_markets = []
            next_cursor = None
            page = 1
            
            while page <= max_pages:
                # Fetch a page of markets
                markets, next_cursor = fetch_markets_page(page_size, next_cursor)
                
                if not markets:
                    logger.warning(f"No markets returned for page {page}")
                    break
                
                all_markets.extend(markets)
                logger.info(f"Fetched page {page} with {len(markets)} markets")
                
                # Break if no more pages
                if not next_cursor:
                    break
                
                # Increment page counter
                page += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
            
            # Filter for active, non-expired markets
            active_markets = filter_active_non_expired_markets(all_markets)
            
            # Filter out already processed markets
            for market in active_markets:
                condition_id = market.get("condition_id")
                if not condition_id:
                    logger.warning("Market missing condition_id, skipping")
                    continue
                
                if condition_id not in processed_ids:
                    logger.info(f"New market found: {condition_id} - {market.get('question')}")
                    new_markets.append(market)
                else:
                    logger.info(f"Market already processed: {condition_id}")
            
            logger.info(f"Found {len(new_markets)} new markets that haven't been processed before")
            
            # Post new markets to Slack
            if new_markets:
                posted_markets = post_markets_to_slack(new_markets, max_to_post)
                
                # Mark posted markets as processed in the database
                for market_info in posted_markets:
                    market_data = market_info["raw_data"]
                    message_id = market_info["message_id"]
                    
                    # Mark as processed in database
                    success = market_tracker.mark_market_as_processed(
                        market_data=market_data,
                        posted=True,
                        message_id=message_id
                    )
                    
                    if success:
                        logger.info(f"Marked market {market_data.get('condition_id')} as processed in database")
                    else:
                        logger.error(f"Failed to mark market {market_data.get('condition_id')} as processed")
                
                logger.info(f"Posted {len(posted_markets)} new markets to Slack")
            else:
                logger.info("No new markets to post")
            
            # Mark all fetched markets as processed (even if not posted)
            markets_marked = 0
            for market in all_markets:
                condition_id = market.get("condition_id")
                if not condition_id or condition_id in processed_ids:
                    continue
                
                # Only mark as processed if not already posted
                already_posted = any(m.get("market_id") == condition_id for m in posted_markets) if 'posted_markets' in locals() else False
                
                if not already_posted:
                    success = market_tracker.mark_market_as_processed(
                        market_data=market,
                        posted=False
                    )
                    if success:
                        markets_marked += 1
            
            logger.info(f"Marked {markets_marked} additional markets as processed (not posted)")
            
            # Summary statistics
            logger.info("\nSummary:")
            logger.info(f"- Total markets fetched: {len(all_markets)}")
            logger.info(f"- Active non-expired markets: {len(active_markets)}")
            logger.info(f"- New markets found: {len(new_markets)}")
            logger.info(f"- Markets posted to Slack: {len(posted_markets) if 'posted_markets' in locals() else 0}")
            logger.info(f"- Additional markets marked as processed: {markets_marked}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error in main process: {str(e)}")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
