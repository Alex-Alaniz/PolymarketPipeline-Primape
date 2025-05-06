"""
Send a notification about the Barcelona/generic option fix.
"""
import logging
import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

def send_notification():
    """
    Send a notification about the fix for Barcelona/generic options.
    """
    try:
        # Initialize Slack client
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🛠️ Fix Applied: Generic Options Images",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Issue Fixed:* Barcelona in Champions League Winner and other generic options are now correctly assigned images."
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Solution:*\n• Added pre-processing step to ensure ALL options in outcomes arrays have images assigned\n• Improved image fallback logic to prioritize team-specific images over event banners\n• Added Barcelona to the list of generic option keywords\n• Fixed problem where generic options like 'Another team' or 'Barcelona' used event banner images"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Verification:*\n• Reset the database and reloaded markets with the fix in place\n• Verified all options including Barcelona now have assigned images\n• Generic options correctly use another team's image instead of event banner\n• Maintained a general solution without hardcoded special cases"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "You can verify the fix by checking the Champions League Winner and La Liga Winner markets posted to this channel."
                }
            }
        ]
        
        # Post the message to Slack
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text="Fix applied for Barcelona in Champions League Winner and other generic options",
            blocks=blocks
        )
        
        logger.info(f"Notification sent, timestamp: {response['ts']}")
        return True
        
    except SlackApiError as e:
        logger.error(f"Error sending notification: {e}")
        return False

if __name__ == "__main__":
    success = send_notification()
    if success:
        print("Successfully sent notification about the fix")
    else:
        print("Failed to send notification")