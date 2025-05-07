# Event Market Filtering

This document explains how the pipeline filters and processes events from Polymarket's API to ensure only active, non-closed events are included in market data.

## Event Filtering Logic

When markets are fetched from the Polymarket API, some may include an `events` array containing multiple events. Not all of these events are active or relevant, so we apply the following filtering:

1. **Active Events Only**: We only include events where `active: true`
2. **Non-Closed Events Only**: We exclude events where `closed: true`

This filtering ensures that:
- We don't show expired or irrelevant options to users
- Event markets only display options that can still be selected
- All displayed options are valid and active

## Implementation

The event filtering is implemented in `utils/event_filter.py` and applied in the pipeline as follows:

```python
# Main pipeline flow
markets = fetch_markets()
markets_with_filtered_events = filter_and_process_market_events(markets)
active_markets = filter_active_non_expired_markets(markets_with_filtered_events)
transformed_markets = transform_markets(active_markets)
```

### Key Functions

- `filter_inactive_events(market_data)`: Filters a single market's events array to only include active, non-closed events
- `process_event_images(market_data)`: Extracts event banner images and option images from filtered events
- `filter_and_process_market_events(markets)`: Applies both filtering and image processing to a list of markets

## Image Handling

After filtering events, we also handle images differently for binary vs multiple-option markets:

### Binary Markets
- Use a single banner image for the entire market
- No individual option images
- Options displayed as a comma-separated list ("Yes, No")

### Multiple-Option (Event) Markets
- Use the main event image as the banner
- Each option can have its own icon/image displayed inline
- Options are displayed as a list with their respective icons

## Debugging

The event filtering process logs detailed information about which events are kept or filtered out:

```
INFO: Filtering events to only include active, non-closed ones
INFO: Keeping event abc123: active and not closed
INFO: Filtering out event def456: active=false, closed=true
INFO: Filtered events: 3 -> 1
```

This helps track which events were excluded and why.

## Market Formatting

After event filtering, markets are formatted for Slack display using the `format_market_with_images` function, which:

1. Uses the appropriate format based on market type (binary vs multiple-option)
2. Validates URLs to ensure only valid images are displayed
3. Formats dates consistently
4. Includes event relationship information when available

The result is consistently formatted market messages in Slack with proper image handling based on market type.