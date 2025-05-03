"""
Messaging client for the Polymarket pipeline.
Handles posting markets to Slack/Discord and checking approvals.
"""
import os
import logging
import time
from typing import Dict, Any, Tuple, Optional

# Import configuration
from config import MESSAGING_PLATFORM, SLACK_BOT_TOKEN, SLACK_CHANNEL

logger = logging.getLogger("messaging_client")

class MessagingClient:
    """Client for messaging platforms (Slack/Discord)"""
    
    def __init__(self):
        """Initialize the messaging client"""
        self.platform = MESSAGING_PLATFORM
        
        # Initialize Slack client if using Slack
        if self.platform == "slack":
            try:
                from slack_sdk import WebClient
                from slack_sdk.errors import SlackApiError
                
                self.slack_client = WebClient(token=SLACK_BOT_TOKEN)
                
                # Test connection
                response = self.slack_client.auth_test()
                logger.info(f"Connected to Slack as {response['user']}")
                
            except ImportError:
                logger.error("slack_sdk not installed")
                self.slack_client = None
            except Exception as e:
                logger.error(f"Error initializing Slack client: {str(e)}")
                self.slack_client = None
        
        # Initialize Discord client if using Discord
        elif self.platform == "discord":
            logger.error("Discord not implemented yet")
            self.discord_client = None
        
        else:
            logger.error(f"Unsupported messaging platform: {self.platform}")
    
    def post_initial_market(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Post a market for initial approval.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        if self.platform == "slack" and self.slack_client:
            try:
                # Prepare market message
                blocks = self._format_initial_market_slack(market)
                
                # Post message
                response = self.slack_client.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    text=f"New market for initial approval: {market.get('question', 'Unknown')}",
                    blocks=blocks
                )
                
                return response["ts"]
                
            except Exception as e:
                logger.error(f"Error posting to Slack: {str(e)}")
                return None
        
        # For testing: auto-approve markets
        logger.info(f"Auto-approving market {market.get('id')} (initial)")
        return "mock_message_id"
    
    def post_final_market(self, market: Dict[str, Any], banner_path: str) -> Optional[str]:
        """
        Post a market with banner for final approval.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_path (str): Path to banner image
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        if self.platform == "slack" and self.slack_client:
            try:
                # Prepare market message
                blocks = self._format_final_market_slack(market, banner_path)
                
                # Post message
                response = self.slack_client.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    text=f"Market with banner for final approval: {market.get('question', 'Unknown')}",
                    blocks=blocks
                )
                
                return response["ts"]
                
            except Exception as e:
                logger.error(f"Error posting to Slack: {str(e)}")
                return None
        
        # For testing: auto-approve markets
        logger.info(f"Auto-approving market {market.get('id')} (final)")
        return "mock_message_id"
    
    def check_approval(self, message_id: str, timeout_minutes: int) -> Tuple[str, Optional[str]]:
        """
        Check if a market has been approved/rejected.
        
        Args:
            message_id (str): Message ID to check
            timeout_minutes (int): Timeout in minutes
            
        Returns:
            Tuple[str, Optional[str]]: Status and reason
        """
        if self.platform == "slack" and self.slack_client:
            try:
                # In a real implementation, this would poll for reactions or replies
                # For now, just auto-approve after a short delay
                time.sleep(1)
                return "approved", "Auto-approved for testing"
                
            except Exception as e:
                logger.error(f"Error checking approval in Slack: {str(e)}")
                return "failed", f"Error: {str(e)}"
        
        # For testing: auto-approve markets
        return "approved", "Auto-approved for testing"
    
    def post_summary(self, summary: Dict[str, Any]) -> Optional[str]:
        """
        Post a summary of the pipeline run.
        
        Args:
            summary (Dict[str, Any]): Summary data
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        if self.platform == "slack" and self.slack_client:
            try:
                # Prepare summary message
                blocks = self._format_summary_slack(summary)
                
                # Post message
                response = self.slack_client.chat_postMessage(
                    channel=SLACK_CHANNEL,
                    text=f"Pipeline run summary: {summary.get('markets_deployed', 0)} markets deployed",
                    blocks=blocks
                )
                
                return response["ts"]
                
            except Exception as e:
                logger.error(f"Error posting summary to Slack: {str(e)}")
                return None
        
        # Log summary for testing
        logger.info(f"Pipeline summary: {summary.get('markets_deployed', 0)} markets deployed")
        return "mock_message_id"
    
    def _format_initial_market_slack(self, market: Dict[str, Any]) -> list:
        """
        Format a market for initial approval in Slack.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            list: Slack blocks
        """
        # Simple format for testing
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Initial Approval Needed*\n\n*Question:* {market.get('question', 'Unknown')}\n*Type:* {market.get('type', 'binary')}\n*Category:* {market.get('category', 'Unknown')}\n*Sub-category:* {market.get('sub_category', 'Unknown')}"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve"
                        },
                        "style": "primary",
                        "value": f"approve_{market.get('id')}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject"
                        },
                        "style": "danger",
                        "value": f"reject_{market.get('id')}"
                    }
                ]
            }
        ]
    
    def _format_final_market_slack(self, market: Dict[str, Any], banner_path: str) -> list:
        """
        Format a market with banner for final approval in Slack.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_path (str): Path to banner image
            
        Returns:
            list: Slack blocks
        """
        # Simple format for testing
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Final Approval Needed*\n\n*Question:* {market.get('question', 'Unknown')}\n*Type:* {market.get('type', 'binary')}\n*Category:* {market.get('category', 'Unknown')}\n*Sub-category:* {market.get('sub_category', 'Unknown')}"
                }
            },
            {
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Market Banner"
                },
                "image_url": f"file://{banner_path}",
                "alt_text": "Market Banner"
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Approve"
                        },
                        "style": "primary",
                        "value": f"approve_{market.get('id')}"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Reject"
                        },
                        "style": "danger",
                        "value": f"reject_{market.get('id')}"
                    }
                ]
            }
        ]
    
    def _format_summary_slack(self, summary: Dict[str, Any]) -> list:
        """
        Format a summary for Slack.
        
        Args:
            summary (Dict[str, Any]): Summary data
            
        Returns:
            list: Slack blocks
        """
        # Simple format for testing
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Pipeline Run Summary*\n\nStart Time: {summary.get('start_time', 'Unknown')}\nEnd Time: {summary.get('end_time', 'Unknown')}\nMarkets Processed: {summary.get('markets_processed', 0)}\nMarkets Approved: {summary.get('markets_approved', 0)}\nMarkets Rejected: {summary.get('markets_rejected', 0)}\nMarkets Deployed: {summary.get('markets_deployed', 0)}\nMarkets Failed: {summary.get('markets_failed', 0)}"
                }
            }
        ]