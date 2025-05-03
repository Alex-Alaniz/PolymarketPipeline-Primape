"""
Messaging utilities for the Polymarket pipeline.
Supports both Slack and Discord for market approval workflow.
"""
import os
import time
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

from config import (
    SLACK_BOT_TOKEN, SLACK_CHANNEL, DISCORD_TOKEN, DISCORD_CHANNEL,
    MESSAGING_PLATFORM, APPROVAL_WINDOW_MINUTES
)

# Try to import Slack SDK
try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = bool(SLACK_BOT_TOKEN and SLACK_CHANNEL)
except ImportError:
    SLACK_AVAILABLE = False
    print("Warning: slack_sdk not installed, Slack integration disabled")

# Try to import Discord
try:
    import discord
    import asyncio
    from discord.ext import commands
    DISCORD_AVAILABLE = bool(DISCORD_TOKEN and DISCORD_CHANNEL)
except ImportError:
    DISCORD_AVAILABLE = False
    print("Warning: discord.py not installed, Discord integration disabled")

class MessagingClient:
    """Client for messaging platform interactions."""
    
    def __init__(self):
        """Initialize the messaging client."""
        self.platform = MESSAGING_PLATFORM
        
        # Initialize Slack client if available
        self.slack_client = None
        if self.platform == "slack" and SLACK_AVAILABLE:
            try:
                self.slack_client = WebClient(token=SLACK_BOT_TOKEN)
                # Test connection
                response = self.slack_client.auth_test()
                print(f"Connected to Slack as {response['user']}")
            except Exception as e:
                print(f"Error connecting to Slack: {str(e)}")
        
        # Initialize Discord client if available
        self.discord_client = None
        if self.platform == "discord" and DISCORD_AVAILABLE:
            try:
                intents = discord.Intents.default()
                intents.message_content = True
                self.discord_client = commands.Bot(command_prefix="!", intents=intents)
                # Note: Discord requires running the bot in an event loop
                # which will be done when needed
                print("Discord client initialized (not connected)")
            except Exception as e:
                print(f"Error initializing Discord client: {str(e)}")
    
    def post_initial_market(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Post initial market details for approval.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        if self.platform == "slack" and self.slack_client:
            return self._post_slack_initial_market(market)
        elif self.platform == "discord" and self.discord_client:
            return self._post_discord_initial_market(market)
        else:
            print("No messaging platform available for posting initial market")
            # For testing/demo purposes, simulate a message ID
            return f"market_{market.get('id', 'unknown')}_initial"
    
    def post_final_market(self, market: Dict[str, Any], image_path: str) -> Optional[str]:
        """
        Post final market details with banner for approval.
        
        Args:
            market (Dict[str, Any]): Market data
            image_path (str): Path to banner image
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        if self.platform == "slack" and self.slack_client:
            return self._post_slack_final_market(market, image_path)
        elif self.platform == "discord" and self.discord_client:
            return self._post_discord_final_market(market, image_path)
        else:
            print("No messaging platform available for posting final market")
            # For testing/demo purposes, simulate a message ID
            return f"market_{market.get('id', 'unknown')}_final"
    
    def _post_slack_initial_market(self, market: Dict[str, Any]) -> Optional[str]:
        """Post initial market to Slack."""
        try:
            # Create blocks for market details
            blocks = self._create_slack_market_blocks(market)
            
            # Add initial approval actions
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👍 Approve"
                        },
                        "style": "primary",
                        "value": "approve"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👎 Reject"
                        },
                        "style": "danger",
                        "value": "reject"
                    }
                ]
            })
            
            # Post message
            response = self.slack_client.chat_postMessage(
                channel=SLACK_CHANNEL,
                text=f"New market for initial approval: {market.get('question')}",
                blocks=blocks
            )
            
            # Return the message timestamp (used as ID in Slack)
            return response["ts"]
            
        except Exception as e:
            print(f"Error posting initial market to Slack: {str(e)}")
            return None
    
    def _post_slack_final_market(self, market: Dict[str, Any], image_path: str) -> Optional[str]:
        """Post final market with banner to Slack."""
        try:
            # Create blocks for market details
            blocks = self._create_slack_market_blocks(market)
            
            # Upload image
            try:
                with open(image_path, "rb") as image_file:
                    file_upload = self.slack_client.files_upload(
                        file=image_file,
                        title=f"Banner for {market.get('question')}",
                        channels=SLACK_CHANNEL
                    )
                    
                    # Add image block
                    blocks.append({
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": "Generated Banner"
                        },
                        "image_url": file_upload["file"]["url_private"],
                        "alt_text": f"Banner for {market.get('question')}"
                    })
            except Exception as e:
                print(f"Error uploading banner image to Slack: {str(e)}")
                # Continue without image
            
            # Add final approval actions
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👍 Approve & Deploy"
                        },
                        "style": "primary",
                        "value": "approve"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "👎 Reject"
                        },
                        "style": "danger",
                        "value": "reject"
                    }
                ]
            })
            
            # Post message
            response = self.slack_client.chat_postMessage(
                channel=SLACK_CHANNEL,
                text=f"Market with banner for final approval: {market.get('question')}",
                blocks=blocks
            )
            
            # Return the message timestamp (used as ID in Slack)
            return response["ts"]
            
        except Exception as e:
            print(f"Error posting final market to Slack: {str(e)}")
            return None
    
    def _create_slack_market_blocks(self, market: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create Slack blocks for a market."""
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": market.get('question', 'Unknown Market')
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*ID:* {market.get('id', 'Unknown')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:* {market.get('type', 'binary')}"
                    }
                ]
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Category:* {market.get('category', 'Other')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Sub-category:* {market.get('sub_category', 'Other')}"
                    }
                ]
            }
        ]
        
        # Add options
        options = market.get('options', [])
        if options:
            option_text = "*Options:*\n"
            for option in options:
                option_name = option.get('name', 'Unknown')
                option_prob = option.get('probability', 0)
                option_text += f"• {option_name} ({option_prob:.1%})\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": option_text
                }
            })
        
        # Add expiry if available
        if market.get('expiry'):
            try:
                expiry = datetime.fromtimestamp(market.get('expiry') / 1000)
                blocks.append({
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Expiry:* {expiry.strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                })
            except:
                # Continue without expiry
                pass
        
        # Add divider
        blocks.append({
            "type": "divider"
        })
        
        return blocks
    
    def _post_discord_initial_market(self, market: Dict[str, Any]) -> Optional[str]:
        """Post initial market to Discord."""
        # This would be implemented for Discord integration
        return None
    
    def _post_discord_final_market(self, market: Dict[str, Any], image_path: str) -> Optional[str]:
        """Post final market with banner to Discord."""
        # This would be implemented for Discord integration
        return None
    
    def check_approval(self, message_id: str, timeout_minutes: int = APPROVAL_WINDOW_MINUTES) -> Tuple[str, str]:
        """
        Check if a message has been approved or rejected.
        
        Args:
            message_id (str): Message ID to check
            timeout_minutes (int): Timeout in minutes
            
        Returns:
            Tuple[str, str]: Status ('approved', 'rejected', 'timeout') and reason
        """
        if self.platform == "slack" and self.slack_client:
            return self._check_slack_approval(message_id, timeout_minutes)
        elif self.platform == "discord" and self.discord_client:
            # This would be implemented for Discord integration
            pass
        
        # For testing/demo purposes, simulate approval
        # In a real implementation, this would wait for user interaction
        # on the messaging platform
        time.sleep(5)  # Simulate waiting for approval
        print(f"Simulating approval for message {message_id}")
        return "approved", "Approved for testing"
    
    def _check_slack_approval(self, message_id: str, timeout_minutes: int) -> Tuple[str, str]:
        """Check approval status of a Slack message."""
        try:
            # Calculate timeout
            end_time = datetime.now() + timedelta(minutes=timeout_minutes)
            
            # Check for reactions periodically
            while datetime.now() < end_time:
                # Get message reactions
                response = self.slack_client.reactions_get(
                    channel=SLACK_CHANNEL,
                    timestamp=message_id
                )
                
                # Check for thumbs up/down reactions
                reactions = response.get("message", {}).get("reactions", [])
                
                # Count reactions
                approval_count = 0
                rejection_count = 0
                
                for reaction in reactions:
                    if reaction.get("name") == "+1" or reaction.get("name") == "thumbsup":
                        approval_count += reaction.get("count", 0)
                    elif reaction.get("name") == "-1" or reaction.get("name") == "thumbsdown":
                        rejection_count += reaction.get("count", 0)
                
                # Check if there's a decision
                if approval_count > rejection_count and approval_count >= 1:
                    return "approved", f"Approved with {approval_count} approvals vs {rejection_count} rejections"
                elif rejection_count > approval_count and rejection_count >= 1:
                    return "rejected", f"Rejected with {rejection_count} rejections vs {approval_count} approvals"
                
                # Check if there are any button interactions
                # This would require additional Slack API calls to check interactive responses
                
                # Wait before checking again
                time.sleep(30)  # Check every 30 seconds
            
            # If we reach here, it's a timeout
            return "timeout", f"No decision after {timeout_minutes} minutes"
            
        except Exception as e:
            print(f"Error checking approval status: {str(e)}")
            return "failed", f"Error: {str(e)}"
    
    def post_summary(self, summary: Dict[str, Any]) -> Optional[str]:
        """
        Post summary of pipeline run.
        
        Args:
            summary (Dict[str, Any]): Summary data
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        if self.platform == "slack" and self.slack_client:
            return self._post_slack_summary(summary)
        elif self.platform == "discord" and self.discord_client:
            # This would be implemented for Discord integration
            pass
        
        # Log summary if no platform available
        print("Pipeline summary:")
        print(json.dumps(summary, indent=2))
        return None
    
    def _post_slack_summary(self, summary: Dict[str, Any]) -> Optional[str]:
        """Post summary to Slack."""
        try:
            # Create summary blocks
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Pipeline Run Summary"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Start Time:* {summary.get('start_time')}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*End Time:* {summary.get('end_time')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Markets Processed:* {summary.get('markets_processed', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Markets Deployed:* {summary.get('markets_deployed', 0)}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Markets Rejected:* {summary.get('markets_rejected', 0)}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Markets Failed:* {summary.get('markets_failed', 0)}"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add details for each market (limited to avoid exceeding message size limits)
            markets = summary.get("markets", {})
            market_count = 0
            
            for market_id, market_data in markets.items():
                if market_count >= 10:  # Limit to 10 markets in summary
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Plus {len(markets) - 10} more markets...*"
                        }
                    })
                    break
                
                status = market_data.get("status", "unknown")
                status_emoji = "✅" if status == "deployed" else "❌" if status in ["rejected", "failed"] else "⏳"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{status_emoji} *{market_data.get('question', market_id)}*\nStatus: {status}"
                    }
                })
                
                market_count += 1
            
            # Post message
            response = self.slack_client.chat_postMessage(
                channel=SLACK_CHANNEL,
                text=f"Pipeline Run Summary: {summary.get('markets_deployed', 0)} markets deployed",
                blocks=blocks
            )
            
            # Return the message timestamp (used as ID in Slack)
            return response["ts"]
            
        except Exception as e:
            print(f"Error posting summary to Slack: {str(e)}")
            return None