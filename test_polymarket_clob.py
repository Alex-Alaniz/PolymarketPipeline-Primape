#!/usr/bin/env python3
"""
Test script for the Polymarket CLOB API
Based on the documentation at https://docs.polymarket.com/#get-markets
"""

import os
import json
import logging
import requests
from pprint import pprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("polymarket_clob_test")

# CLOB API endpoint
CLOB_ENDPOINT = "https://clob.polymarket.com"

def get_markets(next_cursor=""):
    """
    Get available CLOB markets (paginated).
    
    Args:
        next_cursor: Cursor to start with, used for traversing paginated response
        
    Returns:
        Response data if successful, None otherwise
    """
    # Construct request URL
    url = f"{CLOB_ENDPOINT}/markets"
    if next_cursor:
        url += f"?next_cursor={next_cursor}"
    
    # Set headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        logger.info(f"Fetching markets from {url}")
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check status code
        if response.status_code == 200:
            data = response.json()
            logger.info(f"Successfully fetched markets. Status code: {response.status_code}")
            return data
        else:
            logger.error(f"Failed to fetch markets. Status code: {response.status_code}")
            logger.error(f"Response content: {response.text[:500]}")
            return None
            
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        return None

def explore_markets():
    """
    Explore markets data structure and print insights.
    """
    # Get first page of markets
    markets_data = get_markets()
    
    if not markets_data:
        logger.error("Could not fetch markets data")
        return
    
    # Print markets data structure
    logger.info("Markets data structure:")
    print("\nMARKETS DATA STRUCTURE:")
    print("-----------------------")
    
    # Extract top-level fields
    top_level_fields = list(markets_data.keys())
    print(f"Top-level fields: {top_level_fields}")
    
    # Check if 'data' field exists
    if 'data' in markets_data and isinstance(markets_data['data'], list):
        markets = markets_data['data']
        market_count = len(markets)
        print(f"\nFound {market_count} markets")
        
        if market_count > 0:
            # Print a sample market
            print("\nSAMPLE MARKET STRUCTURE:")
            print("------------------------")
            sample_market = markets[0]
            sample_json = json.dumps(sample_market, indent=2)
            print(sample_json[:2000] + "..." if len(sample_json) > 2000 else sample_json)
            
            # Extract fields from sample market
            market_fields = list(sample_market.keys())
            print(f"\nMarket fields: {market_fields}")
            
            # Print some stats about markets
            print("\nMARKET STATISTICS:")
            print("------------------")
            
            # Questions
            questions = [market.get('question', 'Unknown') for market in markets]
            print(f"\nSample questions:")
            for i, question in enumerate(questions[:5], 1):
                print(f"{i}. {question}")
            
            # Categories
            categories = {}
            for market in markets:
                category = market.get('category', 'Unknown')
                if category in categories:
                    categories[category] += 1
                else:
                    categories[category] = 1
            
            print("\nCategories distribution:")
            for category, count in categories.items():
                print(f"- {category}: {count} markets")
    else:
        print("\nNo 'data' field with markets found in the response")
    
    # Pagination details
    print("\nPAGINATION DETAILS:")
    print("------------------")
    if 'next_cursor' in markets_data:
        print(f"Next cursor: {markets_data['next_cursor']}")
    if 'limit' in markets_data:
        print(f"Limit: {markets_data['limit']}")
    if 'count' in markets_data:
        print(f"Count: {markets_data['count']}")

def main():
    """Main function"""
    logger.info("Starting Polymarket CLOB API test")
    explore_markets()
    logger.info("Test completed")

if __name__ == "__main__":
    main()