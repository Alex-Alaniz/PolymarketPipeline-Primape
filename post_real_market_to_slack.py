#!/usr/bin/env python3

"""
Test Script to Fetch a Real Market and Post to Slack
 
This script fetches a real market from the Polymarket API,
processes it as the production pipeline would, and posts it to Slack
to verify proper formatting, images, and expiry dates.
"""

import os
import json
import logging
import requests
from datetime import datetime

from filter_active_markets import fetch_markets
from utils.messaging import format_market_with_images, post_slack_message

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("slack_real_market_test")

def fetch_one_market(prefer_multiple=True):
    """
    Fetch one real market from the Polymarket API.
    
    Args:
        prefer_multiple: If True, try to find a multiple-choice market.
                         If False, try to find a binary market.
    """
    logger.info("Fetching a market from the Polymarket API...")
    
    try:
        # Fetch all markets first
        markets = fetch_markets()
        
        if not markets or len(markets) == 0:
            logger.error("No markets found")
            return None
            
        logger.info(f"Fetched {len(markets)} markets from API")
        
        # First try to find a market with the preferred type and image
        for market in markets:
            is_multiple = market.get("is_multiple_option", False)
            
            # Skip if not matching our preference
            if prefer_multiple != is_multiple:
                continue
                
            # Check if it has end date and condition ID
            if market.get("endDate") and "conditionId" in market:
                logger.info(f"Found {'multiple-choice' if is_multiple else 'binary'} market: {market.get('question', 'Unknown')}")
                
                # Check if it has image
                if market.get("image_url"):
                    logger.info("Market has an image URL")
                    return market
        
        # If no market of the preferred type with image was found,
        # try to find any market of the preferred type
        for market in markets:
            is_multiple = market.get("is_multiple_option", False)
            
            # Skip if not matching our preference
            if prefer_multiple != is_multiple:
                continue
                
            if market.get("endDate"):
                logger.info(f"Found {'multiple-choice' if is_multiple else 'binary'} market without image: {market.get('question', 'Unknown')}")
                return market
                
        # If still not found, just return any market with an end date
        for market in markets:
            if market.get("endDate"):
                logger.info(f"Found market (any type) with end date: {market.get('question', 'Unknown')}")
                return market
                
        # Last resort: return the first market
        logger.info("No suitable market found, using first market")
        return markets[0]
    
    except Exception as e:
        logger.error(f"Error fetching market: {str(e)}")
        return None

def prepare_market_for_posting(market_data):
    """
    Prepare the market data for posting to Slack.
    
    This simulates the processing done by the pipeline.
    """
    if not market_data:
        return None
        
    # Clone the market data to avoid modifying the original
    import copy
    import json
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
    
    # First check if the market itself has image/icon fields
    if "image" in processed_market and processed_market["image"]:
        market_image = processed_market["image"]
        logger.info(f"Found market image: {market_image[:50]}...")
        
    if "icon" in processed_market and processed_market["icon"]:
        market_icon = processed_market["icon"]
        logger.info(f"Found market icon: {market_icon[:50]}...")
    
    # If no market image/icon, check events array for images
    if (not market_image or not market_icon) and "events" in processed_market:
        events = processed_market["events"]
        if events and len(events) > 0:
            event = events[0]  # Use the first event
            
            if not market_image and "image" in event and event["image"]:
                market_image = event["image"]
                logger.info(f"Using event image: {market_image[:50]}...")
                
            if not market_icon and "icon" in event and event["icon"]:
                market_icon = event["icon"]
                logger.info(f"Using event icon: {market_icon[:50]}...")
    
    # Set the image URLs in the market data
    if market_image:
        processed_market["event_image"] = market_image
    else:
        # If still no image, use a placeholder
        processed_market["event_image"] = "https://i.imgur.com/MRLqEOy.png"
        logger.info(f"No image found, using placeholder")
    
    # Now handle the market options
    # Determine if this is a binary or multiple choice market
    outcomes = []
    outcomes_str = processed_market.get("outcomes", "[]")
    
    # Parse outcomes if it's a string (expected format: "[\"Yes\", \"No\"]")
    if isinstance(outcomes_str, str):
        try:
            outcomes = json.loads(outcomes_str)
            logger.info(f"Parsed outcomes: {outcomes}")
        except Exception as e:
            logger.error(f"Error parsing outcomes: {e}")
            outcomes = []
    
    # If outcomes is already a list, use it directly
    elif isinstance(outcomes_str, list):
        outcomes = outcomes_str
    
    # Determine if this is a binary or multiple choice market
    is_binary = len(outcomes) == 2 and "Yes" in outcomes and "No" in outcomes
    
    if is_binary:
        # Binary market - Yes/No options
        logger.info("Processing as binary market (Yes/No)")
        processed_market["option_images"] = {
            "Yes": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png",
            "No": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png"
        }
        processed_market["options"] = ["Yes", "No"]
    else:
        # Multiple choice market
        if outcomes:
            logger.info(f"Processing as multiple choice market with {len(outcomes)} options")
            processed_market["options"] = outcomes
            
            # Set up option images
            processed_market["option_images"] = {}
            for option in outcomes:
                processed_market["option_images"][option] = market_icon or market_image or "https://i.imgur.com/MRLqEOy.png"
        else:
            # Fallback for markets with no outcomes
            logger.warning("No outcomes found in market data")
            processed_market["options"] = ["Yes", "No"]  # Default to binary
            processed_market["option_images"] = {
                "Yes": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png",
                "No": market_icon or market_image or "https://i.imgur.com/MRLqEOy.png"
            }
    
    # If this is part of an event, also extract event info
    if "events" in processed_market and processed_market["events"]:
        event = processed_market["events"][0]
        processed_market["event_id"] = event.get("id")
        processed_market["event_name"] = event.get("title")
        logger.info(f"Added event info: {processed_market.get('event_name')}")
    
    return processed_market

def post_real_market_to_slack():
    """Fetch a real market and post it to Slack."""
    # First try to fetch a multiple-choice market
    market = None
    try:
        # Try to find a multiple choice market
        market_list = fetch_markets()
        
        if market_list:
            import json
            # Look for a market with more than 2 options
            for m in market_list:
                if "outcomes" in m and isinstance(m["outcomes"], str):
                    try:
                        outcomes = json.loads(m["outcomes"])
                        if len(outcomes) > 2:
                            logger.info(f"Found multiple choice market with {len(outcomes)} options: {m.get('question')}")
                            market = m
                            break
                    except:
                        pass
    except Exception as e:
        logger.error(f"Error searching for multiple choice market: {e}")
    
    # If no multiple choice market found, fallback to any market
    if not market:
        logger.info("No multiple choice market found, falling back to a binary market")
        market = fetch_one_market(prefer_multiple=False)
    
    if not market:
        logger.error("Failed to fetch a market")
        return False
    
    # Log key details for debugging
    logger.info(f"Market question: {market.get('question', 'Unknown')}")
    logger.info(f"Market endDate: {market.get('endDate', 'Unknown')}")
    logger.info(f"Market image: {market.get('image', 'None')}")
    logger.info(f"Market icon: {market.get('icon', 'None')}")
    
    # Log event info if available
    if "events" in market and market["events"]:
        event = market["events"][0]
        logger.info(f"Event title: {event.get('title', 'Unknown')}")
        logger.info(f"Event image: {event.get('image', 'None')}")
        logger.info(f"Event icon: {event.get('icon', 'None')}")
        
    # Log outcomes
    if "outcomes" in market:
        logger.info(f"Market outcomes: {market.get('outcomes', 'None')}")
    
    # Prepare market for posting
    processed_market = prepare_market_for_posting(market)
    
    if not processed_market:
        logger.error("Failed to process market")
        return False
    
    # Post to Slack
    response = post_slack_message(message="New Market for Approval", market_data=processed_market)
    
    if response:
        logger.info(f"Posted real market to Slack with message ID {response.get('ts')}")
        return True
    else:
        logger.error("Failed to post market to Slack")
        return False

def main():
    """Main function to run the test."""
    logger.info("Starting real market Slack test")
    success = post_real_market_to_slack()
    
    if success:
        logger.info("Real market posted successfully to Slack")
        logger.info(f"Check Slack channel for the message")
    else:
        logger.error("Failed to post real market to Slack")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())