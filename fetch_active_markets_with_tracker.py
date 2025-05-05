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
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import or_

from models import db, ProcessedMarket
from filter_active_markets import fetch_markets, filter_active_markets
from utils.messaging import post_markets_to_slack

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("market_fetcher")

# Create data directory if it doesn't exist
DATA_DIR = os.path.join(os.getcwd(), "data")
os.makedirs(DATA_DIR, exist_ok=True)

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include truly active, non-expired ones.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    return filter_active_markets(markets)

def filter_new_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include those not already in the database.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: List of new markets
    """
    new_markets = []
    condition_ids = [market.get("conditionId") for market in markets if market.get("conditionId")]
    
    if not condition_ids:
        return []
    
    # Find existing condition IDs in the database
    existing_markets = ProcessedMarket.query.filter(
        ProcessedMarket.condition_id.in_(condition_ids)
    ).all()
    
    existing_ids = set(market.condition_id for market in existing_markets)
    
    # Filter out markets that already exist in the database
    for market in markets:
        condition_id = market.get("conditionId")
        if condition_id and condition_id not in existing_ids:
            new_markets.append(market)
    
    logger.info(f"Filtered {len(markets)} markets to {len(new_markets)} new markets")
    return new_markets

def track_markets_in_db(markets: List[Dict[str, Any]]) -> List[ProcessedMarket]:
    """
    Add markets to the database for tracking.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[ProcessedMarket]: List of created database entries
    """
    created_entries = []
    
    for market_data in markets:
        condition_id = market_data.get("conditionId")
        
        if not condition_id:
            logger.warning(f"Skipping market without condition ID: {market_data.get('id')}")
            continue
        
        try:
            # Create a new database entry
            market_entry = ProcessedMarket(
                condition_id=condition_id,
                question=market_data.get("question"),
                first_seen=datetime.utcnow(),
                last_processed=datetime.utcnow(),
                process_count=1,
                posted=False,
                raw_data=market_data  # Store the complete raw data
            )
            
            db.session.add(market_entry)
            created_entries.append(market_entry)
            
        except Exception as e:
            logger.error(f"Error adding market to database: {str(e)}")
    
    # Commit all changes
    try:
        db.session.commit()
        logger.info(f"Added {len(created_entries)} markets to the database")
    except Exception as e:
        logger.error(f"Error committing to database: {str(e)}")
        db.session.rollback()
    
    return created_entries

def format_market_message(market: Dict[str, Any]) -> str:
    """
    Format a market message for posting to Slack/Discord
    
    Args:
        market: Raw market data from Polymarket API
        
    Returns:
        str: Formatted message text
    """
    # Extract market details
    question = market.get("question", "N/A")
    condition_id = market.get("conditionId", "N/A")
    end_date = market.get("endDate", "N/A")
    outcomes = market.get("outcomes", "N/A")
    
    # Format the message
    message = f"**New Market:** {question}\n"
    message += f"**Condition ID:** {condition_id}\n"
    message += f"**End Date:** {end_date}\n"
    message += f"**Outcomes:** {outcomes}\n"
    
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
    # First track the markets in the database
    db_entries = track_markets_in_db(markets)
    
    if not db_entries:
        return []
    
    # Limit the number of markets to post
    markets_to_post = [entry.raw_data for entry in db_entries[:max_to_post]]
    
    # Post markets to Slack
    posted_markets = post_markets_to_slack(markets_to_post, max_to_post)
    
    # Update the database with posted status and message IDs
    posted_condition_ids = []
    for posted_market in posted_markets:
        condition_id = posted_market.get("conditionId")
        message_id = posted_market.get("message_id")
        
        if condition_id and message_id:
            posted_condition_ids.append(condition_id)
            
            # Update the database entry
            db_entry = next((entry for entry in db_entries if entry.condition_id == condition_id), None)
            if db_entry:
                db_entry.posted = True
                db_entry.message_id = message_id
    
    # Commit changes
    try:
        db.session.commit()
        logger.info(f"Updated {len(posted_condition_ids)} markets with posted status")
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        db.session.rollback()
    
    # Return the updated database entries
    return [entry for entry in db_entries if entry.condition_id in posted_condition_ids]

def main():
    """
    Main function to run the market fetching process with database tracking.
    """
    logger.info("Starting market fetcher with database tracking")
    
    # Import Flask app to get application context
    from main import app
    
    try:
        # Fetch markets from Polymarket API
        markets = fetch_markets(limit=100)
        
        if not markets:
            logger.error("No markets fetched. Exiting.")
            return 1
        
        logger.info(f"Fetched {len(markets)} markets from Polymarket API")
        
        # Filter active, non-expired markets
        active_markets = filter_active_non_expired_markets(markets)
        logger.info(f"Found {len(active_markets)} active, non-expired markets")
        
        # Database operations need application context
        with app.app_context():
            # Filter out markets already in the database
            new_markets = filter_new_markets(active_markets)
            logger.info(f"Found {len(new_markets)} new markets")
            
            if not new_markets:
                logger.info("No new markets to process. Exiting.")
                return 0
            
            # Post new markets to Slack for approval
            posted_markets = post_new_markets(new_markets, max_to_post=5)
            logger.info(f"Posted {len(posted_markets)} markets to Slack for approval")
        
        logger.info("Market fetching complete")
        return 0
        
    except Exception as e:
        logger.error(f"Error in market fetcher: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
