"""
Test Post Real Market to Slack

This script fetches a real market from the Polymarket API,
formats it with our enhanced image and date handling,
and posts it to Slack to verify the formatting.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add local path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import utilities
from utils.messaging import format_market_with_images
from utils.slack import post_message_with_blocks

# Polymarket API endpoints - use the same endpoint as the main pipeline
POLYMARKET_API_BASE = "https://clob.polymarket.com"
MARKET_API_ENDPOINT = f"{POLYMARKET_API_BASE}/v1/markets"
EVENT_API_ENDPOINT = f"{POLYMARKET_API_BASE}/v1/events"

def fetch_market_from_api(prefer_multiple: bool = True) -> Optional[Dict[str, Any]]:
    """
    Fetch a single market from the Polymarket API.
    
    Args:
        prefer_multiple: True to prefer multiple-choice markets, False for binary
        
    Returns:
        Market data dictionary or None if fetching failed
    """
    try:
        # Fetch markets from API
        response = requests.get(
            MARKET_API_ENDPOINT,
            params={"_limit": 50, "_sort": "createdAt:DESC"}
        )
        
        if response.status_code != 200:
            logger.error(f"API request failed with status {response.status_code}")
            return None
        
        markets = response.json()
        
        if not markets:
            logger.error("No markets returned from API")
            return None
            
        logger.info(f"Fetched {len(markets)} markets from API")
        
        # Filter for active markets
        active_markets = [
            m for m in markets 
            if m.get("isActive", False) and not m.get("isResolved", False)
        ]
        
        if not active_markets:
            logger.error("No active markets found")
            return None
            
        logger.info(f"Found {len(active_markets)} active markets")
        
        # Find a multi-option market if preferred
        target_market = None
        
        if prefer_multiple:
            # Look for markets with multiple options (non-binary)
            for market in active_markets:
                outcomes = market.get("outcomes", "[]")
                try:
                    if isinstance(outcomes, str):
                        parsed_outcomes = json.loads(outcomes)
                    else:
                        parsed_outcomes = outcomes
                        
                    if isinstance(parsed_outcomes, list) and len(parsed_outcomes) > 2:
                        logger.info(f"Found multi-option market with {len(parsed_outcomes)} options")
                        target_market = market
                        break
                except Exception as e:
                    logger.warning(f"Error parsing outcomes: {e}")
                    continue
                    
        # If no multi-option market found or not preferred, use first binary market
        if not target_market:
            target_market = active_markets[0]
            logger.info("Using binary market")
        
        return target_market
    
    except Exception as e:
        logger.error(f"Error fetching market from API: {e}")
        return None

def prepare_market_for_posting(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare the market data for Slack posting.
    
    This adds the necessary fields expected by our formatter.
    
    Args:
        market_data: Raw market data from API
        
    Returns:
        Processed market data ready for Slack formatting
    """
    # Copy data to avoid modifying original
    data = market_data.copy()
    
    # Check for multiple options
    outcomes = data.get("outcomes", "[]")
    try:
        if isinstance(outcomes, str):
            parsed_outcomes = json.loads(outcomes)
        else:
            parsed_outcomes = outcomes
            
        is_multiple = isinstance(parsed_outcomes, list) and len(parsed_outcomes) > 2
    except Exception:
        is_multiple = False
    
    # Add flags for event classification
    data["is_event"] = is_multiple
    data["is_multiple_option"] = is_multiple
    
    # Extract event ID and name if present
    if "events" in data and isinstance(data["events"], list) and len(data["events"]) > 0:
        event = data["events"][0]
        data["event_id"] = event.get("id")
        data["event_name"] = event.get("title")
    
    # Ensure category is set
    data["category"] = data.get("category", "uncategorized")
    
    # Additional preprocessing
    if "expiry_time" not in data and "endDate" in data:
        data["expiry_time"] = data["endDate"]
    
    return data

def post_real_market() -> bool:
    """
    Fetch a real market and post it to Slack.
    
    Returns:
        True if successful, False otherwise
    """
    # Fetch a market (try for multiple-choice first)
    market_data = fetch_market_from_api(prefer_multiple=True)
    
    if not market_data:
        logger.error("No market data available")
        return False
    
    # Log what we found
    logger.info(f"Fetched market: {market_data.get('question', 'Unknown')}")
    
    # Prepare for posting
    processed_market = prepare_market_for_posting(market_data)
    
    # Format message
    message, blocks = format_market_with_images(processed_market)
    
    # Post to Slack
    result = post_message_with_blocks(message, blocks)
    
    return result is not None

def main():
    """Main function to run the test."""
    try:
        from main import app
        with app.app_context():
            success = post_real_market()
            return 0 if success else 1
    except ImportError:
        # If we can't import app, just run without context
        success = post_real_market()
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())