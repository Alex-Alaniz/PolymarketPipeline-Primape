# Polymarket Pipeline Event-Based Model Implementation Guide

## Overview

This guide outlines the steps to update the pipeline with our new event-based model. The event-based model properly handles the relationship between events (like "UEFA Champions League") and their associated markets (like "Will Arsenal win?").

## Why This Update is Needed

The current model is missing proper event tracking, which causes several issues:
1. We're losing events in the data transformation process
2. Market IDs are being treated as events, causing confusion
3. Banner images and icons are not correctly associated with events and markets
4. Category filtering doesn't connect properly to the frontend

## Implementation Steps

### Step 1: Create Backup (Optional but Recommended)

```bash
pg_dump -U $PGUSER -d $PGDATABASE > polymarket_backup_$(date +%Y%m%d).sql
```

### Step 2: Reset and Setup the New Database Schema

We've created a script to drop all existing tables and create new ones with the proper event-market relationship:

```bash
python reset_and_setup_events_model.py
```

This will:
- Drop all existing tables (you'll be asked to confirm with 'YES')
- Create the new schema with proper event-market relationships
- Set up the initial database structure

### Step 3: Replace Key Files

Replace these files with their updated versions:

1. Replace `models.py` with `models_updated.py`:

```bash
cp models_updated.py models.py
```

2. Add our new transform utility:

```bash
mkdir -p utils
cp utils/transform_market_with_events.py utils/
```

3. Replace the main application file:

```bash
cp main_updated.py main.py
```

4. Use the new pipeline script:

```bash
cp run_pipeline_with_events.py run_pipeline.py
```

### Step 4: Run the Updated Pipeline

Start the application with the new model:

```bash
gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app
```

Then navigate to the web interface and test the functionality:

1. Click "Run Pipeline" to fetch markets and extract events
2. Once markets are fetched, click "Post Pending Batch" to post them to Slack
3. Check Slack for the new format with event information
4. Process approvals as usual

## Database Schema Changes

The main changes to the database schema are:

1. **New Events Table**:
   - Stores information about events like "UEFA Champions League"
   - Contains banner images for the event level
   - Has a category for frontend filtering

2. **Updated Markets Table**:
   - Now references an event via `event_id` foreign key
   - Better handling of options and option images

3. **Updated PendingMarket Table**:
   - Added event_name and event_id fields
   - Added option_images JSON field

## Testing the New Model

To verify the new model is working correctly:

1. Check that events are being correctly extracted:
   ```sql
   SELECT id, name, category FROM events LIMIT 10;
   ```

2. Verify markets are linked to events:
   ```sql
   SELECT m.id, m.question, e.name as event_name, m.event_id 
   FROM markets m JOIN events e ON m.event_id = e.id LIMIT 10;
   ```

3. Confirm option images are being saved:
   ```sql
   SELECT id, question, option_images FROM markets 
   WHERE option_images IS NOT NULL LIMIT 5;
   ```

## Troubleshooting

If you encounter issues:

1. **Database Connection Problems**:
   - Verify environment variables (DATABASE_URL, PGHOST, etc.)
   - Check PostgreSQL is running

2. **Missing Events**:
   - Check the event extraction logic in `utils/transform_market_with_events.py`
   - Verify the events table has entries

3. **Slack Integration**:
   - Confirm SLACK_BOT_TOKEN and SLACK_CHANNEL are set correctly
   - Check the bot has proper permissions

4. **Reset Process Failed**:
   - You can run the SQL commands manually:
   ```sql
   DROP TABLE IF EXISTS events CASCADE;
   DROP TABLE IF EXISTS markets CASCADE;
   /* ... other tables ... */
   ```

## Next Steps

After implementing this updated model:

1. Complete end-to-end tests of the pipeline
2. Update any remaining scripts to use the event-based model
3. Deploy the smart contract with proper category mappings
4. Monitor the system for a few days to ensure stability

The event-based model provides a more accurate representation of the Polymarket data and will support proper frontend filtering and display.