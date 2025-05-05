#!/usr/bin/env python3

"""
Optimized Market Fetcher for Polymarket API

This script demonstrates an advanced approach for fetching only truly active, 
non-expired markets from the Polymarket API by combining API parameters
with sophisticated post-processing filters.

It generates a curl command you can use in Postman to verify the results.
"""

import requests
import json
import logging
import sys
import re
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("optimized_fetcher")

def fetch_markets(limit: int = 500) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API using basic filtering parameters.
    
    Args:
        limit: Maximum number of markets to fetch
        
    Returns:
        List of market data dictionaries
    """
    # Endpoint with basic filtering parameters
    url = f"https://clob.polymarket.com/markets?accepting_orders=true&active=true&limit={limit}"
    
    logger.info(f"Fetching markets from: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if "data" in data and isinstance(data["data"], list):
                markets = data["data"]
                logger.info(f"Fetched {len(markets)} markets from API")
                return markets
            else:
                logger.error("No 'data' field in response")
        else:
            logger.error(f"Failed to fetch markets: HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
    
    return []

def filter_future_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply advanced filtering to get only truly future markets.
    
    This function uses multiple filtering techniques:
    1. Date-based filtering using end_date_iso
    2. Text analysis to identify future vs past events
    3. Year extraction from question text
    4. Score-based prioritization for most likely active markets
    
    Args:
        markets: List of raw market data dictionaries
        
    Returns:
        List of filtered, truly active market data dictionaries
    """
    now = datetime.now(timezone.utc)
    current_year = now.year
    
    # Regular expressions for finding years in text
    year_pattern = re.compile(r'\b(202[0-9])\b')  # Match years 2020-2029
    
    # Words that suggest past events
    past_indicators = ["was", "were", "ended", "finished", "concluded", "completed"]
    
    # Words that suggest future events
    future_indicators = ["will", "shall", "going to", "upcoming", "future", "next"]
    
    # Initialize list for filtered markets with scoring
    scored_markets = []
    
    for market in markets:
        # Start with a base score
        score = 0
        
        # Get the question and convert to lowercase for text analysis
        question = market.get("question", "").lower()
        desc = market.get("description", "").lower()
        
        # Skip markets without a question
        if not question:
            continue
        
        # Check end date if available
        end_date_iso = market.get("end_date_iso")
        has_future_end_date = False
        
        if end_date_iso:
            try:
                end_date = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                
                # Check if the end date is in the future
                if end_date > now:
                    has_future_end_date = True
                    days_in_future = (end_date - now).days
                    
                    # Higher score for markets ending soon (but not too soon)
                    if days_in_future < 30:
                        score += 5  # Near-term markets are more relevant
                    else:
                        score += 2
                else:
                    # Expired market, heavy penalty
                    score -= 20
            except Exception as e:
                logger.debug(f"Error parsing end_date_iso: {e}")
        
        # Find years mentioned in the question
        years_mentioned = year_pattern.findall(question)
        years_mentioned.extend(year_pattern.findall(desc))
        
        # Check for future years
        has_future_year = False
        for year_str in years_mentioned:
            try:
                year = int(year_str)
                if year >= current_year:
                    has_future_year = True
                    score += 3  # Bonus for mentioning future years
                else:
                    score -= 1  # Small penalty for past years
            except ValueError:
                pass
        
        # Check for past/future indicator words
        past_word_count = sum(1 for word in past_indicators if word in question)
        future_word_count = sum(1 for word in future_indicators if word in question)
        
        score -= past_word_count * 2  # Penalty for past-tense indicators
        score += future_word_count * 2  # Bonus for future-tense indicators
        
        # Accepting orders is a strong positive signal
        if market.get("accepting_orders", False):
            score += 10
        
        # Add a composite field for our filtering decision
        market_with_score = {
            "market": market,
            "score": score,
            "has_future_end_date": has_future_end_date,
            "has_future_year": has_future_year,
            "future_indicators": future_word_count,
            "past_indicators": past_word_count
        }
        
        scored_markets.append(market_with_score)
    
    # Sort markets by score (descending)
    scored_markets.sort(key=lambda x: x["score"], reverse=True)
    
    # Filter out markets with very negative scores as they're almost certainly expired
    future_markets = [m["market"] for m in scored_markets if m["score"] > -5]
    
    # Limit to top N markets
    top_markets = future_markets[:50]  # Adjust this number as needed
    
    logger.info(f"Filtered {len(markets)} markets to {len(future_markets)} possible future markets")
    logger.info(f"Selected top {len(top_markets)} markets by relevance score")
    
    # Print some examples of the top markets
    if top_markets:
        logger.info("\nTop 5 markets by relevance score:")
        for i, market in enumerate(top_markets[:5]):
            logger.info(f"{i+1}. {market.get('question')}")
            logger.info(f"   - Condition ID: {market.get('condition_id')}")
            logger.info(f"   - End date: {market.get('end_date_iso')}")
    
    return top_markets

def generate_curl_commands(markets: List[Dict[str, Any]]):
    """
    Generate curl commands for the filtered markets.
    """
    if not markets:
        logger.warning("No markets to generate curl commands for.")
        return
    
    # Extract market IDs
    market_ids = [m.get("condition_id") for m in markets if m.get("condition_id")]
    
    if not market_ids:
        logger.warning("No valid market IDs found.")
        return
    
    logger.info("\n\nCURL COMMAND FOR FUTURE MARKETS:")
    logger.info("=================================")
    
    # Generate curl command for a specific market by ID
    if market_ids:
        example_id = market_ids[0]
        logger.info(f"\nCurl command for a specific market (ID: {example_id}):")
        logger.info("-" * 80)
        logger.info(f'''curl -X GET \
  "https://clob.polymarket.com/markets/{example_id}" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" \
  -H "Accept: application/json"''')

def save_market_data(markets: List[Dict[str, Any]], filename: str = "future_markets.json"):
    """
    Save filtered market data to a JSON file.
    
    Args:
        markets: List of market data dictionaries
        filename: Name of the file to save to
    """
    if not markets:
        logger.warning("No markets to save.")
        return
    
    try:
        with open(filename, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "count": len(markets),
                "markets": markets
            }, f, indent=2)
        
        logger.info(f"\nSaved {len(markets)} markets to {filename}")
    except Exception as e:
        logger.error(f"Error saving markets to file: {str(e)}")

def main():
    """
    Main function to run the optimized market fetcher.
    """
    logger.info("Starting optimized market fetcher")
    
    # Fetch markets with basic filtering
    markets = fetch_markets(limit=500)
    
    # Apply advanced filtering to get future markets
    future_markets = filter_future_markets(markets)
    
    # Generate curl commands for testing
    generate_curl_commands(future_markets)
    
    # Save filtered markets to file
    save_market_data(future_markets, "data/future_markets.json")
    
    # Final recommendations
    logger.info("\n\nRECOMMENDATIONS FOR INTEGRATION:")
    logger.info("===============================")
    logger.info("1. Use the base API parameters: 'accepting_orders=true&active=true'")
    logger.info("2. Implement the sophisticated post-processing filters from this script:")
    logger.info("   - Date-based filtering for future end dates")
    logger.info("   - Text analysis for future vs past event indicators")
    logger.info("   - Scoring system to prioritize most relevant markets")
    logger.info("3. Maintain a list of known expired markets to avoid reprocessing them")
    logger.info("\nCompleted optimized market fetcher")

if __name__ == "__main__":
    main()
