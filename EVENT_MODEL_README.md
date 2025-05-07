# Event Model Implementation for Market Pipeline

This document explains the updated implementation for the event model in our market pipeline. The event model ensures proper grouping of related markets and maintains the relationship between events, markets, and their visual assets.

## Event Model Overview

Events represent competitions, tournaments, or other real-world happenings that can have multiple related prediction markets. For example, "UEFA Champions League 2025" is an event that could have multiple markets like "Will Manchester United win?", "Will there be more than 3 goals?", etc.

Each event has:
- A unique identifier (`event_id`)
- A name (`event_name`)
- A banner image (`event_image`)
- Optional icons and additional metadata

## Implementation Details

### 1. Database Schema

Both `Market` and `PendingMarket` tables include:
- `event_id` (String): The unique identifier for the event
- `event_name` (String): The human-readable name of the event
- Foreign key relationship pointing back to the Events table (planned for future)

### 2. Extracting Event Information

Events are extracted directly from the Polymarket API response:

```python
# Extract event information from market data
event_id = None
event_name = None
event_image = None
event_icon = None

# Check if event data is directly available
if 'event_id' in market:
    event_id = market.get('event_id')

if 'event_name' in market:
    event_name = market.get('event_name')
    
if 'event_image' in market:
    event_image = market.get('event_image')
    
if 'event_icon' in market:
    event_icon = market.get('event_icon')

# Then check for detailed event data from API
events = market.get('events', [])
if events:
    for event in events:
        if 'id' in event:
            event_id = event['id']
        if 'name' in event:
            event_name = event['name']
        if 'image' in event:
            event_image = event['image']
        if 'icon' in event:
            event_icon = event['icon']
```

### 3. Slack Integration for Event Display

When posting markets to Slack, we now include:
- The event name and ID
- The event banner image (if available)
- Option images for the market (if available)

This allows approvers to see the complete visual context of a market.

### 4. Testing Event Display

The `post_test_market_to_slack.py` script includes a sample market with:
- Event name: "UEFA Champions League 2025"
- Event ID: "event_champions_league_2025"
- Event banner image (UEFA Champions League logo)
- Option images (team logos or symbols)

This allows for testing the rich message formatting with images.

## Benefits of the Event Model

1. **Better Grouping**: Related markets are properly grouped by event
2. **Consistent Branding**: Event banners and icons ensure visual consistency
3. **Better User Experience**: Users can find related markets more easily
4. **Organized Data Structure**: Clear relationship between events and markets

## Future Enhancements

1. **Dedicated Events Table**: A separate table to store event metadata
2. **Event Category Mapping**: Associate events with specific categories
3. **Event Timeline**: Track event start/end dates and milestones
4. **Event Hierarchy**: Support for nested events (tournaments → matches)

## Testing the Event Model

To test the event model implementation:
1. Run `python post_test_market_to_slack.py` to post a sample market with event data
2. Verify that the event banner image is displayed in Slack
3. Verify that option images are displayed for market choices
4. Run `python check_test_approval.py` to see event details in the approval status