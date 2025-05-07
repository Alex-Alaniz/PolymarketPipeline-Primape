#!/bin/bash
# Run the daily pipeline with proper environment setup
# This is a production script, not a test script

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

# Run the production pipeline
echo "Starting production pipeline at $(date)"
python run_pipeline_with_events.py

# Check exit code
exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Pipeline completed successfully at $(date)"
else
    echo "Pipeline failed with exit code $exit_code at $(date)"
fi

exit $exit_code