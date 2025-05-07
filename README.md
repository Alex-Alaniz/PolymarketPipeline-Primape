# Polymarket Pipeline

## Overview
This application is an AI-powered blockchain prediction market platform that automates the process of fetching, categorizing, approving, and deploying markets from Polymarket to Apechain. It leverages a multi-step pipeline with AI categorization, human approval workflows via Slack, and blockchain integration.

## Core Features
- Fetches prediction markets from Polymarket's public API
- Categorizes markets using GPT-4o-mini AI
- Posts markets to Slack for human approval
- Generates market banner images
- Deploys approved markets to the Apechain blockchain
- Groups related markets into events
- Provides a web UI to monitor and control the pipeline

## Main Components

### 1. Web Interface
The application provides a web UI at the root URL (`/`) that shows:
- Current pipeline status
- Options to run different pipeline stages
- Recent pipeline logs

### 2. Pipeline Stages
The pipeline consists of several distinct stages:

1. **Fetch Markets**: Gets markets from Polymarket API
2. **Filter Active Markets**: Removes expired/closed markets
3. **AI Categorization**: Uses OpenAI to categorize markets
4. **Post to Slack**: Sends markets to Slack for human approval
5. **Check Approvals**: Monitors Slack for approval/rejection reactions
6. **Image Generation**: Creates banner images for approved markets
7. **Deployment Approval**: Final QA check before blockchain deployment
8. **Deploy to Apechain**: Sends approved markets to the blockchain

### 3. API Endpoints
The application provides API endpoints at `/api` for frontend integration:
- `/api/status` - Get pipeline status
- `/api/markets` - Get all deployed markets
- `/api/categories` - Get market categories and counts
- `/api/market/<id>` - Get details for a specific market
- `/api/events` - Get all events and related markets

## How to Use

### Running the Pipeline
1. Access the web UI at the root URL (`/`)
2. Use the control buttons to run different stages of the pipeline:
   - **Run Pipeline**: Runs the complete pipeline from fetching to approval checking
   - **Check Market Approvals**: Checks Slack for market approval reactions
   - **Post Next Batch**: Posts the next batch of markets to Slack
   - **Check Deployment Approvals**: Checks for final approval before deployment

### API Usage
You can use the API endpoints to integrate with a frontend:
```
GET /api/markets?category=sports
GET /api/market/12345
GET /api/events
```

## Key Files

- `main.py` - Main entry point and web UI
- `pipeline.py` - Core pipeline orchestration logic
- `models.py` - Database models
- `api_routes.py` - API endpoints for frontend integration
- `filter_active_markets.py` - Market filtering functions
- `check_market_approvals.py` - Slack approval checking

## Environment Variables

Required environment variables:
- `DATABASE_URL` - PostgreSQL database connection string
- `OPENAI_API_KEY` - OpenAI API key for categorization
- `SLACK_BOT_TOKEN` - Slack API token for posting markets
- `SLACK_CHANNEL_ID` - Slack channel to post markets to

## Integration Workflows

The application supports integration with:
- **Slack** for human approvals
- **OpenAI** for AI-powered categorization
- **Apechain** blockchain for market deployment