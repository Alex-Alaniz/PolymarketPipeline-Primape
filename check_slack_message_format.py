#!/usr/bin/env python3
"""
Check Slack Message Format

This script fetches messages from the Slack channel to analyze their formatting.
Use this to ensure new message templates match the formatting of previous successful runs.
"""

import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional

from utils.messaging import get_channel_history

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('check_format')

def fetch_messages(limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetch messages from the Slack channel.
    
    Args:
        limit: Maximum number of messages to fetch
        
    Returns:
        List of message data dictionaries
    """
    messages, _ = get_channel_history(limit=limit)
    
    if not messages:
        logger.warning("No messages found in the channel")
        return []
    
    logger.info(f"Fetched {len(messages)} messages from Slack channel")
    return messages

def analyze_message_format(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the format of a Slack message.
    
    Args:
        message: Message data dictionary
        
    Returns:
        Dictionary of format analysis
    """
    # Extract key formatting elements
    has_blocks = 'blocks' in message
    block_count = len(message.get('blocks', []))
    block_types = [block.get('type') for block in message.get('blocks', [])]
    has_attachments = 'attachments' in message
    attachment_count = len(message.get('attachments', []))
    has_reactions = 'reactions' in message
    reaction_names = [r.get('name') for r in message.get('reactions', [])]
    
    # Check for market content patterns
    text = message.get('text', '')
    is_market_post = 'market' in text.lower() or 'question' in text.lower()
    has_category = 'category' in text.lower()
    has_options = 'options' in text.lower()
    
    # Format analysis result
    analysis = {
        'message_type': 'market_post' if is_market_post else 'other',
        'has_blocks': has_blocks,
        'block_count': block_count,
        'block_types': block_types,
        'has_attachments': has_attachments,
        'attachment_count': attachment_count,
        'has_reactions': has_reactions,
        'reaction_names': reaction_names,
        'has_category': has_category,
        'has_options': has_options,
        'text_preview': text[:100] + ('...' if len(text) > 100 else '')
    }
    
    return analysis

def save_message_sample(message: Dict[str, Any], filename: str = 'message_sample.json'):
    """
    Save a message sample to a JSON file.
    
    Args:
        message: Message data dictionary
        filename: Output filename
    """
    try:
        # Save message with indentation for readability
        with open(filename, 'w') as f:
            json.dump(message, f, indent=2)
        logger.info(f"Message sample saved to {filename}")
    except Exception as e:
        logger.error(f"Error saving message sample: {str(e)}")

def main():
    """Main function to check message formats."""
    try:
        # Fetch messages
        messages = fetch_messages(limit=20)
        
        if not messages:
            logger.error("No messages found to analyze")
            return 1
        
        # Find market posts
        market_messages = []
        for message in messages:
            analysis = analyze_message_format(message)
            if analysis['message_type'] == 'market_post':
                market_messages.append(message)
                logger.info(f"Found market post: {analysis['text_preview']}")
                logger.info(f"Format details: {json.dumps(analysis, indent=2)}")
        
        # Save a sample message
        if market_messages:
            save_message_sample(market_messages[0])
            return 0
        else:
            logger.warning("No market posts found in the channel")
            return 0
        
    except Exception as e:
        logger.error(f"Error checking message formats: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())