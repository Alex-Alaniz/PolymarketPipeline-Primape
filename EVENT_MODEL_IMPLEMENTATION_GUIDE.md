# Event Model Implementation Guide

This guide explains how the event relationship model works within the Polymarket pipeline and provides guidance on maintaining and extending it.

## Overview

Events in the pipeline represent logical groupings of related markets. For example, all markets related to the "FIFA World Cup 2026" would share the same event ID and name. This allows the frontend to group related markets together and helps users find related predictions.

## Database Structure

Events are represented by two fields in both the `markets` and `pending_markets` tables:

1. `event_id` - A unique identifier for the event (string)
2. `event_name` - A human-readable name for the event (string)

There is no separate events table - the relationship is maintained by these fields being identical across related markets.

## How Events Are Used

1. **Grouping Related Markets**: Markets that share the same `event_id` are considered related.
2. **Categorization**: Events typically belong to a single category, making it easier to browse.
3. **Frontend Display**: The frontend can use event relationships to show related markets together.
4. **Pipeline Processing**: The pipeline maintains event relationships throughout all stages.

## Implementation Details

### Event ID Format

Event IDs follow a simple format: `event_CATEGORY_IDENTIFIER` where:
- `CATEGORY` is the primary category (sports, politics, crypto, etc.)
- `IDENTIFIER` is a unique identifier for the event (can include dates, names, etc.)

Examples:
- `event_sports_001`
- `event_worldcup_2026`
- `event_crypto_001`
- `event_uselection_2028`

### Creating Event Relationships

When markets are fetched from Polymarket, they must be analyzed to determine if they belong to existing events or require new events. This process happens during the categorization phase, typically using these approaches:

1. **Keyword Matching**: Identify markets that mention specific events (e.g., "World Cup", "Champions League")
2. **Entity Recognition**: Extract entities like competitions, elections, or conferences
3. **Temporal Grouping**: Group markets with similar timeframes
4. **Manual Assignment**: Allow manual assignment of events in the approval process

### Maintaining Event Relationships

Event relationships are maintained throughout the pipeline:

1. **Pending Markets**: Initial event assignment when markets are categorized
2. **Approval Process**: Event relationships are preserved when moving from pending_markets to markets table
3. **Deployment**: Event information is retained in the deployed markets

### Utility Scripts

Several scripts help manage and inspect event relationships:

1. `check_events.py`: Shows markets grouped by events
2. `check_shared_events.py`: Finds events with multiple markets
3. `inspect_events.py`: Detailed inspection of specific events
4. `add_event_fields_migration.py`: Ensures database tables have event fields

## Best Practices

1. **Consistency**: Use consistent event IDs and names across related markets
2. **Meaningful Names**: Make event names descriptive and human-readable
3. **Category Alignment**: Events should generally align with a single category
4. **Relationship Preservation**: Ensure event relationships are preserved in all pipeline stages
5. **Validation**: Regularly check for orphaned or inconsistent event relationships

## Database Migration

If you need to add event fields to tables, use the provided migration script:

```
python add_event_fields_migration.py
```

## Diagnosing Issues

If you encounter problems with event relationships:

1. Check if event fields exist in both tables using the migration script
2. Inspect event relationships using the provided utility scripts
3. Verify that market approval preserves event fields
4. Ensure both event_id and event_name are being properly set

## Implementation Example

```python
# Example of setting event relationship during categorization
def categorize_market(market_data):
    question = market_data["question"]
    
    # Detect World Cup markets
    if "world cup" in question.lower() and "2026" in question:
        event_id = "event_worldcup_2026"
        event_name = "FIFA World Cup 2026"
    # Detect Champions League markets
    elif "champions league" in question.lower() and "2025" in question:
        event_id = "event_champions_league_2025"
        event_name = "Champions League 2025-2026"
    else:
        event_id = None
        event_name = None
    
    # Create pending market with event relationship
    pending_market = PendingMarket(
        poly_id=market_data["id"],
        question=question,
        category=detect_category(question),
        event_id=event_id,
        event_name=event_name
    )
    
    return pending_market
```