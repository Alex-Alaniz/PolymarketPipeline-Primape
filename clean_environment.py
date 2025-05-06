#!/usr/bin/env python3

"""
Clean Environment for Pipeline Testing

This script provides a clean slate for testing the pipeline by:
1. Resetting the database (dropping and recreating all tables)
2. Cleaning the Slack channel (removing all messages)

Use this script before running end-to-end tests of the pipeline.
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
logger = logging.getLogger("environment_cleaner")

# Import modules
from utils.messaging import slack_client, slack_channel_id
from reset_db import reset_database

def get_channel_history(limit: int = 100, cursor: str = None) -> tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Get message history from the Slack channel.
    
    Args:
        limit: Maximum number of messages to retrieve
        cursor: Pagination cursor for fetching next batch
        
    Returns:
        Tuple of (messages, next_cursor)
    """
    try:
        logger.info(f"Fetching up to {limit} messages from Slack channel")
        
        response = slack_client.conversations_history(
            channel=slack_channel_id,
            limit=limit,
            cursor=cursor
        )
        
        messages = response.get('messages', [])
        next_cursor = response.get('response_metadata', {}).get('next_cursor')
        
        logger.info(f"Fetched {len(messages)} messages")
        return messages, next_cursor
    except Exception as e:
        logger.error(f"Error fetching channel history: {str(e)}")
        return [], None

def delete_message(ts: str) -> bool:
    """
    Delete a message from the Slack channel.
    
    Args:
        ts: Message timestamp/ID
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        response = slack_client.chat_delete(
            channel=slack_channel_id,
            ts=ts
        )
        return response.get('ok', False)
    except Exception as e:
        logger.error(f"Error deleting message {ts}: {str(e)}")
        return False

def clean_channel(batch_size: int = 100, rate_limit_delay: float = 0.5) -> int:
    """
    Clean all messages from the Slack channel.
    
    Args:
        batch_size: Number of messages to fetch and delete at once
        rate_limit_delay: Delay between deletions to avoid rate limiting
        
    Returns:
        Number of messages deleted
    """
    deleted_count = 0
    cursor = None
    
    logger.info("Starting Slack channel cleaning...")
    
    while True:
        # Get batch of messages
        messages, cursor = get_channel_history(limit=batch_size, cursor=cursor)
        
        if not messages:
            logger.info("No more messages to delete")
            break
            
        # Delete messages
        for message in messages:
            ts = message.get('ts')
            if ts:
                success = delete_message(ts)
                if success:
                    deleted_count += 1
                    logger.info(f"Deleted message {ts} ({deleted_count} total)")
                else:
                    logger.warning(f"Failed to delete message {ts}")
                
                # Sleep to avoid rate limiting
                time.sleep(rate_limit_delay)
                
        # If no cursor, we've reached the end
        if not cursor:
            break
            
    logger.info(f"Slack channel cleaning complete. Deleted {deleted_count} messages.")
    return deleted_count

def reset_full_environment():
    """
    Reset both the database and clean the Slack channel.
    """
    # Step 1: Reset database
    logger.info("Step 1: Resetting database...")
    db_success = reset_database()
    
    if db_success:
        logger.info("Database reset successful")
    else:
        logger.error("Database reset failed")
        return False
        
    # Step 2: Clean Slack channel
    logger.info("Step 2: Cleaning Slack channel...")
    messages_deleted = clean_channel()
    
    if messages_deleted >= 0:  # Zero is ok if there were no messages
        logger.info(f"Slack channel cleaning successful ({messages_deleted} messages deleted)")
    else:
        logger.error("Slack channel cleaning failed")
        return False
        
    return True

def main():
    """
    Main function to run the environment cleaning.
    """
    logger.info("Starting environment cleaning...")
    
    success = reset_full_environment()
    
    if success:
        logger.info("Environment cleaning completed successfully")
        return 0
    else:
        logger.error("Environment cleaning failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())