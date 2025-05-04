#!/usr/bin/env python3
"""
Test script for Polymarket pipeline tasks 1-3.

This script runs tasks 1-3 in sequence:
1. Fetch and post markets
2. Capture approvals 
3. Generate banners and get final approval

Usage:
    python test_tasks_1_to_3.py
"""
import os
import sys
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_pipeline")

# Ensure the modules can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

# Import the task modules
from tasks.task1_fetch_and_post import run_task as run_task1
from tasks.task2_capture_approvals import run_task as run_task2
from tasks.task3_generate_banners import run_task as run_task3
from utils.messaging import MessagingClient

def main():
    """Run pipeline test for tasks 1-3"""
    logger.info("Starting pipeline test for tasks 1-3")
    
    # Create results directory
    os.makedirs('tmp', exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"tmp/pipeline_results_{timestamp}.json"
    
    # Initialize results
    results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tasks": {
            "task1": {"status": "pending"},
            "task2": {"status": "pending"},
            "task3": {"status": "pending"}
        },
        "overall_status": "running"
    }
    
    try:
        # Save initial results
        save_results(results, results_file)
        
        # Initialize messaging client
        logger.info("Initializing messaging client...")
        messaging_client = MessagingClient()
        
        # ===== TASK 1: Fetch and Post =====
        logger.info("\n===== TASK 1: Fetch and Post =====")
        markets, stats = run_task1(messaging_client)
        
        if not markets:
            logger.error("❌ Task 1 failed: No active markets found from Polymarket")
            results["tasks"]["task1"] = {
                "status": "failed",
                "error": "No active markets found from Polymarket",
                "markets_count": 0
            }
            results["overall_status"] = "failed"
            save_results(results, results_file)
            return
        
        logger.info(f"✅ Task 1 completed: {len(markets)} markets fetched")
        results["tasks"]["task1"] = {
            "status": "success",
            "markets_count": len(markets)
        }
        save_results(results, results_file)
        
        # ===== TASK 2: Capture Approvals =====
        logger.info("\n===== TASK 2: Capture Approvals =====")
        
        # Prepare task1 results in the format expected by task2
        task1_results = {
            "market_list": markets,
            "stats": stats
        }
        
        # Run Task 2 with a timeout of 1 minute for testing purposes
        logger.info("Starting approval collection with 1 minute timeout...")
        logger.info("Since this is a test, during this time please approve some markets in Slack!")
        
        # Disable auto-approve for testing
        os.environ["AUTO_APPROVE_FOR_TESTING"] = "false"
        
        # Run Task 2 with the messaging client
        approved_markets, task2_stats = run_task2(messaging_client, task1_results)
        
        # Extract the counts from task2's stats
        markets_approved = task2_stats.get("markets_approved", 0)
        markets_rejected = task2_stats.get("markets_rejected", 0) 
        markets_timeout = task2_stats.get("markets_timeout", 0)
        
        # Only use markets that have actually been approved
        test_approved_markets = approved_markets
        
        # If no markets were approved, fail the pipeline
        if not test_approved_markets:
            logger.error("❌ Task 2 failed: No markets were approved")
            results["tasks"]["task2"] = {
                "status": "failed",
                "error": "No markets were approved",
                "approved_count": 0,
                "rejected_count": markets_rejected,
                "timed_out_count": markets_timeout
            }
            results["overall_status"] = "failed"
            save_results(results, results_file)
            return
        
        logger.info(f"✅ Task 2 completed: {markets_approved} markets approved, {markets_rejected} rejected, {markets_timeout} timed out")
        results["tasks"]["task2"] = {
            "status": "success",
            "approved_count": markets_approved,
            "rejected_count": markets_rejected,
            "timed_out_count": markets_timeout,
            "test_approved_count": len(test_approved_markets)
        }
        save_results(results, results_file)
        
        # ===== TASK 3: Generate Banners and Final Approval =====
        logger.info("\n===== TASK 3: Generate Banners and Final Approval =====")
        
        # Prepare task2 results in the format expected by task3
        task2_results = {
            "market_list": test_approved_markets,
            "stats": task2_stats
        }
        
        # Require real approvals (no auto-approval)
        os.environ["AUTO_APPROVE_FOR_TESTING"] = "false"
        
        # Run Task 3 with the messaging client - this will generate banners and require real approval
        final_approved_markets, task3_stats = run_task3(messaging_client, task2_results)
        
        # Extract counts from task3's stats
        markets_final_approved = task3_stats.get("markets_approved", 0)
        markets_final_rejected = task3_stats.get("markets_rejected", 0)
        markets_failed = task3_stats.get("markets_failed", 0)
        
        # Filter markets that have banner paths
        test_final_approved_markets = []
        for market in final_approved_markets:
            if "banner_path" in market and market["banner_path"]:
                test_final_approved_markets.append(market)
        
        # If no markets were approved in the final stage, fail the pipeline
        if not test_final_approved_markets:
            logger.error("❌ Task 3 failed: No markets were approved in the final stage")
            results["tasks"]["task3"] = {
                "status": "failed",
                "error": "No markets were approved in the final stage",
                "final_approved_count": 0,
                "final_rejected_count": markets_final_rejected,
                "failed_count": markets_failed
            }
            results["overall_status"] = "failed"
            save_results(results, results_file)
            return
        
        logger.info(f"✅ Task 3 completed: {markets_final_approved} markets approved with banners, {markets_final_rejected} rejected, {markets_failed} failed")
        results["tasks"]["task3"] = {
            "status": "success",
            "final_approved_count": markets_final_approved,
            "final_rejected_count": markets_final_rejected, 
            "failed_count": markets_failed,
            "test_final_approved_count": len(test_final_approved_markets)
        }
        
        # Pipeline completed successfully up to task 3
        results["overall_status"] = "success"
        save_results(results, results_file)
        
        # ===== FINAL SUMMARY =====
        logger.info("\n===== PIPELINE SUMMARY (TASKS 1-3) =====")
        logger.info(f"- Task 1 (Fetch and Post): ✅ {len(markets)} markets")
        logger.info(f"- Task 2 (Approvals): ✅ {len(test_approved_markets)} markets approved for testing")
        logger.info(f"- Task 3 (Banners): ✅ {len(test_final_approved_markets)} markets with banners")
        logger.info(f"- Overall status: ✅ SUCCESS")
        logger.info(f"- Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed with error: {str(e)}")
        results["overall_status"] = "error"
        results["error"] = str(e)
        save_results(results, results_file)

def save_results(results, file_path):
    """Save results to a JSON file"""
    try:
        with open(file_path, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Results saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

if __name__ == "__main__":
    main()