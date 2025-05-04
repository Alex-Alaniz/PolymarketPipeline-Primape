#!/usr/bin/env python3

"""
Test script for fetching only truly active, non-expired markets from Polymarket API and posting to Slack.

This script applies more stringent filtering to find only markets that:
1. Are accepting orders
2. Have not closed or archived
3. Have an end date in the future
"""

import os
import json
import logging
import sys
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

# Set up path to find project modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import project modules
from utils.messaging import MessagingClient
from config import TMP_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("active_markets")

def fetch_and_filter_active_markets(limit: int = 50, max_return: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch and filter active markets from Polymarket API.
    
    Args:
        limit: Maximum number of markets to fetch from API
        max_return: Maximum number of markets to return after filtering
        
    Returns:
        List of active, non-expired market data dictionaries
    """
    logger.info(f"Fetching up to {limit} markets from Polymarket API and filtering for truly active ones...")
    
    # API endpoint - focus on accepting_orders=true parameter
    url = f"https://clob.polymarket.com/markets?accepting_orders=true&limit={limit}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        # Get current time for filtering by date
        now = datetime.now(timezone.utc)
        future_date = now + timedelta(days=30)  # Looking for markets expiring at least 30 days ahead
        now_iso = now.isoformat()
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "data" in data and isinstance(data["data"], list):
                all_markets = data["data"]
                logger.info(f"Successfully fetched {len(all_markets)} markets with accepting_orders=true")
                
                # Filter markets for truly active ones
                active_markets = []
                
                for market in all_markets:
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
                    
                    # Skip if question contains past year references
                    past_years = ["2020", "2021", "2022", "2023"]
                    if any(year in question for year in past_years):
                        continue
                    
                    # Skip if question contains past events
                    past_events = ["super bowl", "world cup", "election"]
                    if any(event in question for event in past_events):
                        # Extra check - if it has 2024 or 2025, keep it
                        if not any(year in question for year in ["2024", "2025"]):
                            continue
                    
                    # This market passes all filters - add it to our list
                    active_markets.append(market)
                    
                    # Break if we have reached our target number of markets
                    if len(active_markets) >= max_return:
                        break
                
                logger.info(f"After filtering: {len(active_markets)} truly active, non-expired markets found")
                
                # Save active markets to file
                if active_markets:
                    os.makedirs(TMP_DIR, exist_ok=True)
                    active_data_path = os.path.join(TMP_DIR, "active_markets.json")
                    with open(active_data_path, 'w') as f:
                        json.dump({"markets": active_markets}, f, indent=2)
                    
                    logger.info(f"Active markets saved to {active_data_path}")
                
                return active_markets
            else:
                logger.error("No 'data' field found in response")
        else:
            logger.error(f"Failed to fetch markets: HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
    
    return []

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

def post_markets_to_slack(markets: List[Dict[str, Any]], max_markets: int = 5) -> List[Dict[str, Any]]:
    """
    Post markets to Slack for approval.
    
    Args:
        markets: List of market data dictionaries
        max_markets: Maximum number of markets to post
        
    Returns:
        List of posted markets with message IDs
    """
    logger.info(f"Posting up to {max_markets} active markets to Slack...")
    
    # Initialize messaging client for Slack
    try:
        messaging_client = MessagingClient(platform="slack")
    except Exception as e:
        logger.error(f"Error initializing messaging client: {e}")
        return []
    
    # Store posted markets with message IDs
    posted_markets = []
    
    # Limit the number of markets to post
    markets_to_post = markets[:max_markets]
    
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
                    "status": "posted"
                })
                
                logger.info(f"Posted market {market_id} to Slack (message ID: {message_id})")
            else:
                logger.error(f"Failed to post market {market_id} to Slack")
            
        except Exception as e:
            logger.error(f"Error posting market {idx+1}: {str(e)}")
    
    # Save posted markets to file
    if posted_markets:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(TMP_DIR, f"active_posted_{timestamp}.json")
        
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "markets_posted": len(posted_markets),
                "markets": posted_markets
            }, f, indent=2)
        
        logger.info(f"Saved posted markets to {output_file}")
    
    return posted_markets

def main():
    """
    Main function to run the test.
    """
    logger.info("Starting active markets fetch and post test")
    
    # Fetch active markets from Polymarket API
    markets = fetch_and_filter_active_markets(limit=100, max_return=5)
    
    if not markets:
        logger.error("No active markets found, cannot proceed")
        return False
    
    # Post markets to Slack
    posted_markets = post_markets_to_slack(markets, max_markets=5)
    
    # Summary
    logger.info("\nTest Summary:")
    logger.info(f"- Active markets found: {len(markets)}")
    logger.info(f"- Markets posted to Slack: {len(posted_markets)}")
    
    return len(posted_markets) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
