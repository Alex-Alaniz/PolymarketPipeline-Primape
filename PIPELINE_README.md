# Polymarket Pipeline

This README provides an overview of the Polymarket pipeline, which processes markets from Polymarket's API, groups them by events, posts them for approval in Slack, and deploys approved markets to Apechain.

## Pipeline Overview

The pipeline includes the following stages:

1. **Fetch Markets**: Retrieve active markets from Polymarket API
2. **Categorize Markets**: Assign categories and detect event relationships
3. **Post to Slack**: Submit markets for approval via Slack
4. **Process Approvals**: Handle approvals/rejections and create market entries
5. **Generate Images**: Create banners and icon images for approved markets
6. **Deploy to Apechain**: Deploy approved markets to the blockchain
7. **Update Frontend**: Update frontend with market data and images

## Event Relationships

The pipeline implements an event relationship model that groups related markets together. For example, all markets related to the "FIFA World Cup 2026" would share the same event ID and name.

See [EVENT_MODEL_IMPLEMENTATION_GUIDE.md](./EVENT_MODEL_IMPLEMENTATION_GUIDE.md) for detailed information on the event model.

## Database Structure

The pipeline uses several database tables:

- **pending_markets**: Markets pending approval
- **markets**: Approved markets ready for deployment
- **processed_markets**: Record of all markets that have been processed
- **approvals_log**: Record of approval/rejection decisions

All tables that store market data include `event_id` and `event_name` fields to maintain event relationships.

## Utility Scripts

The pipeline includes various utility scripts for testing, monitoring, and debugging:

### Market Inspection
- `check_markets.py`: Display all markets in the database
- `check_pending_markets.py`: Display all pending markets
- `inspect_pending_markets.py`: Detailed inspection of pending markets

### Event Relationship Tools
- `check_events.py`: Show markets grouped by events
- `check_shared_events.py`: Find events with multiple markets 
- `inspect_events.py`: Detailed inspection of specific events

### Approval Workflow
- `test_approval_script.py`: Test market approval workflow
- `check_approval_logs.py`: View approval logs and clean up approved markets

### End-to-End Testing
- `run_end_to_end_test.py`: Test the full pipeline workflow
- `insert_multiple_test_markets.py`: Create test markets with proper event relationships

### Database Management  
- `add_event_fields_migration.py`: Ensure database tables have event fields
- `clean_pending_approved_markets.py`: Remove pending markets that have been approved

## Running the Pipeline

To run the full pipeline:

```bash
# Fetch, categorize, and post markets to Slack
python pipeline.py

# Process approvals from Slack
python check_pending_market_approvals.py

# Deploy approved markets to Apechain
python deploy_approved_markets.py
```

For development and testing, you can use:

```bash
# Run an end-to-end test of the pipeline
python run_end_to_end_test.py

# Insert test markets with event relationships
python insert_multiple_test_markets.py
```

## Monitoring and Debugging

To monitor the pipeline status:

```bash
# Check markets in the database
python check_markets.py

# Check pending markets
python check_pending_markets.py

# View event relationships
python check_events.py

# Inspect specific events
python inspect_events.py --event EVENT_ID
```

## Configuration

The pipeline uses environment variables for configuration:

- **DATABASE_URL**: PostgreSQL database connection
- **SLACK_BOT_TOKEN**: Slack API token for posting messages
- **SLACK_CHANNEL_ID**: Slack channel for market approvals
- **APECHAIN_RPC_URL**: RPC URL for Apechain blockchain
- **WALLET_PRIVATE_KEY**: Private key for signing transactions
- **WALLET_ADDRESS**: Wallet address for deploying markets
- **OPENAI_API_KEY**: OpenAI API key for market categorization

## Known Issues and Limitations

- The pipeline assumes all markets in an event belong to the same category
- Event detection is primarily keyword-based and may miss some relationships
- Cross-category events are not currently supported