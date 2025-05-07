#!/bin/bash
# Run the daily pipeline with proper environment setup

# Change to the project directory (adjust as needed)
cd "$(dirname "$0")"

# Source the environment variables if using .env file
if [ -f ".env" ]; then
    echo "Loading environment variables from .env"
    set -a
    source .env
    set +a
fi

# Run the daily pipeline
echo "Starting daily pipeline at $(date)"
python daily_pipeline.py
exit_code=$?

echo "Pipeline completed with exit code $exit_code at $(date)"
exit $exit_code