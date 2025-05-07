"""
Transform Polymarket data into the format needed for ApeChain deployment.

This module handles the transformation of market data from Polymarket's format
to the format needed for ApeChain deployment, with proper event handling.
"""

import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

def generate_event_id(event_name: str) -> str:
    """
    Generate a deterministic ID for an event based on its name.
    
    Args:
        event_name: Name of the event
        
    Returns:
        Deterministic ID for the event
    """
    return hashlib.sha256(event_name.encode()).hexdigest()[:40]

def extract_event_from_market(market_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Extract event information from market data.
    
    Args:
        market_data: Raw market data from Polymarket API
        
    Returns:
        Tuple of (event_data, updated_market_data)
    """
    # Extract market metadata
    market_id = market_data.get('conditionId') or market_data.get('id')
    title = market_data.get('title') or market_data.get('question')
    description = market_data.get('description', '')
    
    # Try to extract event name from title or description
    # This is a simplistic approach - enhance with more sophisticated logic as needed
    event_name = None
    
    # Check if title indicates an event within a larger category
    indicators = ["Champions League", "La Liga", "NBA Finals", "World Cup", 
                 "Super Bowl", "Stanley Cup", "Grand Slam", "Olympics",
                 "Presidential Election", "Democratic Primary", "Republican Primary"]
    
    for indicator in indicators:
        if indicator in title or (description and indicator in description):
            event_name = indicator
            break
    
    # If no specific event found, try to extract from category
    if not event_name:
        if "sports" in market_data.get('category', '').lower():
            # For sports, try to extract team names or league
            if "football" in description.lower() or "soccer" in description.lower():
                event_name = "Football"
            elif "basketball" in description.lower() or "nba" in description.lower():
                event_name = "Basketball"
            else:
                event_name = "Sports Event"
        elif "politics" in market_data.get('category', '').lower():
            if "election" in title.lower() or "election" in description.lower():
                event_name = "Election"
            else:
                event_name = "Political Event"
        elif "crypto" in market_data.get('category', '').lower():
            event_name = "Crypto Market"
        else:
            # Fallback to a generic event name if no specific event can be identified
            event_name = "News Event"
    
    # Generate event ID
    event_id = generate_event_id(event_name)
    
    # Extract image URLs
    banner_url = market_data.get('image')
    icon_url = market_data.get('icon')
    
    # Create event data
    event_data = {
        'id': event_id,
        'name': event_name,
        'description': description,
        'category': market_data.get('category', 'news'),
        'banner_url': banner_url,
        'icon_url': icon_url,
        'source_id': market_id,
        'raw_data': {
            'original_market': market_id,
            'event_metadata': {
                'extracted_at': datetime.utcnow().isoformat(),
                'source': 'polymarket'
            }
        }
    }
    
    # Update market data with event reference
    updated_market_data = market_data.copy()
    updated_market_data['event_id'] = event_id
    updated_market_data['event_name'] = event_name
    
    return event_data, updated_market_data

def extract_market_options(market_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract market options from Polymarket data.
    
    Args:
        market_data: Raw market data from Polymarket API
        
    Returns:
        List of market options with image URLs
    """
    options = []
    
    # Get outcomes from the right field based on API structure
    api_outcomes_raw = market_data.get('outcomes')
    api_options_raw = market_data.get('options')
    
    # First, try to handle the JSON string format for outcomes (Gamma API)
    if api_outcomes_raw and isinstance(api_outcomes_raw, str):
        try:
            # Try to parse as JSON string
            outcomes = json.loads(api_outcomes_raw)
            
            # If successful, create option objects
            if isinstance(outcomes, list):
                for i, value in enumerate(outcomes):
                    options.append({
                        'id': f"option_{i}",
                        'value': value,
                        'image_url': None  # No images in the JSON string format
                    })
                return options
            
        except json.JSONDecodeError:
            print(f"Failed to parse outcomes as JSON: {api_outcomes_raw}")
    
    # If we reach here, either parsing JSON failed or the format wasn't a JSON string
    # Try other formats for backward compatibility
    outcomes = None
    if isinstance(api_outcomes_raw, list):
        outcomes = api_outcomes_raw
    elif isinstance(api_options_raw, list):
        outcomes = api_options_raw
    else:
        # Default to empty list if no options found
        outcomes = []
    
    # Handle different API formats
    if isinstance(outcomes, list):
        # Simple list of option strings or objects
        for i, outcome in enumerate(outcomes):
            if isinstance(outcome, str):
                options.append({
                    'id': f"option_{i}",
                    'value': outcome,
                    'image_url': None  # We'll need to generate or assign images later
                })
            elif isinstance(outcome, dict):
                # More complex option structure with metadata
                option_id = outcome.get('id') or f"option_{i}"
                options.append({
                    'id': option_id,
                    'value': outcome.get('value') or outcome.get('name'),
                    'image_url': outcome.get('image_url') or outcome.get('image') or outcome.get('icon')
                })
    elif isinstance(outcomes, dict):
        # Dictionary of options with IDs as keys
        for option_id, option_data in outcomes.items():
            if isinstance(option_data, str):
                options.append({
                    'id': option_id,
                    'value': option_data,
                    'image_url': None
                })
            elif isinstance(option_data, dict):
                options.append({
                    'id': option_id,
                    'value': option_data.get('value') or option_data.get('name'),
                    'image_url': option_data.get('image_url') or option_data.get('image') or option_data.get('icon')
                })
    
    # If no options were found, provide default Yes/No
    if not options:
        options = [
            {'id': 'option_0', 'value': 'Yes', 'image_url': None},
            {'id': 'option_1', 'value': 'No', 'image_url': None}
        ]
    
    return options

def transform_market_for_apechain(market_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Transform market data from Polymarket's format to ApeChain format.
    
    Args:
        market_data: Raw market data from Polymarket API
        
    Returns:
        Tuple of (event_data, transformed_market_data)
    """
    # Extract event data and update market data with event reference
    event_data, updated_market_data = extract_event_from_market(market_data)
    
    # Extract market options
    options = extract_market_options(updated_market_data)
    
    # Extract key fields
    market_id = updated_market_data.get('conditionId') or updated_market_data.get('id')
    title = updated_market_data.get('title') or updated_market_data.get('question')
    description = updated_market_data.get('description', '')
    
    # Determine market type (binary, categorical, etc.)
    market_type = 'binary' if len(options) == 2 else 'categorical'
    
    # Create option images mapping
    option_images = {}
    for option in options:
        if option['image_url']:
            option_images[option['id']] = option['image_url']
    
    # Create transformed market data
    transformed_market = {
        'id': market_id,
        'question': title,
        'type': market_type,
        'event_id': event_data['id'],
        'original_market_id': market_id,
        'options': options,
        'option_images': option_images,
        'expiry': updated_market_data.get('endDate'),
        'status': 'new',
        'banner_uri': updated_market_data.get('image'),
        'icon_url': updated_market_data.get('icon'),
        'raw_data': updated_market_data
    }
    
    return event_data, transformed_market

def transform_markets_batch(markets_data: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Transform a batch of markets, grouping them by events.
    
    Args:
        markets_data: List of raw market data from Polymarket API
        
    Returns:
        Tuple of (events_data, transformed_markets_data)
    """
    events = {}  # Dictionary to store unique events
    transformed_markets = []
    
    for market_data in markets_data:
        # Transform each market
        event_data, transformed_market = transform_market_for_apechain(market_data)
        
        # Store unique events
        if event_data['id'] not in events:
            events[event_data['id']] = event_data
        
        # Add transformed market to the list
        transformed_markets.append(transformed_market)
    
    # Convert events dictionary to list
    events_list = list(events.values())
    
    return events_list, transformed_markets