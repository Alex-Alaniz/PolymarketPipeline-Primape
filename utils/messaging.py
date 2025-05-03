"""
Messaging client for Slack/Discord integration.

This module handles posting markets to Slack/Discord and checking for reactions.
"""
import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Import configuration
from config import (
    MESSAGING_PLATFORM,
    SLACK_BOT_TOKEN,
    SLACK_CHANNEL,
    DISCORD_TOKEN,
    DISCORD_CHANNEL
)

# Configure logger
logger = logging.getLogger("messaging")

# Import platform-specific libraries
if MESSAGING_PLATFORM == "slack":
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

class MessagingClient:
    """Client for interacting with messaging platforms (Slack/Discord)."""
    
    def __init__(self):
        """Initialize the messaging client based on configuration."""
        self.platform = MESSAGING_PLATFORM
        
        if self.platform == "slack":
            if not SLACK_BOT_TOKEN or not SLACK_CHANNEL:
                logger.error("Slack configuration incomplete: SLACK_BOT_TOKEN and SLACK_CHANNEL_ID required")
                raise ValueError("Slack configuration incomplete")
            
            self.client = WebClient(token=SLACK_BOT_TOKEN)
            
            # Debug Slack token
            logger.info(f"Using Slack token: {SLACK_BOT_TOKEN[:4]}...{SLACK_BOT_TOKEN[-4:]}")
            
            # Ensure channel starts with # if it's not an ID
            if SLACK_CHANNEL and not SLACK_CHANNEL.startswith('C'):
                self.channel = f"#{SLACK_CHANNEL}"
            else:
                self.channel = SLACK_CHANNEL
                
            # Try to get available channels to validate channel ID
            try:
                response = self.client.conversations_list()
                channels = response.get("channels", [])
                channel_ids = [c["id"] for c in channels]
                
                if self.channel not in channel_ids:
                    logger.warning(f"Specified channel {self.channel} not found in available channels")
                    if channel_ids:
                        # Use the first available channel as fallback
                        channel_name = next((c["name"] for c in channels if c["id"] == channel_ids[0]), "unknown")
                        logger.info(f"Using first available channel {channel_ids[0]} ({channel_name}) as fallback")
                        self.channel = channel_ids[0]
                        
                # Try to join the channel
                try:
                    logger.info(f"Attempting to join channel {self.channel}")
                    join_response = self.client.conversations_join(channel=self.channel)
                    logger.info(f"Join response: {join_response}")
                except Exception as e:
                    if "not_in_channel" in str(e) or "missing_scope" in str(e):
                        logger.warning(f"Cannot join channel due to permissions: {str(e)}")
                        logger.info("Attempting to create a direct message channel instead")
                        
                        try:
                            # Try to open a DM with ourselves as a fallback
                            open_response = self.client.conversations_open(users=self.client.auth_test()["user_id"])
                            if open_response and open_response.get("ok") and open_response.get("channel", {}).get("id"):
                                self.channel = open_response["channel"]["id"]
                                logger.info(f"Created direct message channel: {self.channel}")
                            else:
                                logger.warning("Failed to create direct message channel")
                        except Exception as dm_error:
                            logger.error(f"Error creating direct message channel: {str(dm_error)}")
                    else:
                        logger.error(f"Failed to join channel: {str(e)}")
            except Exception as e:
                logger.error(f"Error validating channels: {str(e)}")
                
            logger.info(f"Initialized Slack client with channel {self.channel}")
            
        elif self.platform == "discord":
            # Discord implementation would go here
            logger.error("Discord integration not implemented yet")
            raise NotImplementedError("Discord integration not implemented")
            
        else:
            logger.error(f"Unsupported messaging platform: {self.platform}")
            raise ValueError(f"Unsupported messaging platform: {self.platform}")
    
    def post_initial_market(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Post a market for initial approval.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Message ID if successful, None if failed
        """
        if self.platform == "slack":
            return self._post_market_to_slack(market, is_final=False)
        elif self.platform == "discord":
            # Discord implementation would go here
            return None
    
    def post_final_market(self, market: Dict[str, Any], banner_path: str) -> Optional[str]:
        """
        Post a market with banner for final approval.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_path (str): Path to banner image
            
        Returns:
            Optional[str]: Message ID if successful, None if failed
        """
        if self.platform == "slack":
            return self._post_market_to_slack(market, is_final=True, banner_path=banner_path)
        elif self.platform == "discord":
            # Discord implementation would go here
            return None
    
    def check_approval(self, message_id: str, timeout_minutes: int = 30) -> Tuple[str, Optional[str]]:
        """
        Check if a market has been approved or rejected.
        
        Args:
            message_id (str): Message ID to check
            timeout_minutes (int): Timeout in minutes
            
        Returns:
            Tuple[str, Optional[str]]: Status and reason. 
                Status can be: "approved", "rejected", "timeout", "error"
        """
        if self.platform == "slack":
            return self._check_slack_approval(message_id, timeout_minutes)
        elif self.platform == "discord":
            # Discord implementation would go here
            return "error", "Discord integration not implemented"
    
    def _post_market_to_slack(self, market: Dict[str, Any], is_final: bool = False, banner_path: Optional[str] = None) -> Optional[str]:
        """
        Post a market to Slack.
        
        Args:
            market (Dict[str, Any]): Market data
            is_final (bool): Whether this is a final approval
            banner_path (Optional[str]): Path to banner image
            
        Returns:
            Optional[str]: Message ID if successful, None if failed
        """
        # Debug channel information
        logger.info(f"Posting to Slack channel: {self.channel}")
        
        # We've already validated the channel in __init__, so we don't need to check again
        
        try:
            # Extract market data
            market_id = market.get("id", "unknown")
            question = market.get("question", "No question provided")
            market_type = market.get("type", "binary")
            category = market.get("category", "Uncategorized")
            sub_category = market.get("sub_category", "")
            
            # Create options text
            options_text = ""
            options = market.get("options", [])
            for option in options:
                name = option.get("name", "Unknown")
                probability = option.get("probability", 0)
                probability_percent = f"{probability * 100:.1f}%" if probability else "N/A"
                options_text += f"• *{name}*: {probability_percent}\n"
            
            # Format expiry date if available
            expiry_text = ""
            expiry = market.get("expiry")
            if expiry:
                # Convert timestamp from milliseconds to seconds if needed
                if expiry > 1e10:  # Large timestamp is likely in milliseconds
                    expiry = expiry / 1000
                expiry_date = datetime.fromtimestamp(expiry).strftime("%Y-%m-%d")
                expiry_text = f"📆 *Expiry*: {expiry_date}\n"
            
            # Approval stage text
            stage_text = "FINAL APPROVAL (with banner)" if is_final else "INITIAL APPROVAL"
            
            # Blocks for Slack message
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Market for {stage_text}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Question*: {question}\n\n*ID*: `{market_id}`\n*Type*: {market_type}\n*Category*: {category} {f'({sub_category})' if sub_category else ''}\n{expiry_text}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Options*:\n{options_text}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "React with ✅ to approve or ❌ to reject"
                        }
                    ]
                },
                {
                    "type": "divider"
                }
            ]
            
            # Add banner image block if available (for final approval)
            if is_final and banner_path:
                try:
                    # Upload the image file
                    upload_response = self.client.files_upload(
                        channels=self.channel,
                        file=banner_path,
                        title=f"Banner for {market_id}"
                    )
                    
                    if upload_response and upload_response.get("file"):
                        file_id = upload_response["file"]["id"]
                        
                        # Add a block referencing the uploaded image
                        blocks.insert(1, {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": "*Generated Banner Image*:"
                            }
                        })
                        blocks.insert(2, {
                            "type": "image",
                            "image_url": upload_response["file"]["permalink"],
                            "alt_text": f"Banner for {question}"
                        })
                except Exception as e:
                    logger.error(f"Error uploading banner image: {str(e)}")
                    # Continue without the image if upload fails
            
            # Post message
            response = self.client.chat_postMessage(
                channel=self.channel,
                text=f"Market for {stage_text}: {question}",
                blocks=blocks
            )
            
            # Get message ID (ts)
            message_id = response.get("ts")
            
            if message_id:
                logger.info(f"Posted market {market_id} to Slack with message ID {message_id}")
                
                # Add initial reactions for voting
                self.client.reactions_add(
                    channel=self.channel,
                    timestamp=message_id,
                    name="white_check_mark"  # ✅
                )
                
                self.client.reactions_add(
                    channel=self.channel,
                    timestamp=message_id,
                    name="x"  # ❌
                )
                
                return message_id
            else:
                logger.error("Failed to get message ID from Slack response")
                return None
                
        except SlackApiError as e:
            logger.error(f"SlackApiError: {e.response['error']}")
            return None
        except Exception as e:
            logger.error(f"Error posting to Slack: {str(e)}")
            return None
    
    def _check_slack_approval(self, message_id: str, timeout_minutes: int = 30) -> Tuple[str, Optional[str]]:
        """
        Check if a market has been approved or rejected in Slack.
        
        Args:
            message_id (str): Slack message ID to check
            timeout_minutes (int): Timeout in minutes
            
        Returns:
            Tuple[str, Optional[str]]: Status and reason
                Status can be: "approved", "rejected", "timeout", "error"
        """
        try:
            # Get reactions on the message
            response = self.client.reactions_get(
                channel=self.channel,
                timestamp=message_id
            )
            
            if not response or "message" not in response:
                return "error", "Failed to get message reactions"
            
            # Process reactions
            reactions = response["message"].get("reactions", [])
            
            approve_count = 0
            reject_count = 0
            
            for reaction in reactions:
                if reaction["name"] == "white_check_mark":
                    approve_count = reaction.get("count", 0)
                    # Subtract 1 for the bot's own reaction
                    if approve_count > 0:
                        approve_count -= 1
                elif reaction["name"] == "x":
                    reject_count = reaction.get("count", 0)
                    # Subtract 1 for the bot's own reaction
                    if reject_count > 0:
                        reject_count -= 1
            
            # Check if approved or rejected (need at least one real user reaction)
            if approve_count > 0 and approve_count > reject_count:
                return "approved", f"Approved with {approve_count} approvals and {reject_count} rejections"
            elif reject_count > 0 and reject_count >= approve_count:
                return "rejected", f"Rejected with {reject_count} rejections and {approve_count} approvals"
            
            # Check if timed out
            message_time = float(message_id.split('.')[0])
            message_datetime = datetime.fromtimestamp(message_time)
            current_time = datetime.now()
            
            if current_time - message_datetime > timedelta(minutes=timeout_minutes):
                return "timeout", f"Timed out after {timeout_minutes} minutes"
            
            # Still pending
            return "pending", "Approval still pending"
            
        except SlackApiError as e:
            logger.error(f"SlackApiError checking approval: {e.response['error']}")
            return "error", f"Slack API error: {e.response['error']}"
        except Exception as e:
            logger.error(f"Error checking approval: {str(e)}")
            return "error", f"Error checking approval: {str(e)}"