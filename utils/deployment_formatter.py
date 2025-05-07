"""
Format deployment approval messages for Slack.

This module provides functions for formatting market deployment approval messages
with rich formatting, including event banners, option images, and category information.
"""

from typing import Dict, List, Any, Optional, Tuple, Union

def format_deployment_message(
    market_id: Union[str, int],
    question: str,
    category: str,
    market_type: str = "Binary Market (Yes/No)",
    options: Optional[List[str]] = None,
    expiry: str = "Unknown",
    banner_uri: Optional[str] = None,
    event_name: Optional[str] = None,
    event_id: Optional[str] = None,
    event_image: Optional[str] = None,
    event_icon: Optional[str] = None,
    option_images: Optional[Dict[str, str]] = None,
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Format a market message for deployment approval with rich formatting.
    
    Args:
        market_id: Market ID
        question: Market question
        category: Market category
        market_type: Type of market (binary, categorical, etc.)
        options: List of option values
        expiry: Human-readable expiry date
        banner_uri: Optional banner image URI
        event_name: Optional event name
        event_id: Optional event ID
        event_image: Optional event banner image URI
        event_icon: Optional event icon URI
        option_images: Optional dictionary mapping option values to image URIs
        
    Returns:
        Tuple[str, List[Dict]]: Formatted message text and blocks
    """
    # Define emoji map for categories
    category_emoji = {
        'politics': ':ballot_box_with_ballot:',
        'crypto': ':coin:',
        'sports': ':sports_medal:',
        'business': ':chart_with_upwards_trend:',
        'culture': ':performing_arts:',
        'tech': ':computer:',
        'news': ':newspaper:',
        # Add fallback for unknown categories
        'unknown': ':question:'
    }
    
    # Get emoji for this category (case-insensitive)
    category_lower = category.lower() if category else 'unknown'
    emoji = category_emoji.get(category_lower, category_emoji['unknown'])
    
    # Default text for fallback
    message_text = f"*Deployment Approval*\n\n*Question:* {question}\n*Category:* {emoji} {category.capitalize() if category else 'Unknown'}"
    
    # Ensure options is a list
    if options is None:
        options = ["Yes", "No"]
    
    # Create rich message blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Deployment Approval",
                "emoji": True
            }
        }
    ]
    
    # Add event info and banner if available
    if event_name:
        # First add the event banner if available
        if event_image:
            blocks.append({
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": f"Event: {event_name}",
                    "emoji": True
                },
                "image_url": event_image,
                "alt_text": event_name
            })
        
        # Then add the event information
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Event:* {event_name} · ID: `{event_id or 'N/A'}`"
            }
        })
    
    # Add the market question
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"*Market Question:* {question}"
        }
    })
    
    # Add metadata section
    blocks.append({
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*Category:* {emoji} {category.capitalize() if category else 'Unknown'}"
            },
            {
                "type": "mrkdwn",
                "text": f"*Type:* {market_type}"
            }
        ]
    })
    
    # Add second row of metadata
    blocks.append({
        "type": "section",
        "fields": [
            {
                "type": "mrkdwn",
                "text": f"*ID:* `{market_id}`"
            },
            {
                "type": "mrkdwn",
                "text": f"*Expiry:* {expiry}"
            }
        ]
    })
    
    # Add market banner if available and different from event banner
    if banner_uri and banner_uri != event_image:
        blocks.append({
            "type": "image",
            "title": {
                "type": "plain_text",
                "text": "Market Banner",
                "emoji": True
            },
            "image_url": banner_uri,
            "alt_text": "Market Banner"
        })
    
    # Add options section
    if options:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Options:*"
            }
        })
        
        # Add each option with its image if available
        for i, option in enumerate(options):
            option_value = str(option)
            
            # Create option section
            option_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"• {option_value}"
                }
            }
            
            # Add icon image if available
            icon_url = None
            if option_images and option_value in option_images:
                icon_url = option_images[option_value]
                
            if icon_url:
                option_block["accessory"] = {
                    "type": "image",
                    "image_url": icon_url,
                    "alt_text": option_value
                }
                
            blocks.append(option_block)
    
    # Add event icon if available
    if event_icon:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Event Icon:*"
            },
            "accessory": {
                "type": "image",
                "image_url": event_icon,
                "alt_text": "Event Icon"
            }
        })
    
    # Add divider
    blocks.append({"type": "divider"})
    
    # Add approval instructions
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Please review this market carefully before deployment to Apechain.\nReact with :white_check_mark: to approve or :x: to reject."
        }
    })
    
    return message_text, blocks