# Option Deduplication Logic

## Overview

When handling markets with multiple options, our system might receive duplicated entities in different formats. For example, a football league market could have:

- "Real Madrid" as a simple entity name
- "Will Real Madrid win the league?" as a question format

This document explains how our deduplication logic ensures each entity appears only once in Slack messages with the correct image.

## Deduplication Process

The deduplication process works as follows:

1. **Entity Extraction**: For each option, we extract the core entity (team, candidate, etc.) using pattern matching
   - Question formats like "Will X win?" are normalized to just the entity "X"
   - Direct entity names are preserved

2. **Entity Grouping**: Options representing the same entity are grouped together
   - Normalized entity names (lowercase, trimmed) are used as keys
   - All representations of the same entity with their display names and icons are collected

3. **Best Representation Selection**: For each entity group, we select the best representation:
   - Non-numeric IDs (typically from events array) are prioritized as they usually have cleaner names
   - If all options have numeric IDs, we choose the one with the shortest display name
   - The associated icon URL is preserved

4. **Display Construction**: The deduplicated list is used to build the Slack message:
   - Each unique entity gets one entry in the options field
   - Each entity gets one image block with its icon
   - Only URLs that are Slack-accessible are included

## Example

For a "La Liga Winner 2024-25" market, we might have:

**Input Options:**
- ID: "real-madrid", Name: "Real Madrid", Icon: "real_madrid_logo.png"
- ID: "101", Name: "Will Real Madrid win La Liga?", Icon: "real_madrid_logo.png"
- ID: "barcelona", Name: "Barcelona", Icon: "barcelona_logo.png"
- ID: "102", Name: "Will Barcelona win La Liga?", Icon: "barcelona_logo.png"

**After Deduplication:**
- "Real Madrid" with icon "real_madrid_logo.png"
- "Barcelona" with icon "barcelona_logo.png"

## Implementation Details

The core deduplication logic is implemented in `utils/messaging.py` in the `format_market_with_images` function:

1. We use regex patterns to extract entities from question formats
2. We normalize entity names for consistent matching
3. We group options by their normalized entity
4. We select the best representation for each unique entity
5. We generate Slack blocks with deduplicated options

## Testing

The deduplication logic is tested in:
- `test_deduplication.py`: Tests with synthetic La Liga market data
- `test_real_api_data.py`: Tests with real API data from Polymarket

Both binary markets (Yes/No only) and multi-option markets are tested to ensure correct handling of all market types.