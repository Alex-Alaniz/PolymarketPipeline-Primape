#!/usr/bin/env python3
"""
Fetch markets with fallback to sample data.

This script attempts to fetch markets from the Polymarket API,
but falls back to sample data if the API is unreachable.
This helps test the pipeline when the Polymarket API is unavailable.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Local imports
from models import db, PendingMarket, ProcessedMarket, PipelineRun
from utils.market_categorizer import categorize_markets

# Import the main fetcher
from fetch_and_categorize_markets import (
    fetch_markets, 
    filter_active_non_expired_markets,
    filter_new_markets,
    store_categorized_markets,
    create_pipeline_run,
    update_pipeline_run
)

# Initialize app
db.init_app(app)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("fetch_markets.log")
    ]
)
logger = logging.getLogger('fetch_fallback')

def load_sample_markets():
    """Load markets from sample_markets.json file and prepare them for processing"""
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
        
        # Prepare sample markets for processing by adding required fields
        current_timestamp = datetime.now().timestamp() * 1000  # Current time in milliseconds
        future_timestamp = current_timestamp + (90 * 24 * 60 * 60 * 1000)  # 90 days in the future
        
        enhanced_markets = []
        for i, market in enumerate(markets):
            # Create enhanced market with all required fields
            enhanced_market = market.copy()
            
            # Add required fields for filtering
            enhanced_market["id"] = market.get("id", f"sample-{i+1}")
            enhanced_market["conditionId"] = market.get("conditionId", f"sample-{i+1}")
            enhanced_market["active"] = True
            enhanced_market["closed"] = False
            enhanced_market["archived"] = False
            enhanced_market["endDate"] = str(int(future_timestamp))  # Future expiry
            enhanced_market["image"] = market.get("image", "https://example.com/sample-banner.jpg")
            enhanced_market["icon"] = market.get("icon", "https://example.com/sample-icon.jpg")
            
            # Add question if not present
            if "question" not in enhanced_market and "title" in enhanced_market:
                enhanced_market["question"] = enhanced_market["title"]
            elif "question" not in enhanced_market:
                enhanced_market["question"] = f"Sample Market Question {i+1}"
            
            # Add options if not present
            if "options" not in enhanced_market and "outcomes" not in enhanced_market:
                enhanced_market["options"] = [
                    {"id": "option-1", "value": "Yes", "image": "https://example.com/yes.jpg"},
                    {"id": "option-2", "value": "No", "image": "https://example.com/no.jpg"}
                ]
            
            enhanced_markets.append(enhanced_market)
        
        logger.info(f"Prepared {len(enhanced_markets)} enhanced sample markets")
        return enhanced_markets
    
    except Exception as e:
        logger.error(f"Error loading sample markets: {str(e)}")
        return []

def main():
    """
    Main function to fetch markets with fallback to sample data.
    """
    with app.app_context():
        try:
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Step 1: Attempt to fetch markets from API
            markets = fetch_markets(limit=50)
            
            if not markets:
                logger.warning("Failed to fetch markets from API, using sample data")
                markets = load_sample_markets()
                
                if not markets:
                    logger.error("Failed to load sample markets")
                    update_pipeline_run(pipeline_run, "failed", error="Failed to fetch markets or load samples")
                    return 1
            
            # Step 2: Filter markets
            filtered_markets = filter_active_non_expired_markets(markets)
            
            if not filtered_markets:
                logger.info("No active, non-expired markets found")
                update_pipeline_run(pipeline_run, "completed", markets_processed=len(markets))
                return 0
            
            # Step 3: Filter out markets already in the database
            new_markets = filter_new_markets(filtered_markets)
            
            if not new_markets:
                logger.info("No new markets to process")
                update_pipeline_run(pipeline_run, "completed", markets_processed=len(filtered_markets))
                return 0
            
            # Step 4: Categorize and store markets
            logger.info(f"Categorizing {len(new_markets)} markets with GPT-4o-mini...")
            categorized_markets = categorize_markets(new_markets)
            
            logger.info("Category distribution:")
            category_counts = {}
            for market in categorized_markets:
                category = market.get('ai_category', 'unknown')
                if category in category_counts:
                    category_counts[category] += 1
                else:
                    category_counts[category] = 1
            
            for category, count in category_counts.items():
                logger.info(f"  - {category}: {count} markets ({count/len(categorized_markets)*100:.1f}%)")
            
            # Store categorized markets
            stored_count = store_categorized_markets(categorized_markets)
            
            logger.info(f"Successfully categorized and stored {stored_count} markets")
            update_pipeline_run(
                pipeline_run, 
                "completed", 
                markets_processed=len(filtered_markets),
                markets_approved=stored_count
            )
            
            return 0
        
        except Exception as e:
            logger.error(f"Error in main function: {str(e)}")
            if 'pipeline_run' in locals():
                update_pipeline_run(pipeline_run, "failed", error=str(e))
            return 1

if __name__ == "__main__":
    sys.exit(main())