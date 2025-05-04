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
from config import POLYMARKET_BASE, POLYMARKET_API, DATA_DIR
from utils.polymarket_blockchain import PolymarketBlockchainClient

logger = logging.getLogger("polymarket_extractor")

class PolymarketExtractor:
    """Extracts market data from Polymarket"""
    
    def __init__(self):
        """Initialize the Polymarket extractor"""
        # Store all possible API endpoints to try
        self.api_endpoints = POLYMARKET_API
        # Set the base URL to the primary one (for backward compatibility)
        self.base_url = POLYMARKET_BASE or "https://polymarket.com/api"
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
            # Approach 1: Try to fetch data from the HTTP API endpoints
            logger.info("Attempting to fetch data from Polymarket API endpoints")
            
            api_markets = self.fetch_polymarket_data()
            
            # If API data is available, transform and return it
            if api_markets and len(api_markets) > 0:
                logger.info(f"Successfully fetched {len(api_markets)} markets from Polymarket API")
                
                # Transform the data using the API-specific method
                transformer = PolymarketTransformer()
                transformed_markets = transformer.transform_markets_from_api(api_markets)
                
                if transformed_markets and len(transformed_markets) > 0:
                    logger.info(f"Successfully transformed {len(transformed_markets)} markets from API data")
                    return transformed_markets
                else:
                    logger.warning("Failed to transform API data, trying blockchain approach")
            else:
                logger.warning("Failed to fetch data from Polymarket API endpoints, trying blockchain approach")
            
            # Approach 2: Try to fetch data directly from the blockchain
            logger.info("Attempting to fetch data directly from Polymarket contracts on Polygon")
            
            # Initialize the blockchain client
            blockchain_client = PolymarketBlockchainClient()
            
            # Check if we can connect to the blockchain
            if not blockchain_client.is_connected():
                logger.error("Failed to connect to Polygon blockchain, cannot fetch market data")
                raise Exception("Cannot connect to any data source for Polymarket data")
            
            # Fetch markets from the blockchain
            blockchain_markets = blockchain_client.fetch_markets(limit=50)
            
            if blockchain_markets and len(blockchain_markets) > 0:
                logger.info(f"Successfully fetched {len(blockchain_markets)} markets from blockchain")
                
                # Transform the data using the API-specific method (same format)
                transformer = PolymarketTransformer()
                transformed_markets = transformer.transform_markets_from_api(blockchain_markets)
                
                if transformed_markets and len(transformed_markets) > 0:
                    logger.info(f"Successfully transformed {len(transformed_markets)} markets from blockchain data")
                    return transformed_markets
                else:
                    logger.error("Failed to transform blockchain data")
                    raise Exception("Cannot transform blockchain data")
            else:
                logger.error("Failed to fetch markets from blockchain")
                raise Exception("Cannot fetch data from any source")
            
        except Exception as e:
            logger.error(f"Error extracting Polymarket data: {str(e)}")
            raise Exception(f"Failed to fetch Polymarket data from any source: {str(e)}")
    
    def fetch_polymarket_data(self) -> List[Dict[str, Any]]:
        """
        Fetch real market data from Polymarket CLOB API.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        try:
            logger.info("Starting Polymarket CLOB API fetch process")
            
            # Use the dedicated CLOB API endpoint
            base_url = self.api_endpoints
            if isinstance(base_url, list):
                base_url = base_url[0] if len(base_url) > 0 else "https://clob.polymarket.com"
            elif not base_url:
                base_url = "https://clob.polymarket.com"
                
            logger.info(f"Using Polymarket CLOB API base URL: {base_url}")
            
            # Construct the full URL
            url = f"{base_url.rstrip('/')}/markets"
            
            # Set headers for the request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            # Initialize markets list and pagination
            all_markets = []
            next_cursor = ""
            page = 1
            max_pages = 2  # Limit to 2 pages (1000 markets) to avoid too much data
            
            # Fetch data with pagination
            while page <= max_pages:
                try:
                    # Build URL with pagination
                    paginated_url = url
                    if next_cursor:
                        paginated_url += f"?next_cursor={next_cursor}"
                    
                    logger.info(f"Fetching page {page} from: {paginated_url}")
                    
                    # Make the request
                    response = requests.get(paginated_url, headers=headers, timeout=10)
                    
                    # Check response
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract markets from the 'data' field
                        if "data" in data and isinstance(data["data"], list):
                            markets = data["data"]
                            all_markets.extend(markets)
                            logger.info(f"Fetched {len(markets)} markets from page {page}")
                            
                            # Save the raw data for reference (first page only)
                            if page == 1:
                                raw_data_path = os.path.join(self.data_dir, "polymarket_raw_data.json")
                                with open(raw_data_path, 'w') as f:
                                    json.dump(data, f, indent=2)
                            
                            # Check for next page
                            if "next_cursor" in data and data["next_cursor"] and data["next_cursor"] != "LTE=":
                                next_cursor = data["next_cursor"]
                                page += 1
                            else:
                                # No more pages
                                break
                        else:
                            logger.warning(f"No 'data' field found in response from {paginated_url}")
                            break
                    else:
                        logger.warning(f"Failed to fetch from {paginated_url}: HTTP {response.status_code}")
                        break
                
                except Exception as page_error:
                    logger.error(f"Error fetching page {page} from {paginated_url}: {str(page_error)}")
                    break
            
            # Return all markets collected
            if all_markets:
                logger.info(f"Successfully fetched a total of {len(all_markets)} markets from Polymarket CLOB API")
                return all_markets
            else:
                logger.warning("No markets fetched from Polymarket CLOB API")
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