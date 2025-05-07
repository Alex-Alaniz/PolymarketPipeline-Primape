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
from utils.messaging import post_markets_to_slack, format_market_with_images

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
    
    # Use event_category ONLY when available, otherwise leave blank
    category = market.get("event_category", "")
    
    is_multiple = market.get("is_multiple_option", False)
    
    # Extract options
    options_text = ""
    outcomes_raw = market.get("outcomes", "[]")
    outcomes = []
    
    # Parse outcomes which come as a JSON string
    try:
        if isinstance(outcomes_raw, str):
            # json is already imported at the top of the file
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
    
    # First, check how many multi-option markets we have to process
    multi_option_count = sum(1 for m in markets if m.get('is_multiple_option', False))
    logger.info(f"Found {multi_option_count} multi-option markets to process")
    
    # Log the first few multi-option markets for debugging
    for i, market in enumerate(markets):
        if market.get('is_multiple_option', False) and i < 3:  # Only log the first 3 for brevity
            logger.info(f"Multi-option market {i+1} before DB tracking:")
            logger.info(f"  - ID: {market.get('id')}")
            logger.info(f"  - Question: {market.get('question', 'Unknown')}")
            # Log the options
            outcomes_raw = market.get("outcomes", "[]")
            try:
                if isinstance(outcomes_raw, str):
                    outcomes = json.loads(outcomes_raw)
                else:
                    outcomes = outcomes_raw
                logger.info(f"  - Options ({len(outcomes)}): {list(set(outcomes))}")
            except Exception as e:
                logger.error(f"Error parsing outcomes: {str(e)}")
    
    # Import Flask app here to avoid circular imports
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # IMPORTANT CHANGE: Track ALL markets in database with posted=False initially
        # This ensures all markets are tracked, even if they aren't posted in this batch
        tracked_markets = track_markets_in_db(markets)
        
        # Explicitly set all tracked markets to posted=False initially
        for market in tracked_markets:
            market.posted = False
            market.message_id = None
        
        # Save this change before proceeding
        db.session.commit()
        
        # Track how many multi-option markets were successfully tracked
        multi_option_tracked = sum(1 for m in tracked_markets 
                                  if m.raw_data and m.raw_data.get('is_multiple_option', False))
        logger.info(f"Successfully tracked {multi_option_tracked} multi-option markets in database")
        
        # Query directly from the database to ensure we have attached session objects
        condition_ids = [market.condition_id for market in tracked_markets]
        if not condition_ids:
            logger.warning("No condition IDs found after tracking markets")
            return []
            
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
        
        # Check how many multi-option markets we have to post    
        multi_option_to_post = sum(1 for m in to_post 
                                  if m.raw_data and m.raw_data.get('is_multiple_option', False))
        logger.info(f"Found {multi_option_to_post} multi-option markets to post to Slack")
        
        # IMPORTANT CHANGE: Count total markets to know how many remain unposted
        total_markets = len(to_post)
        
        # Limit number of markets to post
        to_post = to_post[:max_to_post]
        
        # Report how many markets will remain unposted for future batches
        markets_for_future = total_markets - len(to_post)
        logger.info(f"Posting {len(to_post)} markets now, {markets_for_future} markets remaining for future batches")
        
        # Post to Slack
        logger.info(f"Posting {len(to_post)} new markets to Slack")
        
        # Extract raw data for posting - this is crucial to preserve the multi-option structure
        market_data_list = []
        for market in to_post:
            raw_data = market.raw_data
            if raw_data:
                is_multiple = raw_data.get('is_multiple_option', False)
                
                # Log details of the raw data for debugging
                logger.info(f"Preparing to post market: {raw_data.get('question', 'Unknown')}")
                logger.info(f"  - Type: {('Multiple-choice' if is_multiple else 'Binary')}")
                logger.info(f"  - ID: {raw_data.get('id') if is_multiple else raw_data.get('conditionId')}")
                
                # Clean up duplicate options for multi-option markets
                if is_multiple:
                    outcomes_raw = raw_data.get("outcomes", "[]")
                    outcomes = []
                    try:
                        if isinstance(outcomes_raw, str):
                            outcomes = json.loads(outcomes_raw)
                        else:
                            outcomes = outcomes_raw
                            
                        # Remove duplicates while preserving order
                        unique_outcomes = []
                        seen = set()
                        for outcome in outcomes:
                            if outcome not in seen:
                                seen.add(outcome)
                                unique_outcomes.append(outcome)
                                
                        # Save back to raw_data
                        raw_data["outcomes"] = json.dumps(unique_outcomes)
                        logger.info(f"  - Options ({len(unique_outcomes)}): {unique_outcomes}")
                    except Exception as e:
                        logger.error(f"Error parsing outcomes: {str(e)}")
                
                # Add to list
                market_data_list.append(raw_data)
        
        # Post directly to Slack, using utils.messaging format_market_with_images
        # Import the function from utils.messaging
        from utils.messaging import format_market_with_images
        
        # Define a custom formatter function to use with post_markets_to_slack
        def format_market_message(market):
            """
            Custom formatter for raw market data with rich image support
            
            This uses the enhanced format_market_with_images function from utils.messaging
            to properly display event images and option icons.
            """
            # IMPORTANT: Remove pre-categorization - all markets should start uncategorized
            # If event_category is in the market data, save it in a different field for later
            if 'event_category' in market:
                market['original_category'] = market['event_category']
                market['event_category'] = 'uncategorized'
            if 'category' in market:
                market['original_category'] = market['category']
                market['category'] = 'uncategorized'
            
            # Check if this is a multi-option market (event)
            is_event = market.get('is_multiple_option', False)
            market['is_event'] = is_event
            
            # Make sure we have the expiry date - look in various fields
            if 'endDate' in market:
                market['expiry_time'] = market['endDate']
            elif 'end_date' in market:
                market['expiry_time'] = market['end_date']
            elif 'expiryTime' in market:
                market['expiry_time'] = market['expiryTime']
                
            # Process option images
            option_images = {}
            if is_event:
                # For multi-option markets, get option images
                outcomes_raw = market.get("outcomes", "[]")
                try:
                    if isinstance(outcomes_raw, str):
                        outcomes = json.loads(outcomes_raw)
                    else:
                        outcomes = outcomes_raw
                    
                    logger.info(f"Processing multi-option market with {len(outcomes)} options")
                    
                    # Extract option images from the market data
                    for option in outcomes:
                        option_key = str(option)
                        if 'option_images' in market and option_key in market['option_images']:
                            option_images[option_key] = market['option_images'][option_key]
                            logger.info(f"Found image for option: {option_key}")
                    
                    # Save option market IDs if available
                    option_market_ids = {}
                    if 'option_market_ids' in market:
                        option_market_ids = market['option_market_ids']
                    market['option_market_ids'] = option_market_ids
                        
                except Exception as e:
                    logger.error(f"Error processing multi-option market: {str(e)}")
            else:
                # For binary markets, use Yes/No if available
                if 'option_images' in market:
                    option_images = market['option_images']
                    logger.info(f"Binary market with option images: {list(option_images.keys())}")
                else:
                    # Create default Yes/No options
                    logger.info("Adding default Yes/No options for binary market")
                    # Use icon/image fields from the API when available
                    image_url = market.get("icon") or market.get("image") or market.get("image_url", "")
                    option_images = {
                        "Yes": image_url,
                        "No": image_url
                    }
            
            # Make sure option_images is set in the market data
            market['option_images'] = option_images
            
            # Extract event banner and icon if available
            # Check for proper image and icon fields from Polymarket API
            # For binary markets and events, prioritize getting banner image and icon
            if 'image' in market and market['image']:
                market['event_image'] = market['image']
                logger.info(f"Using API image field as event banner: {market['event_image'][:50]}...")
            elif 'event_image' in market:
                logger.info(f"Market has event banner image: {market['event_image'][:50]}...")
            elif 'image_url' in market:
                market['event_image'] = market['image_url']
                logger.info(f"Using image_url as event banner: {market['event_image'][:50]}...")
                
            if 'icon' in market and market['icon']:
                market['event_icon'] = market['icon']
                logger.info(f"Using API icon field as event icon: {market['event_icon'][:50]}...")
            elif 'event_icon' in market:
                logger.info(f"Market has event icon: {market['event_icon'][:50]}...")
            elif 'icon_url' in market:
                market['event_icon'] = market['icon_url']
                logger.info(f"Using icon_url as event icon: {market['event_icon'][:50]}...")
                
            # For multiple-option markets, check if they have an events array
            # This is important for extracting the main event image and icon
            if 'events' in market and isinstance(market['events'], list) and len(market['events']) > 0:
                event = market['events'][0]  # Use the first event
                
                # Extract event details
                if 'id' in event:
                    market['event_id'] = event['id']
                    logger.info(f"Using event ID from events array: {market['event_id']}")
                    
                if 'title' in event:
                    market['event_name'] = event['title']
                    logger.info(f"Using event title from events array: {market['event_name']}")
                
                # For multiple-option markets, prioritize event images from the events array
                if is_event:
                    if 'image' in event:
                        market['event_image'] = event['image']
                        logger.info(f"Using event image from events array for multi-option market: {market['event_image'][:50]}...")
                        
                    if 'icon' in event:
                        market['event_icon'] = event['icon']
                        logger.info(f"Using event icon from events array for multi-option market: {market['event_icon'][:50]}...")
                # For binary markets, only use event images if we don't already have images
                else:
                    if (not market.get('event_image') or market.get('event_image') == '') and 'image' in event:
                        market['event_image'] = event['image']
                        logger.info(f"Using event image from events array as fallback: {market['event_image'][:50]}...")
                        
                    if (not market.get('event_icon') or market.get('event_icon') == '') and 'icon' in event:
                        market['event_icon'] = event['icon']
                        logger.info(f"Using event icon from events array as fallback: {market['event_icon'][:50]}...")
                
            if 'option_images' in market:
                logger.info(f"Market has {len(market['option_images'])} option images")
            
            # Use the enhanced formatter from utils.messaging
            return format_market_with_images(market)
        
        # Use utils.messaging version with formatter function
        posted_count = post_markets_to_slack(market_data_list, format_market_message_func=format_market_message)
        logger.info(f"Posted {posted_count} markets to Slack")
        
        # Update database records for posted markets
        posted_markets = []
        
        # We can't iterate over results since post_markets_to_slack only returns a count now
        # Instead, update all markets that were attempted to be posted
        for i, market in enumerate(to_post):
            if i < posted_count:
                # This market was successfully posted
                market.posted = True
                # We can't know the message_id here, but it's stored in the function
                posted_markets.append(market)
                logger.info(f"Posted market {market.condition_id} to Slack")
            else:
                # IMPORTANT: Keep posted=False if posting failed, so it can be retried
                logger.warning(f"Failed to post market {market.condition_id} to Slack")
        
        # Count how many multi-option markets were successfully posted
        multi_option_posted = sum(1 for m in posted_markets 
                                if m.raw_data and m.raw_data.get('is_multiple_option', False))
        logger.info(f"Successfully posted {multi_option_posted} multi-option markets to Slack")
        
        # Save changes
        db.session.commit()
        
        # Double-check unposted count for confirmation
        unposted_count = ProcessedMarket.query.filter_by(posted=False).count()
        logger.info(f"Posted {len(posted_markets)} markets to Slack, {unposted_count} markets remain unposted")
        
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