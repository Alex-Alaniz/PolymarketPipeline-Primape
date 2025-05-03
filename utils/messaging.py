"""
Messaging Client for Slack/Discord

This module provides a unified interface for posting messages to Slack or Discord
and handling reactions for the approval process.
"""

import os
import logging
import time
import json
from typing import List, Dict, Any, Optional

import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from config import SLACK_BOT_TOKEN, SLACK_CHANNEL, DISCORD_TOKEN, DISCORD_CHANNEL, MESSAGING_PLATFORM

logger = logging.getLogger("messaging")

class MessagingClient:
    """Client for interacting with Slack or Discord"""
    
    def __init__(self, platform: str = None, channel_id: str = None):
        """
        Initialize the messaging client
        
        Args:
            platform: Messaging platform to use ('slack' or 'discord')
            channel_id: Channel ID to post messages to
        """
        # Use configured platform if not specified
        self.platform = platform or MESSAGING_PLATFORM
        
        # Initialize platform-specific client
        if self.platform == "slack":
            # Get Slack token and channel ID
            self.slack_token = SLACK_BOT_TOKEN
            self.slack_channel = channel_id or SLACK_CHANNEL
            
            if not self.slack_token:
                raise ValueError("SLACK_BOT_TOKEN is required for Slack integration")
            if not self.slack_channel:
                raise ValueError("SLACK_CHANNEL_ID is required for Slack integration")
            
            # Initialize Slack client
            logger.info(f"Using Slack token: {self.slack_token[:4]}...{self.slack_token[-4:]}")
            self.client = WebClient(token=self.slack_token)
            
            # Try to join the channel (if not already joined)
            try:
                logger.info(f"Attempting to join channel {self.slack_channel}")
                join_response = self.client.conversations_join(channel=self.slack_channel)
                logger.info(f"Join response: {join_response}")
            except SlackApiError as e:
                # Some errors are expected (e.g., already in channel)
                if "already_in_channel" in str(e):
                    logger.info(f"Already in channel {self.slack_channel}")
                else:
                    logger.warning(f"Error joining channel: {str(e)}")
            
            logger.info(f"Initialized Slack client with channel {self.slack_channel}")
            
        elif self.platform == "discord":
            # Get Discord token and channel
            self.discord_token = DISCORD_TOKEN
            self.discord_channel = channel_id or DISCORD_CHANNEL
            
            if not self.discord_token:
                raise ValueError("DISCORD_TOKEN is required for Discord integration")
            if not self.discord_channel:
                raise ValueError("DISCORD_CHANNEL is required for Discord integration")
            
            # Discord uses a different client (direct API calls for simplicity)
            self.client = None
            self.discord_api_url = "https://discord.com/api/v9"
            logger.info(f"Initialized Discord client with channel {self.discord_channel}")
            
        else:
            raise ValueError(f"Unsupported messaging platform: {self.platform}")
    
    def post_message(self, text: str, blocks: List[Dict[str, Any]] = None) -> Optional[str]:
        """
        Post a message to the configured channel
        
        Args:
            text: Message text (shown in notifications and fallbacks)
            blocks: Message blocks for rich formatting (Slack) or embeds (Discord)
            
        Returns:
            str: Message ID if successful, None otherwise
        """
        if self.platform == "slack":
            try:
                # Post the message to Slack
                response = self.client.chat_postMessage(
                    channel=self.slack_channel,
                    text=text,
                    blocks=blocks
                )
                
                # Return the message ID (ts in Slack)
                return response["ts"]
                
            except SlackApiError as e:
                logger.error(f"Error posting message to Slack: {str(e)}")
                return None
                
        elif self.platform == "discord":
            try:
                # Prepare the payload for Discord
                payload = {
                    "content": text
                }
                
                # Convert blocks to Discord embeds if provided
                if blocks:
                    # Simple conversion, not comprehensive
                    embeds = [{"title": "Market Information", "description": text}]
                    payload["embeds"] = embeds
                
                # Send the request to Discord API
                headers = {
                    "Authorization": f"Bot {self.discord_token}",
                    "Content-Type": "application/json"
                }
                
                response = requests.post(
                    f"{self.discord_api_url}/channels/{self.discord_channel}/messages",
                    headers=headers,
                    data=json.dumps(payload)
                )
                
                if response.status_code == 200:
                    return response.json().get("id")
                else:
                    logger.error(f"Error posting to Discord: {response.status_code} - {response.text}")
                    return None
                    
            except Exception as e:
                logger.error(f"Error posting message to Discord: {str(e)}")
                return None
    
    def add_reactions(self, message_id: str, reactions: List[str]) -> bool:
        """
        Add reactions to a message for approval/rejection
        
        Args:
            message_id: Message ID to add reactions to
            reactions: List of reaction emoji names to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        if self.platform == "slack":
            try:
                # Add each reaction
                for reaction in reactions:
                    self.client.reactions_add(
                        channel=self.slack_channel,
                        timestamp=message_id,
                        name=reaction
                    )
                    # Sleep to avoid rate limiting
                    time.sleep(0.5)
                
                return True
                
            except SlackApiError as e:
                logger.error(f"Error adding reactions to Slack message: {str(e)}")
                return False
                
        elif self.platform == "discord":
            try:
                # Discord uses unicode emoji or custom emoji IDs
                # Need to convert from name to unicode or ID
                emoji_map = {
                    "white_check_mark": "%E2%9C%85",  # URL encoded ✅
                    "x": "%E2%9D%8C"  # URL encoded ❌
                }
                
                # Add each reaction
                headers = {
                    "Authorization": f"Bot {self.discord_token}"
                }
                
                success = True
                
                for reaction in reactions:
                    emoji = emoji_map.get(reaction, reaction)
                    
                    response = requests.put(
                        f"{self.discord_api_url}/channels/{self.discord_channel}/messages/{message_id}/reactions/{emoji}/@me",
                        headers=headers
                    )
                    
                    if response.status_code not in [204, 200]:
                        logger.error(f"Error adding reaction to Discord: {response.status_code} - {response.text}")
                        success = False
                    
                    # Sleep to avoid rate limiting
                    time.sleep(0.5)
                
                return success
                
            except Exception as e:
                logger.error(f"Error adding reactions to Discord message: {str(e)}")
                return False
    
    def get_reactions(self, message_id: str) -> Dict[str, int]:
        """
        Get reactions for a message
        
        Args:
            message_id: Message ID to get reactions for
            
        Returns:
            Dict[str, int]: Dictionary of reaction emoji names and counts
        """
        reactions = {}
        
        if self.platform == "slack":
            try:
                # Get reactions from Slack
                response = self.client.reactions_get(
                    channel=self.slack_channel,
                    timestamp=message_id
                )
                
                # Extract reactions
                message = response.get("message", {})
                for reaction in message.get("reactions", []):
                    reactions[reaction["name"]] = reaction["count"]
                
            except SlackApiError as e:
                logger.error(f"Error getting reactions from Slack: {str(e)}")
                
        elif self.platform == "discord":
            try:
                # Get message from Discord
                headers = {
                    "Authorization": f"Bot {self.discord_token}"
                }
                
                response = requests.get(
                    f"{self.discord_api_url}/channels/{self.discord_channel}/messages/{message_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    message = response.json()
                    
                    # Extract reactions
                    for reaction in message.get("reactions", []):
                        reactions[reaction["emoji"]["name"]] = reaction["count"]
                else:
                    logger.error(f"Error getting message from Discord: {response.status_code} - {response.text}")
                
            except Exception as e:
                logger.error(f"Error getting reactions from Discord: {str(e)}")
        
        return reactions
    
    def post_image(self, text: str, image_path: str) -> Optional[str]:
        """
        Post an image with text to the configured channel
        
        Args:
            text: Message text
            image_path: Path to the image file
            
        Returns:
            str: Message ID if successful, None otherwise
        """
        if self.platform == "slack":
            try:
                # Upload the image to Slack
                response = self.client.files_upload_v2(
                    channel=self.slack_channel,
                    file=image_path,
                    initial_comment=text
                )
                
                # Return the message ID (ts in Slack)
                return response.get("message_ts")
                
            except SlackApiError as e:
                logger.error(f"Error posting image to Slack: {str(e)}")
                return None
                
        elif self.platform == "discord":
            try:
                # Upload the image to Discord
                with open(image_path, "rb") as image_file:
                    files = {
                        "file": (os.path.basename(image_path), image_file)
                    }
                    
                    payload = {
                        "content": text
                    }
                    
                    headers = {
                        "Authorization": f"Bot {self.discord_token}"
                    }
                    
                    response = requests.post(
                        f"{self.discord_api_url}/channels/{self.discord_channel}/messages",
                        headers=headers,
                        data={"payload_json": json.dumps(payload)},
                        files=files
                    )
                    
                    if response.status_code == 200:
                        return response.json().get("id")
                    else:
                        logger.error(f"Error posting image to Discord: {response.status_code} - {response.text}")
                        return None
                    
            except Exception as e:
                logger.error(f"Error posting image to Discord: {str(e)}")
                return None
    
    def get_channel_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent messages from the channel
        
        Args:
            limit: Maximum number of messages to retrieve
            
        Returns:
            List[Dict[str, Any]]: List of messages with their reactions
        """
        messages = []
        
        if self.platform == "slack":
            try:
                # Get channel history from Slack
                response = self.client.conversations_history(
                    channel=self.slack_channel,
                    limit=limit
                )
                
                # Process messages
                for msg in response["messages"]:
                    message_data = {
                        "id": msg["ts"],
                        "text": msg.get("text", ""),
                        "user": msg.get("user", ""),
                        "reactions": {}
                    }
                    
                    # Extract reactions
                    for reaction in msg.get("reactions", []):
                        message_data["reactions"][reaction["name"]] = reaction["count"]
                    
                    messages.append(message_data)
                
            except SlackApiError as e:
                logger.error(f"Error getting channel history from Slack: {str(e)}")
                
        elif self.platform == "discord":
            try:
                # Get channel history from Discord
                headers = {
                    "Authorization": f"Bot {self.discord_token}"
                }
                
                response = requests.get(
                    f"{self.discord_api_url}/channels/{self.discord_channel}/messages?limit={limit}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    discord_messages = response.json()
                    
                    # Process messages
                    for msg in discord_messages:
                        message_data = {
                            "id": msg["id"],
                            "text": msg.get("content", ""),
                            "user": msg.get("author", {}).get("id", ""),
                            "reactions": {}
                        }
                        
                        # Extract reactions
                        for reaction in msg.get("reactions", []):
                            message_data["reactions"][reaction["emoji"]["name"]] = reaction["count"]
                        
                        messages.append(message_data)
                else:
                    logger.error(f"Error getting channel history from Discord: {response.status_code} - {response.text}")
                
            except Exception as e:
                logger.error(f"Error getting channel history from Discord: {str(e)}")
        
        return messages