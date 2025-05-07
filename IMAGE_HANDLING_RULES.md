# Image Handling Rules for Polymarket Events

This document specifies the rules for handling images in the Polymarket pipeline, particularly for events and multi-option markets.

## Market Types

The pipeline processes two main types of markets:

1. **Binary Markets (Yes/No outcomes)**
   - Simple markets with only "Yes" and "No" outcomes
   - Usually standalone without event grouping

2. **Multi-Option Markets**
   - Markets with multiple possible outcomes (e.g., "Real Madrid", "Manchester City", etc.)
   - Often grouped under an "event" (e.g., "Champions League 2025")

## Image Handling Rules

### Binary Markets (Yes/No outcomes)

For binary markets with only "Yes" and "No" outcomes:

- **Banner Image**: Use the market-level image URL (`market["image"]`)
- **Option Images**: Do NOT use individual option images for Yes/No outcomes
- **Icon**: Do NOT use market-level icon URL

Example:
```json
{
  "id": "binary-123",
  "question": "Will Bitcoin exceed $100,000 by the end of 2024?",
  "outcomes": ["Yes", "No"],
  "image": "https://example.com/bitcoin-banner.jpg",  <-- USE THIS for banner
  "icon": "https://example.com/bitcoin-icon.jpg"      <-- DO NOT USE
}
```

### Multi-Option Markets

For markets with multiple outcomes grouped under an events array:

- **Banner Image**: MUST use `market["events"][0]["image"]` (NOT `market["image"]`)
- **Event Icon**: Use `market["events"][0]["icon"]` for event-level icon
- **Option Icons**: For each option, use `option_market["icon"]` or `option_market["image"]` if icon is not available

Example:
```json
{
  "id": "multi-123",
  "question": "Which team will win the Champions League 2025?",
  "image": "https://example.com/incorrect-banner.jpg",  <-- DO NOT USE
  "is_multiple_choice": true,
  "events": [
    {
      "id": "event-123",
      "title": "Champions League 2025",
      "image": "https://example.com/champions-league-banner.jpg",  <-- USE THIS for banner
      "icon": "https://example.com/champions-league-icon.jpg",     <-- USE THIS for event icon
      "outcomes": [
        {
          "id": "real-madrid",
          "title": "Real Madrid",
          "icon": "https://example.com/real-madrid-icon.jpg"       <-- USE THIS for option icon
        },
        {
          "id": "manchester-city",
          "title": "Manchester City",
          "icon": "https://example.com/man-city-icon.jpg"          <-- USE THIS for option icon
        }
      ]
    }
  ]
}
```

## Implementation Details

The image handling logic is implemented in the `process_event_images` function in `utils/event_filter.py`:

1. Determine if the market is binary (Yes/No) or multi-option
2. For binary markets, use market-level image URL for banner
3. For multi-option markets:
   - Use events[0].image for banner
   - Use events[0].icon for event icon
   - Collect option icons from each outcome in events[0].outcomes

## Slack Message Formatting

When posting markets to Slack:

1. For binary markets, display only the main banner image.
2. For multi-option markets, display the main event banner at the top, and individual option icons inline with option names in the format: "*Real Madrid* : <icon_url>".

## Testing

To test the image handling rules:

```bash
python test_event_images.py
```

This will run tests for both binary and multi-option markets to ensure the correct images are being extracted according to the rules.

You can also run the full pipeline test:

```bash
python test_new_image_rules.py
```

This will reset the database, run the image handling tests, and then run the full pipeline to ensure everything works correctly.