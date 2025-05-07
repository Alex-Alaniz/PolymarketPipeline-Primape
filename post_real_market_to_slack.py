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
            
    # If no image_url is available, add a placeholder image
    if not processed_market.get("image_url"):
        # Use a generic prediction market image
        processed_market["image_url"] = "https://i.imgur.com/MRLqEOy.png"
        logger.info("Added placeholder image URL")
        
    # Handle options based on market type
    is_multiple = processed_market.get("is_multiple_option", False)
    
    if not is_multiple:
        # Binary market - add Yes/No options with images
        processed_market["option_images"] = {
            "Yes": processed_market.get("image_url", "https://i.imgur.com/MRLqEOy.png"),
            "No": processed_market.get("image_url", "https://i.imgur.com/MRLqEOy.png")
        }
        logger.info(f"Added Yes/No option images")
    else:
        # Multiple choice market - set up options with images
        processed_market["options"] = []
        processed_market["option_images"] = {}
        
        # Try to get options from different fields in the data
        options = []
        if "outcomes" in processed_market and isinstance(processed_market["outcomes"], list):
            options = processed_market["outcomes"]
            logger.info(f"Found {len(options)} options in 'outcomes' field")
        elif "answers" in processed_market and isinstance(processed_market["answers"], list):
            options = processed_market["answers"]
            logger.info(f"Found {len(options)} options in 'answers' field")
        
        # If options were found, add them with images
        if options:
            processed_market["options"] = options
            
            # Add an image for each option
            for option in options:
                processed_market["option_images"][option] = processed_market.get("image_url", "https://i.imgur.com/MRLqEOy.png")
            
            logger.info(f"Added {len(options)} multiple choice options with images")
        else:
            # If no options found, create some placeholder options
            default_options = ["Option A", "Option B", "Option C"]
            processed_market["options"] = default_options
            
            for option in default_options:
                processed_market["option_images"][option] = processed_market.get("image_url", "https://i.imgur.com/MRLqEOy.png")
                
            logger.info("Added default multiple choice options with images")
    
    # Set event image if available
    processed_market["event_image"] = processed_market.get("image_url", "https://i.imgur.com/MRLqEOy.png")
    logger.info(f"Set event image: {processed_market['event_image'][:50]}...")
    
    return processed_market

def post_real_market_to_slack():
    """Fetch a real market and post it to Slack."""
    # Fetch a real market
    market = fetch_one_market()
    
    if not market:
        logger.error("Failed to fetch a market")
        return False
    
    # Log key details for debugging
    logger.info(f"Market question: {market.get('question', 'Unknown')}")
    logger.info(f"Market endDate: {market.get('endDate', 'Unknown')}")
    logger.info(f"Market image URL: {market.get('image_url', 'None')}")
    
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