"""
Deployment message formatting utilities.

This module provides functions for formatting messages for deployment approval
in Slack, matching the format used in the original pipeline.
"""

from typing import Dict, List, Any, Tuple, Optional

def format_deployment_message(
    market_id: str,
    question: str,
    category: str,
    market_type: str,
    options: List[str],
    expiry: str,
    banner_uri: Optional[str] = None,
    event_name: Optional[str] = None,
    event_id: Optional[str] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for deployment approval.
    
    Args:
        market_id: Market ID
        question: Market question
        category: Market category
        market_type: Market type (e.g., 'Binary Market (Yes/No)')
        options: List of option values
        expiry: Human-readable expiry date 
        banner_uri: Optional banner image URI
        event_name: Optional name of the event this market belongs to
        event_id: Optional ID of the event this market belongs to
        
    Returns:
        Tuple of (message text, blocks)
    """
    # Format options as numbered list
    options_text = "*Options:*\n"
    for i, option in enumerate(options):
        options_text += f"  {i+1}. {option}\n"
    
    # Simple message text (matching original format)
    message_text = f"*Market for Deployment Approval*  *Question:* {question}"
    if event_name:
        message_text += f"  *Event:* {event_name}"
    
    # Create blocks with exact same format as original messages
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
        }
    ]
    
    # Add event information if available
    if event_name:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event:* {event_name}"
            }
        })
    
    blocks.extend([
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn", 
                    "text": f"*Category:* {category}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Expiry:* {expiry}"
                }
            ]
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Type:* {market_type}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*ID:* {market_id}"
                }
            ]
        }
    ])
    
    # Add event ID if available
    if event_id:
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Event ID:* {event_id}"
                }
            ]
        })
    
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": options_text
        }
    })
    
    # Add banner if available
    if banner_uri:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Market Banner*"
            },
            "accessory": {
                "type": "image",
                "image_url": banner_uri,
                "alt_text": "Market Banner"
            }
        })
    
    # Add approval instructions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Please review this market carefully before deployment to Apechain.\nReact with :white_check_mark: to approve or :x: to reject."
        }
    })
    
    return message_text, blocks