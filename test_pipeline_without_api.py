#!/usr/bin/env python3
"""
Test Pipeline Without API

This script tests the pipeline without requiring API access.
It uses sample market data from sample_markets.json and validates 
that the categorization is working correctly.
"""

import os
import json
import logging
from typing import Dict, List, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_pipeline")

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import necessary modules
from models import db, Market, PendingMarket, ProcessedMarket, PipelineRun
from utils.market_categorizer import categorize_markets, VALID_CATEGORIES

# Initialize app
db.init_app(app)

def load_sample_markets():
    """Load markets from sample_markets.json file"""
    try:
        logger.info("Loading sample markets from sample_markets.json...")
        with open("sample_markets.json", "r") as f:
            data = json.load(f)
        
        # Extract markets structure
        if isinstance(data, list):
            markets = data
        elif isinstance(data, dict) and "markets" in data:
            markets = data["markets"]
        elif isinstance(data, dict) and "items" in data:
            markets = data["items"]
        else:
            # Try to extract markets from unknown structure
            for key, value in data.items():
                if isinstance(value, list) and len(value) > 0:
                    markets = value
                    break
            else:
                raise ValueError("Could not find markets in sample_markets.json")
        
        # Add question and ID if needed
        for market in markets:
            if "question" not in market and "title" in market:
                market["question"] = market["title"]
            if "id" not in market:
                market["id"] = f"sample-{hash(market.get('question', ''))}"
        
        logger.info(f"Loaded {len(markets)} sample markets")
        return markets
    
    except Exception as e:
        logger.error(f"Error loading sample markets: {str(e)}")
        return []

def categorize_and_store(markets: List[Dict[str, Any]]):
    """Test categorization and store in database"""
    logger.info(f"Starting categorization and storage of {len(markets)} markets")
    
    # Track category distribution
    category_counts = {category: 0 for category in VALID_CATEGORIES}
    
    # Categorize all markets
    categorized = categorize_markets(markets)
    
    # Track results
    results = []
    
    for market in categorized:
        category = market.get("ai_category", "news")
        question = market.get("question", "")
        
        # Count category
        if category in category_counts:
            category_counts[category] += 1
        
        # Store result for logging
        results.append({
            "question": question,
            "category": category
        })
        
        # Add to pending_markets table for verification
        try:
            # Generate a unique ID for the test
            test_id = f"test-{int(datetime.now().timestamp())}-{hash(question) % 10000}"
            
            # Create a PendingMarket entry
            pending = PendingMarket(
                poly_id=test_id,
                question=question,
                category=category,
                expiry="1777777777000",  # Future date
                banner_url="https://example.com/test-banner.jpg",
                icon_url="https://example.com/test-icon.jpg",
                options=[{"id": "1", "value": "Yes"}, {"id": "2", "value": "No"}],
                option_images={},
                raw_data=market,
                needs_manual_categorization=False,
                posted=False
            )
            
            db.session.add(pending)
            logger.info(f"Added test market '{question[:30]}...' with category '{category}'")
            
        except Exception as e:
            logger.error(f"Error adding test market: {str(e)}")
    
    # Commit changes
    db.session.commit()
    
    # Log overall statistics
    logger.info("Categorization results:")
    for category, count in category_counts.items():
        logger.info(f"  - {category}: {count} markets ({count/len(markets)*100:.1f}%)")
    
    # Print detailed results
    logger.info("\nDetailed categorization results:")
    for r in results:
        logger.info(f"Question: {r['question'][:50]}...")
        logger.info(f"Category: {r['category']}")
        logger.info("-" * 40)
    
    return results

def main():
    """Main function to run pipeline test"""
    with app.app_context():
        try:
            # Load sample markets
            markets = load_sample_markets()
            if not markets:
                logger.error("No sample markets loaded")
                return 1
            
            # Process sample markets
            results = categorize_and_store(markets)
            
            logger.info(f"Successfully processed {len(results)} sample markets")
            return 0
            
        except Exception as e:
            logger.error(f"Error in main function: {str(e)}")
            return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())