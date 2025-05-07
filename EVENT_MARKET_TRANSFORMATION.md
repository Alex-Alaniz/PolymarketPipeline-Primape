# Event-Based Market Transformation

This document explains how we transform Polymarket's binary markets into event-based markets with team options.

## Problem Statement

The Polymarket API provides markets in a binary format, where each market represents a yes/no question about a specific team or outcome:

```
Will Inter Milan win the UEFA Champions League?
"outcomes": ["Yes", "No"]

Will Arsenal win the UEFA Champions League?
"outcomes": ["Yes", "No"]

Will PSG win the UEFA Champions League?
"outcomes": ["Yes", "No"]
```

For a better user experience, we want to transform these related binary markets into a single event market with multiple options:

```
Event Market: Champions League Winner
Options:
- Inter Milan
- Arsenal 
- PSG
```

## Transformation Process

1. **Identify Events**: Markets with the same `event_id` are grouped together
2. **Extract Teams**: Team names are extracted from binary market questions
3. **Create Event Market**: A new event market is created with teams as options
4. **Preserve Market IDs**: Original market IDs are preserved for each team option

## Implementation

The transformation is implemented in `utils/transform_markets_with_events.py`:

```python
def transform_markets_with_events(raw_markets):
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
            "expiry_time": max(market.get("endDate", "") for market in markets),
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
            parts = question.split("Will ")
            if len(parts) < 2:
                continue
                
            team_part = parts[1].split(" win")[0].strip()
            if not team_part:
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
    
    return transformed_markets
```

## Slack Message Formatting

When posting to Slack, event markets have a different formatting:

1. The message title shows "New Event for Approval"
2. The event banner image is shown
3. Each team option is listed with its icon
4. The binary "Yes/No" options are removed
5. Original market IDs are preserved for tracking

## Testing

You can test the event market transformation with:

```
python post_test_market_to_slack.py
```

This will post a sample event market for "UEFA Champions League Winner" with multiple team options and their icons.

## Benefits

This transformation:

1. Reduces information overload by consolidating related markets
2. Creates a cleaner, more intuitive user interface
3. Maintains all the original data for tracking and deployment
4. Preserves the relationship between teams and their original market IDs
5. Properly displays event banner images and team icons

## Pipeline Integration

The transformation is integrated into the pipeline flow:

1. Fetch markets from Polymarket API
2. Transform binary markets into event-based markets
3. Categorize the transformed markets
4. Post to Slack for approval
5. Store in database with proper relationships