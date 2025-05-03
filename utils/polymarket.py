"""
Polymarket data extraction and processing utilities.
"""
import os
import sys
import subprocess
import json
from typing import List, Dict, Any, Optional

from config import DATA_DIR
from transform_polymarket_data_capitalized import PolymarketTransformer, main as transform_main

class PolymarketExtractor:
    """Extracts and processes Polymarket data."""
    
    def __init__(self):
        """Initialize the Polymarket extractor."""
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def extract_data(self) -> List[Dict[str, Any]]:
        """
        Run the transform_polymarket_data_capitalized.py script to extract data.
        
        Returns:
            List[Dict[str, Any]]: List of transformed market data
        """
        # Run the transformer script
        try:
            # Option 1: Import and run directly
            transform_result = transform_main()
            if transform_result != 0:
                print(f"Warning: Transform script returned non-zero exit code: {transform_result}")
            
            # Read the transformed data
            transformed_file = os.path.join(DATA_DIR, "transformed_markets.json")
            if not os.path.exists(transformed_file):
                print(f"Error: Transformed markets file not found at {transformed_file}")
                return []
            
            with open(transformed_file, 'r') as f:
                data = json.load(f)
            
            # Process markets
            markets = data.get("markets", [])
            processed_markets = []
            
            for market in markets:
                processed_market = self._process_market(market)
                if processed_market:
                    processed_markets.append(processed_market)
            
            return processed_markets
            
        except Exception as e:
            print(f"Error extracting Polymarket data: {str(e)}")
            return []
    
    def _process_market(self, market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process a market to ensure it has all required fields.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[Dict[str, Any]]: Processed market data, or None if invalid
        """
        # Validate required fields
        if not market.get("id") or not market.get("question") or not market.get("options"):
            return None
        
        # Ensure required fields are present
        processed_market = {
            "id": market.get("id"),
            "type": market.get("type", "binary"),
            "question": market.get("question"),
            "options": market.get("options", []),
            "category": market.get("category", "Other"),
            "sub_category": market.get("sub_category", "Other"),
            "expiry": market.get("expiry", None),
            "original_market_id": market.get("original_market_id", market.get("id"))
        }
        
        return processed_market