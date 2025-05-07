#!/usr/bin/env python3

"""
Find a Multiple Choice Market from Polymarket API

This script explores different Polymarket API endpoints to find
a multiple choice market (more than Yes/No options) to use for testing.
"""

import json
import requests
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_finder")

def explore_endpoints():
    """Explore different endpoints to find a multiple choice market."""
    
    # Endpoints to try
    endpoints = [
        "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=200",
        "https://gamma-api.polymarket.com/markets?category=Sports&closed=false&archived=false&active=true&limit=100",
        "https://gamma-api.polymarket.com/markets?category=Politics&closed=false&archived=false&active=true&limit=100",
        "https://gamma-api.polymarket.com/markets?category=Crypto&closed=false&archived=false&active=true&limit=100",
        "https://gamma-api.polymarket.com/markets?category=Entertainment&closed=false&archived=false&active=true&limit=100",
        "https://gamma-api.polymarket.com/events?limit=100"
    ]
    
    for endpoint in endpoints:
        logger.info(f"Checking endpoint: {endpoint}")
        response = requests.get(endpoint)
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if not isinstance(data, list):
                    logger.info(f"Endpoint returned non-list data: {type(data)}")
                    continue
                    
                logger.info(f"Found {len(data)} items")
                
                # Check for markets with multiple outcomes
                for item in data:
                    if "outcomes" in item and isinstance(item.get("outcomes"), str):
                        try:
                            outcomes = json.loads(item.get("outcomes"))
                            
                            if isinstance(outcomes, list) and len(outcomes) > 2:
                                logger.info(f"FOUND MULTIPLE CHOICE MARKET!")
                                logger.info(f"Question: {item.get('question', 'Unknown')}")
                                logger.info(f"Outcomes: {outcomes}")
                                logger.info(f"ID: {item.get('id', 'Unknown')}")
                                logger.info(f"Image: {item.get('image', 'None')}")
                                logger.info(f"Icon: {item.get('icon', 'None')}")
                                logger.info(f"Full item data: {json.dumps(item, indent=2)}")
                                return item
                                
                        except Exception as e:
                            pass  # Skip items with parsing errors
                            
                    # For events endpoint
                    if "markets" in item and isinstance(item.get("markets"), list):
                        for market in item.get("markets"):
                            if "outcomes" in market and isinstance(market.get("outcomes"), str):
                                try:
                                    outcomes = json.loads(market.get("outcomes"))
                                    
                                    if isinstance(outcomes, list) and len(outcomes) > 2:
                                        logger.info(f"FOUND MULTIPLE CHOICE MARKET IN EVENT!")
                                        logger.info(f"Question: {market.get('question', 'Unknown')}")
                                        logger.info(f"Outcomes: {outcomes}")
                                        logger.info(f"ID: {market.get('id', 'Unknown')}")
                                        logger.info(f"Image: {market.get('image', 'None')}")
                                        logger.info(f"Icon: {market.get('icon', 'None')}")
                                        logger.info(f"Event title: {item.get('title', 'Unknown')}")
                                        logger.info(f"Full market data: {json.dumps(market, indent=2)}")
                                        return market
                                        
                                except Exception as e:
                                    pass  # Skip items with parsing errors
                
            except Exception as e:
                logger.error(f"Error processing endpoint {endpoint}: {e}")
        else:
            logger.error(f"Failed to fetch from {endpoint}: {response.status_code}")
    
    logger.info("No multiple choice markets found in any endpoint")
    return None

def main():
    """Main function to find multiple choice markets."""
    logger.info("Starting search for multiple choice markets")
    market = explore_endpoints()
    
    if market:
        logger.info("Successfully found a multiple choice market")
        # Save to a file for later use
        with open("multiple_choice_market.json", "w") as f:
            json.dump(market, f, indent=2)
        logger.info("Saved market data to multiple_choice_market.json")
    else:
        logger.error("Failed to find any multiple choice markets")
    
    return 0 if market else 1

if __name__ == "__main__":
    exit(main())