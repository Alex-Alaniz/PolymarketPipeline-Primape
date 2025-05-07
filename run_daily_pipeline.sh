#!/bin/bash
# Polymarket Event Pipeline - Daily Production Run
# This script runs the daily pipeline to fetch and process markets from Polymarket
# It handles both binary markets and event-based markets

# Change to the project directory
cd "$(dirname "$0")"

# Source environment variables if .env exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env"
    set -a
    source .env
    set +a
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Run the production pipeline to fetch and categorize markets
echo "Stage 1: Starting main market pipeline at $(date)"
echo "- Fetching binary markets from Markets API"
echo "- Fetching event markets from Events API" 
echo "- Categorizing and transforming markets"
echo "- Storing in database and posting to Slack"
python run_pipeline_with_events.py

# Check exit code for the main pipeline
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Pipeline completed successfully at $(date)"
    
    # Reminder for next steps
    echo ""
    echo "=============== NEXT STEPS ==============="
    echo "When markets have been approved/rejected in Slack, run:"
    echo "python check_pending_approvals.py"
    echo ""
    echo "To deploy approved markets to Apechain, run:"
    echo "python deploy_event_markets.py"
    echo "=========================================="
else
    echo "Pipeline failed with exit code $exit_code at $(date)"
fi

exit $exit_code