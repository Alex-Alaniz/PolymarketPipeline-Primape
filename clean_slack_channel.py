#!/usr/bin/env python3

"""
Clean Slack Channel

This script deletes all messages in the configured Slack channel.
Use this to clean up the channel before testing the pipeline.
"""

import os
import sys
import logging
import time
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_cleaner")

# Import Slack utilities
from utils.messaging import slack_client, slack_channel_id

def get_channel_history(limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get message history from the Slack channel.
    
    Args:
        limit: Maximum number of messages to retrieve
        
    Returns:
        List of message dictionaries
    """
    try:
        logger.info(f"Fetching up to {limit} messages from Slack channel")
        
        response = slack_client.conversations_history(
            channel=slack_channel_id,
            limit=limit
        )
        
        if not response.get("ok"):
            logger.error(f"Failed to fetch channel history: {response.get('error')}")
            return []
            
        messages = response.get("messages", [])
        logger.info(f"Fetched {len(messages)} messages from channel")
        
        return messages
        
    except Exception as e:
        logger.error(f"Error fetching channel history: {str(e)}")
        return []

def delete_message(ts: str) -> bool:
    """
    Delete a message from the Slack channel.
    
    Args:
        ts: Message timestamp/ID
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        logger.info(f"Deleting message with ts: {ts}")
        
        response = slack_client.chat_delete(
            channel=slack_channel_id,
            ts=ts
        )
        
        if response.get("ok"):
            logger.info(f"Successfully deleted message: {ts}")
            return True
        else:
            logger.error(f"Failed to delete message: {response.get('error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        return False

def clean_channel(batch_size: int = 100, rate_limit_delay: float = 0.2) -> int:
    """
    Clean all messages from the Slack channel.
    
    Args:
        batch_size: Number of messages to fetch and delete at once
        rate_limit_delay: Delay between deletions to avoid rate limiting
        
    Returns:
        Number of messages deleted
    """
    total_deleted = 0
    
    while True:
        # Fetch a batch of messages
        messages = get_channel_history(limit=batch_size)
        
        if not messages:
            logger.info("No more messages to delete")
            break
            
        # Delete each message with rate limiting
        deleted_count = 0
        
        for message in messages:
            ts = message.get("ts")
            
            if not ts:
                continue
                
            success = delete_message(ts)
            
            if success:
                deleted_count += 1
                total_deleted += 1
                
                # Add delay to avoid hitting rate limits
                time.sleep(rate_limit_delay)
        
        logger.info(f"Deleted {deleted_count} messages in this batch")
        
        # If we deleted fewer messages than the batch size, we're done
        if deleted_count < batch_size:
            break
    
    return total_deleted

def main():
    """
    Main function to run the Slack channel cleaning.
    """
    logger.info("Starting Slack channel cleaning...")
    
    # Check if Slack client is initialized
    if not slack_client or not slack_channel_id:
        logger.error("Slack client or channel ID not initialized")
        return 1
        
    # Clean the channel with smaller batch size
    deleted_count = clean_channel(batch_size=20, rate_limit_delay=0.1)
    
    logger.info(f"Deleted a total of {deleted_count} messages from the Slack channel")
    logger.info("Slack channel cleaning completed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())