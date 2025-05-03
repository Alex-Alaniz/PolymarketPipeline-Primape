"""
Task 2: Capture Approvals from Slack/Discord

This module is responsible for checking the reactions on market posts
and determining which markets have been approved or rejected.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone, timedelta

# Import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.messaging import MessagingClient
from config import DATA_DIR, TMP_DIR, APPROVAL_WINDOW_MINUTES

logger = logging.getLogger("task2")

def run_task(messaging_client: MessagingClient, task1_results: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run Task 2: Capture approvals from Slack/Discord
    
    Args:
        messaging_client: MessagingClient instance for interacting with Slack/Discord
        task1_results: Results from Task 1 containing posted markets
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, Any]]: Approved markets and task statistics
    """
    logger.info("Starting Task 2: Capturing approvals from Slack/Discord")
    
    # Start the clock for this task
    start_time = time.time()
    
    # Dictionary to store statistics
    stats = {
        "task": "task2_capture_approvals",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "markets_checked": 0,
        "markets_approved": 0,
        "markets_rejected": 0,
        "markets_timeout": 0,
        "market_list": [],
        "errors": [],
        "status": "running"
    }
    
    try:
        # Extract market list from task1 results
        if not task1_results or "market_list" not in task1_results:
            logger.error("Invalid task1 results: missing market_list")
            stats["errors"].append("Invalid task1 results: missing market_list")
            stats["status"] = "failed"
            return [], stats
        
        # Get the market list
        markets = task1_results.get("market_list", [])
        
        if not markets:
            logger.warning("No markets to check for approval")
            stats["status"] = "success"  # Still a success, just nothing to do
            return [], stats
        
        # Calculate the approval window
        approval_window = APPROVAL_WINDOW_MINUTES
        
        # Check each market for approval
        approved_markets = []
        
        for market in markets:
            market_id = market.get("market_id", "unknown")
            message_id = market.get("message_id")
            question = market.get("question", "Unknown question")
            
            # Skip markets that don't have a message ID (weren't posted)
            if not message_id:
                logger.warning(f"Skipping market {market_id} - no message ID")
                continue
            
            # Update stats
            stats["markets_checked"] += 1
            
            # Create market entry for statistics
            market_stats = {
                "market_id": market_id,
                "question": question,
                "message_id": message_id,
                "status": "pending"
            }
            
            # Get reactions from the message
            reactions = messaging_client.get_reactions(message_id)
            
            # Check for approval/rejection reactions
            approval_count = reactions.get("white_check_mark", 0)
            rejection_count = reactions.get("x", 0)
            
            # Determine status based on reactions
            if approval_count > 0 and approval_count > rejection_count:
                logger.info(f"Market {market_id} approved (✅: {approval_count}, ❌: {rejection_count})")
                market_stats["status"] = "approved"
                stats["markets_approved"] += 1
                
                # Add to approved markets
                approved_markets.append({
                    "id": market_id,
                    "question": question,
                    "message_id": message_id,
                    "status": "approved"
                })
                
            elif rejection_count > 0:
                logger.info(f"Market {market_id} rejected (✅: {approval_count}, ❌: {rejection_count})")
                market_stats["status"] = "rejected"
                stats["markets_rejected"] += 1
                
            else:
                # Check if it's past the approval window
                post_time = datetime.fromtimestamp(float(message_id), tz=timezone.utc)
                now = datetime.now(timezone.utc)
                time_diff = now - post_time
                
                if time_diff > timedelta(minutes=approval_window):
                    logger.info(f"Market {market_id} timed out (no reactions after {approval_window} minutes)")
                    market_stats["status"] = "timeout"
                    stats["markets_timeout"] += 1
                else:
                    logger.info(f"Market {market_id} still pending approval (within {approval_window} minute window)")
                    market_stats["status"] = "pending"
            
            # Add market stats to the stats list
            stats["market_list"].append(market_stats)
        
        # Create output directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
        
        # Save approved markets to file for persistence
        approved_file = os.path.join(TMP_DIR, f"task2_approved_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(approved_file, 'w') as f:
            json.dump({"markets": approved_markets}, f, indent=2)
        
        # Calculate task duration
        stats["duration"] = time.time() - start_time
        
        # Final status
        stats["status"] = "success"
        
        logger.info(f"Task 2 completed: {stats['markets_approved']} approved, {stats['markets_rejected']} rejected, {stats['markets_timeout']} timed out")
        return approved_markets, stats
        
    except Exception as e:
        # Handle any errors
        logger.error(f"Error in Task 2: {str(e)}")
        stats["errors"].append(f"Task error: {str(e)}")
        stats["status"] = "failed"
        stats["duration"] = time.time() - start_time
        return [], stats