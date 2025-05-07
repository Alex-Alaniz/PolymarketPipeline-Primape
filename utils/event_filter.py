#!/usr/bin/env python3
"""
Event filter for processing market event images.

This module extracts and validates images from market events data,
following specific rules for binary vs multi-option markets.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    # Basic validation - must start with http/https
    return url.startswith('http://') or url.startswith('https://')

def is_binary_market(market_data: Dict[str, Any]) -> bool:
    """Check if a market is a binary Yes/No market.
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        bool: True if binary market, False otherwise
    """
    # Check explicit flag if available
    if 'is_binary' in market_data:
        return market_data['is_binary']
    
    # Check for Yes/No outcomes
    outcomes = market_data.get('outcomes', [])
    if isinstance(outcomes, str):
        try:
            outcomes = json.loads(outcomes)
        except:
            outcomes = []
    
    # Binary markets have Yes/No outcomes
    if isinstance(outcomes, list) and len(outcomes) == 2:
        yes_no = set(['Yes', 'No'])
        outcomes_set = set([o.strip() if isinstance(o, str) else str(o) for o in outcomes])
        if outcomes_set == yes_no:
            return True
    
    return False

def is_multiple_option_market(market_data: Dict[str, Any]) -> bool:
    """Check if a market has multiple options (not binary Yes/No).
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        bool: True if multiple-option market, False otherwise
    """
    # Check explicit flag if available
    if 'is_multiple_option' in market_data:
        return market_data['is_multiple_option']
    
    # Check option_markets field
    option_markets = market_data.get('option_markets', [])
    if option_markets and len(option_markets) > 1:
        return True
    
    # Check events structure
    events = market_data.get('events', [])
    if events and isinstance(events, list) and len(events) > 0:
        for event in events:
            if isinstance(event, dict) and 'outcomes' in event:
                outcomes = event.get('outcomes', [])
                if len(outcomes) > 2:
                    return True
    
    # Not a multiple-option market
    return False

def extract_option_icons(market_data: Dict[str, Any]) -> Dict[str, str]:
    """Extract option icons from market data.
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Dict mapping option IDs to icon URLs
    """
    option_icons = {}
    
    # Extract from option_markets if available
    option_markets = market_data.get('option_markets', [])
    if option_markets:
        for option_market in option_markets:
            if isinstance(option_market, dict):
                market_id = option_market.get('id', '')
                icon_url = option_market.get('icon', '')
                
                if market_id and icon_url and is_valid_url(icon_url):
                    option_icons[market_id] = icon_url
                    logger.info(f"Added icon from option_markets for ID {market_id}: {icon_url[:30]}...")
    
    # Extract from events if available
    events = market_data.get('events', [])
    if events and isinstance(events, list) and len(events) > 0:
        logger.info(f"Processing {len(events[0].get('outcomes', []))} outcomes from events array")
        for event in events:
            if isinstance(event, dict) and 'outcomes' in event:
                outcomes = event.get('outcomes', [])
                for outcome in outcomes:
                    if isinstance(outcome, dict):
                        outcome_id = outcome.get('id', '')
                        icon_url = outcome.get('icon', '')
                        
                        if outcome_id and icon_url and is_valid_url(icon_url):
                            option_icons[outcome_id] = icon_url
                            logger.info(f"Added option icon for {outcome_id}: {icon_url[:30]}...")
    
    return option_icons

def process_event_images(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process and extract images from market event data.
    
    This function applies specific rules for extracting images:
    1. For binary markets, use the main market image
    2. For multi-option markets, use market["events"][0]["image"] for banner
    3. For option icons, collect from both option_markets[].icon and events[0].outcomes[].icon
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Processed market data with extracted images
    """
    # Make a copy to avoid modifying the original
    processed_data = market_data.copy()
    
    # Determine market type
    is_binary = is_binary_market(processed_data)
    is_multiple_option = is_multiple_option_market(processed_data)
    
    if is_binary:
        logger.info("Detected binary Yes/No market")
        # RULE 1: For binary markets, use the market-level image URL
        event_image = processed_data.get('image', '')
        if event_image and is_valid_url(event_image):
            processed_data['event_image'] = event_image
            logger.info(f"Binary market: Using market-level image: {event_image[:30]}...")
    elif is_multiple_option:
        logger.info("Detected multi-option market")
        # RULE 2: For multi-option markets, use market["events"][0]["image"] for banner
        events = processed_data.get('events', [])
        if events and isinstance(events, list) and len(events) > 0:
            first_event = events[0]
            if isinstance(first_event, dict) and 'image' in first_event:
                event_image = first_event.get('image')
                if is_valid_url(event_image):
                    processed_data['event_image'] = event_image
                    logger.info(f"Multi-option market: Using events[0].image for banner: {event_image[:30]}...")
    
    # Mark the market type
    processed_data['is_binary'] = is_binary
    processed_data['is_multiple_option'] = is_multiple_option
    processed_data['is_event'] = is_multiple_option
    
    # For multi-option markets, extract option icons
    if is_multiple_option:
        # RULE 3: For multi-option markets, extract option icons
        option_markets = processed_data.get('option_markets', [])
        logger.info(f"Processing {len(option_markets)} option markets for icons")
        option_icons = extract_option_icons(processed_data)
        
        # Store the extracted icons
        processed_data['option_images'] = option_icons
    
    # Log what we found
    logger.info(f"""
    Final image decisions:
    - is_binary: {is_binary}
    - is_multiple_option: {is_multiple_option}
    - event_image: {processed_data.get('event_image', 'None')[:30]}...
    - event_icon: {processed_data.get('event_icon', 'None')}...
    - option_images: {len(processed_data.get('option_images', {}))} images
    """)
    
    return processed_data

def filter_inactive_events(events):
    """
    Filter out inactive events from a list of events.
    
    Args:
        events: List of event dictionaries
        
    Returns:
        List of active events
    """
    if not events:
        return []
    
    active_events = []
    for event in events:
        # Check if the event is still active based on its end date
        if isinstance(event, dict):
            end_date = event.get('endDate')
            if end_date:
                try:
                    # Parse the end date and compare with current time
                    from datetime import datetime
                    import dateutil.parser
                    
                    now = datetime.utcnow()
                    event_end = dateutil.parser.parse(end_date)
                    
                    if event_end > now:
                        active_events.append(event)
                except Exception as e:
                    logger.error(f"Error parsing event end date: {e}")
                    # If date parsing fails, include the event by default
                    active_events.append(event)
            else:
                # If no end date, include it by default
                active_events.append(event)
    
    logger.info(f"Filtered events: {len(events)} original, {len(active_events)} active")
    return active_events

def filter_and_process_market_events(markets):
    """
    Filter events and process images for a list of markets.
    
    This function combines event filtering and image processing:
    1. Filters out inactive events in each market
    2. Processes images for each market according to the image handling rules
    
    Args:
        markets: List of market dictionaries
        
    Returns:
        List of processed market dictionaries
    """
    if not markets:
        return []
    
    processed_markets = []
    for market in markets:
        try:
            # Filter inactive events
            if 'events' in market and isinstance(market['events'], list):
                market['events'] = filter_inactive_events(market['events'])
            
            # Process images
            processed_market = process_event_images(market)
            processed_markets.append(processed_market)
        except Exception as e:
            logger.error(f"Error processing market: {e}")
            # If processing fails, include the original market
            processed_markets.append(market)
    
    logger.info(f"Processed {len(processed_markets)} markets")
    return processed_markets