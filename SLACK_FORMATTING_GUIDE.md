# Slack Messaging Format Guide

This document explains how markets are formatted for display in Slack.

## Market Types and Formatting Rules

The pipeline formats markets differently based on their type:

### 1. Binary Markets (Yes/No)

Binary markets have a simple Yes/No outcome structure. For these markets:

- One banner image is displayed for the entire market
- No individual option images are shown
- Options are displayed as a comma-separated list: "Yes, No"
- The market is labeled as "Binary Market (Yes/No)"

Example format:
```
New Market for Approval
-----------------------
Question: Will Bitcoin exceed $100,000 by the end of 2024?
Category: crypto
Type: Binary Market (Yes/No)
End Date: 2024-12-31 23:59 UTC
Options: Yes, No
```

### 2. Multiple-Option (Event) Markets

Event markets have multiple possible outcomes. For these markets:

- The main event image is used as a banner
- Each option can have its own icon/image displayed inline
- Options are displayed as a list with their respective icons
- The market is labeled as "Multiple-choice Market"

Example format:
```
New Event for Approval
---------------------
Event: Which team will win the Champions League 2025?
Category: sports
End Date: 2025-05-31 23:59 UTC

Options:
• Real Madrid [icon]
• Manchester City [icon]
• Bayern Munich [icon]
• PSG [icon]
```

## Implementation Details

The formatting is implemented in the `utils/messaging.py` module:

1. `format_market_with_images(market_data)` - Main function for formatting markets
2. `is_valid_url(url)` - Validates image URLs before including them
3. `post_markets_to_slack(markets, format_market_message_func)` - Batch posts markets

## Key Features

### Date Formatting

Expiry dates in various formats (ISO, timestamp) are consistently converted to:
```
YYYY-MM-DD HH:MM UTC
```

### Image Validation

Images are validated to ensure:
- Only HTTP/HTTPS URLs are used
- URLs have valid structure
- No invalid patterns (undefined, null, etc.)
- Error logging for any invalid URLs

### Option Processing

For event markets with multiple options:
1. First, check outcomes in events array with active=true, closed=false
2. Use option_images dictionary when available
3. Fall back to event_icon when necessary
4. Always display option text, even when no image is available

### Slack Blocks

The formatter creates Slack blocks for rich formatting:
- Header with market type
- Section with question/event
- Fields for category and expiry
- Image for banner
- Sections with inline images for options