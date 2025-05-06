#!/usr/bin/env python3
"""
Clean Slack Channel

This script removes all messages from the Slack channel to provide a clean slate
for testing the pipeline.
"""

import os
import sys
import time
import logging
from typing import List, Dict, Any, Optional, Tuple

from utils.messaging import get_channel_history, delete_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('slack_cleaner')

def clean_channel(
    batch_size: int = 100, 
    rate_limit_delay: float = 0.5, 
    max_messages: int = 1000
) -> int:
    """
    Clean all messages from the Slack channel.
    
    Args:
        batch_size: Number of messages to fetch and delete at once
        rate_limit_delay: Delay between deletions to avoid rate limiting
        max_messages: Maximum number of messages to delete (safety limit)
        
    Returns:
        Number of messages deleted
    """
    deleted_count = 0
    total_fetched = 0
    cursor = None
    
    logger.info("Starting Slack channel cleanup...")
    
    while total_fetched < max_messages:
        # Get a batch of messages
        messages, next_cursor = get_channel_history(limit=batch_size, cursor=cursor)
        
        if not messages:
            logger.info("No more messages found in the channel")
            break
        
        total_fetched += len(messages)
        logger.info(f"Fetched {len(messages)} messages (total: {total_fetched})")
        
        # Delete each message
        for message in messages:
            ts = message.get('ts')
            
            if not ts:
                logger.warning("Message missing timestamp, skipping")
                continue
            
            # Skip messages that can't be deleted by bots (e.g., system messages)
            if message.get('subtype') in ['bot_add', 'channel_join', 'channel_purpose', 'channel_topic']:
                logger.info(f"Skipping system message with subtype: {message.get('subtype')}")
                continue
            
            # Try to delete the message
            success = delete_message(ts)
            
            if success:
                deleted_count += 1
                logger.info(f"Deleted message {ts} ({deleted_count}/{total_fetched})")
            else:
                logger.warning(f"Failed to delete message {ts}")
            
            # Add delay to avoid rate limiting
            time.sleep(rate_limit_delay)
        
        # Set cursor for next batch if available
        if next_cursor:
            cursor = next_cursor
        else:
            break
    
    logger.info(f"Channel cleanup completed. Deleted {deleted_count} out of {total_fetched} messages.")
    return deleted_count

def main():
    """Main function to clean the Slack channel."""
    try:
        deleted_count = clean_channel()
        
        if deleted_count > 0:
            logger.info(f"Successfully deleted {deleted_count} messages from Slack channel")
            return 0
        else:
            logger.info("No messages were deleted. Channel may already be clean.")
            return 0
        
    except Exception as e:
        logger.error(f"Error cleaning Slack channel: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())