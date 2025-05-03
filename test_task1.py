#!/usr/bin/env python3
"""
Test script for Task 1: Slack Integration + Market Data Fetching

This script runs the task1_fetch_and_post module to test fetching Polymarket data 
and posting to Slack for initial approval.

Usage:
    python test_task1.py
"""

import os
import logging
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_task1")

# Import the task
from tasks.task1_fetch_and_post import run_task

def main():
    """Run Task 1 test"""
    logger.info("Starting Task 1 test: Fetch market data and post to Slack")
    
    # Run the task
    markets = run_task()
    
    # Print results
    logger.info(f"Task 1 completed, posted {len(markets)} markets to Slack")
    
    # Save results to file for reference
    output_dir = "tmp"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f"task1_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "markets_posted": len(markets),
            "markets": markets
        }, f, indent=2)
    
    logger.info(f"Results saved to {output_file}")
    
    return len(markets) > 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)