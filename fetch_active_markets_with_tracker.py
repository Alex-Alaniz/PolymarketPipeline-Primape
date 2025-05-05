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
from filter_active_markets import fetch_markets, transform_markets, filter_active_markets
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
    
    # Log markets received for filtering
    logger.info(f"Filtering {len(markets)} markets")
    multi_count = sum(1 for m in markets if m.get("is_multiple_option", False))
    logger.info(f"Received {multi_count} multiple-option markets to filter")
    
    # For debugging, log the first few markets
    for i, market in enumerate(markets[:3]):
        logger.info(f"Market {i+1} to filter:")
        logger.info(f"  ID: {market.get('id')}")
        logger.info(f"  Question: {market.get('question', 'Unknown')}")
        logger.info(f"  Type: {'Multiple-option' if market.get('is_multiple_option', False) else 'Binary'}")
        if market.get('is_multiple_option', False):
            # Parse outcomes which come as a JSON string
            outcomes_raw = market.get("outcomes", "[]")
            outcomes = []
            try:
                if isinstance(outcomes_raw, str):
                    import json
                    outcomes = json.loads(outcomes_raw)
                else:
                    outcomes = outcomes_raw
                logger.info(f"  Options ({len(outcomes)}): {outcomes}")
            except Exception as e:
                logger.error(f"Error parsing outcomes: {str(e)}")
        
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
    new_markets = []
    for market in markets:
        # For multiple-option markets, use the group ID
        if market.get("is_multiple_option"):
            # Use the group ID as the unique identifier
            market_id = market.get("id")
            logger.info(f"Checking multiple-option market: {market.get('question')} with ID: {market_id}")
            if market_id not in existing_ids:
                new_markets.append(market)
                logger.info(f"  Added as new multiple-option market")
            else:
                logger.info(f"  Skipped as existing multiple-option market")
        else:
            # For binary markets, use the condition ID
            condition_id = market.get("conditionId")
            logger.info(f"Checking binary market: {market.get('question')} with ID: {condition_id}")
            if condition_id not in existing_ids:
                new_markets.append(market)
                logger.info(f"  Added as new binary market")
            else:
                logger.info(f"  Skipped as existing binary market")
    
    # Log results
    multi_count_after = sum(1 for m in new_markets if m.get("is_multiple_option", False))
    logger.info(f"Filtered to {len(new_markets)} new markets, including {multi_count_after} multiple-option markets")
    
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
    
    # Create a list to track market IDs
    # For binary markets, we'll use conditionId
    # For multiple-option markets, we'll use the group ID
    market_ids = []
    market_id_to_data = {}
    
    # Extract market IDs and prepare data mapping
    for market_data in markets:
        # Handle multiple-option markets
        if market_data.get("is_multiple_option"):
            market_id = market_data.get("id")
            if not market_id:
                logger.warning(f"Multiple-option market missing id: {market_data.get('question', 'Unknown')}")
                continue
            
            market_ids.append(market_id)
            market_id_to_data[market_id] = market_data
            logger.debug(f"Processing multiple-option market with id: {market_id}")
        else:
            # Handle binary markets
            condition_id = market_data.get("conditionId")
            if not condition_id:
                logger.warning(f"Binary market missing conditionId: {market_data.get('question', 'Unknown')}")
                continue
            
            market_ids.append(condition_id)
            market_id_to_data[condition_id] = market_data
            logger.debug(f"Processing binary market with conditionId: {condition_id}")
    
    if not market_ids:
        logger.warning("No valid market IDs found in market data")
        return []
    
    # The function should be called within an app context
    # Get existing markets in a single query
    existing_markets = {
        market.condition_id: market for market in 
        ProcessedMarket.query.filter(ProcessedMarket.condition_id.in_(market_ids)).all()
    }
    
    logger.info(f"Found {len(existing_markets)} existing markets in database")
    
    tracked_markets = []
    now = datetime.utcnow()
    
    # Process each market
    for market_id, market_data in market_id_to_data.items():
        if market_id in existing_markets:
            # Update existing record
            market = existing_markets[market_id]
            market.last_processed = now
            market.process_count += 1
            
            if market.raw_data != market_data:
                market.raw_data = market_data
                
            tracked_markets.append(market)
            logger.debug(f"Updated existing market: {market_id}")
            
        else:
            # Create new record
            market = ProcessedMarket(
                condition_id=market_id,  # For multi-option, this is the group ID
                question=market_data.get("question", "Unknown"),
                raw_data=market_data
            )
            
            db.session.add(market)
            tracked_markets.append(market)
            logger.debug(f"Added new market: {market_id}")
    
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
    is_multiple = market.get("is_multiple_option", False)
    
    # Extract options
    options_text = ""
    outcomes_raw = market.get("outcomes", "[]")
    outcomes = []
    
    # Parse outcomes which come as a JSON string
    try:
        if isinstance(outcomes_raw, str):
            import json
            outcomes = json.loads(outcomes_raw)
        else:
            outcomes = outcomes_raw
    except Exception as e:
        logger.error(f"Error parsing outcomes: {str(e)}")
        
    if outcomes:
        options_text = "*Options:*\n"
        
        # Handle different formats of options
        if is_multiple:
            # Multiple-option market (consolidated)
            for i, option in enumerate(outcomes):
                options_text += f"  {i+1}. {option}\n"
        else:
            # Binary market (Yes/No)
            for i, option in enumerate(outcomes):
                options_text += f"  {i+1}. {option}\n"
    
    # Add market type
    market_type = "Multiple-choice Market" if is_multiple else "Binary Market (Yes/No)"
    
    # Format message
    message = f"""
*New Market for Approval*

*Question:* {question}
*Category:* {category}
*Type:* {market_type}
*End Date:* {end_date}
{options_text}
React with :white_check_mark: to approve or :x: to reject.
"""
    
    return message

def post_new_markets(markets: List[Dict[str, Any]], max_to_post: int = 20) -> List[ProcessedMarket]:
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
        market_data_list = []
        for market in to_post:
            raw_data = market.raw_data
            if raw_data:
                # Log details of the raw data for debugging
                logger.info(f"Preparing to post market: {raw_data.get('question', 'Unknown')}")
                logger.info(f"  - Type: {('Multiple-choice' if raw_data.get('is_multiple_option', False) else 'Binary')}")
                if raw_data.get('is_multiple_option', False):
                    logger.info(f"  - ID: {raw_data.get('id')}")
                    # Parse outcomes which come as a JSON string
                    outcomes_raw = raw_data.get("outcomes", "[]")
                    outcomes = []
                    try:
                        if isinstance(outcomes_raw, str):
                            outcomes = json.loads(outcomes_raw)
                        else:
                            outcomes = outcomes_raw
                        logger.info(f"  - Options ({len(outcomes)}): {outcomes}")
                    except Exception as e:
                        logger.error(f"Error parsing outcomes: {str(e)}")
                market_data_list.append(raw_data)
        
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
        
        # Transform markets to consolidate multi-option markets
        logger.info("Transforming markets")
        transformed_markets = transform_markets(active_markets)
        logger.info(f"Transformed into {len(transformed_markets)} markets")
        
        # Filter new markets
        new_markets = filter_new_markets(transformed_markets)
        
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