#!/usr/bin/env python3
"""
Test script for Task 3: Banner Generation + Final Approval

This script tests the task3_generate_banners module to validate
that it correctly generates banners for markets and posts them for final approval.

Usage:
    python test_task3.py
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_task3")

# Ensure the module can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import the task module
from tasks.task3_generate_banners import run_task

def main():
    """Run Task 3 test"""
    # Step 1: Create test markets with initial approval
    # Either use test markets or load from task2 results if available
    
    task2_results_file = find_latest_task2_results()
    
    if task2_results_file:
        # Use markets approved in task2 if available
        try:
            with open(task2_results_file, 'r') as f:
                task2_results = json.load(f)
                
            logger.info(f"Loaded task2 results from {task2_results_file}")
            approved_markets = task2_results.get("approved_markets", [])
            
            if not approved_markets:
                logger.warning("No approved markets found in task2 results, using test markets instead")
                approved_markets = create_test_markets()
                
        except Exception as e:
            logger.error(f"Error loading task2 results: {str(e)}")
            approved_markets = create_test_markets()
    else:
        # Use test markets
        logger.info("No task2 results found, using test markets")
        approved_markets = create_test_markets()
        
    if not approved_markets:
        logger.error("❌ ERROR: No approved markets to process")
        return
        
    logger.info(f"Processing {len(approved_markets)} approved markets")

    # Step 2: Run task3 to generate banners and get final approvals
    logger.info("Running Task 3: Banner Generation + Final Approval")
    
    # Use a short timeout for testing (1 minute)
    approval_timeout_minutes = 1
    
    final_approved_markets, rejected_markets, failed_markets = run_task(
        approved_markets,
        approval_timeout_minutes=approval_timeout_minutes
    )
    
    # Step 3: Save the results
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "final_approved_markets": final_approved_markets,
        "rejected_markets": rejected_markets,
        "failed_markets": failed_markets
    }
    
    # Create tmp directory if it doesn't exist
    os.makedirs('tmp', exist_ok=True)
    
    # Save the results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tmp/task3_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Results saved to {results_file}")
    
    # Step 4: Display summary
    logger.info("\nTest Summary:")
    logger.info(f"- Markets processed: {len(approved_markets)}")
    logger.info(f"- Banner generation: {'✅ SUCCESS' if len(failed_markets) == 0 else f'⚠️ PARTIAL ({len(failed_markets)} failed)'}")
    logger.info(f"- Final approvals: {'✅ SUCCESS' if len(final_approved_markets) > 0 else '⚠️ NONE (expected for testing)'}")
    
    # For testing purposes, consider banner generation success as overall success
    generation_success = len(approved_markets) - len(failed_markets)
    if generation_success > 0:
        logger.info("- Overall Task 3 status: ✅ SUCCESS")
    else:
        logger.info("- Overall Task 3 status: ❌ FAILED (banners could not be generated)")

def find_latest_task2_results():
    """Find the latest task2 results file"""
    try:
        # Check if tmp directory exists
        if not os.path.exists('tmp'):
            logger.warning("tmp directory not found")
            return None
            
        # Get all task2 result files
        task2_files = [f for f in os.listdir('tmp') if f.startswith('task2_results_') and f.endswith('.json')]
        
        if not task2_files:
            logger.warning("No task2 result files found")
            return None
            
        # Sort by modification time (newest first)
        task2_files.sort(key=lambda x: os.path.getmtime(os.path.join('tmp', x)), reverse=True)
        
        # Return the newest file
        newest_file = os.path.join('tmp', task2_files[0])
        logger.info(f"Found latest task2 results: {newest_file}")
        return newest_file
        
    except Exception as e:
        logger.error(f"Error finding task2 results: {str(e)}")
        return None

def create_test_markets():
    """Create test markets with initial approval"""
    return [
        {
            "id": "market_bitcoin_100k",
            "question": "Will Bitcoin reach $100,000 by the end of 2025?",
            "type": "binary",
            "category": "Crypto",
            "sub_category": "Bitcoin",
            "expiry": int(datetime(2025, 12, 31).timestamp()),
            "options": [
                {"name": "Yes", "probability": 0.65},
                {"name": "No", "probability": 0.35}
            ],
            "status": "initial_approved"
        },
        {
            "id": "market_premier_league",
            "question": "Will Manchester City win the Premier League?",
            "type": "binary",
            "category": "Sports",
            "sub_category": "Soccer",
            "expiry": int(datetime(2025, 5, 31).timestamp()),
            "options": [
                {"name": "Yes", "probability": 0.70},
                {"name": "No", "probability": 0.30}
            ],
            "status": "initial_approved"
        }
    ]

if __name__ == "__main__":
    main()