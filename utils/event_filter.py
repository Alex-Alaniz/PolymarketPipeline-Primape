"""
Event filtering utilities for marketplace data.

This module provides functions to filter events and ensure
that only active, non-closed events are included in market data.
"""

import json
import logging
from typing import Dict, List, Any
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def filter_inactive_events(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter the market data to only include active, non-closed events.
    
    Args:
        market_data: Raw market data with events array
        
    Returns:
        Filtered market data with only active, non-closed events
    """
    # Make a copy of the data to avoid modifying the original
    filtered_data = market_data.copy()
    
    # Check if the market has events
    if 'events' in filtered_data and isinstance(filtered_data['events'], list):
        original_events = filtered_data['events']
        filtered_events = []
        
        # Filter events to only include active, non-closed ones
        for event in original_events:
            if event.get('active', False) and not event.get('closed', False):
                # This event is active and not closed, keep it
                filtered_events.append(event)
                logger.info(f"Keeping event {event.get('id', 'Unknown')}: active and not closed")
            else:
                # This event is either inactive or closed, skip it
                logger.info(f"Filtering out event {event.get('id', 'Unknown')}: active={event.get('active')}, closed={event.get('closed')}")
        
        # Replace the events array with the filtered version
        filtered_data['events'] = filtered_events
        
        # Log how many events were filtered
        logger.info(f"Filtered events: {len(original_events)} -> {len(filtered_events)}")
    
    return filtered_data

def process_event_images(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract event images and option images from filtered event data.
    
    This function processes the events array and extracts images for the
    main event banner and individual options.
    
    IMPORTANT IMAGE HANDLING RULES:
    1. Binary markets (Yes/No outcomes): 
       - Banner: use market-level image URL
       - Icon: Do NOT use market-level icon URL
      
    2. Multi-option markets (grouped under an events array):
       - Banner: MUST use market["events"][0]["image"] (NOT market["id"]["image"])
       - Option icons: For each option, use option_market["icon"]
    
    Args:
        market_data: Filtered market data with only active, non-closed events
        
    Returns:
        Market data with extracted event_image, event_icon, and option_images
    """
    # Make a copy of the data to avoid modifying the original
    processed_data = market_data.copy()
    
    # Initialize option images dict if not present
    if 'option_images' not in processed_data:
        processed_data['option_images'] = {}
    
    # Store these flags in the processed data for easier debugging
    processed_data['is_binary'] = False
    processed_data['is_multiple_option'] = False
    
    # First check if this is a multiple choice market from the API flag
    is_multiple_choice = processed_data.get('is_multiple_choice', False)
    
    # Then check if this has an events array with multiple outcomes
    has_event_array = (
        'events' in processed_data 
        and isinstance(processed_data['events'], list) 
        and len(processed_data['events']) > 0
    )
    
    # Determine if this is a binary market (Yes/No outcomes)
    is_binary = False
    outcomes_raw = processed_data.get("outcomes", "[]")
    try:
        if isinstance(outcomes_raw, str):
            outcomes = json.loads(outcomes_raw)
        else:
            outcomes = outcomes_raw
            
        # Check if outcomes are exactly ["Yes", "No"]
        if isinstance(outcomes, list) and sorted(outcomes) == ["No", "Yes"]:
            is_binary = True
            processed_data['is_binary'] = True
            logger.info("Detected binary Yes/No market")
    except Exception as e:
        logger.error(f"Error checking binary market status: {str(e)}")
    
    # A market is "multiple option" if it's either flagged as multiple choice
    # OR it has an events array with options
    is_multiple = (
        is_multiple_choice
        or processed_data.get('is_event', False)
        or (has_event_array and not is_binary)
    )
    
    # Store the flag for later use
    processed_data['is_multiple_option'] = is_multiple
    
    # PRIORITY 1: Binary Markets (Yes/No outcomes)
    if is_binary:
        # For binary markets, use market-level image
        if 'image' in processed_data:
            processed_data['event_image'] = processed_data['image']
            logger.info(f"Binary market: Using market-level image: {processed_data['image'][:30]}...")
        
        # For binary markets, we don't use option icons
        processed_data['option_images'] = {}
        
        # If there's no events array or we're done with binary processing, we can return early
        if not has_event_array:
            return processed_data
    
    # PRIORITY 2: Multi-option markets with events array
    if is_multiple and has_event_array:
        # Get the main event data (first event in array)
        event = processed_data['events'][0]
        
        # Set event ID and name
        if 'id' in event:
            processed_data['event_id'] = event['id']
        if 'title' in event:
            processed_data['event_name'] = event['title']
        
        # RULE 2: For multi-option markets, MUST use market["events"][0]["image"]
        if 'image' in event:
            processed_data['event_image'] = event['image']
            logger.info(f"Multi-option market: Using events[0].image for banner: {event['image'][:30]}...")
        
        # For multi-option markets, store event icon too
        if 'icon' in event:
            processed_data['event_icon'] = event['icon']
            logger.info(f"Multi-option market: Using events[0].icon: {event['icon'][:30]}...")
        
        # Extract option images from outcomes if available
        option_images = processed_data.get('option_images', {}) or {}
        
        # RULE 2: For option icons, use option_market["icon"]
        if 'outcomes' in event and isinstance(event['outcomes'], list):
            for outcome in event['outcomes']:
                # Skip if no outcome data
                if not isinstance(outcome, dict):
                    continue
                    
                # Get option ID, name, and icon
                option_id = outcome.get('id')
                option_name = outcome.get('title') or outcome.get('name')
                
                # Prefer icon over image for option icons
                option_icon = outcome.get('icon')
                if not option_icon:
                    option_icon = outcome.get('image')
                
                # Store option image if available - use ID as key if available, otherwise name
                key = option_id if option_id else option_name
                if key and option_icon:
                    option_images[key] = option_icon
                    logger.info(f"Added option icon for {key}: {option_icon[:30]}...")
        
        # Update option images
        processed_data['option_images'] = option_images
    
    # Log the final image decisions for debugging
    logger.info(f"""
    Final image decisions:
    - is_binary: {processed_data.get('is_binary', False)}
    - is_multiple_option: {processed_data.get('is_multiple_option', False)}
    - event_image: {processed_data.get('event_image', 'None')[:30]}...
    - event_icon: {processed_data.get('event_icon', 'None')[:30]}...
    - option_images: {len(processed_data.get('option_images', {}))} images
    """)
    
    return processed_data

def filter_and_process_market_events(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter and process events for a list of markets.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List of markets with filtered events and processed images
    """
    processed_markets = []
    
    for market in markets:
        # First filter inactive events
        filtered_market = filter_inactive_events(market)
        
        # Then process images from the filtered events
        processed_market = process_event_images(filtered_market)
        
        # Add to processed list
        processed_markets.append(processed_market)
    
    return processed_markets