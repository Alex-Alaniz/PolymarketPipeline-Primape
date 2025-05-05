#!/usr/bin/env python3

"""
Create Test Channel for Pipeline

This script creates a new Slack channel for testing the pipeline.
It outputs the new channel ID to use in your environment variables.
"""

import os
import sys
import logging
import time
import random
import string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_channel")

# Import Slack client
from utils.messaging import slack_client

def generate_channel_name():
    """
    Generate a random channel name for testing.
    
    Returns:
        str: Random channel name like 'test-pipeline-abc123'
    """
    # Generate random suffix
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    # Create channel name
    return f"test-pipeline-{suffix}"

def create_test_channel():
    """
    Create a new test channel in Slack.
    
    Returns:
        str: Channel ID if successful, None otherwise
    """
    try:
        # Generate channel name
        channel_name = generate_channel_name()
        
        logger.info(f"Creating new test channel with name: {channel_name}")
        
        # Create channel
        response = slack_client.conversations_create(
            name=channel_name,
            is_private=False
        )
        
        if not response.get("ok"):
            logger.error(f"Failed to create channel: {response.get('error')}")
            return None
            
        # Get channel ID
        channel_id = response.get("channel", {}).get("id")
        
        if not channel_id:
            logger.error("Failed to get channel ID from response")
            return None
            
        logger.info(f"Successfully created test channel: {channel_name} (ID: {channel_id})")
        
        return channel_id
        
    except Exception as e:
        logger.error(f"Error creating test channel: {str(e)}")
        return None

def main():
    """
    Main function to create a test channel.
    """
    print("\n===== CREATE TEST CHANNEL FOR PIPELINE =====\n")
    
    # Check if Slack client is initialized
    if not slack_client:
        logger.error("Slack client not initialized")
        print("Error: Slack client not initialized. Please check your SLACK_BOT_TOKEN.")
        return 1
        
    # Create test channel
    channel_id = create_test_channel()
    
    if not channel_id:
        print("\nFailed to create test channel. Please check logs for details.")
        print("Try updating your SLACK_BOT_TOKEN with the required permissions:")
        print("  - channels:manage or groups:write")
        print("  - chat:write")
        return 1
        
    # Success
    print(f"\nSuccessfully created test channel with ID: {channel_id}")
    print("\nTo use this channel for testing:")
    print("1. Update your .env file with:")
    print(f"   SLACK_CHANNEL_ID={channel_id}")
    print("2. Restart your application")
    print("3. Run the pipeline\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())