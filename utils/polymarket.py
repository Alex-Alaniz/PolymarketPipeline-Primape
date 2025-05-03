"""
Polymarket extractor for the Polymarket pipeline.
This module extracts market data from Polymarket for processing.
"""
import os
import json
import logging
from datetime import datetime, timedelta
import requests
from typing import List, Dict, Any

# Import from the project
from transform_polymarket_data_capitalized import PolymarketTransformer
from config import POLYMARKET_BASE_URL, POLYMARKET_API_ENDPOINTS, DATA_DIR

logger = logging.getLogger("polymarket_extractor")

class PolymarketExtractor:
    """Extracts market data from Polymarket"""
    
    def __init__(self):
        """Initialize the Polymarket extractor"""
        # Store all possible API endpoints to try
        self.api_endpoints = POLYMARKET_API_ENDPOINTS
        # Set the base URL to the primary one (for backward compatibility)
        self.base_url = POLYMARKET_BASE_URL or "https://polymarket.com/api"
        self.data_dir = DATA_DIR
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
    
    def extract_data(self) -> List[Dict[str, Any]]:
        """
        Extract market data from Polymarket.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        try:
            # First, try to fetch data from the Polymarket API
            logger.info("Attempting to fetch data from Polymarket API")
            
            api_markets = self.fetch_polymarket_data()
            
            # If we got data from the API, transform it and return
            if api_markets and len(api_markets) > 0:
                logger.info(f"Successfully fetched {len(api_markets)} markets from Polymarket API")
                
                # Transform the data using the API-specific method
                transformer = PolymarketTransformer()
                transformed_markets = transformer.transform_markets_from_api(api_markets)
                
                if transformed_markets and len(transformed_markets) > 0:
                    logger.info(f"Successfully transformed {len(transformed_markets)} markets from API data")
                    return transformed_markets
                else:
                    logger.warning("Failed to transform API data, falling back to backup data")
            else:
                logger.warning("Failed to fetch data from Polymarket API, falling back to backup data")
            
            # If API fetch failed or no data was returned, use backup data
            logger.info("Using backup data source for market data")
            transformer = PolymarketTransformer()
            
            # Load backup Polymarket data
            if not transformer.load_polymarket_data():
                logger.error("Failed to load backup Polymarket data")
                return []
                
            # Transform the backup data
            if not transformer.transform_markets():
                logger.error("Failed to transform backup Polymarket data")
                return []
            
            # Load the transformed backup data
            transformed_file = os.path.join(self.data_dir, "transformed_markets.json")
            with open(transformed_file, 'r') as f:
                transformed_data = json.load(f)
            
            # Log success with backup data
            markets = transformed_data.get("markets", [])
            logger.info(f"Successfully loaded {len(markets)} markets from backup data source")
            
            return markets
            
        except Exception as e:
            logger.error(f"Error extracting Polymarket data: {str(e)}")
            return []
    
    def fetch_polymarket_data(self) -> List[Dict[str, Any]]:
        """
        Fetch real market data from Polymarket API.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        try:
            logger.info("Starting Polymarket API fetch process with multiple endpoints")
            
            # Common API patterns to try for each base URL
            api_patterns = [
                # Primary endpoint (current version)
                {
                    "path": "/markets",
                    "params": {
                        "limit": 50,
                        "sortBy": "volume",
                        "sortDirection": "desc",
                        "status": "open"
                    }
                },
                # Alternative v2 endpoint
                {
                    "path": "/v2/markets",
                    "params": {
                        "limit": 50,
                        "sortBy": "volume",
                        "status": "active"
                    }
                },
                # Try GraphQL endpoint
                {
                    "path": "/graphql",
                    "method": "post",
                    "json": {
                        "query": """
                        query GetMarkets {
                            markets(first: 50, orderBy: volume, orderDirection: desc, where: { status: open }) {
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
                }
            ]
            
            # Try all base URLs and patterns until we get data
            markets = []
            
            # First try all combinations of base URLs and API patterns
            for base_url in self.api_endpoints:
                if not base_url:
                    continue
                    
                logger.info(f"Trying Polymarket API base URL: {base_url}")
                
                for pattern in api_patterns:
                    try:
                        # Construct the full URL
                        path = pattern["path"]
                        url = f"{base_url.rstrip('/')}{path}"
                        method = pattern.get("method", "get")
                        
                        logger.info(f"Trying API endpoint: {url} (method: {method})")
                        
                        # Make the request based on method
                        if method.lower() == "post":
                            response = requests.post(
                                url, 
                                **{k: v for k, v in pattern.items() if k not in ["path", "method"]}
                            )
                        else:
                            response = requests.get(url, params=pattern.get("params", {}))
                        
                        # Check response
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Try to extract markets based on different response formats
                            if "markets" in data:
                                markets = data["markets"]
                            elif "data" in data and "markets" in data["data"]:
                                markets = data["data"]["markets"]
                            elif "data" in data:
                                markets = data["data"]
                            
                            # If we found markets, break out of the loop
                            if markets and len(markets) > 0:
                                logger.info(f"Fetched {len(markets)} active markets from Polymarket API endpoint: {url}")
                                
                                # Save the raw data for reference
                                raw_data_path = os.path.join(self.data_dir, "polymarket_raw_data.json")
                                with open(raw_data_path, 'w') as f:
                                    json.dump(data, f, indent=2)
                                
                                # We found markets, so return immediately
                                return markets
                            else:
                                logger.warning(f"No markets found in response from endpoint: {url}")
                        else:
                            logger.warning(f"Failed to fetch from endpoint {url}: HTTP {response.status_code}")
                    
                    except Exception as endpoint_error:
                        logger.warning(f"Error with endpoint {base_url}{pattern['path']}: {str(endpoint_error)}")
                        continue
            
            # If we reach here, we didn't find any markets with any combination
            logger.warning("Failed to fetch markets from any Polymarket API endpoint")
            return []
                
        except Exception as e:
            logger.error(f"Error fetching Polymarket data: {str(e)}")
            return []

    def fetch_real_data(self) -> List[Dict[str, Any]]:
        """
        Fetch real market data from Polymarket API.
        This is a legacy method that now just calls fetch_polymarket_data.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        # Just call the main fetch method for consistency
        return self.fetch_polymarket_data()