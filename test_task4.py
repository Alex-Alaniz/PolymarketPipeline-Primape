#!/usr/bin/env python3
"""
Test script for Task 4: Deployment to ApeChain + Frontend Push

This script tests the task4_deploy module to validate
that it correctly deploys markets to ApeChain and pushes banners to the frontend.

Usage:
    python test_task4.py
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
logger = logging.getLogger("test_task4")

# Ensure the module can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import the task module
from tasks.task4_deploy import run_task

def main():
    """Run Task 4 test"""
    # Step 1: Create test markets with final approval
    # Either use test markets or load from task3 results if available
    
    task3_results_file = find_latest_task3_results()
    
    if task3_results_file:
        # Use markets approved in task3 if available
        try:
            with open(task3_results_file, 'r') as f:
                task3_results = json.load(f)
                
            logger.info(f"Loaded task3 results from {task3_results_file}")
            final_approved_markets = task3_results.get("final_approved_markets", [])
            
            if not final_approved_markets:
                logger.warning("No final approved markets found in task3 results, using test markets instead")
                final_approved_markets = create_test_markets()
                
        except Exception as e:
            logger.error(f"Error loading task3 results: {str(e)}")
            final_approved_markets = create_test_markets()
    else:
        # Use test markets
        logger.info("No task3 results found, using test markets")
        final_approved_markets = create_test_markets()
        
    if not final_approved_markets:
        logger.error("❌ ERROR: No final approved markets to process")
        return
        
    logger.info(f"Processing {len(final_approved_markets)} final approved markets")

    # Step 2: Run task4 to deploy markets
    logger.info("Running Task 4: Deployment to ApeChain + Frontend Push")
    
    deployed_markets, failed_markets = run_task(final_approved_markets)
    
    # Step 3: Save the results
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deployed_markets": deployed_markets,
        "failed_markets": failed_markets
    }
    
    # Create tmp directory if it doesn't exist
    os.makedirs('tmp', exist_ok=True)
    
    # Save the results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tmp/task4_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    logger.info(f"Results saved to {results_file}")
    
    # Step 4: Display summary
    logger.info("\nTest Summary:")
    logger.info(f"- Markets processed: {len(final_approved_markets)}")
    logger.info(f"- Markets deployed: {len(deployed_markets)}")
    logger.info(f"- Markets failed: {len(failed_markets)}")
    
    if len(deployed_markets) > 0:
        logger.info("- Deployment status: ✅ SUCCESS")
        logger.info("- Overall Task 4 status: ✅ SUCCESS")
    elif len(final_approved_markets) == 0:
        logger.info("- Deployment status: ⚠️ NONE (no markets to deploy)")
        logger.info("- Overall Task 4 status: ✅ SUCCESS (nothing to deploy)")
    else:
        logger.info("- Deployment status: ❌ FAILED (no markets deployed)")
        logger.info("- Overall Task 4 status: ❌ FAILED")

def find_latest_task3_results():
    """Find the latest task3 results file"""
    try:
        # Check if tmp directory exists
        if not os.path.exists('tmp'):
            logger.warning("tmp directory not found")
            return None
            
        # Get all task3 result files
        task3_files = [f for f in os.listdir('tmp') if f.startswith('task3_results_') and f.endswith('.json')]
        
        if not task3_files:
            logger.warning("No task3 result files found")
            return None
            
        # Sort by modification time (newest first)
        task3_files.sort(key=lambda x: os.path.getmtime(os.path.join('tmp', x)), reverse=True)
        
        # Return the newest file
        newest_file = os.path.join('tmp', task3_files[0])
        logger.info(f"Found latest task3 results: {newest_file}")
        return newest_file
        
    except Exception as e:
        logger.error(f"Error finding task3 results: {str(e)}")
        return None

def create_test_markets():
    """Create test markets with final approval and banners"""
    # Get current timestamp for testing
    now = datetime.now()
    
    # Create tmp directory if it doesn't exist
    os.makedirs('tmp', exist_ok=True)
    
    # Create test banner files (1x1 transparent pixel)
    png_data = bytes.fromhex('89504e470d0a1a0a0000000d494844520000000100000001010300000025db56ca00000003504c5445000000a77a3dda0000000174524e530040e6d8660000000a4944415408d76360000000020001e221bc330000000049454e44ae426082')
    
    # Create test banner for market 1
    banner_path_1 = os.path.join('tmp', 'market_btc_100k.png')
    with open(banner_path_1, 'wb') as f:
        f.write(png_data)
        
    # Create test banner for market 2
    banner_path_2 = os.path.join('tmp', 'market_premier_league.png')
    with open(banner_path_2, 'wb') as f:
        f.write(png_data)
    
    return [
        {
            "id": "market_btc_100k",
            "question": "Will Bitcoin reach $100,000 by the end of 2025?",
            "type": "binary",
            "category": "Crypto",
            "sub_category": "Bitcoin",
            "expiry": int(datetime(2025, 12, 31).timestamp() * 1000),
            "options": [
                {"name": "Yes", "probability": 0.65},
                {"name": "No", "probability": 0.35}
            ],
            "banner_path": banner_path_1,
            "status": "final_approved"
        },
        {
            "id": "market_premier_league",
            "question": "Will Manchester City win the Premier League?",
            "type": "binary",
            "category": "Sports",
            "sub_category": "Soccer",
            "expiry": int(datetime(2025, 5, 31).timestamp() * 1000),
            "options": [
                {"name": "Yes", "probability": 0.70},
                {"name": "No", "probability": 0.30}
            ],
            "banner_path": banner_path_2,
            "status": "final_approved"
        }
    ]

if __name__ == "__main__":
    main()