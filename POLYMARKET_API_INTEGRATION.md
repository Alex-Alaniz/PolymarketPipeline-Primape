# Polymarket API Integration

This document explains how our pipeline integrates with Polymarket's API to fetch and process markets.

## API Endpoints

The pipeline uses two distinct Polymarket API endpoints:

1. **Binary Markets API**
   - URL: `https://gamma-api.polymarket.com/markets`
   - Purpose: Fetches true binary markets (standalone, not part of an event)
   - Query parameters:
     - `closed=false`: Only fetch open markets
     - `archived=false`: Skip archived markets
     - `active=true`: Only fetch active markets
     - `limit=100`: Limit the number of results

2. **Events API**
   - URL: `https://gamma-api.polymarket.com/events`
   - Purpose: Fetches event-based markets (to be transformed into a single market with options)
   - Query parameters:
     - Same as Binary Markets API

## Authentication

The Polymarket Gamma API is publicly accessible and doesn't require authentication or an API key.

## Market Types

### Binary Markets

Binary markets are standalone markets with exactly two outcomes (Yes/No):

```json
{
  "id": "0x123...",
  "conditionId": "0xabc...",
  "question": "Will Arsenal win the Premier League?",
  "type": "binary",
  "image": "https://example.com/arsenal-banner.jpg",
  "icon": "https://example.com/arsenal-icon.png",
  "endDate": 1714694400000,
  "options": [
    {
      "id": "0x...",
      "value": "Yes",
      "image": "https://example.com/yes-icon.png"
    },
    {
      "id": "0x...",
      "value": "No",
      "image": "https://example.com/no-icon.png"
    }
  ]
}
```

### Event Markets

Event markets represent multiple related markets grouped under a single event. We transform these into a single market with multiple options:

```json
{
  "id": "0x456...",
  "name": "Champions League Winner",
  "endDate": 1728192000000,
  "image": "https://example.com/champions-league-banner.jpg",
  "icon": "https://example.com/champions-league-icon.png",
  "markets": [
    {
      "id": "0xdef...",
      "question": "Will Arsenal win the Champions League?",
      "image": "https://example.com/arsenal-banner.jpg",
      "icon": "https://example.com/arsenal-icon.png"
    },
    {
      "id": "0xghi...",
      "question": "Will Barcelona win the Champions League?",
      "image": "https://example.com/barcelona-banner.jpg",
      "icon": "https://example.com/barcelona-icon.png"
    }
  ]
}
```

This is transformed into:

```json
{
  "id": "0x456...",
  "question": "Champions League Winner",
  "type": "event",
  "is_event": true,
  "event_id": "0x456...",
  "event_name": "Champions League Winner",
  "event_image": "https://example.com/champions-league-banner.jpg",
  "event_icon": "https://example.com/champions-league-icon.png",
  "options": [
    {
      "id": "0xdef...",
      "value": "Arsenal",
      "image": "https://example.com/arsenal-icon.png"
    },
    {
      "id": "0xghi...",
      "value": "Barcelona",
      "image": "https://example.com/barcelona-icon.png"
    }
  ],
  "option_market_ids": {
    "Arsenal": "0xdef...",
    "Barcelona": "0xghi..."
  }
}
```

## Transformation Process

### Binary Markets Transformation

Binary markets only need minimal transformation:
1. Filtering out expired or inactive markets
2. Ensuring required fields exist (image, icon, options)
3. Adding category based on AI classification

### Event Markets Transformation

Event markets undergo significant transformation:
1. Event data is extracted to create an `Event` record
2. Child markets are transformed into options for a single market
3. Option names are extracted from market questions
4. Option images use the child market icons
5. A map of option values to market IDs is maintained to track which option corresponds to which original market

## Implementation

The transformation happens in the `utils/transform_market_with_events.py` module:

- `transform_markets_batch()`: Processes a batch of markets, identifying events and binary markets
- `transform_market_for_apechain()`: Prepares market data for Apechain deployment
- `extract_option_from_question()`: Extracts team/option names from market questions

## API Response Handling

The pipeline has fallback mechanisms for API changes:
1. First attempts to use the REST API endpoints
2. Logs detailed information about API request failures
3. Filters results to ensure only valid, complete markets are processed

## Rate Limiting

The Polymarket API has rate limits. The pipeline implements best practices:
1. Fetching data in batches rather than individual requests
2. Processing and storing all retrieved markets before making additional requests
3. Limiting the number of markets fetched in each pipeline run