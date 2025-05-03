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
from config import POLYMARKET_BASE_URL, DATA_DIR

logger = logging.getLogger("polymarket_extractor")

class PolymarketExtractor:
    """Extracts market data from Polymarket"""
    
    def __init__(self):
        """Initialize the Polymarket extractor"""
        self.base_url = POLYMARKET_BASE_URL
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
            # First try to fetch real data from Polymarket API
            markets = self.fetch_polymarket_data()
            
            if markets:
                logger.info(f"Successfully fetched {len(markets)} markets from Polymarket API")
                
                # Transform the real data using our transformer
                transformer = PolymarketTransformer()
                transformed_markets = transformer.transform_markets_from_api(markets)
                
                if transformed_markets:
                    logger.info(f"Successfully transformed {len(transformed_markets)} markets from Polymarket")
                    return transformed_markets
                else:
                    logger.warning("No markets returned after transformation, trying backup data source")
            else:
                logger.warning("Failed to fetch data from Polymarket API, trying backup data source")
            
            # If API fetch fails or returns no markets, use the data transformer as backup
            logger.info("Using backup data source")
            transformer = PolymarketTransformer()
            
            # Load Polymarket data
            if not transformer.load_polymarket_data():
                logger.error("Failed to load backup Polymarket data")
                return []
                
            # Transform the data
            if not transformer.transform_markets():
                logger.error("Failed to transform backup Polymarket data")
                return []
            
            # Load the transformed data
            transformed_file = os.path.join(self.data_dir, "transformed_markets.json")
            with open(transformed_file, 'r') as f:
                transformed_data = json.load(f)
            
            return transformed_data.get("markets", [])
            
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
            logger.info(f"Fetching market data from {self.base_url}")
            
            # The API endpoint for active markets
            url = f"{self.base_url}/markets"
            
            # API parameters - different for each API endpoint
            # Try new API format first
            params = {
                "filters[status][$eq]": "open",  # Only get open markets
                "pagination[limit]": 50,         # Limit to 50 markets
                "sort[0]": "volume:desc",        # Sort by volume (most popular)
            }
            
            # Make the request
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                # The API format might be different than expected
                # Try different formats
                if "data" in data:
                    # New API format 
                    markets = data.get("data", [])
                else:
                    # Legacy API format
                    markets = data.get("markets", [])
                
                logger.info(f"Fetched {len(markets)} active markets from Polymarket API")
                
                # Save the raw data for reference
                raw_data_path = os.path.join(self.data_dir, "polymarket_raw_data.json")
                with open(raw_data_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                return markets
            else:
                logger.error(f"Failed to fetch markets from Polymarket API: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching Polymarket data: {str(e)}")
            return []

    def fetch_real_data(self) -> List[Dict[str, Any]]:
        """
        Fetch real market data from Polymarket API.
        This is a placeholder for when we switch to real data.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        try:
            # Placeholder for real API call
            # In a real implementation, this would call the Polymarket API
            logger.info(f"Fetching market data from {self.base_url}")
            
            # For now, return empty list as this is just a placeholder
            return []
            
        except Exception as e:
            logger.error(f"Error fetching Polymarket data: {str(e)}")
            return []