#!/usr/bin/env python3

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

import re
import logging
from typing import Dict, List, Any, Tuple, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("transform_markets")

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
    if not raw_markets:
        return []
    
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
            "category": markets[0].get("category", "unknown"),
            "expiry_time": max((market.get("expiry_time", "") for market in markets), default=""),
            "event_id": event_id,
            "event_name": event_data.get("name", ""),
            "event_image": event_data.get("image"),
            "event_icon": event_data.get("icon"),
            "options": [],  # Team names
            "option_images": {},  # Team images
            "option_market_ids": {}  # Original market IDs
        }
        
        # Extract team names from the markets in this event
        for market in markets:
            # Extract team name from question
            question = market.get("question", "")
            team_name = extract_team_from_question(question)
            
            if not team_name:
                continue
            
            # Add team as an option
            if team_name not in event_market["options"]:
                event_market["options"].append(team_name)
            
            # Save market ID for this option
            event_market["option_market_ids"][team_name] = market.get("id")
            
            # Add option image if available
            if market.get("icon"):
                event_market["option_images"][team_name] = market.get("icon")
        
        # Only add events with at least 2 options
        if len(event_market["options"]) >= 2:
            transformed_markets.append(event_market)
        else:
            # Not enough options, keep original markets
            standalone_markets.extend(markets)
    
    # Step 3: Add standalone markets
    transformed_markets.extend(standalone_markets)
    
    logger.info(f"Transformed {len(raw_markets)} markets into {len(transformed_markets)} markets/events")
    logger.info(f"Created {len(transformed_markets) - len(standalone_markets)} event markets")
    
    return transformed_markets

def extract_team_from_question(question: str) -> Optional[str]:
    """
    Extract team name from a binary question.
    
    Args:
        question: Market question string (e.g., "Will Inter Milan win the UEFA Champions League?")
        
    Returns:
        Team name or None if extraction fails
    """
    # Pattern 1: "Will X win Y?"
    pattern1 = r"Will ([^?]+?) win "
    match = re.search(pattern1, question)
    if match:
        return match.group(1).strip()
    
    # Pattern 2: "Will X be the winner of Y?"
    pattern2 = r"Will ([^?]+?) be the winner of "
    match = re.search(pattern2, question)
    if match:
        return match.group(1).strip()
    
    # Pattern 3: "Will X become the Y champion?"
    pattern3 = r"Will ([^?]+?) become the .* champion"
    match = re.search(pattern3, question)
    if match:
        return match.group(1).strip()
    
    return None


if __name__ == "__main__":
    # Simple test
    test_markets = [
        {
            "id": "market_1",
            "question": "Will Inter Milan win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": "2025-05-30",
            "events": [
                {
                    "id": "ucl_2025",
                    "name": "UEFA Champions League 2025",
                    "image": "https://example.com/ucl.png"
                }
            ],
            "icon": "https://example.com/inter.png"
        },
        {
            "id": "market_2",
            "question": "Will Real Madrid win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": "2025-05-30",
            "events": [
                {
                    "id": "ucl_2025",
                    "name": "UEFA Champions League 2025",
                    "image": "https://example.com/ucl.png"
                }
            ],
            "icon": "https://example.com/real.png"
        },
        {
            "id": "market_3",
            "question": "Will Arsenal win the UEFA Champions League?",
            "category": "sports",
            "expiry_time": "2025-05-30",
            "events": [
                {
                    "id": "ucl_2025",
                    "name": "UEFA Champions League 2025",
                    "image": "https://example.com/ucl.png"
                }
            ],
            "icon": "https://example.com/arsenal.png"
        },
        {
            "id": "market_4",
            "question": "Will the price of Bitcoin exceed $100,000 in 2025?",
            "category": "crypto",
            "expiry_time": "2025-12-31",
            "events": []
        }
    ]
    
    transformed = transform_markets_with_events(test_markets)
    
    # Print results
    for i, market in enumerate(transformed):
        print(f"\nMarket {i+1}:")
        print(f"ID: {market.get('id')}")
        print(f"Is Event: {market.get('is_event', False)}")
        print(f"Question: {market.get('question')}")
        print(f"Options: {market.get('options', ['Yes', 'No'])}")
        if market.get('is_event'):
            print(f"Option Market IDs: {market.get('option_market_ids', {})}")