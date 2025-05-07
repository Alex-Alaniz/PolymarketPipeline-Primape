# Image Handling Rules for Polymarket Events

This document specifies the rules for handling images in the Polymarket pipeline, particularly for events and multi-option markets.

## Overview

The Polymarket API provides data for prediction markets in different formats. Some markets are binary (Yes/No) questions, while others are multi-option questions with several possible outcomes. These multi-option markets are often part of an "event" (like sports tournaments or elections) and have their own image structure.

This document defines the rules for extracting and displaying images from these markets to ensure consistency.

## Market Types

The pipeline processes two main types of markets:

1. **Binary Markets (Yes/No outcomes)**
   - Simple markets with only "Yes" and "No" outcomes
   - Usually standalone without event grouping
   - Example: "Will Bitcoin exceed $100,000 by the end of 2024?"

2. **Multi-Option Markets**
   - Markets with multiple possible outcomes (e.g., "Real Madrid", "Manchester City", etc.)
   - Often grouped under an "event" (e.g., "Champions League 2025")
   - Example: "Which team will win the Champions League 2025?"

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
- **Option Icons**: We collect option icons from TWO sources:
  1. Primary source: `market["option_markets"][*]["icon"]` - each option market's icon
  2. Secondary source: `market["events"][0]["outcomes"][*]["icon"]` - each outcome's icon

Example structure with both sources of options:
```json
{
  "events": [
    {
      "id": "12672",
      "title": "La Liga Winner",
      "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/la-liga-winner-0Gd3D1MaSklO.png",  <-- USE THIS for banner
      "outcomes": [
        {
          "id": "real-madrid",
          "title": "Real Madrid",
          "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/real-madrid-icon.png"  <-- Option icon from events.outcomes
        }
      ]
    }
  ],
  "option_markets": [
    {
      "id": "507396",
      "question": "Will Barcelona win La Liga?",
      "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-la-liga-vCC-C0S5sp4O.png"  <-- Option icon from option_markets
    }
  ]
}

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

### Core Components

1. **Image Extraction**: `utils/event_filter.py` contains the core image handling logic:
   - `process_event_images()` function identifies market type and extracts the correct images
   - `filter_inactive_events()` function ensures only active event options are included

2. **Message Formatting**: `utils/messaging.py` contains the Slack message formatting logic:
   - `format_market_with_images()` function creates properly formatted Slack messages with images
   - Images are displayed according to the market type rules

### Detection Process

The market type detection follows these steps:

1. Check for explicit flags: `is_binary` and `is_multiple_option`
2. If not set, check the outcomes array for exactly ["Yes", "No"]
3. If still not determined, check for `is_multiple_choice` or `is_event` flags
4. If an events array exists, assume it's a multi-option market

### Image Extraction Logic

The image handling logic is implemented in the `process_event_images` function in `utils/event_filter.py`:

1. Determine if the market is binary (Yes/No) or multi-option using the detection process above
2. For binary markets:
   - Use `market["event_image"]` if set by a previous processing step
   - Otherwise, use market-level image URL (`market["image"]`)
   - Do not extract or use option-level images

3. For multi-option markets:
   - Use `market["event_image"]` if set by a previous processing step
   - Otherwise, use the first event's image: `market["events"][0]["image"]`
   - Use the first event's icon: `market["events"][0]["icon"]`
   - Extract option icons from each outcome in `events[0].outcomes`
   - Each option icon is stored in a dictionary mapping option ID to icon URL

## Slack Message Formatting

The Slack message formatting follows specific rules for each market type:

### Binary Markets (Yes/No)

For binary markets, the Slack message includes:
- A header with the market question
- Category and expiry date fields
- The banner image (market-level image)
- A simple list of options ("Yes, No")
- No individual option images

### Multi-Option Markets

For multi-option markets, the Slack message includes:
- A header with the event name and question
- Category and expiry date fields
- The event banner image (from events[0].image)
- A section for options
- Each option displayed with both name and icon URL in format: "*Option Name* : icon_url"

## Testing

Several test scripts are available to verify the correct image handling:

### Unit Tests for Image Extraction

```bash
python test_event_images.py
```

This script tests the image extraction logic independently:
- Creates test market data for both binary and multi-option markets
- Processes them with the `process_event_images` function
- Verifies that the correct images are extracted according to the rules

### Slack Message Formatting Tests

```bash
python test_slack_formatting.py
```

This script tests the Slack message formatting:
- Creates test market data with proper image structure
- Formats Slack messages with the `format_market_with_images` function
- Verifies that the banner and option images appear in the correct format
- Option images should be in the format "*Option Name* : icon_url"

### Full Pipeline Test

```bash
python test_new_image_rules.py
```

This script tests the complete pipeline:
- Resets the database
- Fetches real market data from the API
- Processes it through the entire pipeline
- Posts formatted messages to Slack
- Verifies that images are correctly displayed in all market types