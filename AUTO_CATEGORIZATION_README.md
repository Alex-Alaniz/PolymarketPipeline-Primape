# Polymarket Pipeline Auto-Categorization Implementation Guide

## Overview

This guide explains how to implement the simplified version of the Polymarket pipeline with automatic categorization using GPT-4o-mini. The implementation maintains what worked well in our first pipeline run while adding categories and capturing option images.

## Implementation Steps

### Step 1: Install Required Dependencies

Ensure you have all required dependencies installed:

```bash
pip install flask flask-sqlalchemy openai slack-sdk tenacity
```

### Step 2: Reset the Database (Optional)

If you want to start with a clean slate:

```bash
python reset_db_simplified.py
```

This will:
- Drop all existing tables (you'll be asked to confirm with 'YES')
- Create new tables without any event-based model complexity
- Keep the tables structure that worked in the first pipeline

### Step 3: Update Your Models

Replace your existing models.py file:

```bash
cp models_updated.py models.py
```

The updated models include:
- Market model with category field and option_images JSON field
- PendingMarket model with category field and posted flag
- ProcessedMarket with appropriate tracking fields

### Step 4: Create Required Utility Files

Make sure the utils directory exists:

```bash
mkdir -p utils
```

Copy the utility files:

```bash
cp utils/market_categorizer.py utils/
cp utils/messaging.py utils/
```

### Step 5: Run the Pipeline

The pipeline has these main steps:

1. **Fetch and categorize markets**:
   ```bash
   python fetch_and_categorize_markets.py
   ```
   
2. **Post unposted pending markets to Slack**:
   ```bash
   python post_unposted_pending_markets.py
   ```
   
3. **Check market approvals**:
   ```bash
   python check_market_approvals.py
   ```

## Key Features

1. **Automatic Categorization**: Markets are categorized using GPT-4o-mini into one of these categories:
   - politics
   - crypto
   - sports
   - business
   - culture
   - news
   - tech
   
2. **Category Badges in Slack**: Markets are posted to Slack with emoji badges for their categories

3. **Option Images**: Option images from the API are captured and stored in the option_images JSON field

4. **Batch Processing**: Pending markets use a posted flag to enable batch processing

## Database Structure

The simplified database structure includes:

- **markets**: Approved markets ready for deployment
  - Contains category, banner_url, and option_images fields
  
- **pending_markets**: Markets awaiting approval
  - Contains category, posted flag, and option_images fields
  
- **processed_markets**: Tracks all markets seen from the API
  - Prevents reprocessing of the same markets

- **approval_events**: Logs approval/rejection decisions

## Testing

1. To test the market fetching and categorization:

```bash
python fetch_and_categorize_markets.py
```

2. To test posting to Slack:

```bash
python post_unposted_pending_markets.py
```

3. To verify the database state:

```bash
python debug_database_state.py
```

## Troubleshooting

If you encounter issues:

1. **Missing dependencies**: Make sure all required packages are installed
2. **Database connection errors**: Check your DATABASE_URL environment variable
3. **Slack errors**: Ensure SLACK_BOT_TOKEN and SLACK_CHANNEL_ID are set correctly
4. **OpenAI errors**: Verify your OPENAI_API_KEY is valid and set

The LSP errors shown in the editor are due to the IDE not finding the imported packages - these will resolve once the dependencies are installed.

## Next Steps

After implementing this version:

1. Test the full pipeline to ensure markets are properly categorized
2. Make sure option images are correctly captured and stored
3. Update any frontend integrations to use the category field
4. Prepare for smart contract redeployment starting at MarketID 1