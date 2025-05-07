"""
Transform Markets with Events

This module transforms raw market data from Polymarket API into a format
that treats events as the primary structure and markets as options within those events.

For example, instead of having multiple separate markets:
- "Will Inter Milan win the UEFA Champions League?" (Yes/No)
- "Will PSG win the UEFA Champions League?" (Yes/No)
- "Will Arsenal win the UEFA Champions League?" (Yes/No)

We transform this into a single event:
- "UEFA Champions League Winner" with options:
  - Inter Milan
  - PSG
  - Arsenal

Only standalone markets (not part of an event) keep their binary Yes/No options.
"""

import logging
from typing import Dict, List, Any, Optional
import json

logger = logging.getLogger(__name__)

def transform_markets_with_events(raw_markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Transform raw markets data from Polymarket API to a format where events are primary.
    
    This transformation:
    1. Groups markets by their event_id
    2. Creates a single event "market" for each group with team options
    3. Passes standalone markets through with their original Yes/No options
    
    Args:
        raw_markets: Raw market data from the Polymarket API
        
    Returns:
        List of transformed markets, with events as primary structures
    """
    # Step 1: Collect all events and their markets
    events_map = {}
    standalone_markets = []
    
    for market in raw_markets:
        # Check if market has events information
        events = market.get("events", [])
        
        if not events:
            # This is a standalone market, keep as-is
            standalone_markets.append(market)
            continue
        
        # Process market with event information
        for event in events:
            event_id = event.get("id")
            if not event_id:
                continue
                
            # Initialize event if we haven't seen it yet
            if event_id not in events_map:
                events_map[event_id] = {
                    "event_data": event,
                    "markets": []
                }
            
            # Add this market to the event
            events_map[event_id]["markets"].append(market)
    
    # Step 2: Transform events into their own "markets"
    transformed_markets = []
    
    # Process events first
    for event_id, event_info in events_map.items():
        event_data = event_info["event_data"]
        markets = event_info["markets"]
        
        # Skip events with only one market
        if len(markets) <= 1:
            standalone_markets.extend(markets)
            continue
        
        # Create a new "market" representing the event
        event_market = {
            "id": f"event_{event_id}",
            "question": event_data.get("name", "Event"),
            "is_event": True,
            "category": markets[0].get("category", "unknown"),  # Use category from first market
            "expiry_time": max(market.get("endDate", "") for market in markets),
            "event_id": event_id,
            "event_name": event_data.get("name", ""),
            "event_image": event_data.get("image"),
            "event_icon": event_data.get("icon"),
            "options": [],  # Will contain team names
            "option_images": {},  # Will map team names to images
            "option_market_ids": {}  # Will map team names to their original market IDs
        }
        
        # Extract team names from the markets in this event
        for market in markets:
            # Extract team name from question (e.g., "Will Arsenal win?")
            question = market.get("question", "")
            
            # Skip markets with unclear team names
            if not question or "?" not in question:
                continue
                
            parts = question.split("Will ")
            if len(parts) < 2:
                continue
                
            team_part = parts[1].split(" win")[0].strip()
            if not team_part:
                continue
            
            # Skip if team already added
            if team_part in event_market["options"]:
                continue
                
            # Add team as an option
            event_market["options"].append(team_part)
            
            # Save market ID for this option
            event_market["option_market_ids"][team_part] = market.get("id")
            
            # Add option image if available
            if market.get("icon"):
                event_market["option_images"][team_part] = market.get("icon")
        
        # Only add events with at least 2 options
        if len(event_market["options"]) >= 2:
            transformed_markets.append(event_market)
    
    # Step 3: Add standalone markets
    transformed_markets.extend(standalone_markets)
    
    logger.info(f"Transformed {len(raw_markets)} raw markets into {len(transformed_markets)} " +
                f"markets ({len(transformed_markets) - len(standalone_markets)} events)")
    
    return transformed_markets