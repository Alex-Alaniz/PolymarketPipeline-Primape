"""
Event filtering utilities for marketplace data.

This module provides functions to filter events and ensure
that only active, non-closed events are included in market data.
"""

import logging
from typing import Dict, List, Any

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
    
    # Skip if no events
    if not processed_data.get('events'):
        return processed_data
    
    # Consider only the first event (main event)
    event = processed_data['events'][0]
    
    # Set event ID and name
    if 'id' in event:
        processed_data['event_id'] = event['id']
    if 'title' in event:
        processed_data['event_name'] = event['title']
    
    # Extract event banner and icon
    if 'image' in event:
        # For multiple-option markets, always use the event image as banner
        if processed_data.get('is_multiple_option') or processed_data.get('is_event'):
            processed_data['event_image'] = event['image']
            logger.info(f"Using event image as banner for multi-option market: {event['image'][:30]}...")
        # For binary markets, only use if no banner image yet
        elif not processed_data.get('event_image'):
            processed_data['event_image'] = event['image']
            logger.info(f"Using event image as fallback banner for binary market: {event['image'][:30]}...")
    
    # Extract event icon for multi-option markets
    if 'icon' in event:
        if processed_data.get('is_multiple_option') or processed_data.get('is_event'):
            processed_data['event_icon'] = event['icon']
            logger.info(f"Using event icon for multi-option market: {event['icon'][:30]}...")
        elif not processed_data.get('event_icon'):
            processed_data['event_icon'] = event['icon']
            logger.info(f"Using event icon as fallback for binary market: {event['icon'][:30]}...")
    
    # Extract option images from outcomes if available
    option_images = processed_data.get('option_images', {})
    if 'outcomes' in event and isinstance(event['outcomes'], list):
        for outcome in event['outcomes']:
            # Skip if no outcome data
            if not isinstance(outcome, dict):
                continue
                
            # Get option name and image
            option_name = outcome.get('title') or outcome.get('name')
            option_image = outcome.get('image')
            
            # Store option image if available
            if option_name and option_image:
                option_images[option_name] = option_image
                logger.info(f"Added option image for {option_name}: {option_image[:30]}...")
    
    # Update option images
    processed_data['option_images'] = option_images
    
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