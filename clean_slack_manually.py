#!/usr/bin/env python3

"""
Clean Slack Channel (Manual Version)

This script provides instructions for manually cleaning the Slack channel
since the bot doesn't have the required permissions to do so automatically.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_cleaner")

# Import Slack channel ID
from utils.messaging import slack_channel_id

def main():
    """
    Main function to display cleaning instructions.
    """
    print("\n===== SLACK CHANNEL CLEANING INSTRUCTIONS =====\n")
    print(f"Slack Channel ID: {slack_channel_id}")
    
    print("\nThe Slack bot doesn't have the required permissions to automatically")
    print("delete messages. You'll need to manually clean the channel.")
    
    print("\nOption 1: Use Slack's UI")
    print("1. Open the Slack workspace in your browser")
    print("2. Navigate to the channel")
    print("3. For each message, hover over it and click the three dots (...)")
    print("4. Select 'Delete message' and confirm")
    
    print("\nOption 2: Reset the Channel")
    print("1. Create a new channel in Slack")
    print("2. Update the SLACK_CHANNEL_ID environment variable to the new channel's ID")
    print("3. Run the pipeline with the new clean channel")
    
    print("\nOption 3: Update Bot Permissions")
    print("1. Go to your Slack App settings at https://api.slack.com/apps")
    print("2. Select your bot application")
    print("3. Go to 'OAuth & Permissions'")
    print("4. Add the following permissions:")
    print("   - channels:history")
    print("   - chat:write:bot (or chat:write)")
    print("   - chat:write:user")
    print("5. Reinstall the app to your workspace")
    print("6. Update the SLACK_BOT_TOKEN environment variable with the new token")
    print("7. Run the clean_slack_channel.py script again")
    
    print("\nAfter cleaning, run the pipeline to post new markets to the clean channel.")
    print("\n==============================================\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())