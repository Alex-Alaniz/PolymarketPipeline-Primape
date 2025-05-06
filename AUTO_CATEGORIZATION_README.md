# Polymarket Auto-Categorization Pipeline

This document explains the new auto-categorization flow added to the Polymarket pipeline.

## Overview

Markets are now automatically categorized by GPT-4o-mini before they're posted to Slack. Each market is assigned one of the following categories:
- politics
- crypto
- sports
- business
- culture
- news
- tech
- all (default/fallback)

The categorized markets are stored in a new `pending_markets` table until approval, and approvals are logged in the new `approvals_log` table.

## New Pipeline Flow

1. **Fetch markets** from Polymarket API
   - Filter active, non-expired markets with banner/icon URLs
   
2. **Categorize markets** with GPT-4o-mini
   - Prompt: "Market: {question}. Pick ONE: [politics,crypto,sports,business,culture,news,tech,all]. Return the word only."
   - Temperature: 0, max_tokens: 1 (for efficient categorization)
   
3. **Store in pending_markets table**
   - Store complete market data with assigned category
   
4. **Post to Slack with category badges**
   - Add category emoji (🗳️ politics, 🪙 crypto, 🏅 sports, etc.)
   - Include approval reaction buttons (✅/❌)
   
5. **Poll Slack for approvals/rejections**
   - ✅ → Approve market, create entry in `markets` table with relevant data
   - ❌ → Reject market, remove from `pending_markets`
   - No reaction for 7+ days → Auto-reject, remove from `pending_markets`
   
6. **Continue existing flow** for approved markets
   - Image generation, ApeChain deployment, etc. remains unchanged

## Database Schema Changes

Two new tables have been added:

1. **pending_markets**
   - `poly_id` (PK): Polymarket condition ID
   - `question`: Market question text
   - `category`: AI-assigned category
   - `banner_url`: URL to banner image
   - `icon_url`: URL to icon image
   - `options`: JSON array of options
   - `expiry`: Expiry timestamp
   - `slack_message_id`: Slack message ID for approval tracking
   - `raw_data`: Complete raw market data
   - `needs_manual_categorization`: Flag for markets that failed auto-categorization
   - `fetched_at`: Timestamp when market was fetched
   - `updated_at`: Last update timestamp

2. **approvals_log**
   - `id` (PK): Auto-incrementing ID
   - `poly_id`: Polymarket condition ID
   - `slack_msg_id`: Slack message ID
   - `reviewer`: User ID of reviewer
   - `decision`: Approval decision ('approved', 'rejected', 'timeout')
   - `created_at`: Timestamp when decision was made

## New Scripts

The following new scripts have been added:

1. **utils/market_categorizer.py**
   - Implements GPT-4o-mini categorization functionality
   - Includes retry logic with exponential backoff
   
2. **fetch_and_categorize_markets.py**
   - Fetches markets from API, categorizes them, and posts to Slack
   - Handles filtration, categorization, storage, and posting
   
3. **check_pending_market_approvals.py**
   - Polls Slack for approvals/rejections on pending markets
   - Updates database based on decisions
   - Creates market entries for approved markets
   
4. **new_pipeline.py**
   - Updated pipeline orchestrator that integrates the new auto-categorization flow
   - Maintains all existing functionality while adding new steps
   
5. **init_db_new_tables.py**
   - Helper script to initialize the new database tables
   - Can be run without affecting existing data
   
6. **reset_db_for_testing.py**
   - Safe database reset that preserves deployed markets
   - Useful for testing the new flow
   
7. **test_auto_categorization.py**
   - Simple test for the GPT-4o-mini categorization function
   - Helps verify API connectivity and expected behavior

## Setup Instructions

1. Run the database initialization script:
   ```
   python init_db_new_tables.py
   ```

2. Test the categorization functionality:
   ```
   python test_auto_categorization.py
   ```

3. Run the new pipeline:
   ```
   python new_pipeline.py
   ```

## Technical Notes

- GPT-4o-mini was chosen for its balance of accuracy and cost (<$0.0002 per market)
- The categorization uses retry logic with exponential backoff to handle API rate limits
- All database operations maintain data integrity by preserving deployed markets
- The Slack message format has been enhanced with rich formatting and category badges