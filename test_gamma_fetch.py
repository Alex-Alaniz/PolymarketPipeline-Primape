#!/usr/bin/env python3
"""
Test Gamma API Fetch with Limited Markets

This script tests the Gamma API fetch with a smaller limit
to make testing faster and more manageable.
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fetch_test.log")
    ]
)
logger = logging.getLogger('test_gamma')

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Local imports
from models import db, Market, PendingMarket, ProcessedMarket, PipelineRun
from utils.batch_categorizer import batch_categorize_markets

# Initialize app
db.init_app(app)

# Constants
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"

def fetch_limited_markets(limit: int = 10):
    """
    Fetch a limited number of markets from Gamma API
    
    Args:
        limit: Maximum number of markets to fetch
    
    Returns:
        List of market data dictionaries
    """
    import requests
    
    params = {
        "closed": "false",
        "archived": "false",
        "active": "true",
        "limit": str(limit)
    }
    
    logger.info(f"Fetching {limit} markets from Gamma API")
    
    try:
        response = requests.get(GAMMA_API_URL, params=params)
        response.raise_for_status()
        
        markets = response.json()
        
        if not isinstance(markets, list):
            raise ValueError(f"Expected list response, got {type(markets)}")
            
        logger.info(f"Successfully fetched {len(markets)} markets")
        
        # Save the raw response for inspection
        with open("test_gamma_response.json", "w") as f:
            json.dump(markets, f, indent=2)
            
        return markets
    
    except Exception as e:
        logger.error(f"Error fetching markets: {str(e)}")
        raise

def test_filter_expired_markets(markets: List[Dict[str, Any]]):
    """
    Test filtering of expired markets
    
    Args:
        markets: List of market data dictionaries
    
    Returns:
        Filtered list of markets
    """
    # Get current time with timezone info
    now = datetime.now(timezone.utc)
    
    # Track filtered markets
    filtered_markets = []
    expired_count = 0
    invalid_date_count = 0
    
    for market in markets:
        end_date_str = market.get("endDate")
        
        if end_date_str:
            try:
                # Parse ISO format date
                from dateutil import parser
                end_date = parser.parse(end_date_str)
                
                # Ensure timezone info
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                
                # Check if expired
                if end_date < now:
                    logger.info(f"Market expired: {market.get('question', '')[:30]}... (End: {end_date_str})")
                    expired_count += 1
                    continue
                else:
                    # Not expired
                    time_left = end_date - now
                    logger.info(f"Market active: {market.get('question', '')[:30]}... (Time left: {time_left.days} days)")
            except Exception as e:
                logger.warning(f"Invalid end date '{end_date_str}': {str(e)}")
                invalid_date_count += 1
        
        # Check required fields
        if not market.get('question'):
            logger.warning(f"Market missing question: {market.get('conditionId')}")
            continue
            
        if not market.get('image') or not market.get('icon'):
            logger.warning(f"Market missing image/icon: {market.get('conditionId')}")
            continue
            
        # Add to filtered list
        filtered_markets.append(market)
    
    logger.info(f"Filtering results: {len(filtered_markets)} valid, {expired_count} expired, {invalid_date_count} invalid dates")
    return filtered_markets

def test_market_options(markets: List[Dict[str, Any]]):
    """
    Test extracting market options
    
    Args:
        markets: List of market data dictionaries
    """
    for i, market in enumerate(markets[:5]):  # Test first 5 markets
        question = market.get('question', '')
        logger.info(f"Market {i+1}: {question[:50]}...")
        
        # Check outcomes/options - they are stored as a JSON string
        outcomes_str = market.get('outcomes', '[]')
        
        try:
            # Parse the JSON string to get the actual outcomes
            if isinstance(outcomes_str, str):
                outcomes = json.loads(outcomes_str)
            else:
                outcomes = outcomes_str
                
            logger.info(f"  Outcomes: {len(outcomes)}")
            
            if isinstance(outcomes, list):
                for j, outcome in enumerate(outcomes):
                    # In this format, outcomes are simple strings
                    logger.info(f"    Outcome {j+1}: {outcome}")
            else:
                logger.warning(f"  Unexpected outcomes format: {type(outcomes)}")
                
        except Exception as e:
            logger.error(f"  Error parsing outcomes: {str(e)}")
            logger.error(f"  Raw outcomes data: {outcomes_str}")

def test_batch_categorization(markets: List[Dict[str, Any]]):
    """
    Test batch categorization of markets
    
    Args:
        markets: List of market data dictionaries
    """
    # Prepare markets for batch categorization
    batch_markets = []
    
    for i, market in enumerate(markets):
        question = market.get('question', '')
        if not question:
            continue
            
        # Create simplified market object
        batch_markets.append({
            'id': i,
            'question': question,
            'description': market.get('description', '')
        })
    
    logger.info(f"Testing batch categorization for {len(batch_markets)} markets")
    
    # Only process 5 markets for quicker testing
    test_batch = batch_markets[:5]
    
    try:
        # Perform batch categorization
        categorized = batch_categorize_markets(test_batch)
        
        # Log results
        for market in categorized:
            market_id = market.get('id')
            category = market.get('ai_category', 'unknown')
            original_question = next((m['question'] for m in test_batch if m['id'] == market_id), '')
            
            logger.info(f"Market {market_id}: '{original_question[:30]}...' -> {category}")
            
        # Count categories
        categories = {}
        for market in categorized:
            cat = market.get('ai_category', 'unknown')
            categories[cat] = categories.get(cat, 0) + 1
        
        logger.info("Category distribution:")
        for cat, count in categories.items():
            logger.info(f"  {cat}: {count}")
            
    except Exception as e:
        logger.error(f"Error in batch categorization: {str(e)}")

def main():
    """Main function to test Gamma API fetch"""
    with app.app_context():
        try:
            # Step 1: Fetch limited markets
            markets = fetch_limited_markets(limit=10)
            
            # Step 2: Test filtering expired markets
            filtered_markets = test_filter_expired_markets(markets)
            
            # Step 3: Test market options
            test_market_options(filtered_markets)
            
            # Step 4: Test batch categorization
            test_batch_categorization(filtered_markets)
            
            logger.info("Test completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())