#!/usr/bin/env python3
"""
Direct Polymarket API Testing Script

This script directly tests the endpoints that are configured in our current application
using the PolymarketTransformer and related classes. It provides detailed error messages
and validation of the API responses.
"""

import os
import json
import logging
import requests
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("polymarket_direct_test")

# Import existing Polymarket transformer if available
try:
    from transform_polymarket_data_capitalized import PolymarketTransformer
    TRANSFORMER_AVAILABLE = True
    logger.info("Successfully imported PolymarketTransformer")
except ImportError:
    TRANSFORMER_AVAILABLE = False
    logger.warning("Could not import PolymarketTransformer, some functionality will be limited")

# Test configuration (based on our current setup)
CONFIG = {
    "endpoints": [
        "https://strapi-matic.poly.market/api",
        "https://polymarket.com/api",
        "https://app.polymarket.com/api",
        "https://gamma-api.poly.market/graphql"
    ],
    "paths": [
        "/markets?limit=10",
        "/markets/trending?limit=10",
        "/markets/featured?limit=10",
        "/v2/markets?limit=10"
    ],
    "graphql_query": """
    query GetMarkets {
        markets(first: 10, orderBy: volume, orderDirection: desc, where: { status: open }) {
            id
            question
            outcomes
            volume
            expiresAt
            categories
        }
    }
    """,
    "data_dir": "data"
}

def test_rest_endpoint(url: str) -> Dict[str, Any]:
    """
    Test a REST API endpoint.
    
    Args:
        url: Full URL to test
        
    Returns:
        Dict with test results
    """
    logger.info(f"Testing REST endpoint: {url}")
    result = {
        "url": url,
        "success": False,
        "status_code": None,
        "error": None,
        "data": None,
        "data_sample": None
    }
    
    try:
        # Add a user agent to avoid potential blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["success"] = True
                result["data"] = data
                
                # Create a truncated sample
                data_str = json.dumps(data, indent=2)
                result["data_sample"] = data_str[:500] + "..." if len(data_str) > 500 else data_str
                
                # Count markets if possible
                market_count = 0
                if isinstance(data, dict) and "markets" in data:
                    market_count = len(data["markets"])
                elif isinstance(data, list):
                    market_count = len(data)
                
                if market_count > 0:
                    logger.info(f"Found {market_count} markets in response")
                else:
                    logger.warning("No markets found in response")
                
            except json.JSONDecodeError:
                result["error"] = "Response was not valid JSON"
                logger.error("Response was not valid JSON")
        else:
            result["error"] = f"HTTP Error: {response.status_code}"
            logger.error(f"HTTP Error: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request error: {str(e)}"
        logger.error(f"Request error: {str(e)}")
        
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
    
    return result

def test_graphql_endpoint(url: str, query: str) -> Dict[str, Any]:
    """
    Test a GraphQL API endpoint.
    
    Args:
        url: GraphQL endpoint URL
        query: GraphQL query
        
    Returns:
        Dict with test results
    """
    logger.info(f"Testing GraphQL endpoint: {url}")
    result = {
        "url": url,
        "success": False,
        "status_code": None,
        "error": None,
        "data": None,
        "data_sample": None
    }
    
    try:
        # Add a user agent to avoid potential blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            url, 
            headers=headers,
            json={"query": query},
            timeout=10
        )
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            try:
                data = response.json()
                result["success"] = True
                result["data"] = data
                
                # Create a truncated sample
                data_str = json.dumps(data, indent=2)
                result["data_sample"] = data_str[:500] + "..." if len(data_str) > 500 else data_str
                
                # Count markets if possible
                market_count = 0
                if isinstance(data, dict) and "data" in data and "markets" in data["data"]:
                    market_count = len(data["data"]["markets"])
                
                if market_count > 0:
                    logger.info(f"Found {market_count} markets in GraphQL response")
                else:
                    logger.warning("No markets found in GraphQL response")
                
            except json.JSONDecodeError:
                result["error"] = "Response was not valid JSON"
                logger.error("Response was not valid JSON")
        else:
            result["error"] = f"HTTP Error: {response.status_code}"
            logger.error(f"HTTP Error: {response.status_code}")
    
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request error: {str(e)}"
        logger.error(f"Request error: {str(e)}")
        
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
    
    return result

def test_with_transformer() -> Dict[str, Any]:
    """
    Test fetching data using the PolymarketTransformer.
    
    Returns:
        Dict with test results
    """
    if not TRANSFORMER_AVAILABLE:
        return {
            "success": False,
            "error": "PolymarketTransformer not available"
        }
    
    logger.info("Testing with PolymarketTransformer")
    result = {
        "success": False,
        "error": None,
        "markets": None,
        "market_count": 0
    }
    
    try:
        transformer = PolymarketTransformer()
        markets = transformer.transform_markets()
        
        if markets and len(markets) > 0:
            result["success"] = True
            result["markets"] = markets
            result["market_count"] = len(markets)
            logger.info(f"Successfully transformed {len(markets)} markets")
        else:
            result["error"] = "No markets returned from transformer"
            logger.warning("No markets returned from transformer")
    
    except Exception as e:
        result["error"] = f"Transformer error: {str(e)}"
        logger.error(f"Transformer error: {str(e)}")
        logger.error(traceback.format_exc())
    
    return result

def main():
    """Run the direct Polymarket API tests"""
    logger.info("Starting Polymarket direct API tests")
    
    # Create data directory if it doesn't exist
    os.makedirs(CONFIG["data_dir"], exist_ok=True)
    
    # Test all REST endpoints
    rest_results = []
    for base_url in CONFIG["endpoints"]:
        if "graphql" in base_url:
            continue
            
        for path in CONFIG["paths"]:
            url = f"{base_url.rstrip('/')}{path}"
            result = test_rest_endpoint(url)
            rest_results.append(result)
    
    # Test GraphQL endpoint
    graphql_results = []
    for base_url in CONFIG["endpoints"]:
        if "graphql" in base_url:
            result = test_graphql_endpoint(base_url, CONFIG["graphql_query"])
            graphql_results.append(result)
    
    # Test with transformer if available
    transformer_result = None
    if TRANSFORMER_AVAILABLE:
        transformer_result = test_with_transformer()
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = os.path.join(CONFIG["data_dir"], f"polymarket_direct_test_{timestamp}.json")
    
    all_results = {
        "rest_results": rest_results,
        "graphql_results": graphql_results,
        "transformer_result": transformer_result,
        "timestamp": datetime.now().isoformat()
    }
    
    with open(result_file, "w") as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"Detailed results saved to {result_file}")
    
    # Print summary
    print("\n" + "="*80)
    print("POLYMARKET DIRECT API TEST SUMMARY")
    print("="*80)
    
    # REST Endpoints
    successful_rest = [r for r in rest_results if r["success"]]
    print(f"\nREST Endpoints: {len(successful_rest)}/{len(rest_results)} successful")
    
    if successful_rest:
        print("\nWorking REST Endpoints:")
        for i, result in enumerate(successful_rest, 1):
            print(f"  {i}. {result['url']}")
            
            # Try to determine if this endpoint has market data
            market_count = 0
            data = result["data"]
            
            if isinstance(data, dict) and "markets" in data and isinstance(data["markets"], list):
                market_count = len(data["markets"])
            elif isinstance(data, list):
                market_count = len(data)
                
            if market_count > 0:
                print(f"     Found {market_count} markets")
            else:
                print("     No markets found in response")
    else:
        print("\nNo working REST endpoints found.")
    
    # GraphQL Endpoints
    successful_graphql = [r for r in graphql_results if r["success"]]
    print(f"\nGraphQL Endpoints: {len(successful_graphql)}/{len(graphql_results)} successful")
    
    if successful_graphql:
        print("\nWorking GraphQL Endpoints:")
        for i, result in enumerate(successful_graphql, 1):
            print(f"  {i}. {result['url']}")
            
            # Try to determine if this endpoint has market data
            market_count = 0
            data = result["data"]
            
            if isinstance(data, dict) and "data" in data and "markets" in data["data"]:
                market_count = len(data["data"]["markets"])
                
            if market_count > 0:
                print(f"     Found {market_count} markets")
            else:
                print("     No markets found in response")
    else:
        print("\nNo working GraphQL endpoints found.")
    
    # Transformer
    if transformer_result:
        print("\nPolymarketTransformer test:")
        if transformer_result["success"]:
            print(f"  ✅ Successfully transformed {transformer_result['market_count']} markets")
        else:
            print(f"  ❌ Transformer failed: {transformer_result['error']}")
    
    # Conclusion
    print("\nCONCLUSION:")
    if successful_rest or successful_graphql or (transformer_result and transformer_result["success"]):
        print("✅ Found working Polymarket data sources.")
        
        if successful_rest or successful_graphql:
            print("✅ Direct API access is working.")
        else:
            print("❌ Direct API access is not working.")
            
        if transformer_result and transformer_result["success"]:
            print("✅ PolymarketTransformer is working.")
        elif transformer_result:
            print("❌ PolymarketTransformer is not working.")
    else:
        print("❌ No working Polymarket data sources found.")
        print("❌ Consider updating API endpoints or checking network connectivity.")
    
    print("="*80)
    
    # Return success if any endpoint worked
    return 0 if (successful_rest or successful_graphql or 
                (transformer_result and transformer_result["success"])) else 1

if __name__ == "__main__":
    import sys
    sys.exit(main())