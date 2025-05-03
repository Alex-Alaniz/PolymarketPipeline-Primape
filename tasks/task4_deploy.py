"""
Task 4: Deploy Markets to ApeChain and Frontend

This module is responsible for deploying approved markets to the ApeChain blockchain
and pushing banner images to the frontend repository.
"""

import os
import sys
import json
import logging
import time
import shutil
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

# Import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.messaging import MessagingClient
from config import DATA_DIR, TMP_DIR

logger = logging.getLogger("task4")

def run_task(messaging_client: MessagingClient, task3_results: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run Task 4: Deploy markets to ApeChain and push banners to frontend
    
    Args:
        messaging_client: MessagingClient instance for posting updates
        task3_results: Results from Task 3 containing markets with banners
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, Any]]: Deployed markets and task statistics
    """
    logger.info("Starting Task 4: Deploying markets to ApeChain and frontend")
    
    # Start the clock for this task
    start_time = time.time()
    
    # Dictionary to store statistics
    stats = {
        "task": "task4_deploy",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "markets_processed": 0,
        "banners_deployed": 0,
        "markets_deployed": 0,
        "market_list": [],
        "errors": [],
        "status": "running"
    }
    
    try:
        # Extract market list from task3 results
        if not task3_results or "market_list" not in task3_results:
            logger.error("Invalid task3 results: missing market_list")
            stats["errors"].append("Invalid task3 results: missing market_list")
            stats["status"] = "failed"
            return [], stats
        
        # Get the market list
        markets = task3_results.get("market_list", [])
        
        # Filter only markets with banners posted
        approved_markets = [m for m in markets if m.get("status") == "posted"]
        
        if not approved_markets:
            logger.warning("No markets with banners to deploy")
            stats["status"] = "success"  # Still a success, just nothing to do
            return [], stats
        
        # Import Github and blockchain utilities here to avoid circular imports
        from utils.github import GitHubClient
        from utils.blockchain import BlockchainClient
        
        # Initialize clients
        github_client = GitHubClient()
        blockchain_client = BlockchainClient()
        
        # Process each approved market
        deployed_markets = []
        
        for market in approved_markets:
            market_id = market.get("id", "unknown")
            question = market.get("question", "Unknown question")
            banner_path = market.get("banner_path")
            
            # Skip markets without a banner path
            if not banner_path:
                logger.warning(f"Skipping market {market_id} - no banner path")
                continue
            
            # Update stats
            stats["markets_processed"] += 1
            
            # Create market entry for statistics
            market_stats = {
                "market_id": market_id,
                "question": question,
                "banner_path": banner_path,
                "github_commit": None,
                "blockchain_tx": None,
                "status": "pending"
            }
            
            try:
                # Step 1: Deploy banner to frontend repository
                logger.info(f"Deploying banner for market {market_id} to frontend repository")
                banner_success, banner_result = github_client.push_banner(market_id, banner_path)
                
                if banner_success:
                    # Update market stats
                    market_stats["github_commit"] = banner_result
                    market_stats["status"] = "banner_deployed"
                    stats["banners_deployed"] += 1
                    
                    # Step 2: Deploy market to blockchain
                    logger.info(f"Deploying market {market_id} to blockchain")
                    banner_uri = github_client.get_banner_uri(market_id)
                    market_success, tx_hash = blockchain_client.create_market(market, banner_uri)
                    
                    if market_success:
                        # Update market stats
                        market_stats["blockchain_tx"] = tx_hash
                        market_stats["status"] = "deployed"
                        stats["markets_deployed"] += 1
                        
                        # Add to deployed markets
                        deployed_markets.append({
                            "id": market_id,
                            "question": question,
                            "banner_path": banner_path,
                            "banner_uri": banner_uri,
                            "github_commit": banner_result,
                            "blockchain_tx": tx_hash,
                            "status": "deployed"
                        })
                        
                        logger.info(f"Market {market_id} successfully deployed")
                    else:
                        logger.error(f"Failed to deploy market {market_id} to blockchain: {tx_hash}")
                        market_stats["status"] = "blockchain_failed"
                        stats["errors"].append(f"Failed to deploy market {market_id} to blockchain: {tx_hash}")
                else:
                    logger.error(f"Failed to deploy banner for market {market_id}: {banner_result}")
                    market_stats["status"] = "banner_failed"
                    stats["errors"].append(f"Failed to deploy banner for market {market_id}: {banner_result}")
            
            except Exception as e:
                logger.error(f"Error deploying market {market_id}: {str(e)}")
                market_stats["status"] = "error"
                stats["errors"].append(f"Error deploying market {market_id}: {str(e)}")
            
            # Add market stats to the stats list
            stats["market_list"].append(market_stats)
        
        # Create output directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
        
        # Save deployed markets to file for persistence
        deployed_file = os.path.join(TMP_DIR, f"task4_deployed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(deployed_file, 'w') as f:
            json.dump({"markets": deployed_markets}, f, indent=2)
        
        # Calculate task duration
        stats["duration"] = time.time() - start_time
        
        # Final status
        if stats["markets_deployed"] > 0:
            stats["status"] = "success"
        else:
            stats["status"] = "failed"
        
        logger.info(f"Task 4 completed: {stats['markets_deployed']} markets deployed, {stats['banners_deployed']} banners deployed")
        return deployed_markets, stats
        
    except Exception as e:
        # Handle any errors
        logger.error(f"Error in Task 4: {str(e)}")
        stats["errors"].append(f"Task error: {str(e)}")
        stats["status"] = "failed"
        stats["duration"] = time.time() - start_time
        return [], stats