# Architecture Overview

## Overview

This application is a pipeline system for managing Polymarket data, focusing on the workflow of fetching market information from Polymarket API, submitting it for approval through Slack, generating banner images, and ultimately deploying approved markets to ApeChain (a blockchain platform). The system implements a multi-stage approval process with human verification steps integrated via Slack.

The application is built as a Flask-based web service with PostgreSQL for data persistence and integrates with several external services including Slack, OpenAI (for image generation), GitHub (for frontend image assets), and ApeChain (blockchain).

## System Architecture

The system follows a modular architecture with distinct components that handle specific stages of the market approval pipeline:

```
┌───────────────┐    ┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  Market Data  │    │  Initial      │    │  Banner       │    │  Deployment   │
│  Fetching     │───▶│  Approval     │───▶│  Generation   │───▶│  to ApeChain  │
│  Module       │    │  Module       │    │  & Approval   │    │  Module       │
└───────────────┘    └───────────────┘    └───────────────┘    └───────────────┘
        │                    │                    │                    │
        ▼                    ▼                    ▼                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                              Database Layer                                    │
└───────────────────────────────────────────────────────────────────────────────┘
        ▲                    ▲                    ▲                    ▲
        │                    │                    │                    │
┌───────────────────────────────────────────────────────────────────────────────┐
│                         External Service Integrations                          │
│   (Polymarket API, Slack, OpenAI, GitHub, ApeChain Blockchain)                │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Key Components

1. **Web Service Layer**
   - Flask application providing the web interface and API endpoints
   - Handles pipeline execution, scheduling, and status reporting
   - Serves as the entry point for manual pipeline triggers and monitoring

2. **Pipeline Modules**
   - Market Data Fetching: Retrieves data from Polymarket API
   - Market Approval: Processes initial approvals from Slack
   - Image Generation: Creates banner images and handles final approval
   - Blockchain Deployment: Deploys approved markets to ApeChain

3. **Database Layer**
   - PostgreSQL database for persistent storage
   - Tracks markets, approval status, and pipeline execution history
   - Maintains the state of the pipeline to handle interruptions gracefully

4. **External Service Integrations**
   - Slack for human approval workflows
   - OpenAI for banner image generation
   - GitHub for storing and managing frontend assets
   - ApeChain for blockchain deployment

## Database Schema

The database schema is centered around tracking markets through various stages of the pipeline:

### Main Tables

1. **Markets** - Stores approved market data ready for deployment
   - Primary keys: `id` (String)
   - Key fields: `question`, `type`, `category`, `expiry`, `status`, `banner_uri`, `apechain_market_id`

2. **ProcessedMarket** - Tracks markets posted for initial approval
   - Fields for tracking Slack message IDs and approval status

3. **ApprovalEvent** - Logs approval events for audit purposes
   - Tracks who approved/rejected markets and when

4. **PipelineRun** - Records pipeline execution history
   - Stores metrics on processing time, success/failure counts, etc.

## Data Flow

The flow of data through the system follows these stages:

1. **Fetch Stage** 
   - Markets are fetched from Polymarket API
   - Data is filtered to include only active, non-expired markets
   - Duplicate markets are identified and grouped when appropriate
   - New markets (not previously processed) are selected for approval

2. **Initial Approval Stage**
   - Selected markets are posted to Slack for initial approval
   - Human reviewers approve or reject markets using Slack reactions
   - Approved markets are recorded in the database for the next stage

3. **Banner Generation Stage**
   - For approved markets, banner images are generated using OpenAI
   - Generated banners are posted to Slack for final approval
   - Approved banners are stored for frontend integration

4. **Deployment Stage**
   - Markets with approved banners are deployed to ApeChain blockchain
   - Banner images are pushed to the frontend repository
   - Market status is updated in the database

## External Dependencies

The system integrates with several external services:

1. **Polymarket API**
   - Source of market data
   - Accessed via REST API endpoints
   - Base URL: `https://strapi-matic.poly.market/api`

2. **Slack**
   - Used for human approval workflow
   - Requires bot token with appropriate scopes (chat:write, files:write, etc.)
   - Messages include reactions for approval/rejection

3. **OpenAI**
   - Used for generating banner images for markets
   - Requires API key with appropriate permissions

4. **GitHub**
   - Used for storing banner images for frontend integration
   - Repository configured via environment variables

5. **ApeChain Blockchain**
   - Destination for approved markets
   - Accessed via RPC endpoint
   - Requires private key for transaction signing

## Deployment Strategy

The application is designed to be deployed as a containerized service:

1. **Deployment Platform**
   - Configured for autoscaling deployment via Replit
   - Uses gunicorn as the WSGI server

2. **Environment Configuration**
   - Environment variables for API keys, tokens, and configuration
   - Sensitive credentials stored as secrets

3. **Database**
   - PostgreSQL 16 for data persistence
   - Connection configured via environment variables

4. **Monitoring and Logging**
   - Comprehensive logging throughout the pipeline
   - Status API endpoints for monitoring pipeline health
   - Pipeline execution metrics stored in the database

## Security Considerations

1. **API Keys and Credentials**
   - Stored as environment variables or secrets
   - Not hard-coded in the codebase

2. **Blockchain Private Key**
   - Used for signing transactions on ApeChain
   - Stored as an environment variable (should be secured as a secret)

3. **Approval Process**
   - Multi-stage human approval workflow to prevent erroneous deployments
   - Audit trail of approvals stored in the database

## Future Extensions

The modular architecture allows for several potential extensions:

1. **Additional Data Sources**
   - The pipeline could be extended to include other market data sources

2. **Enhanced Banner Generation**
   - More sophisticated image generation techniques could be implemented

3. **Automated Testing**
   - Additional test coverage for pipeline components
   - Integration tests for external service interactions

4. **Performance Optimizations**
   - Batch processing for markets
   - Caching of frequently accessed data