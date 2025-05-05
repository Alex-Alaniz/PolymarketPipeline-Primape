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
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from models import db, ProcessedMarket
from filter_active_markets import fetch_markets, filter_active_markets
from utils.messaging import post_markets_to_slack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_tracker")

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include truly active, non-expired ones.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    # Use the filter_active_markets function from the other module
    return filter_active_markets(markets)

def filter_new_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include those not already in the database.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: List of new markets
    """
    if not markets:
        return []
        
    # Get condition IDs of markets already in database
    existing_ids = set()
    
    # Import Flask app here to avoid circular imports
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        try:
            existing_markets = ProcessedMarket.query.all()
            existing_ids = {market.condition_id for market in existing_markets}
            
            logger.info(f"Found {len(existing_ids)} existing markets in database")
            
        except Exception as e:
            logger.error(f"Error fetching existing markets: {str(e)}")
    
    # Filter out markets that already exist in database
    new_markets = [
        market for market in markets 
        if market.get("conditionId") not in existing_ids
    ]
    
    logger.info(f"Filtered to {len(new_markets)} new markets")
    return new_markets

def track_markets_in_db(markets: List[Dict[str, Any]]) -> List[ProcessedMarket]:
    """
    Add markets to the database for tracking.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[ProcessedMarket]: List of created database entries
    """
    if not markets:
        return []
    
    # Create a list to track condition IDs
    condition_ids = []
    condition_id_to_data = {}
    
    # Extract condition IDs and prepare data mapping
    for market_data in markets:
        condition_id = market_data.get("conditionId")
        
        if not condition_id:
            logger.warning(f"Market missing conditionId: {market_data.get('question', 'Unknown')}")
            continue
            
        condition_ids.append(condition_id)
        condition_id_to_data[condition_id] = market_data
    
    if not condition_ids:
        logger.warning("No valid condition IDs found in market data")
        return []
    
    # The function should be called within an app context
    # Get existing markets in a single query
    existing_markets = {
        market.condition_id: market for market in 
        ProcessedMarket.query.filter(ProcessedMarket.condition_id.in_(condition_ids)).all()
    }
    
    logger.info(f"Found {len(existing_markets)} existing markets in database")
    
    tracked_markets = []
    now = datetime.utcnow()
    
    # Process each market
    for condition_id, market_data in condition_id_to_data.items():
        if condition_id in existing_markets:
            # Update existing record
            market = existing_markets[condition_id]
            market.last_processed = now
            market.process_count += 1
            
            if market.raw_data != market_data:
                market.raw_data = market_data
                
            tracked_markets.append(market)
            logger.debug(f"Updated existing market: {condition_id}")
            
        else:
            # Create new record
            market = ProcessedMarket(
                condition_id=condition_id,
                question=market_data.get("question", "Unknown"),
                raw_data=market_data
            )
            
            db.session.add(market)
            tracked_markets.append(market)
            logger.debug(f"Added new market: {condition_id}")
    
    # Save changes
    db.session.commit()
    
    logger.info(f"Tracked {len(tracked_markets)} markets in database")
    return tracked_markets

def format_market_message(market: Dict[str, Any]) -> str:
    """
    Format a market message for posting to Slack/Discord
    
    Args:
        market: Raw market data from Polymarket API
        
    Returns:
        str: Formatted message text
    """
    # Extract relevant fields
    question = market.get("question", "Unknown")
    end_date = market.get("endDate", "Unknown")
    category = market.get("fetched_category", "general")
    
    # Format message
    message = f"""
*New Market for Approval*

*Question:* {question}
*Category:* {category}
*End Date:* {end_date}

React with :white_check_mark: to approve or :x: to reject.
"""
    
    return message

def post_new_markets(markets: List[Dict[str, Any]], max_to_post: int = 5) -> List[ProcessedMarket]:
    """
    Post new markets to Slack for approval and update the database.
    
    Args:
        markets: List of market data dictionaries
        max_to_post: Maximum number of markets to post
        
    Returns:
        List[ProcessedMarket]: List of updated database entries
    """
    if not markets:
        return []
    
    # Import Flask app here to avoid circular imports
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # Track markets in database within the app context
        tracked_markets = track_markets_in_db(markets)
        
        # Query directly from the database to ensure we have attached session objects
        condition_ids = [market.condition_id for market in tracked_markets]
        tracked_markets = ProcessedMarket.query.filter(
            ProcessedMarket.condition_id.in_(condition_ids)
        ).all()
        
        # Only process markets that haven't been posted yet
        to_post = [
            market for market in tracked_markets 
            if not market.posted and market.raw_data is not None
        ]
        
        if not to_post:
            logger.info("No new markets to post")
            return []
            
        # Limit number of markets to post
        to_post = to_post[:max_to_post]
        
        # Post to Slack
        logger.info(f"Posting {len(to_post)} new markets to Slack")
        
        # Extract raw data for posting
        market_data_list = [market.raw_data for market in to_post]
        
        # Post to Slack
        posted_results = post_markets_to_slack(market_data_list, max_to_post)
        
        # Update database records with message IDs
        posted_markets = []
        
        for i, (raw_data, message_id) in enumerate(posted_results):
            if i >= len(to_post):
                break
                
            market = to_post[i]
            
            if message_id:
                market.posted = True
                market.message_id = message_id
                posted_markets.append(market)
                logger.info(f"Posted market {market.condition_id} to Slack")
            else:
                logger.warning(f"Failed to post market {market.condition_id} to Slack")
        
        # Save changes
        db.session.commit()
        
        logger.info(f"Posted {len(posted_markets)} markets to Slack")
        return posted_markets

def main():
    """
    Main function to run the market fetching process with database tracking.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # Fetch markets from Polymarket API
        markets = fetch_markets()
        
        if not markets:
            logger.error("Failed to fetch markets from Polymarket API")
            return 1
            
        logger.info(f"Fetched {len(markets)} markets from Polymarket API")
        
        # Filter active markets
        active_markets = filter_active_non_expired_markets(markets)
        
        if not active_markets:
            logger.error("No active markets found")
            return 1
            
        logger.info(f"Filtered to {len(active_markets)} active markets")
        
        # Filter new markets
        new_markets = filter_new_markets(active_markets)
        
        if not new_markets:
            logger.info("No new markets found")
            return 0
            
        logger.info(f"Found {len(new_markets)} new markets")
        
        # Post new markets to Slack
        posted_markets = post_new_markets(new_markets)
        
        logger.info(f"Posted {len(posted_markets)} markets to Slack")
        
        # Success!
        return 0

if __name__ == "__main__":
    sys.exit(main())