#!/usr/bin/env python3
"""
Fetch markets from Polymarket Gamma API.

This script fetches markets directly from the Polymarket Gamma API,
processes them for active, non-expired markets, and stores them 
in the database for further pipeline processing.

IMPORTANT: This script NEVER uses sample or mock data. All data must 
come from the actual Polymarket API via the Gamma Markets endpoint.
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
from utils.batch_categorizer import batch_categorize_markets

# Import the main fetcher
from fetch_and_categorize_markets import (
    fetch_markets, 
    filter_active_non_expired_markets,
    filter_new_markets,
    store_categorized_markets,
    create_pipeline_run,
    update_pipeline_run
)

# Import the event market transformer to handle event grouping correctly
from utils.transform_market_with_events import transform_with_events

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
logger = logging.getLogger('fetch_gamma')

# IMPORTANT: This script MUST NEVER use fallback mechanisms or sample data.
# ALL data MUST come from the actual Polymarket API via the Gamma Markets endpoint:
# GET https://gamma-api.polymarket.com/markets
# 
# When the API is unreachable, the script should fail rather than use any fallback data.

def main():
    """
    Main function to fetch markets from Polymarket Gamma API.
    
    IMPORTANT: This script NEVER uses sample or mock data. All data must
    come from the actual Polymarket API via the Gamma Markets endpoint.
    """
    with app.app_context():
        try:
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Step 1: Fetch markets from API with retries for network issues
            try:
                # Make multiple attempts to fetch markets
                max_retries = 3
                retry_delay = 2  # seconds
                
                for attempt in range(1, max_retries + 1):
                    try:
                        logger.info(f"Attempt {attempt}/{max_retries} to fetch markets from API")
                        markets = fetch_markets(limit=50)
                        
                        if markets:
                            logger.info(f"Successfully fetched {len(markets)} markets on attempt {attempt}")
                            break
                        else:
                            logger.warning(f"No markets returned on attempt {attempt}")
                    except Exception as e:
                        logger.warning(f"Network error on attempt {attempt}: {str(e)}")
                        if attempt < max_retries:
                            import time
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            raise  # Re-raise the last exception if all retries failed
                else:
                    # This executes if the for loop completes without a break
                    markets = None
                    logger.error(f"Failed to fetch markets after {max_retries} attempts")
            except Exception as e:
                logger.error(f"Error fetching markets from API: {str(e)}")
                markets = None
            
            if not markets:
                logger.error("Failed to fetch markets from API")
                update_pipeline_run(pipeline_run, "failed", error="Failed to fetch markets from API")
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
            
            # Step 4: Categorize and store markets (using efficient batch categorization)
            logger.info(f"Batch categorizing {len(new_markets)} markets with GPT-4o-mini in a single API call...")
            categorized_markets = batch_categorize_markets(new_markets)
            
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
            
            # Store categorized markets - directly store markets we already categorized
            # to avoid redundant API calls in store_categorized_markets function
            stored_count = 0
            
            # Manually store each market to avoid redundant categorization
            from fetch_and_categorize_markets import transform_market_options
            
            for market_data in categorized_markets:
                try:
                    # Extract key data - handle string values as well as dict
                    if isinstance(market_data, dict):
                        market_id = market_data.get('conditionId') or market_data.get('id')
                        question = market_data.get('question', '')
                    else:
                        logger.error(f"Unexpected market_data type: {type(market_data)}")
                        continue
                        
                    # Skip if missing critical data
                    if not market_id or not question:
                        logger.error(f"Market missing ID or question: {market_data}")
                        continue
                    
                    # Skip if already in database (safety check)
                    if db.session.query(PendingMarket).filter_by(poly_id=market_id).count() > 0:
                        continue
                    
                    # Get category and manual review flag from categorization
                    category = market_data.get('ai_category', 'news')
                    needs_manual = market_data.get('needs_manual_categorization', True)
                    
                    # Transform market with proper event detection and option extraction
                    try:
                        # First transform the market with event detection
                        transformed_market = transform_with_events(market_data)
                        
                        # Extract options from the transformed market
                        options = transformed_market.get('options', [])
                        option_images = transformed_market.get('option_images', {})
                        
                        # Extract event information
                        event_id = transformed_market.get('event_id')
                        event_name = transformed_market.get('event_name')
                        
                        logger.info(f"Transformed market with event detection: event_id={event_id}, event_name={event_name}")
                    except Exception as e:
                        logger.error(f"Error transforming market with events: {str(e)}")
                        # Fall back to basic option transformation without events
                        try:
                            options, option_images = transform_market_options(market_data)
                            event_id = None
                            event_name = None
                        except Exception as inner_e:
                            logger.error(f"Error in fallback option transformation: {str(inner_e)}")
                            # Skip markets with invalid/unparseable options
                            logger.error(f"Skipping market with invalid options: {market_id}")
                            continue
                    
                    # Create pending market entry with event information
                    pending_market = PendingMarket(
                        poly_id=market_id,
                        question=question,
                        category=category,
                        banner_url=market_data.get('image'),
                        icon_url=market_data.get('icon'),
                        options=options,
                        option_images=option_images,
                        expiry=market_data.get('endDate'),
                        raw_data=market_data,
                        needs_manual_categorization=needs_manual,
                        posted=False,
                        event_id=event_id,
                        event_name=event_name
                    )
                    
                    # Add to database
                    db.session.add(pending_market)
                    
                    # Also add to processed_markets to prevent re-processing
                    processed_market = ProcessedMarket(
                        condition_id=market_id,
                        question=question,
                        category=category,
                        raw_data=market_data,
                        posted=False
                    )
                    
                    db.session.add(processed_market)
                    stored_count += 1
                    
                    logger.info(f"Stored market '{question[:50]}...' with category '{category}'")
                    
                except Exception as e:
                    market_id_display = market_id if isinstance(market_id, str) else "unknown"
                    logger.error(f"Error storing market {market_id_display}: {str(e)}")
                    logger.error(f"Error details: {type(e).__name__}")
                    db.session.rollback()
                    continue
                
            # Commit all changes
            db.session.commit()
            
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