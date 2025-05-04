"""
Polymarket extractor for the Polymarket pipeline.
This module extracts market data from Polymarket for processing.
"""
import os
import json
import logging
import re
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
                # Build URL with pagination - define outside try block to ensure it's always available
                current_url = url
                if next_cursor:
                    current_url += f"?next_cursor={next_cursor}"
                
                logger.info(f"Fetching page {page} from: {current_url}")
                
                try:
                    
                    # Make the request
                    response = requests.get(current_url, headers=headers, timeout=10)
                    
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
                            logger.warning(f"No 'data' field found in response from {current_url}")
                            break
                    else:
                        logger.warning(f"Failed to fetch from {current_url}: HTTP {response.status_code}")
                        break
                
                except Exception as page_error:
                    # Use a simple error message without relying on current_url
                    logger.error(f"Error fetching page {page} from Polymarket API: {str(page_error)}")
                    break
            
            # Return all markets collected, but filter out any that are expired or closed
            if all_markets:
                # Apply additional filtering to ensure only current/open markets
                filtered_markets = []
                current_time = datetime.now()
                
                for market in all_markets:
                    try:
                        # First, explicitly check for 'active' flag - this is the correct field to determine live markets
                        if "active" in market and market["active"] is False:
                            logger.info(f"Filtering out market {market.get('condition_id')} - not active (active: False)")
                            continue
                        
                        # Also check closed or archived flags as a fallback
                        if market.get("closed", False) or market.get("archived", False):
                            logger.info(f"Filtering out market {market.get('condition_id')} - closed or archived")
                            continue
                            
                        # If the market has a 'state' field, check if it's not "open" or "active"
                        if "state" in market and market["state"] not in ["open", "active", "live"]:
                            logger.info(f"Filtering out market {market.get('condition_id')} - state is {market['state']}")
                            continue
                            
                        # If the market has a 'status' field, check if it's not "open" or "active"
                        if "status" in market and market["status"] not in ["open", "active", "live"]:
                            logger.info(f"Filtering out market {market.get('condition_id')} - status is {market['status']}")
                            continue
                            
                        # Check expiry dates from various fields
                        is_expired = False
                        
                        # Check end_date_iso if available
                        if "end_date_iso" in market and market["end_date_iso"]:
                            try:
                                end_date = datetime.fromisoformat(market["end_date_iso"].replace("Z", "+00:00"))
                                if end_date < current_time:
                                    logger.info(f"Filtering out market {market.get('condition_id')} - already ended (ISO date: {end_date})")
                                    is_expired = True
                            except Exception as e:
                                logger.warning(f"Could not parse end_date_iso for market {market.get('condition_id')}: {e}")
                        
                        # Also check question text for past dates
                        if not is_expired and "question" in market:
                            question = market["question"]
                            # Check for date references like "by March 31" or "by end of 2023"
                            past_date_patterns = [
                                r"by\s+([a-zA-Z]+\s+\d{1,2})",  # by March 31
                                r"before\s+([a-zA-Z]+\s+\d{1,2})",  # before March 31
                                r"prior\s+to\s+([a-zA-Z]+\s+\d{1,2})"  # prior to March 31
                            ]
                            
                            for pattern in past_date_patterns:
                                match = re.search(pattern, question, re.IGNORECASE)
                                if match:
                                    date_text = match.group(1)
                                    try:
                                        # For month day format, add current year
                                        current_year = current_time.year
                                        date_text = f"{date_text}, {current_year}"
                                        
                                        # Check if it's a valid date
                                        import dateutil.parser
                                        parsed_date = dateutil.parser.parse(date_text)
                                        
                                        # If the date is in the past, filter out the market
                                        if parsed_date < current_time:
                                            logger.info(f"Filtering out market {market.get('condition_id')} - contains past date in question: {date_text}")
                                            is_expired = True
                                            break
                                    except Exception as e:
                                        logger.warning(f"Could not parse date from question for market {market.get('condition_id')}: {e}")
                        
                        # Add to filtered markets if not expired
                        if not is_expired:
                            filtered_markets.append(market)
                    except Exception as e:
                        logger.error(f"Error filtering market {market.get('condition_id')}: {e}")
                
                logger.info(f"Successfully fetched a total of {len(all_markets)} markets from Polymarket CLOB API")
                logger.info(f"After filtering expired/closed markets: {len(filtered_markets)} markets remain")
                return filtered_markets
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