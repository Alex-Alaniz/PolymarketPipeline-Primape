# Auto-Categorization for Polymarket Pipeline

This document explains the auto-categorization feature added to the Polymarket pipeline. The feature automatically assigns one of eight predefined categories to each market before it's posted to Slack for approval.

## Categories

Markets are assigned to one of the following categories:

| Category | Emoji | Description |
|----------|-------|-------------|
| politics | :ballot_box: | Political elections, policy decisions, government actions |
| crypto | :coin: | Cryptocurrency prices, blockchain events, token launches |
| sports | :sports_medal: | Sports events, tournaments, championships, team/player performance |
| business | :chart_with_upwards_trend: | Corporate news, stock prices, economic indicators |
| culture | :performing_arts: | Entertainment, music, movies, art, celebrities |
| news | :newspaper: | Current events, breaking news, world affairs |
| tech | :computer: | Technology releases, scientific discoveries, breakthroughs |
| all | :globe_with_meridians: | Default category for markets that don't fit other categories |

## Implementation Details

### Technical Components

1. **Market Categorizer** (`utils/market_categorizer.py`)
   - Uses OpenAI GPT-4o-mini model with temperature=0
   - Processes market questions and assigns a single category
   - Implements retry mechanism with exponential backoff
   - Includes fallback to "all" category if API fails or returns invalid category

2. **Pending Markets Database** (`models.py`)
   - `PendingMarket` model stores markets before approval
   - `category` field stores the assigned category
   - `ApprovalLog` tracks approval/rejection events

3. **Market Fetching and Posting** (`fetch_and_categorize_markets.py`)
   - Fetches markets from Polymarket API
   - Filters active, non-expired markets
   - Sends market questions to categorizer
   - Stores categorized markets in database
   - Posts to Slack with category badge

4. **Approval Processing** (`check_pending_market_approvals.py`)
   - Checks for approvals/rejections in Slack
   - Moves approved markets to main Market table
   - Records decision in approval log

### Workflow

1. Markets are fetched from Polymarket API
2. Each market is categorized using GPT-4o-mini
3. Categorized markets are stored in the pending_markets table
4. Markets are posted to Slack with category badge
5. Human reviewers approve or reject with reactions
6. Approved markets move to the next stage of the pipeline

## Performance and Cost Considerations

- GPT-4o-mini costs approximately $0.0002 per market
- Average categorization time is about 300-400ms per market
- Retry mechanism handles transient API failures
- Default fallback to "all" ensures pipeline continues even if categorization fails

## Example Usage

To run the auto-categorization pipeline:

```bash
# Run the full pipeline with auto-categorization
python new_pipeline.py

# Just fetch and categorize new markets
python fetch_and_categorize_markets.py

# Check for approvals on pending markets
python check_pending_market_approvals.py

# Test auto-categorization on sample markets
python test_auto_categorization.py
```

## Integration with Existing Pipeline

The auto-categorization feature integrates with the existing pipeline while maintaining backward compatibility:

1. Previously deployed markets remain intact
2. New markets go through categorization before deployment
3. The category field is added to the Market model for frontend integration
4. The "all" category serves as a fallback for markets that don't fit other categories

## Testing and Validation

The auto-categorization system has been tested with a variety of market questions and consistently produces appropriate categories. The `test_auto_categorization.py` script can be used to test the system with sample markets.