# Event Market Transformation Guide

## Overview

This document explains the process of transforming individual prediction markets into event-based grouped markets for the Polymarket-to-Apechain pipeline. The event transformation process is a critical step that allows related markets to be properly grouped, displayed with appropriate imagery, and deployed as a unified entity.

## Market Types

The pipeline handles two main types of markets:

1. **Standalone Markets**: Individual markets with binary (Yes/No) outcomes, not related to other markets.
2. **Event-Based Markets**: Groups of related markets that share a common event (e.g., "Champions League"), where each option represents a possible outcome (e.g., different teams that could win).

## Transformation Process

The transformation process follows these steps:

1. **Identify Related Markets**: Markets about the same event (e.g., "Will Real Madrid win Champions League?", "Will Barcelona win Champions League?") are detected as related.

2. **Group by Common Event**: Related markets are grouped under a common event entity (e.g., "Champions League 2025").

3. **Create Event Structure**: An event market is created with:
   - A descriptive name (e.g., "Champions League 2025")
   - A banner image representing the event
   - Options corresponding to each related market (e.g., team names)
   - Option images for each option (e.g., team logos)
   - Mappings to the original market IDs

4. **Transform Data Format**: The original order book structure is transformed to a parimutel format suitable for Apechain deployment.

## Data Structure

### Input Format (Individual Markets)

```json
[
  {
    "id": "market_real",
    "question": "Will Real Madrid win the UEFA Champions League?",
    "category": "sports",
    "expiry_time": "2025-07-07T00:00:00Z",
    "icon": "https://i.imgur.com/vvL5yfp.png"
  },
  {
    "id": "market_barca",
    "question": "Will Barcelona win the UEFA Champions League?",
    "category": "sports",
    "expiry_time": "2025-07-07T00:00:00Z",
    "icon": "https://i.imgur.com/7kLZZSQ.png"
  }
]
```

### Output Format (Event-Based Structure)

```json
[
  {
    "id": "event_ucl_test",
    "question": "UEFA Champions League 2025",
    "category": "sports",
    "is_event": true,
    "event_id": "ucl_test",
    "event_name": "UEFA Champions League 2025",
    "event_image": "https://i.imgur.com/Ux7r6Fp.png",
    "event_icon": "https://i.imgur.com/Ux7r6Fp.png",
    "options": ["Real Madrid", "Barcelona"],
    "option_images": {
      "Real Madrid": "https://i.imgur.com/vvL5yfp.png",
      "Barcelona": "https://i.imgur.com/7kLZZSQ.png"
    },
    "option_market_ids": {
      "Real Madrid": "market_real",
      "Barcelona": "market_barca"
    }
  }
]
```

## Database Schema Extensions

To support event-based markets, the following fields were added to both the `Market` and `PendingMarket` tables:

```
event_id          - Unique identifier for the event
event_name        - Display name for the event
event_image       - URL to the event banner image
event_icon        - URL to the event icon
is_event          - Boolean flag indicating if this is an event market
option_market_ids - JSON mapping of option values to original market IDs
```

## Implementation Details

### Key Components

1. **transform_markets_with_events.py**
   - Main utility for transforming markets into event-based format
   - Groups related markets and creates event structures

2. **add_event_fields_migration.py**
   - Migration script that adds event-related fields to database tables

3. **check_pending_approvals.py**
   - Handles approval process for event-based markets
   - Creates proper Market entries from approved PendingMarkets

4. **deploy_event_markets.py**
   - Specialized script for deploying event markets to Apechain
   - Handles the mapping of option images and market IDs

### Event-Based Market API

The API provides endpoints to retrieve markets in event-based format:

- **GET /api/markets-with-events**
  - Returns all markets grouped by events
  - Includes both event markets and standalone markets

```json
{
  "events": [
    {
      "id": "ucl_test",
      "name": "UEFA Champions League 2025",
      "image": "https://i.imgur.com/Ux7r6Fp.png",
      "icon": "https://i.imgur.com/Ux7r6Fp.png",
      "category": "sports",
      "options": ["Real Madrid", "Barcelona", "Inter Milan", "Arsenal"],
      "option_images": {
        "Real Madrid": "https://i.imgur.com/vvL5yfp.png",
        "Barcelona": "https://i.imgur.com/7kLZZSQ.png"
      },
      "option_market_ids": {
        "Real Madrid": "market_real",
        "Barcelona": "market_barca"
      }
    }
  ],
  "markets": [
    {
      "id": "market_btc",
      "question": "Will Bitcoin exceed $100,000 in 2025?",
      "category": "crypto",
      "options": ["Yes", "No"],
      "expiry": null,
      "banner_uri": null,
      "apechain_market_id": null,
      "status": "approved"
    }
  ]
}
```

## Deployment Workflow

1. **Initial Approval**: Events are posted to Slack for initial approval as grouped entities with proper formatting.

2. **Database Storage**: Approved events are stored in the Market table with their event relationships.

3. **Deployment**: The specialized deployment script handles deployment of events to Apechain.

4. **Frontend Integration**: Event images and option images are properly mapped for frontend display.

## Testing

Testing event market transformation can be done using the following scripts:

- **run_event_pipeline_test.py**: Runs an end-to-end test of the event pipeline.
- **clean_db_for_event_testing.py**: Cleans the database for testing event markets.
- **check_events.py**: Displays event relationships in the database.

## Conclusion

The event-based market transformation is a critical enhancement that allows the pipeline to properly handle related markets, improving the user experience by grouping related betting opportunities under a common event. This structure provides better categorization, more intuitive interfaces, and proper relationships between markets.