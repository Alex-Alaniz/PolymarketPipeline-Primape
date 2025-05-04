"""
Task 1: Slack/Discord Integration + Market Data Fetching

This module is responsible for fetching Polymarket data and posting it to Slack/Discord
for initial approval.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Tuple
from datetime import datetime, timezone

# Import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.messaging import MessagingClient
from transform_polymarket_data_capitalized import PolymarketTransformer
from config import DATA_DIR, TMP_DIR

logger = logging.getLogger("task1")

def run_task(messaging_client: MessagingClient) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run Task 1: Fetch Polymarket data and post for initial approval
    
    Args:
        messaging_client: MessagingClient instance for interacting with Slack/Discord
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, Any]]: Markets posted and task statistics
    """
    logger.info("Starting Task 1: Fetching Polymarket data and posting for initial approval")
    
    # Start the clock for this task
    start_time = time.time()
    
    # Dictionary to store statistics
    stats = {
        "task": "task1_fetch_and_post",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "markets_fetched": 0,
        "markets_posted": 0,
        "market_list": [],
        "errors": [],
        "status": "running"
    }
    
    try:
        # Create a PolymarketTransformer to fetch and transform data
        transformer = PolymarketTransformer()
        
        # Fetch data from Polymarket API
        logger.info("Fetching data from Polymarket API")
        
        # Load data from file and then transform it
        load_success = transformer.load_polymarket_data()
        
        if load_success:
            # Get transformed markets from the API file
            # The load_polymarket_data method loads the data into transformer.polymarket_data
            market_data = transformer.polymarket_data.get('markets', [])
            logger.info(f"Loaded {len(market_data)} markets from file")
            
            # Transform the data
            polymarket_data = transformer.transform_markets_from_api(market_data)
            logger.info(f"Transformed {len(polymarket_data)} markets")
        else:
            # Attempt to fetch from blockchain as a backup
            logger.warning("No data from Polymarket API, attempting to fetch from blockchain")
            try:
                # Import dynamically to avoid circular imports
                from utils.polymarket_blockchain import PolymarketBlockchainClient
                
                # Initialize blockchain client
                blockchain_client = PolymarketBlockchainClient()
                
                # Fetch market data from blockchain
                blockchain_markets = blockchain_client.fetch_markets(limit=20)
                
                if blockchain_markets:
                    logger.info(f"Successfully fetched {len(blockchain_markets)} markets from blockchain")
                    
                    # Transform the blockchain markets to the required format
                    polymarket_data = transformer.transform_markets_from_api(blockchain_markets)
                else:
                    polymarket_data = []
                    raise Exception("Failed to fetch markets from both API and blockchain")
            except Exception as e:
                polymarket_data = []
                logger.error(f"Error fetching from blockchain: {str(e)}")
                stats["errors"].append(f"Failed to fetch market data: {str(e)}")
                stats["status"] = "failed"
                return [], stats
        
        # Update stats with number of markets fetched
        if isinstance(polymarket_data, list):
            stats["markets_fetched"] = len(polymarket_data)
            logger.info(f"Fetched {stats['markets_fetched']} markets from Polymarket")
        else:
            stats["markets_fetched"] = 0
            logger.error(f"Failed to fetch markets, polymarket_data is not a list: {type(polymarket_data)}")
        
        # Create output directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
        
        # Save the raw data for reference
        raw_data_path = os.path.join(TMP_DIR, "polymarket_raw_data.json")
        with open(raw_data_path, 'w') as f:
            if isinstance(polymarket_data, list):
                json.dump({"markets": polymarket_data}, f, indent=2)
            else:
                json.dump({"markets": []}, f, indent=2)
        
        # Markets to post to Slack/Discord
        posted_markets = []
        
        # Limit to 10 markets for initial post (avoid spam)
        markets_to_post = []
        if isinstance(polymarket_data, list):
            markets_to_post = polymarket_data[:10]
        
        # Post each market to Slack/Discord for initial approval
        for idx, market in enumerate(markets_to_post):
            try:
                market_id = market.get("id", f"unknown-{idx}")
                question = market.get("question", "Unknown question")
                
                # Format the message
                message = format_market_message(market)
                
                # Post to messaging platform
                message_id = messaging_client.post_message(message)
                
                if message_id:
                    # Add reactions for approval/rejection
                    messaging_client.add_reactions(message_id, ["white_check_mark", "x"])
                    
                    # Add to posted markets list
                    posted_markets.append({
                        "market_id": market_id,
                        "question": question,
                        "message_id": message_id,
                        "status": "posted"
                    })
                    
                    # Update stats
                    stats["markets_posted"] += 1
                    stats["market_list"].append({
                        "market_id": market_id,
                        "question": question,
                        "message_id": message_id,
                        "status": "posted"
                    })
                    
                    logger.info(f"Posted market {market_id} for initial approval (message ID: {message_id})")
                else:
                    logger.error(f"Failed to post market {market_id}")
                    stats["errors"].append(f"Failed to post market {market_id}")
            
            except Exception as e:
                logger.error(f"Error posting market {idx}: {str(e)}")
                stats["errors"].append(f"Error posting market {idx}: {str(e)}")
            
            # Sleep to avoid rate limiting
            time.sleep(1)
        
        # Save posted markets to file for persistence
        posted_file = os.path.join(TMP_DIR, f"task1_posted_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(posted_file, 'w') as f:
            json.dump({"markets": posted_markets}, f, indent=2)
        
        # Calculate task duration
        stats["duration"] = time.time() - start_time
        
        # Final status
        if stats["markets_posted"] > 0:
            stats["status"] = "success"
        else:
            stats["status"] = "failed"
        
        logger.info(f"Task 1 completed: {stats['markets_posted']} markets posted for initial approval")
        return posted_markets, stats
        
    except Exception as e:
        # Handle any errors
        logger.error(f"Error in Task 1: {str(e)}")
        stats["errors"].append(f"Task error: {str(e)}")
        stats["status"] = "failed"
        stats["duration"] = time.time() - start_time
        return [], stats

def format_market_message(market: Dict[str, Any]) -> str:
    """
    Format a market message for posting to Slack/Discord
    
    Args:
        market: Market data
        
    Returns:
        str: Formatted message text
    """
    market_id = market.get("id", "unknown")
    question = market.get("question", "Unknown question")
    category = market.get("category", "Uncategorized")
    sub_category = market.get("sub_category", "")
    expiry = market.get("expiry", 0)
    
    # Format expiry date if available
    expiry_date = ""
    if expiry:
        try:
            # Convert milliseconds to seconds if needed
            if expiry > 10000000000:  # Likely milliseconds
                expiry = expiry / 1000
            expiry_date = datetime.fromtimestamp(expiry, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        except:
            expiry_date = "Unknown"
    
    # Get options (binary or multi-option)
    options = market.get("options", [])
    if not options:
        options_str = "Yes/No"
    else:
        options_str = ", ".join([opt.get("name", str(i)) for i, opt in enumerate(options)])
    
    # Format the message
    message = (
        f"*MARKET APPROVAL NEEDED*\n\n"
        f"*Question:* {question}\n"
        f"*Market ID:* {market_id}\n"
        f"*Category:* {category}"
    )
    
    if sub_category:
        message += f" > {sub_category}"
    
    message += f"\n*Options:* {options_str}"
    
    if expiry_date:
        message += f"\n*Expiry:* {expiry_date}"
    
    message += "\n\nPlease react with :white_check_mark: to approve or :x: to reject this market."
    
    return message