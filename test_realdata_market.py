#!/usr/bin/env python3

"""
Test script to post a real market from the Polymarket API to Slack.
This verifies that actual options from the market are displayed correctly.
"""

import sys
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from utils.market_transformer import MarketTransformer
from utils.messaging import post_market_for_approval

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_realdata_market")

def fetch_sample_market():
    """Fetch a sample market from Polymarket API."""
    logger.info("Fetching sample market from Polymarket API...")
    
    # Use the Champions League market query as it has multiple options
    base_url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    params = {
        "search": "Champions League",
        "limit": 5,
        "closed": "false",
        "archived": "false",
        "active": "true"
    }
    
    try:
        response = requests.get(base_url, params=params)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch markets: Status {response.status_code}")
            return None
        
        markets = response.json()
        
        if not markets:
            logger.error("No markets found in response")
            return None
        
        logger.info(f"Found {len(markets)} markets")
        
        # Transform markets using MarketTransformer
        transformer = MarketTransformer()
        transformed_markets = transformer.transform_markets(markets)
        
        if not transformed_markets:
            logger.error("No transformed markets found")
            # Return a single market if no transformed markets
            return markets[0]
        
        # Find a multi-option market if available
        multi_option_markets = [m for m in transformed_markets if m.get("is_multiple_option", False)]
        
        if multi_option_markets:
            logger.info(f"Found {len(multi_option_markets)} multi-option markets")
            market = multi_option_markets[0]
            
            # Add event image and event icon to the market data
            # These would normally come from the events field
            if len(markets) > 0 and markets[0].get("events"):
                event = markets[0]["events"][0]
                market["event_image"] = event.get("image")
                market["event_icon"] = event.get("icon")
                
                # Get event category if available
                if "category" in event:
                    market["event_category"] = event["category"]
                    logger.info(f"Found event category: {event['category']}")
            
            # Return the enhanced market
            return market
        else:
            logger.info("No multi-option markets found, using first transformed market")
            # Add event data to the market
            market = transformed_markets[0]
            if len(markets) > 0 and markets[0].get("events"):
                event = markets[0]["events"][0]
                market["event_image"] = event.get("image")
                market["event_icon"] = event.get("icon")
                
                # Get event category if available
                if "category" in event:
                    market["event_category"] = event["category"]
                    logger.info(f"Found event category: {event['category']}")
            
            return market
        
    except Exception as e:
        logger.error(f"Error fetching sample market: {str(e)}")
        return None

def post_sample_market(market_data: Dict[str, Any]) -> Optional[str]:
    """Post a sample market to Slack for approval."""
    if not market_data:
        logger.error("No market data provided")
        return None
    
    # Make sure the market has the required fields
    required_fields = [
        "question", "endDate", "image", "icon", "outcomes", "original_market_ids"
    ]
    
    missing_fields = [field for field in required_fields if not market_data.get(field)]
    if missing_fields:
        logger.error(f"Market is missing required fields: {missing_fields}")
        
        # Try to fix missing fields
        if "outcomes" in missing_fields and market_data.get("options"):
            market_data["outcomes"] = market_data["options"]
            logger.info("Using 'options' field for 'outcomes'")
            missing_fields.remove("outcomes")
            
        if "endDate" in missing_fields and market_data.get("expiryDate"):
            market_data["endDate"] = market_data["expiryDate"]
            logger.info("Using 'expiryDate' field for 'endDate'")
            missing_fields.remove("endDate")
            
        if missing_fields:
            logger.error(f"Still missing required fields: {missing_fields}")
            return None
            
    # Market is multiple-choice
    market_data["is_multiple_option"] = True
    
    logger.info("Posting multi-option market to Slack...")
    logger.info(f"Market ID: {market_data.get('id')}")
    logger.info(f"Question: {market_data.get('question')}")
    
    # Make sure outcomes is JSON string
    if isinstance(market_data.get("outcomes"), list):
        market_data["outcomes"] = json.dumps(market_data["outcomes"])
        
    # Print options for debugging    
    try:
        options = json.loads(market_data.get("outcomes", "[]"))
        logger.info(f"Options ({len(options)}): {options}")
    except Exception as e:
        logger.error(f"Error parsing options: {str(e)}")
        
    # Post market for approval
    return post_market_for_approval(market_data)

def main():
    """Main test function."""
    # Fetch sample market
    market_data = fetch_sample_market()
    
    if not market_data:
        logger.error("Failed to fetch sample market")
        return 1
    
    # Post sample market
    message_id = post_sample_market(market_data)
    
    if message_id:
        logger.info(f"Successfully posted sample market with message ID: {message_id}")
        return 0
    else:
        logger.error("Failed to post sample market")
        return 1

if __name__ == "__main__":
    sys.exit(main())