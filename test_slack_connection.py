"""
Test Slack connection and messaging capabilities.
"""
import os
import logging
import sys
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_test")

def test_slack_connection():
    """Test the connection to Slack and ability to post messages."""
    # Get environment variables
    slack_token = os.environ.get('SLACK_BOT_TOKEN')
    slack_channel_id = os.environ.get('SLACK_CHANNEL_ID')
    
    if not slack_token:
        logger.error("SLACK_BOT_TOKEN not found in environment variables")
        return 1
    
    if not slack_channel_id:
        logger.error("SLACK_CHANNEL_ID not found in environment variables")
        return 1
    
    logger.info(f"Testing Slack connection with channel ID: {slack_channel_id}")
    
    # Initialize Slack client
    client = WebClient(token=slack_token)
    
    try:
        # Test connection by getting channel info
        response = client.conversations_info(channel=slack_channel_id)
        channel_name = response['channel']['name']
        logger.info(f"Successfully connected to Slack channel: #{channel_name}")
        
        # Send a test message
        message_text = "Test message from Polymarket pipeline - testing Slack connectivity"
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Slack Connection Test*\nThis is a test message to verify the connection to Slack for the Polymarket pipeline."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "If you can see this message, the Slack integration is working correctly."
                }
            }
        ]
        
        response = client.chat_postMessage(
            channel=slack_channel_id,
            text=message_text,
            blocks=blocks
        )
        
        logger.info(f"Successfully sent test message to Slack, ts: {response['ts']}")
        
        # Clean up by deleting the test message
        client.chat_delete(
            channel=slack_channel_id,
            ts=response['ts']
        )
        
        logger.info("Test message deleted - Slack connection test successful")
        return 0
        
    except SlackApiError as e:
        logger.error(f"Slack API error: {e.response['error']}")
        return 1
    except Exception as e:
        logger.error(f"Error testing Slack connection: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(test_slack_connection())