#!/usr/bin/env python3

"""
Test script for fetching active markets from Polymarket API and posting them to Slack.

This script demonstrates:
1. How to fetch truly active markets from Polymarket API
2. How to format them properly for Slack
3. How to post them to a Slack channel for approval/rejection
"""

import os
import json
import logging
import sys
import requests
from datetime import datetime, timezone
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

logger = logging.getLogger("fetch_and_post")

def fetch_active_markets(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Fetch active markets from Polymarket API.
    
    Args:
        limit: Maximum number of markets to fetch
        
    Returns:
        List of market data dictionaries
    """
    logger.info(f"Fetching up to {limit} active markets from Polymarket API...")
    
    # API endpoint with optimal parameters based on testing
    url = f"https://clob.polymarket.com/markets?accepting_orders=true&limit={limit}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        # Make the request
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "data" in data and isinstance(data["data"], list):
                markets = data["data"]
                logger.info(f"Successfully fetched {len(markets)} markets from Polymarket API")
                
                # Save raw data for reference
                os.makedirs(TMP_DIR, exist_ok=True)
                raw_data_path = os.path.join(TMP_DIR, "polymarket_raw_data.json")
                with open(raw_data_path, 'w') as f:
                    json.dump({"markets": markets}, f, indent=2)
                
                logger.info(f"Raw market data saved to {raw_data_path}")
                
                return markets
            else:
                logger.error("No 'data' field found in response")
        else:
            logger.error(f"Failed to fetch markets: HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
    
    return []

def transform_market_for_apechain(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform a Polymarket market to ApeChain format.
    
    Args:
        market: Raw market data from Polymarket API
        
    Returns:
        Transformed market data for ApeChain
    """
    try:
        # Extract market ID
        market_id = market.get("condition_id", "")
        if not market_id:
            logger.warning("Market missing condition_id")
            return {}
        
        # Extract question
        question = market.get("question", "Unknown question")
        if not question:
            logger.warning(f"Market {market_id} missing question")
            return {}
        
        # Extract description
        description = market.get("description", "")
        
        # Extract end date
        end_date_iso = market.get("end_date_iso")
        expiry = None
        if end_date_iso:
            try:
                # Convert ISO string to timestamp
                dt = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                expiry = int(dt.timestamp())
            except Exception as e:
                logger.warning(f"Error parsing end_date_iso: {e}")
        
        # Extract options (outcomes)
        tokens = market.get("tokens", [])
        options = []
        for token in tokens:
            option_name = token.get("outcome")
            if option_name:
                options.append({"name": option_name})
        
        # If no options found, default to binary Yes/No
        if not options:
            options = [{"name": "Yes"}, {"name": "No"}]
        
        # Determine category based on tags or defaults
        tags = market.get("tags", [])
        category = "Other"
        sub_category = ""
        
        if tags and len(tags) > 0:
            # First tag is usually the main category
            category = tags[0]
            # Second tag (if present) can be the subcategory
            if len(tags) > 1:
                sub_category = tags[1]
        
        # Build transformed market data
        transformed = {
            "id": market_id,
            "question": question,
            "description": description,
            "category": category,
            "sub_category": sub_category,
            "expiry": expiry,
            "options": options,
            "original_market_id": market_id
        }
        
        return transformed
    
    except Exception as e:
        logger.error(f"Error transforming market: {str(e)}")
        return {}

def format_market_message(market: Dict[str, Any]) -> str:
    """
    Format a market message for posting to Slack/Discord
    
    Args:
        market: Transformed market data
        
    Returns:
        str: Formatted message text
    """
    market_id = market.get("id", "unknown")
    question = market.get("question", "Unknown question")
    description = market.get("description", "")
    category = market.get("category", "Uncategorized")
    sub_category = market.get("sub_category", "")
    expiry = market.get("expiry", 0)
    
    # Format expiry date if available
    expiry_date = ""
    if expiry:
        try:
            # Convert milliseconds to seconds if needed
            if expiry > 10000000000:  # Likely milliseconds
                expiry = expiry / 1000
            expiry_date = datetime.fromtimestamp(expiry, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except Exception as e:
            logger.warning(f"Error formatting expiry date: {e}")
            expiry_date = "Unknown"
    
    # Get options (binary or multi-option)
    options = market.get("options", [])
    if not options:
        options_str = "Yes/No"
    else:
        options_str = ", ".join([opt.get("name", str(i)) for i, opt in enumerate(options)])
    
    # Format the message
    message = (
        f"*MARKET APPROVAL NEEDED*\n\n"
        f"*Question:* {question}\n"
        f"*Market ID:* {market_id}\n"
        f"*Category:* {category}"
    )
    
    if sub_category:
        message += f" > {sub_category}"
    
    message += f"\n*Options:* {options_str}"
    
    if expiry_date:
        message += f"\n*Expiry:* {expiry_date}"
    
    # Add description if available (truncated if too long)
    if description:
        # Truncate if too long
        if len(description) > 300:
            description = description[:297] + "..."
        message += f"\n\n*Description:*\n{description}"
    
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
    logger.info(f"Posting up to {max_markets} markets to Slack...")
    
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
    for idx, raw_market in enumerate(markets_to_post):
        try:
            # Transform market to ApeChain format
            market = transform_market_for_apechain(raw_market)
            
            if not market:
                logger.warning(f"Skipping market {idx+1} - transformation failed")
                continue
            
            # Get market ID and question
            market_id = market.get("id", f"unknown-{idx}")
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
        output_file = os.path.join(TMP_DIR, f"posted_markets_{timestamp}.json")
        
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
    logger.info("Starting fetch and post test")
    
    # Fetch active markets from Polymarket API
    markets = fetch_active_markets(limit=10)
    
    if not markets:
        logger.error("No markets fetched, cannot proceed")
        return False
    
    # Post markets to Slack
    posted_markets = post_markets_to_slack(markets, max_markets=5)
    
    # Summary
    logger.info("\nTest Summary:")
    logger.info(f"- Markets fetched: {len(markets)}")
    logger.info(f"- Markets posted to Slack: {len(posted_markets)}")
    
    return len(posted_markets) > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
