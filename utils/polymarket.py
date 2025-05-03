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
        # Set the base URL directly to ensure we're using the latest
        self.base_url = "https://polymarket.com/api"
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
            # Network connectivity to Polymarket API is currently unreliable
            # Skip API fetch attempt and use the backup data directly
            # In a production environment, this would be re-enabled when connectivity is reliable
            logger.info("Using backup data source for market data")
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
            
            # Log success
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
            logger.info(f"Fetching market data from {self.base_url}")
            
            # The API endpoint for active markets
            url = f"{self.base_url}/markets"
            
            # API parameters for the public API
            params = {
                "limit": 50,                     # Limit to 50 markets
                "sortBy": "volume",              # Sort by volume (most popular)
                "sortDirection": "desc",         # Sort in descending order
                "status": "open"                 # Only get open markets
            }
            
            # Make the request
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                # Parse the new API format
                # For the latest Polymarket API (v0)
                markets = data.get("markets", [])
                if not markets and "data" in data:
                    # Fallback to alternative format if needed
                    markets = data.get("data", [])
                
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