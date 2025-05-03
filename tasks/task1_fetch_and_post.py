"""
Task 1: Fetching Polymarket Data and Initial Approval

This module is responsible for fetching Polymarket data and posting market information
to the messaging platform (Slack or Discord) for initial approval.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

# Import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.polymarket import PolymarketExtractor
from utils.messaging import MessagingClient
from config import DATA_DIR, TMP_DIR, MESSAGING_PLATFORM

logger = logging.getLogger("task1")

def run_task(messaging_client: MessagingClient) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run Task 1: Extract Polymarket data and post for initial approval
    
    Args:
        messaging_client: MessagingClient instance for posting to Slack/Discord
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, Any]]: Extracted markets and task statistics
    """
    logger.info("Starting Task 1: Fetching market data and posting to Slack")
    
    # Start the clock for this task
    start_time = time.time()
    
    # Initialize the Polymarket extractor
    extractor = PolymarketExtractor()
    
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
        # Extract market data from Polymarket
        # We require real data - no fallbacks allowed
        markets = extractor.extract_data()
        
        # Update statistics
        if markets:
            stats["markets_fetched"] = len(markets)
            logger.info(f"Fetched {len(markets)} markets from Polymarket")
        else:
            logger.error("Failed to fetch any markets from Polymarket")
            stats["errors"].append("Failed to fetch markets from Polymarket")
            stats["status"] = "failed"
            return [], stats
        
        # Create output directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
        
        # Save fetched markets to file for persistence
        markets_file = os.path.join(TMP_DIR, f"task1_markets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(markets_file, 'w') as f:
            json.dump({"markets": markets}, f, indent=2)
        
        logger.info(f"Saved {len(markets)} markets to {markets_file}")
        
        # Post markets to Slack/Discord for approval
        for market in markets:
            # Update market specific stats before posting
            market_stats = {
                "market_id": market.get("id"),
                "question": market.get("question"),
                "status": "pending",
                "message_id": None
            }
            
            # Check if this is a binary or multiple-option market for formatting
            market_type = market.get("type", "binary")
            
            # Format message differently based on market type
            if market_type == "binary":
                message = format_binary_market(market)
            else:
                message = format_multiple_market(market)
            
            # Post message to Slack/Discord
            try:
                message_id = messaging_client.post_message(message)
                
                if message_id:
                    # Add reactions for approval/rejection
                    messaging_client.add_reactions(message_id, ["white_check_mark", "x"])
                    
                    # Update market stats
                    market_stats["message_id"] = message_id
                    market_stats["status"] = "posted"
                    
                    # Update overall stats
                    stats["markets_posted"] += 1
                    
                    logger.info(f"Posted market {market.get('id')} for approval (message ID: {message_id})")
                else:
                    logger.error(f"Failed to post market {market.get('id')} for approval")
                    market_stats["status"] = "failed"
                    stats["errors"].append(f"Failed to post market {market.get('id')}")
            
            except Exception as e:
                logger.error(f"Error posting market {market.get('id')}: {str(e)}")
                market_stats["status"] = "failed"
                stats["errors"].append(f"Error posting market {market.get('id')}: {str(e)}")
            
            # Add market stats to the stats list
            stats["market_list"].append(market_stats)
            
            # Sleep to avoid rate limiting
            time.sleep(1)
        
        # Calculate task duration
        stats["duration"] = time.time() - start_time
        
        # Final status
        if stats["markets_posted"] > 0:
            stats["status"] = "success"
        else:
            stats["status"] = "failed"
        
        logger.info(f"Task 1 completed: {stats['markets_posted']} markets posted for approval")
        return markets, stats
        
    except Exception as e:
        # Handle any errors
        logger.error(f"Error in Task 1: {str(e)}")
        stats["errors"].append(f"Task error: {str(e)}")
        stats["status"] = "failed"
        stats["duration"] = time.time() - start_time
        return [], stats

def format_binary_market(market: Dict[str, Any]) -> str:
    """
    Format a binary market for posting to Slack/Discord
    
    Args:
        market: Market data dictionary
        
    Returns:
        str: Formatted message text
    """
    question = market.get("question", "Unknown question")
    market_id = market.get("id", "unknown")
    category = market.get("category", "Uncategorized")
    sub_category = market.get("sub_category", "")
    
    # Format options
    options = market.get("options", [])
    options_text = "\n".join([f"• {option.get('name')}" for option in options])
    
    # Format expiry date
    expiry = market.get("expiry")
    expiry_text = "Not specified"
    if expiry:
        try:
            # Expiry can be in seconds or milliseconds
            if expiry > 1e10:  # Likely milliseconds
                expiry_date = datetime.fromtimestamp(expiry / 1000)
            else:
                expiry_date = datetime.fromtimestamp(expiry)
            expiry_text = expiry_date.strftime("%Y-%m-%d")
        except Exception:
            pass
    
    # Build the message
    if MESSAGING_PLATFORM == "slack":
        message = (
            f"*INITIAL APPROVAL NEEDED*\n\n"
            f"*Question:* {question}\n"
            f"*Market ID:* {market_id}\n"
            f"*Type:* Binary\n"
            f"*Category:* {category}\n"
            f"*Sub-category:* {sub_category}\n"
            f"*Options:*\n{options_text}\n"
            f"*Expiry:* {expiry_text}\n\n"
            f"React with :white_check_mark: to approve or :x: to reject"
        )
    else:  # Discord
        message = (
            f"**INITIAL APPROVAL NEEDED**\n\n"
            f"**Question:** {question}\n"
            f"**Market ID:** {market_id}\n"
            f"**Type:** Binary\n"
            f"**Category:** {category}\n"
            f"**Sub-category:** {sub_category}\n"
            f"**Options:**\n{options_text}\n"
            f"**Expiry:** {expiry_text}\n\n"
            f"React with ✅ to approve or ❌ to reject"
        )
    
    return message

def format_multiple_market(market: Dict[str, Any]) -> str:
    """
    Format a multiple-option market for posting to Slack/Discord
    
    Args:
        market: Market data dictionary
        
    Returns:
        str: Formatted message text
    """
    question = market.get("question", "Unknown question")
    market_id = market.get("id", "unknown")
    category = market.get("category", "Uncategorized")
    sub_category = market.get("sub_category", "")
    
    # Format options
    options = market.get("options", [])
    options_text = "\n".join([f"• {option.get('name')}" for option in options])
    
    # Format expiry date
    expiry = market.get("expiry")
    expiry_text = "Not specified"
    if expiry:
        try:
            # Expiry can be in seconds or milliseconds
            if expiry > 1e10:  # Likely milliseconds
                expiry_date = datetime.fromtimestamp(expiry / 1000)
            else:
                expiry_date = datetime.fromtimestamp(expiry)
            expiry_text = expiry_date.strftime("%Y-%m-%d")
        except Exception:
            pass
    
    # Build the message
    if MESSAGING_PLATFORM == "slack":
        message = (
            f"*INITIAL APPROVAL NEEDED*\n\n"
            f"*Question:* {question}\n"
            f"*Market ID:* {market_id}\n"
            f"*Type:* Multiple-option\n"
            f"*Category:* {category}\n"
            f"*Sub-category:* {sub_category}\n"
            f"*Options:*\n{options_text}\n"
            f"*Expiry:* {expiry_text}\n\n"
            f"React with :white_check_mark: to approve or :x: to reject"
        )
    else:  # Discord
        message = (
            f"**INITIAL APPROVAL NEEDED**\n\n"
            f"**Question:** {question}\n"
            f"**Market ID:** {market_id}\n"
            f"**Type:** Multiple-option\n"
            f"**Category:** {category}\n"
            f"**Sub-category:** {sub_category}\n"
            f"**Options:**\n{options_text}\n"
            f"**Expiry:** {expiry_text}\n\n"
            f"React with ✅ to approve or ❌ to reject"
        )
    
    return message