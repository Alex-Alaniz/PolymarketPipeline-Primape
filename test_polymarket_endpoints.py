#!/usr/bin/env python3
"""
Polymarket API Endpoint Validation Script

This script tests various possible Polymarket API endpoints to:
1. Validate which endpoints are currently working
2. Extract and analyze the data schema from working endpoints
3. Output detailed information about market data structure

This is a critical test to ensure our pipeline can fetch real Polymarket data.
"""

import os
import sys
import json
import logging
from datetime import datetime
import requests
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("polymarket_api_test")

# List of potential Polymarket endpoints to test
ENDPOINTS = [
    # Main website endpoints
    {
        "name": "Polymarket Main API",
        "base_url": "https://polymarket.com/api",
        "paths": [
            "/markets",
            "/v2/markets", 
            "/markets/featured",
            "/markets/trending"
        ],
        "params": {"limit": 10}
    },
    # Strapi endpoints
    {
        "name": "Polymarket Strapi API",
        "base_url": "https://strapi-matic.poly.market/api",
        "paths": [
            "/markets",
            "/markets/trending",
            "/markets/featured"
        ],
        "params": {"limit": 10}
    },
    # CLOB API endpoints
    {
        "name": "Polymarket CLOB API",
        "base_url": "https://clob.polymarket.com/api",
        "paths": [
            "/market-data",
            "/markets",
            "/markets/info"
        ],
        "params": {"limit": 10}
    },
    # GraphQL endpoints
    {
        "name": "Polymarket GraphQL API",
        "base_url": "https://gamma-api.poly.market/graphql",
        "paths": ["/"],
        "method": "post",
        "json": {
            "query": """
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
            """
        }
    },
    # Alternative CTAPI endpoints
    {
        "name": "Polymarket CTAPI",
        "base_url": "https://ctapi.polymarket.com",
        "paths": [
            "/v1/markets",
            "/markets",
            "/markets/trending"
        ],
        "params": {"limit": 10}
    }
]

def test_endpoint(endpoint_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test a specific endpoint configuration.
    
    Args:
        endpoint_config: Configuration for the endpoint to test
        
    Returns:
        Dict containing test results
    """
    base_url = endpoint_config["base_url"]
    name = endpoint_config["name"]
    paths = endpoint_config["paths"]
    method = endpoint_config.get("method", "get")
    
    logger.info(f"Testing {name} at {base_url}")
    
    results = {
        "name": name,
        "base_url": base_url,
        "working_paths": [],
        "samples": {},
        "schema": {}
    }
    
    for path in paths:
        url = f"{base_url.rstrip('/')}{path}"
        logger.info(f"Trying {url}")
        
        try:
            if method.lower() == "post":
                json_data = endpoint_config.get("json", {})
                response = requests.post(url, json=json_data, timeout=10)
            else:
                params = endpoint_config.get("params", {})
                response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Success! Status code: {response.status_code}")
                
                try:
                    data = response.json()
                    # Store success
                    results["working_paths"].append(path)
                    
                    # Store a sample of the response
                    sample_text = json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data)) > 500 else json.dumps(data, indent=2)
                    results["samples"][path] = sample_text
                    
                    # Extract schema information
                    schema_info = extract_schema(data)
                    results["schema"][path] = schema_info
                    
                    logger.info(f"Successfully parsed JSON response for {url}")
                except Exception as json_error:
                    logger.error(f"Failed to parse JSON from {url}: {str(json_error)}")
            else:
                logger.warning(f"Failed with status code: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error testing {url}: {str(e)}")
    
    return results

def extract_schema(data: Any) -> Dict[str, Any]:
    """
    Extract schema information from API response data.
    
    Args:
        data: JSON response data
        
    Returns:
        Dict containing schema information
    """
    schema = {
        "type": type(data).__name__,
        "structure": {}
    }
    
    # For dictionaries, extract keys and their types
    if isinstance(data, dict):
        for key, value in data.items():
            if key == "data" and isinstance(value, (dict, list)):
                # Special handling for common GraphQL or REST wrapper
                schema["structure"] = extract_schema(value)
            else:
                schema["structure"][key] = type(value).__name__
                
                # If this is a container type, go one level deeper
                if isinstance(value, (dict, list)) and value:
                    if isinstance(value, dict):
                        schema["structure"][key] = extract_schema(value)
                    elif isinstance(value, list) and len(value) > 0:
                        schema["structure"][key] = {
                            "type": "list",
                            "items": extract_schema(value[0]) if isinstance(value[0], (dict, list)) else type(value[0]).__name__
                        }
    
    # For lists, extract type information from the first item
    elif isinstance(data, list) and data:
        schema["type"] = "list"
        first_item = data[0]
        if isinstance(first_item, (dict, list)):
            schema["items"] = extract_schema(first_item)
        else:
            schema["items"] = type(first_item).__name__
    
    return schema

def analyze_market_data(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze test results to find working endpoints with market data.
    
    Args:
        results: List of test results
        
    Returns:
        Dict with analysis results
    """
    analysis = {
        "working_endpoints": 0,
        "market_endpoints": 0,
        "recommended_endpoints": [],
        "market_fields": set()
    }
    
    for result in results:
        if result["working_paths"]:
            analysis["working_endpoints"] += 1
            
            # Check if any endpoints seem to contain market data
            for path, schema in result["schema"].items():
                market_indicators = ["market", "question", "outcomes", "volume", "probability"]
                
                # Look for market-related fields in the response
                has_market_data = False
                
                def check_for_market_fields(schema_part, prefix=""):
                    nonlocal has_market_data
                    if isinstance(schema_part, dict):
                        for key, value in schema_part.items():
                            if isinstance(value, dict) and "structure" in value:
                                for field in value["structure"].keys():
                                    if any(indicator in field.lower() for indicator in market_indicators):
                                        has_market_data = True
                                        analysis["market_fields"].add(f"{prefix}{field}")
                                check_for_market_fields(value["structure"], f"{prefix}{key}.")
                            elif key == "items" and isinstance(value, dict):
                                check_for_market_fields(value, prefix)
                
                check_for_market_fields(schema)
                
                if has_market_data:
                    analysis["market_endpoints"] += 1
                    endpoint_info = {
                        "name": result["name"],
                        "url": f"{result['base_url']}{path}",
                        "fields": list(analysis["market_fields"])
                    }
                    analysis["recommended_endpoints"].append(endpoint_info)
    
    analysis["market_fields"] = list(analysis["market_fields"])
    return analysis

def main():
    """Run the Polymarket API endpoint validation tests"""
    logger.info("Starting Polymarket API endpoint validation")
    
    results = []
    for endpoint in ENDPOINTS:
        result = test_endpoint(endpoint)
        results.append(result)
    
    # Write detailed results to file
    os.makedirs("data", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"data/polymarket_api_test_{timestamp}.json"
    
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Detailed results written to {results_file}")
    
    # Analyze results
    analysis = analyze_market_data(results)
    
    # Print summary
    print("\n" + "="*80)
    print("POLYMARKET API ENDPOINT VALIDATION SUMMARY")
    print("="*80)
    print(f"Total endpoints tested: {len(ENDPOINTS)}")
    print(f"Working endpoints found: {analysis['working_endpoints']}")
    print(f"Endpoints with market data: {analysis['market_endpoints']}")
    
    if analysis["recommended_endpoints"]:
        print("\nRECOMMENDED ENDPOINTS FOR MARKET DATA:")
        for i, endpoint in enumerate(analysis["recommended_endpoints"], 1):
            print(f"\n{i}. {endpoint['name']}")
            print(f"   URL: {endpoint['url']}")
            print(f"   Fields: {', '.join(endpoint['fields'][:5])}{'...' if len(endpoint['fields']) > 5 else ''}")
    else:
        print("\nWARNING: No working endpoints with market data were found.")
        print("The Polymarket API endpoints may have changed or may be temporarily unavailable.")
    
    print("\nCONCLUSION:")
    if analysis["recommended_endpoints"]:
        print("✅ Polymarket API endpoints are operational and can be used for market data extraction.")
        print(f"✅ Found {len(analysis['recommended_endpoints'])} usable endpoints for market data.")
    else:
        print("❌ No usable Polymarket API endpoints were found.")
        print("❌ Consider exploring alternative data sources or checking for API changes.")
    
    print("="*80)
    
    return 0 if analysis["recommended_endpoints"] else 1

if __name__ == "__main__":
    sys.exit(main())