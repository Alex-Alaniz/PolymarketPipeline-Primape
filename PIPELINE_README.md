# Polymarket Pipeline Documentation

## Overview
This pipeline fetches markets from Polymarket's public API, categorizes them with GPT-4o-mini, groups related markets by events, posts them to Slack for approval, and deploys approved markets to the Apechain smart contract.

## Pipeline Flow
1. **Fetch Markets**: Use `fetch_gamma_markets.py` to get markets from Polymarket's Gamma API
2. **Transform Markets**: Use `utils/transform_market_with_events.py` to detect events and group related markets
3. **Post to Slack**: Use `post_unposted_pending_markets.py` to post markets to Slack for approval
4. **Check Approvals**: Use `check_pending_market_approvals.py` to process approvals/rejections
5. **Generate Images**: Generate banner images for approved markets
6. **Post Images**: Post banner images to Slack for approval
7. **Check Image Approvals**: Use `check_image_approvals.py` to process image approvals
8. **Deploy**: Use `check_deployment_approvals.py` for final approval and deployment to Apechain
9. **Track IDs**: Use `track_market_id_after_deployment.py` to update database with Apechain market IDs

## Core Files

### Fetching
- **fetch_gamma_markets.py**: Main fetcher that connects to Polymarket Gamma API
- **utils/transform_market_with_events.py**: Transforms markets and detects events

### Categorization
- **utils/batch_categorizer.py**: Categorizes markets in batch using GPT-4o-mini
- **utils/market_categorizer.py**: Individual market categorization (fallback)

### Slack Integration
- **utils/messaging.py**: Core messaging utilities for Slack
- **post_unposted_pending_markets.py**: Posts pending markets to Slack
- **check_pending_market_approvals.py**: Processes market approvals
- **check_image_approvals.py**: Processes image approvals
- **check_deployment_approvals.py**: Final deployment approval

### Deployment
- **utils/apechain.py**: Interacts with Apechain smart contract
- **utils/deployment_formatter.py**: Formats messages for deployment
- **track_market_id_after_deployment.py**: Updates database with market IDs

### Coordination
- **pipeline.py**: Main coordinator that orchestrates all pipeline steps

## Event Handling
The `transform_market_with_events.py` module detects and processes events by:

1. Extracting event information from market titles and descriptions
2. Creating unique event IDs based on event names
3. Grouping related markets under the same event
4. Ensuring proper mapping between events, markets, and options

## Database Structure
The database tracks markets through various stages:

1. **PendingMarket**: Markets fetched from API awaiting approval
2. **ProcessedMarket**: Tracked markets to prevent reprocessing
3. **Market**: Approved markets ready for deployment
4. **ApprovalEvent**: Log of all approval actions
5. **PipelineRun**: Records of pipeline execution runs

## Environment Setup
Required environment variables:
- `DATABASE_URL`: PostgreSQL database connection string
- `SLACK_BOT_TOKEN`: Slack API token for posting messages
- `SLACK_CHANNEL_ID`: Slack channel for market approvals
- `OPENAI_API_KEY`: OpenAI API key for categorization
- `APECHAIN_RPC_URL`: Apechain blockchain RPC endpoint
- `WALLET_PRIVATE_KEY`: Private key for transaction signing
- `WALLET_ADDRESS`: Address for deploying markets

## Running the Pipeline
To run the complete pipeline:
```
python pipeline.py
```

To run individual steps:
```
python fetch_gamma_markets.py
python post_unposted_pending_markets.py
python check_pending_market_approvals.py
```

## Error Handling
The pipeline includes robust error handling:
- Network connectivity issues are logged and retried
- API rate limits are handled with exponential backoff
- Database transactions use proper commit/rollback
- Failed markets are tracked and can be reprocessed

## Security Notes
- Never display or expose the WALLET_PRIVATE_KEY
- Deployed markets must NEVER be removed from the database as they represent real assets on the blockchain
- All user interactions are logged in the ApprovalEvent table for audit purposes