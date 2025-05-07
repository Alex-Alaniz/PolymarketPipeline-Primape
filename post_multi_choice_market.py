#!/usr/bin/env python3

"""
Post a Multiple Choice Market to Slack

This script posts the previously found multiple-choice market to Slack
to verify proper formatting with multiple options.
"""

import os
import json
import logging
from datetime import datetime
import copy

from utils.messaging import format_market_with_images, post_slack_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("multi_choice_post")

def prepare_market_for_posting(market_data):
    """
    Prepare the market data for posting to Slack.
    
    Args:
        market_data: The raw market data from the API
        
    Returns:
        Processed market data ready for Slack posting
    """
    if not market_data:
        return None
        
    # Clone the market data to avoid modifying the original
    processed_market = copy.deepcopy(market_data)
    
    # Set the category to uncategorized
    processed_market["category"] = "uncategorized"
    
    # Handle expiry date
    if "endDate" in processed_market:
        processed_market["expiry_time"] = processed_market["endDate"]
        
        # Also convert to a readable format if it's in ISO format
        try:
            if isinstance(processed_market["endDate"], str) and "T" in processed_market["endDate"]:
                from datetime import datetime
                expiry_date = datetime.fromisoformat(processed_market["endDate"].replace("Z", "+00:00"))
                processed_market["expiry_time"] = expiry_date.strftime("%Y-%m-%d %H:%M UTC")
                logger.info(f"Formatted expiry date: {processed_market['expiry_time']}")
        except Exception as e:
            logger.error(f"Error formatting expiry date: {e}")
    
    # Get the image URLs for this market
    market_image = None
    market_icon = None
    
    # Check if the market itself has image/icon fields
    if "image" in processed_market and processed_market["image"]:
        market_image = processed_market["image"]
        logger.info(f"Found market image: {market_image[:50]}...")
        
    if "icon" in processed_market and processed_market["icon"]:
        market_icon = processed_market["icon"]
        logger.info(f"Found market icon: {market_icon[:50]}...")
    
    # Set the image URLs in the market data
    if market_image:
        processed_market["event_image"] = market_image
    else:
        # If still no image, use a placeholder
        processed_market["event_image"] = "https://i.imgur.com/MRLqEOy.png"
        logger.info(f"No image found, using placeholder")
    
    # Parse the outcomes field (expected format: "[\"Option A\", \"Option B\", \"Option C\"]")
    outcomes = []
    outcomes_str = processed_market.get("outcomes", "[]")
    
    if isinstance(outcomes_str, str):
        try:
            outcomes = json.loads(outcomes_str)
            logger.info(f"Parsed {len(outcomes)} outcomes: {outcomes}")
        except Exception as e:
            logger.error(f"Error parsing outcomes: {e}")
            outcomes = []
    elif isinstance(outcomes_str, list):
        outcomes = outcomes_str
        logger.info(f"Found {len(outcomes)} outcomes already as list")
    
    if outcomes and len(outcomes) > 0:
        processed_market["options"] = outcomes
        
        # Set up option images
        processed_market["option_images"] = {}
        for option in outcomes:
            processed_market["option_images"][option] = market_icon or market_image or "https://i.imgur.com/MRLqEOy.png"
        
        logger.info(f"Added {len(outcomes)} options with images")
    else:
        logger.warning("No outcomes found, creating default options")
        processed_market["options"] = ["Option A", "Option B", "Option C"]
        processed_market["option_images"] = {
            "Option A": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png",
            "Option B": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png",
            "Option C": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png"
        }
    
    # Set the event name/id for the market
    processed_market["event_id"] = processed_market.get("id", "unknown_id")
    processed_market["event_name"] = processed_market.get("question", "Unknown Event")
    
    return processed_market

def load_market_data():
    """Load the saved multiple choice market data."""
    try:
        with open("multiple_choice_market.json", "r") as f:
            market_data = json.load(f)
            return market_data
    except Exception as e:
        logger.error(f"Error loading market data: {e}")
        return None

def post_multiple_choice_market():
    """Post the multiple choice market to Slack."""
    # Load the saved market data
    market_data = load_market_data()
    
    if not market_data:
        logger.error("Failed to load market data")
        return False
    
    # Log key details for debugging
    logger.info(f"Market question: {market_data.get('question', 'Unknown')}")
    logger.info(f"Market outcomes: {market_data.get('outcomes', 'None')}")
    logger.info(f"Market image: {market_data.get('image', 'None')}")
    logger.info(f"Market icon: {market_data.get('icon', 'None')}")
    
    # Prepare the market for posting
    processed_market = prepare_market_for_posting(market_data)
    
    if not processed_market:
        logger.error("Failed to process market")
        return False
    
    # Post to Slack
    response = post_slack_message(
        message="New Multiple Choice Market for Approval", 
        market_data=processed_market
    )
    
    if response:
        logger.info(f"Posted multiple choice market to Slack with message ID {response.get('ts')}")
        return True
    else:
        logger.error("Failed to post market to Slack")
        return False

def main():
    """Main function to run the post."""
    logger.info("Starting multiple choice market post to Slack")
    success = post_multiple_choice_market()
    
    if success:
        logger.info("Multiple choice market posted successfully to Slack")
        logger.info(f"Check Slack channel for the message")
    else:
        logger.error("Failed to post multiple choice market to Slack")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())