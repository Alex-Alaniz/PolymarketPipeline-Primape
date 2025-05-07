# Polymarket Pipeline Usage Guide

This guide explains how to use the updated pipeline for fetching and processing markets from Polymarket.

## Initial Setup (First-time Only)

Before running the pipeline for the first time, you need to set up the database schema with the event-based model:

```bash
python reset_and_setup_events_model.py
```

This will create the necessary tables in the database to handle both binary markets and event markets.

## Daily Pipeline Execution

### Step 1: Run the Pipeline

Run the pipeline script to fetch, categorize, and post markets to Slack:

```bash
./run_daily_pipeline.sh
```

This script will:
1. Fetch binary markets from the Markets API
2. Fetch event markets from the Events API
3. Filter out markets that are already in the database
4. Categorize new markets using GPT-4o-mini
5. Store markets in the database with proper event relationships
6. Post markets to Slack for approval

#### Command-line Options

You can customize the pipeline by running it directly with options:

```bash
python run_pipeline_with_events.py --max-markets 20 --max-events 10
```

Options:
- `--max-markets`: Maximum number of binary markets to process (default: 20)
- `--max-events`: Maximum number of events to process (default: 10)

### Step 2: Process Approvals

After markets have been posted to Slack and received approvals/rejections, run:

```bash
python check_pending_approvals.py
```

This script will check Slack for approval reactions and update the database accordingly.

### Step 3: Deploy Approved Markets

Once markets have been approved, deploy them to the blockchain:

```bash
python deploy_event_markets.py
```

This script will:
1. Find markets ready for deployment
2. Deploy them to Apechain
3. Update the database with deployment status and Apechain market IDs

## Monitoring and Troubleshooting

### Check Pipeline Status

To check the status of the pipeline:

```bash
python check_pipeline_status.py
```

### View Database State

To see current markets in the database:

```bash
python check_markets.py  # View all markets
python check_events.py   # View event relationships
```

### Error Recovery

If the pipeline fails, check the logs directory for detailed error messages:

```bash
ls -l logs/
```

Individual log files are named with timestamps to help track issues over time.