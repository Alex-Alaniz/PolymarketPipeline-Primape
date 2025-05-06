#!/usr/bin/env python3
"""
Check Deployment Approval Message Format

This script examines the format of deployment approval messages in Slack
and creates a function to match this format for consistency.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Tuple, Optional

from utils.messaging import get_channel_history

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_deployment_approval_messages(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Find deployment approval messages in Slack.
    
    Args:
        limit: Maximum number of messages to search
        
    Returns:
        List of deployment approval messages
    """
    messages, _ = get_channel_history(limit=limit)
    
    deployment_messages = []
    for message in messages:
        text = message.get('text', '')
        if 'Market for Deployment Approval' in text:
            deployment_messages.append(message)
    
    logger.info(f"Found {len(deployment_messages)} deployment approval messages")
    return deployment_messages

def analyze_deployment_message_format(message: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the format of a deployment approval message.
    
    Args:
        message: Message data dictionary
        
    Returns:
        Dictionary of format analysis
    """
    block_count = len(message.get('blocks', []))
    block_types = [block.get('type') for block in message.get('blocks', [])]
    
    # Get block text content
    block_texts = []
    for block in message.get('blocks', []):
        if block.get('type') == 'section' and 'text' in block:
            text_block = block.get('text', {})
            if text_block.get('type') == 'mrkdwn':
                block_texts.append(text_block.get('text', ''))
    
    # Analyze sections
    has_header = block_types and block_types[0] == 'header'
    has_question = any('Question' in text for text in block_texts)
    has_category = any('Category' in text for text in block_texts)
    has_options = any('Options' in text for text in block_texts)
    has_expiry = any('Expiry' in text for text in block_texts)
    has_banner = any('Banner' in text for text in block_texts)
    
    # Format analysis result
    analysis = {
        'block_count': block_count,
        'block_types': block_types,
        'has_header': has_header,
        'has_question': has_question,
        'has_category': has_category,
        'has_options': has_options,
        'has_expiry': has_expiry,
        'has_banner': has_banner,
        'text_preview': message.get('text', '')[:100] + ('...' if len(message.get('text', '')) > 100 else '')
    }
    
    return analysis

def format_deployment_message(
    market_id: str,
    question: str,
    category: str,
    options: List[str],
    expiry: str,
    banner_uri: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for deployment approval.
    
    Args:
        market_id: Market ID
        question: Market question
        category: Market category
        options: List of option values
        expiry: Human-readable expiry date
        banner_uri: Optional banner image URI
        
    Returns:
        Tuple of (message text, blocks)
    """
    # Format options as comma-separated string
    options_str = ', '.join(options) if options else 'Yes, No'
    
    # Format message text
    message_text = f"*Market for Deployment Approval*  *Question:* {question}"
    
    # Create blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Market for Deployment Approval",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {question}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Category:* {category}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Options:* {options_str}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Expiry:* {expiry}"
            }
        }
    ]
    
    # Add banner if available
    if banner_uri:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Banner:* {banner_uri}"
            }
        })
    
    # Add approval context
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "React with :white_check_mark: to approve deployment or :x: to reject"
        }
    })
    
    return message_text, blocks

def save_function_to_file():
    """Save the format_deployment_message function to a file."""
    function_code = """
def format_deployment_message(
    market_id: str,
    question: str,
    category: str,
    options: List[str],
    expiry: str,
    banner_uri: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    \"\"\"
    Format a market message for deployment approval.
    
    Args:
        market_id: Market ID
        question: Market question
        category: Market category
        options: List of option values
        expiry: Human-readable expiry date
        banner_uri: Optional banner image URI
        
    Returns:
        Tuple of (message text, blocks)
    \"\"\"
    # Format options as comma-separated string
    options_str = ', '.join(options) if options else 'Yes, No'
    
    # Format message text
    message_text = f"*Market for Deployment Approval*  *Question:* {question}"
    
    # Create blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Market for Deployment Approval",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Question:* {question}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Category:* {category}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Options:* {options_str}"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Expiry:* {expiry}"
            }
        }
    ]
    
    # Add banner if available
    if banner_uri:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Banner:* {banner_uri}"
            }
        })
    
    # Add approval context
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "React with :white_check_mark: to approve deployment or :x: to reject"
        }
    })
    
    return message_text, blocks
"""
    
    with open('format_deployment_message.py', 'w') as f:
        f.write(function_code)
    
    logger.info("Saved format_deployment_message function to format_deployment_message.py")

def main():
    """Main function to check deployment approval message format."""
    try:
        # Find deployment approval messages
        deployment_messages = find_deployment_approval_messages()
        
        if not deployment_messages:
            logger.warning("No deployment approval messages found")
            # Still save the function
            save_function_to_file()
            return 0
        
        # Analyze message format
        for i, message in enumerate(deployment_messages):
            analysis = analyze_deployment_message_format(message)
            logger.info(f"Deployment message {i+1}:")
            logger.info(f"  Text: {analysis['text_preview']}")
            logger.info(f"  Block count: {analysis['block_count']}")
            logger.info(f"  Block types: {analysis['block_types']}")
            logger.info(f"  Has header: {analysis['has_header']}")
            logger.info(f"  Has question: {analysis['has_question']}")
            logger.info(f"  Has category: {analysis['has_category']}")
            logger.info(f"  Has options: {analysis['has_options']}")
            logger.info(f"  Has expiry: {analysis['has_expiry']}")
            logger.info(f"  Has banner: {analysis['has_banner']}")
        
        # Save first message as example
        with open('deployment_message_sample.json', 'w') as f:
            json.dump(deployment_messages[0], f, indent=2)
        
        logger.info("Saved deployment message sample to deployment_message_sample.json")
        
        # Save function
        save_function_to_file()
        
        return 0
        
    except Exception as e:
        logger.error(f"Error checking deployment message format: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())