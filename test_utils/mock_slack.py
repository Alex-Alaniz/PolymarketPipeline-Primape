#!/usr/bin/env python3

"""
Mock Slack messaging module for testing purposes.

This module provides mock implementations of Slack messaging functions
for testing the pipeline without requiring actual Slack API calls.
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Store mock messages and reactions
_mock_messages = {}
_mock_reactions = {}
_mock_message_counter = 0

def is_test_environment():
    """Check if we're in test environment."""
    return os.environ.get("TESTING") == "true"

def post_message(channel_id: str, text: str, blocks: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Mock implementation of posting a message to Slack.
    
    Args:
        channel_id: The Slack channel ID to post to
        text: Plain text message content
        blocks: Rich layout blocks (optional)
        
    Returns:
        Dict with mock response containing the message timestamp (ts)
    """
    global _mock_message_counter
    
    if not is_test_environment():
        # Call actual implementation if not in test environment
        from utils.messaging import post_message as real_post_message
        return real_post_message(channel_id, text, blocks)
    
    # Mock implementation
    _mock_message_counter += 1
    message_id = f"test_message_{_mock_message_counter}_{int(datetime.now().timestamp())}"
    
    # Store the message
    _mock_messages[message_id] = {
        "text": text,
        "blocks": blocks,
        "ts": message_id,
        "channel": channel_id,
        "user": "mock_user",
        "reactions": []
    }
    
    logger.info(f"[MOCK] Posted message to Slack: {message_id}")
    
    return {"ok": True, "ts": message_id, "channel": channel_id}

def get_message_reactions(message_id: str) -> List[Dict[str, Any]]:
    """
    Mock implementation of getting reactions for a message.
    
    Args:
        message_id: The message timestamp (ts)
        
    Returns:
        List of reaction objects with name and users
    """
    if not is_test_environment():
        # Call actual implementation if not in test environment
        from utils.messaging import get_message_reactions as real_get_reactions
        return real_get_reactions(message_id)
    
    # Mock implementation
    if message_id not in _mock_messages:
        return []
    
    return _mock_messages[message_id].get("reactions", [])

def add_reaction(message_id: str, reaction: str, user: str = "mock_user"):
    """
    Add a mock reaction to a message for testing.
    
    Args:
        message_id: The message timestamp (ts)
        reaction: The reaction emoji name (without colons)
        user: The user ID who added the reaction
    """
    if message_id not in _mock_messages:
        logger.error(f"[MOCK] Cannot add reaction to non-existent message: {message_id}")
        return
    
    # Check if reaction already exists
    for existing_reaction in _mock_messages[message_id].get("reactions", []):
        if existing_reaction["name"] == reaction:
            # Add user if not already in the list
            if user not in existing_reaction["users"]:
                existing_reaction["users"].append(user)
                existing_reaction["count"] += 1
            return
    
    # Add new reaction
    new_reaction = {
        "name": reaction,
        "users": [user],
        "count": 1
    }
    
    if "reactions" not in _mock_messages[message_id]:
        _mock_messages[message_id]["reactions"] = []
    
    _mock_messages[message_id]["reactions"].append(new_reaction)
    logger.info(f"[MOCK] Added reaction :{reaction}: to message {message_id}")

def get_channel_messages(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Mock implementation of getting channel messages.
    
    Args:
        limit: Maximum number of messages to return
        
    Returns:
        List of message objects
    """
    if not is_test_environment():
        # Call actual implementation if not in test environment
        from utils.messaging import get_channel_messages as real_get_messages
        return real_get_messages(limit)
    
    # Mock implementation
    messages = list(_mock_messages.values())
    messages.sort(key=lambda m: m["ts"], reverse=True)
    return messages[:limit]

def approve_test_market(message_id: Optional[str]):
    """
    Helper function to add an approval reaction to a test message.
    
    Args:
        message_id: The message timestamp (ts)
    """
    if message_id:
        add_reaction(message_id, "white_check_mark", "mock_approver")

def reject_test_market(message_id: Optional[str]):
    """
    Helper function to add a rejection reaction to a test message.
    
    Args:
        message_id: The message timestamp (ts)
    """
    if message_id:
        add_reaction(message_id, "x", "mock_rejector")

def clear_test_data():
    """Clear all mock data."""
    global _mock_messages, _mock_reactions, _mock_message_counter
    _mock_messages = {}
    _mock_reactions = {}
    _mock_message_counter = 0
    logger.info("[MOCK] Cleared all mock Slack data")