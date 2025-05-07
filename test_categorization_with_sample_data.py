#!/usr/bin/env python3
"""
Test Categorization with Sample Data

This script tests the market categorization function using
sample markets from the sample_markets.json file.
"""

import json
import logging
from datetime import datetime
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("categorization_test")

# Import categorizer
from utils.market_categorizer import categorize_market, categorize_markets, VALID_CATEGORIES

# Flask setup for database context if needed
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import models if needed
from models import db
db.init_app(app)

def load_sample_markets():
    """Load markets from sample_markets.json file"""
    try:
        logger.info("Loading sample markets from sample_markets.json...")
        with open("sample_markets.json", "r") as f:
            data = json.load(f)
        
        # Extract markets from the structure
        if isinstance(data, list):
            markets = data
        elif isinstance(data, dict) and "markets" in data:
            markets = data["markets"]
        elif isinstance(data, dict) and "items" in data:
            markets = data["items"]
        else:
            logger.warning("Unknown structure in sample_markets.json, trying to extract markets...")
            # Try to find a list of markets somewhere in the structure
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    markets = value
                    break
            else:
                raise ValueError("Could not find markets in sample_markets.json")
        
        logger.info(f"Loaded {len(markets)} sample markets")
        return markets
    
    except Exception as e:
        logger.error(f"Error loading sample markets: {str(e)}")
        return []

def test_categorization():
    """Test categorization of sample markets"""
    # Load sample markets
    markets = load_sample_markets()
    if not markets:
        logger.error("No sample markets to categorize")
        return 1
    
    # Prepare markets for categorization (extract questions)
    market_data = []
    for market in markets:
        if "question" in market:
            market_data.append({"question": market["question"]})
        elif "title" in market:
            market_data.append({"question": market["title"]})
    
    logger.info(f"Prepared {len(market_data)} markets for categorization")
    
    # Skip if no markets to categorize
    if not market_data:
        logger.error("No markets with questions/titles found")
        return 1
    
    # Categorize markets
    logger.info("Categorizing sample markets...")
    categorized_markets = categorize_markets(market_data)
    
    # Print categorization results
    logger.info("Categorization results:")
    categories_count = {}
    for market in categorized_markets:
        category = market["ai_category"]
        needs_manual = market["needs_manual_categorization"]
        
        # Count categories
        if category in categories_count:
            categories_count[category] += 1
        else:
            categories_count[category] = 1
        
        # Log categorization result
        logger.info(f"Question: {market['question'][:50]}...")
        logger.info(f"Category: {category}, Needs manual review: {needs_manual}")
        logger.info("-" * 40)
    
    # Log category distribution
    logger.info("Category distribution:")
    for category, count in categories_count.items():
        logger.info(f"  - {category}: {count} markets ({count / len(categorized_markets) * 100:.1f}%)")
    
    # Check if all markets were categorized
    if len(categorized_markets) != len(market_data):
        logger.warning(f"Not all markets were categorized: {len(categorized_markets)} of {len(market_data)}")
    
    # Success!
    logger.info("Categorization test completed successfully")
    return 0

def main():
    """Main function"""
    try:
        with app.app_context():
            return test_categorization()
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())