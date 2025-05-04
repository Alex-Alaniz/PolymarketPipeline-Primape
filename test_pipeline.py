#!/usr/bin/env python3
"""
Test script for the full Polymarket pipeline.

This script runs the complete pipeline from start to finish,
testing all four tasks in sequence.

Usage:
    python test_pipeline.py
"""
import os
import sys
import json
import logging
import time
from datetime import datetime
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
from tasks.task4_deploy import run_task as run_task4

# Import utilities
from utils.messaging import MessagingClient

def main():
    """Run the full pipeline test"""
    logger.info("Starting full pipeline test")
    
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
            "task3": {"status": "pending"},
            "task4": {"status": "pending"}
        },
        "overall_status": "running"
    }
    
    try:
        # ===== TASK 1: Fetch and post to Slack =====
        logger.info("\n===== TASK 1: Fetch and post to Slack =====")
        
        # Initialize messaging client
        messaging_client = MessagingClient()
        logger.info(f"Initialized messaging client for platform: {messaging_client.platform}")
        
        # Set configuration to limit markets posted during test
        import config
        config.MAX_MARKETS_TO_POST = 2  # Only post 2 markets during test
        
        # Run Task 1 with the messaging client
        posted_markets, stats = run_task1(messaging_client)
        markets = posted_markets
        
        if not markets:
            logger.error("❌ Task 1 failed: No markets returned")
            results["tasks"]["task1"] = {
                "status": "failed",
                "error": "No markets returned",
                "markets_count": 0
            }
            results["overall_status"] = "failed"
            save_results(results, results_file)
            return
        
        logger.info(f"✅ Task 1 completed: {len(markets)} markets posted to Slack")
        results["tasks"]["task1"] = {
            "status": "success",
            "markets_count": len(markets)
        }
        save_results(results, results_file)
        
        # ===== TASK 2: Capture Approvals =====
        logger.info("\n===== TASK 2: Capture Approvals =====")
        
        # Prepare task1 results in the format expected by task2
        task1_results = {
            "markets": markets,
            "stats": stats
        }
        
        # Run Task 2 with the messaging client
        approved_markets, task2_stats = run_task2(messaging_client, task1_results)
        
        # Extract the counts from task2's stats
        markets_approved = task2_stats.get("markets_approved", 0)
        markets_rejected = task2_stats.get("markets_rejected", 0) 
        markets_timeout = task2_stats.get("markets_timeout", 0)
        
        # For testing, consider timed out markets as approved
        # In a real scenario, we'd wait longer for actual approvals
        test_approved_markets = approved_markets
        
        if not test_approved_markets:
            logger.error("❌ Task 2 failed: No markets approved")
            results["tasks"]["task2"] = {
                "status": "failed",
                "error": "No markets approved",
                "approved_count": markets_approved,
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
            "markets": test_approved_markets,
            "stats": task2_stats
        }
        
        # Run Task 3 with the messaging client
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
        
        if not test_final_approved_markets:
            logger.error("❌ Task 3 failed: No markets with banners")
            results["tasks"]["task3"] = {
                "status": "failed",
                "error": "No markets with banners",
                "final_approved_count": markets_final_approved,
                "final_rejected_count": markets_final_rejected,
                "failed_count": markets_failed,
                "test_final_approved_count": 0
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
        save_results(results, results_file)
        
        # ===== TASK 4: Deployment =====
        logger.info("\n===== TASK 4: Deployment =====")
        
        # Prepare task3 results in the format expected by task4
        task3_results = {
            "markets": test_final_approved_markets,
            "stats": task3_stats
        }
        
        # Run Task 4 with the messaging client
        deployed_markets, task4_stats = run_task4(messaging_client, task3_results)
        
        # Extract counts from task4's stats
        markets_deployed = task4_stats.get("markets_deployed", 0)
        markets_deployment_failed = task4_stats.get("markets_failed", 0)
        
        if not deployed_markets:
            logger.error("❌ Task 4 failed: No markets deployed")
            results["tasks"]["task4"] = {
                "status": "failed",
                "error": "No markets deployed",
                "deployed_count": 0,
                "failed_count": markets_deployment_failed
            }
            results["overall_status"] = "failed"
            save_results(results, results_file)
            return
        
        logger.info(f"✅ Task 4 completed: {markets_deployed} markets deployed, {markets_deployment_failed} failed")
        results["tasks"]["task4"] = {
            "status": "success",
            "deployed_count": markets_deployed,
            "failed_count": markets_deployment_failed
        }
        
        # Pipeline completed successfully
        results["overall_status"] = "success"
        save_results(results, results_file)
        
        # ===== FINAL SUMMARY =====
        logger.info("\n===== PIPELINE SUMMARY =====")
        logger.info(f"- Task 1 (Fetch and Post): ✅ {len(markets)} markets")
        logger.info(f"- Task 2 (Approvals): ✅ {len(test_approved_markets)} markets approved for testing")
        logger.info(f"- Task 3 (Banners): ✅ {len(test_final_approved_markets)} markets with banners")
        logger.info(f"- Task 4 (Deployment): ✅ {len(deployed_markets)} markets deployed")
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