"""
Script to send a notification about the fixed image handling for generic options.
"""
import os
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

def send_notification():
    """Send notification to Slack about the fix"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.error("Slack credentials not available - cannot send notification")
        return False
    
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Create a message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔧 Image Handling Fix Notification",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ *Generic Option Image Fix Complete*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "The issue with generic options like 'Another Team' and 'Barcelona' using event banner images has been fixed. These options will now use team-specific images instead."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Issues Fixed:*\n• Generic options were incorrectly using event banner images\n• Special case for Champions League/Barcelona was using event images\n• Image fallback logic wasn't correctly prioritizing team-specific images"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Technical Improvements:*\n• Enhanced generic option detection\n• Improved image selection logic\n• Added multiple fallback options for finding appropriate images\n• Added final validation to ensure no generic option uses event images"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "The fix has been verified with both synthetic test data and integration tests. All generic options now correctly use team-specific images rather than event banners."
                }
            }
        ]
        
        # Post the message
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text="Generic Option Image Fix Complete",
            blocks=blocks
        )
        
        logger.info(f"Posted notification to Slack, message timestamp: {response['ts']}")
        return True
        
    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e}")
        return False

def main():
    """Main function"""
    logger.info("Sending fix notification to Slack")
    success = send_notification()
    
    if success:
        logger.info("Notification sent successfully")
    else:
        logger.error("Failed to send notification")

if __name__ == "__main__":
    main()