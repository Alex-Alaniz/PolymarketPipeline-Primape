"""
Clean Slack Channel Only

This script focuses specifically on cleaning the Slack channel.
It will attempt to delete as many messages as possible from the Slack channel.
"""

import sys
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_slack_channel(max_messages=100):
    """
    Attempt to clean recent messages from the Slack channel.
    
    Args:
        max_messages: Maximum number of messages to retrieve
        
    Returns:
        bool: True if operation completed, False on critical error
    """
    try:
        from utils.slack import slack_client, SLACK_CHANNEL_ID
        
        if not slack_client or not SLACK_CHANNEL_ID:
            logger.error("Slack client not initialized - check environment variables")
            return False
        
        # Get channel history in batches
        total_deleted = 0
        total_attempts = 0
        cursor = None
        
        while total_attempts < max_messages:
            # Get a batch of messages
            response = slack_client.conversations_history(
                channel=SLACK_CHANNEL_ID,
                limit=20,
                cursor=cursor
            )
            
            if not response.get('ok'):
                logger.error(f"Failed to get channel history: {response.get('error')}")
                return False
                
            messages = response.get('messages', [])
            if not messages:
                logger.info("No more messages to delete")
                break
                
            logger.info(f"Found {len(messages)} messages in this batch")
            
            # Try to delete each message
            for message in messages:
                ts = message.get('ts')
                total_attempts += 1
                
                if not ts:
                    continue
                    
                try:
                    result = slack_client.chat_delete(
                        channel=SLACK_CHANNEL_ID,
                        ts=ts
                    )
                    
                    if result.get('ok'):
                        total_deleted += 1
                        logger.info(f"Deleted message {ts}")
                    else:
                        error = result.get('error')
                        logger.warning(f"Failed to delete message {ts}: {error}")
                        
                        # If we get rate limited, pause briefly
                        if error == 'ratelimited':
                            logger.info("Rate limited - pausing for 5 seconds")
                            time.sleep(5)
                except Exception as e:
                    logger.error(f"Error deleting message {ts}: {str(e)}")
                
                # Small pause to avoid rate limits
                time.sleep(0.5)
            
            # Get next cursor for pagination
            cursor = response.get('response_metadata', {}).get('next_cursor')
            if not cursor:
                logger.info("No more pages of messages")
                break
        
        logger.info(f"Successfully cleaned {total_deleted} of {total_attempts} messages from Slack channel")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning Slack channel: {str(e)}")
        return False

def main():
    """Main function to clean Slack channel."""
    logger.info("Starting Slack channel cleanup...")
    success = clean_slack_channel()
    
    if success:
        logger.info("✅ Slack channel cleanup attempted")
        logger.info("Some messages may still remain if they couldn't be deleted (too old, posted by someone else, etc.)")
        return 0
    else:
        logger.error("❌ Slack channel cleanup failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())