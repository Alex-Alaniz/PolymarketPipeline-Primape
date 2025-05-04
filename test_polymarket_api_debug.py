#!/usr/bin/env python3

"""
Debug script for Polymarket API connectivity.

This script tests connectivity to the Polymarket API endpoints
and provides detailed response information to help diagnose issues.
"""

import requests
import json
import logging
import sys
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("polymarket_api_debug")

def test_polymarket_clob_api():
    """
    Test connectivity to the Polymarket CLOB API.
    """
    logger.info("Testing Polymarket CLOB API connectivity...")
    
    # Define endpoints to test
    endpoints = [
        "https://clob.polymarket.com/markets",
        "https://clob.polymarket.com/markets?active=true",
        "https://clob.polymarket.com/markets?limit=10"
    ]
    
    # Test each endpoint
    for endpoint in endpoints:
        try:
            logger.info(f"Testing endpoint: {endpoint}")
            
            # Set headers for the request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            # Make the request
            response = requests.get(endpoint, headers=headers, timeout=10)
            
            # Check response
            if response.status_code == 200:
                data = response.json()
                
                # Check if data is in expected format
                if "data" in data and isinstance(data["data"], list):
                    markets = data["data"]
                    active_markets = [m for m in markets if m.get("active", False)]
                    has_expired = any(m.get("closed", False) or m.get("archived", False) for m in markets)
                    
                    logger.info(f"Success! Received {len(markets)} markets from {endpoint}")
                    logger.info(f"Active markets: {len(active_markets)}")
                    logger.info(f"Has expired markets: {has_expired}")
                    
                    # Print first market for inspection
                    if markets:
                        logger.info("Sample market:")
                        print(json.dumps(markets[0], indent=2))
                    
                    # Check pagination
                    if "next_cursor" in data and data["next_cursor"]:
                        logger.info(f"Pagination available, next_cursor: {data['next_cursor']}")
                else:
                    logger.warning(f"Unexpected data format from {endpoint}")
                    print(json.dumps(data, indent=2))
            else:
                logger.error(f"Failed to connect to {endpoint}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
        
        except Exception as e:
            logger.error(f"Error testing {endpoint}: {str(e)}")

def test_polygon_blockchain_endpoints():
    """
    Test connectivity to the Polygon blockchain endpoints used for fetching Polymarket data.
    """
    logger.info("Testing Polygon blockchain endpoints...")
    
    # Endpoints to test
    endpoints = [
        "https://api.polygonscan.com/api?module=logs&action=getLogs&address=0x5fe561A11e7D83908608790C4D8FC820e528a348&topic0=0xf710eb0a588a212e53e58c32bf2366848fb927f5f72ce9982332922723d6ea8e",
        "https://polygon-mainnet.infura.io/v3/84842078b09946638c03157f83405213", 
        "https://polygon-rpc.com/api/v1/markets"
    ]
    
    # Test each endpoint
    for endpoint in endpoints:
        try:
            logger.info(f"Testing endpoint: {endpoint}")
            
            # Make the request
            response = requests.get(endpoint, timeout=10)
            
            # Check response
            if response.status_code == 200:
                logger.info(f"Success! Connected to {endpoint}")
                
                # Try to parse the response as JSON
                try:
                    data = response.json()
                    logger.info("Response is valid JSON")
                    
                    # Check if we got market data
                    if "result" in data:
                        result = data["result"]
                        if isinstance(result, list) and len(result) > 0:
                            logger.info(f"Found {len(result)} items in result")
                        else:
                            logger.warning("Result is empty or not a list")
                    else:
                        logger.warning("No 'result' field in response")
                except json.JSONDecodeError:
                    logger.warning("Response is not valid JSON")
                    print(response.text[:200] + "..." if len(response.text) > 200 else response.text)
            else:
                logger.error(f"Failed to connect to {endpoint}: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
        
        except Exception as e:
            logger.error(f"Error testing {endpoint}: {str(e)}")

def generate_curl_commands():
    """
    Generate curl commands for testing Polymarket API endpoints.
    """
    logger.info("Generating curl commands for testing Polymarket API endpoints")
    
    # Define endpoints to test
    endpoints = [
        "https://clob.polymarket.com/markets",
        "https://clob.polymarket.com/markets?active=true",
        "https://clob.polymarket.com/markets?limit=10"
    ]
    
    # Generate curl commands for each endpoint
    for endpoint in endpoints:
        curl_cmd = f'''curl -X GET \
  "{endpoint}" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" \
  -H "Accept: application/json"'''
        
        print("\n" + "-"*80)
        print(f"Curl command for {endpoint}:")
        print("-"*80)
        print(curl_cmd)

def main():
    """
    Main function to run the tests.
    """
    logger.info("Starting Polymarket API debug tests")
    
    # Test Polymarket CLOB API
    test_polymarket_clob_api()
    
    # Test Polygon blockchain endpoints
    test_polygon_blockchain_endpoints()
    
    # Generate curl commands
    generate_curl_commands()
    
    logger.info("Completed API debug tests")

if __name__ == "__main__":
    main()
