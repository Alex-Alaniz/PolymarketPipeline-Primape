#!/usr/bin/env python3
"""
Fetch and categorize markets from Polymarket API.

This script fetches markets from the Polymarket API,
filters them for active and non-expired markets,
categorizes them using GPT-4o-mini, and stores them
in the database as pending markets.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
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
from models import db, Market, PendingMarket, ProcessedMarket, PipelineRun
from utils.market_categorizer import categorize_market
from utils.batch_categorizer import batch_categorize_markets

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
logger = logging.getLogger('fetch_markets')

# Constants
MARKET_API_URL = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100 "
MARKETS_QUERY = """
query FetchMarkets($first: Int!, $skip: Int!) {
  markets(
    first: $first
    skip: $skip
    orderDirection: desc
    orderBy: updatedAtBlock
    where: { active: true, archived: false, closed: false }
  ) {
    id
    conditionId
    question
    description
    type
    initialOdds
    title
    image
    icon
    category
    endDate
    tokenAddress
    virtualFloor
    tradingViewSymbol
    options {
      id
      value
      image
    }
    outcomes {
      id
      value
      image
    }
    active
    closed
    archived
  }
}
"""

def create_pipeline_run():
    """Create a new pipeline run record in the database."""
    pipeline_run = PipelineRun(
        start_time=datetime.utcnow(),
        status="running"
    )
    db.session.add(pipeline_run)
    db.session.commit()
    
    logger.info(f"Created pipeline run with ID {pipeline_run.id}")
    return pipeline_run

def update_pipeline_run(pipeline_run, status, markets_processed=0, markets_approved=0, 
                       markets_rejected=0, markets_failed=0, markets_deployed=0, error=None):
    """Update the pipeline run record with results."""
    pipeline_run.end_time = datetime.utcnow()
    pipeline_run.status = status
    pipeline_run.markets_processed = markets_processed
    pipeline_run.markets_approved = markets_approved
    pipeline_run.markets_rejected = markets_rejected
    pipeline_run.markets_failed = markets_failed
    pipeline_run.markets_deployed = markets_deployed
    pipeline_run.error = error
    
    db.session.commit()
    logger.info(f"Updated pipeline run {pipeline_run.id} with status {status}")

def fetch_markets(limit: int = 100, skip: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API.
    
    Args:
        limit: Maximum number of markets to fetch
        skip: Number of markets to skip (for pagination)
        
    Returns:
        List of market data dictionaries
    """
    try:
        # Define GraphQL query
        payload = {
            "query": MARKETS_QUERY,
            "variables": {
                "first": limit,
                "skip": skip
            }
        }
        
        # Make request to API
        response = requests.post(MARKET_API_URL, json=payload)
        response.raise_for_status()
        
        data = response.json()
        if "errors" in data:
            logger.error(f"GraphQL errors: {data['errors']}")
            return []
        
        markets = data.get('data', {}).get('markets', [])
        logger.info(f"Fetched {len(markets)} markets from Gamma API (skip={skip})")
        
        return markets
    
    except Exception as e:
        logger.error(f"Error fetching markets from API: {str(e)}")
        return []

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include active, non-expired ones with banner/icon URLs.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    now = datetime.now().timestamp() * 1000  # Current time in milliseconds
    
    filtered_markets = []
    for market in markets:
        # Skip if market is closed, archived, or inactive
        if market.get('closed') or market.get('archived') or not market.get('active', True):
            continue
        
        # Skip if market has already expired
        end_date = market.get('endDate')
        if end_date and int(end_date) < now:
            continue
        
        # Skip if market doesn't have image or icon URLs
        if not market.get('image') or not market.get('icon'):
            continue
        
        # Skip markets without options/outcomes
        options = market.get('options') or market.get('outcomes') or []
        if not options:
            continue
        
        # Add to filtered list
        filtered_markets.append(market)
    
    logger.info(f"Filtered down to {len(filtered_markets)} active, non-expired markets with banner/icon")
    
    return filtered_markets

def transform_market_options(market_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Transform market options and extract option images.
    
    Args:
        market_data: Raw market data from API
        
    Returns:
        Tuple of (options list, option_images dict)
    """
    # Get options from market data (either 'options' or 'outcomes')
    api_options = market_data.get('options') or market_data.get('outcomes') or []
    
    # Format options for our database
    options = []
    option_images = {}
    
    for opt in api_options:
        option_id = opt.get('id')
        value = opt.get('value')
        image_url = opt.get('image')
        
        options.append({
            'id': option_id,
            'value': value
        })
        
        if image_url:
            option_images[value] = image_url
    
    return options, option_images

def filter_new_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include those not already in the database.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: List of new markets
    """
    # Get IDs of markets already in the database
    existing_market_ids = set()
    
    # Check pending_markets
    pending_market_ids = db.session.query(PendingMarket.poly_id).all()
    existing_market_ids.update([m[0] for m in pending_market_ids])
    
    # Check markets
    market_ids = db.session.query(Market.original_market_id).all()
    existing_market_ids.update([m[0] for m in market_ids if m[0]])
    
    # Check processed_markets
    processed_ids = db.session.query(ProcessedMarket.condition_id).all()
    existing_market_ids.update([m[0] for m in processed_ids])
    
    # Filter out markets that are already in the database
    new_markets = [m for m in markets if m.get('conditionId') not in existing_market_ids and m.get('id') not in existing_market_ids]
    
    logger.info(f"Found {len(new_markets)} new markets not yet in the database")
    
    return new_markets

def store_categorized_markets(markets: List[Dict[str, Any]]) -> int:
    """
    Categorize and store markets in the database using batch processing.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        int: Number of markets stored
    """
    # Check if we have markets to process
    if not markets:
        logger.info("No markets to categorize")
        return 0
    
    # Prepare markets for batch categorization
    batch_ready_markets = []
    original_markets = {}  # Map to track original market data by batch ID
    
    for i, market in enumerate(markets):
        # Extract question from the market
        question = market.get('title', '') or market.get('question', '')
        
        # Skip markets without questions
        if not question:
            logger.warning(f"Skipping market with no question: {market.get('conditionId', 'unknown')}")
            continue
            
        # Create a simple object for categorization with just the fields needed
        market_obj = {
            'id': i,  # Use index as batch ID
            'question': question,
            'description': market.get('description', '')
        }
        batch_ready_markets.append(market_obj)
        
        # Store original market data for later use
        original_markets[i] = market
    
    # Batch categorize all markets in a single API call
    logger.info(f"Batch categorizing {len(batch_ready_markets)} markets with GPT-4o-mini in a single API call...")
    categorized_batch = batch_categorize_markets(batch_ready_markets)
    
    # Create a map of categorization results
    categorization_map = {}
    for market in categorized_batch:
        batch_id = market.get('id')
        if batch_id is not None:
            categorization_map[batch_id] = market
    
    # Log category distribution
    category_counts = {}
    for market in categorized_batch:
        category = market.get('ai_category', 'news')
        if category in category_counts:
            category_counts[category] += 1
        else:
            category_counts[category] = 1
    
    logger.info("Category distribution:")
    for category, count in category_counts.items():
        percentage = count / len(categorized_batch) * 100
        logger.info(f"  - {category}: {count} markets ({percentage:.1f}%)")
    
    # Store markets with their categories
    stored_count = 0
    
    for batch_id, original_market in original_markets.items():
        try:
            # Extract Polymarket ID and question
            market_id = original_market.get('conditionId') or original_market.get('id')
            question = original_market.get('title') or original_market.get('question', '')
            
            # Skip if already in database (safety check)
            if db.session.query(PendingMarket).filter_by(poly_id=market_id).count() > 0:
                logger.info(f"Market {market_id} already exists in database, skipping")
                continue
            
            # Get category from batch categorization results
            if batch_id in categorization_map:
                batch_result = categorization_map[batch_id]
                category = batch_result.get('ai_category', 'news')
                needs_manual = batch_result.get('needs_manual_categorization', True)
                logger.info(f"Using batch categorization for market {batch_id}: {category}")
            else:
                # Fallback to keyword-based categorization if not found in batch results
                from utils.batch_categorizer import keyword_based_categorization
                category = keyword_based_categorization(question)
                needs_manual = True
                logger.warning(f"Market {batch_id} not found in batch results, using keyword fallback: {category}")
            
            # Process outcome options with error handling
            try:
                options, option_images = transform_market_options(original_market)
            except Exception as e:
                logger.warning(f"Error transforming options for market {market_id}: {str(e)}")
                # Create fallback options for binary markets
                options = [
                    {"value": "Yes", "displayName": "Yes"},
                    {"value": "No", "displayName": "No"}
                ]
                option_images = {"Yes": None, "No": None}
            
            # Create pending market entry
            pending_market = PendingMarket(
                poly_id=market_id,
                question=question,
                category=category,
                banner_url=original_market.get('image'),
                icon_url=original_market.get('icon'),
                options=options,
                option_images=option_images,
                expiry=original_market.get('endDate'),
                raw_data=original_market,
                needs_manual_categorization=needs_manual,
                posted=False
            )
            
            # Add to database
            db.session.add(pending_market)
            
            # Also add to processed_markets to prevent re-processing
            processed_market = ProcessedMarket(
                condition_id=market_id,
                question=question,
                category=category,
                raw_data=original_market,
                posted=False
            )
            
            db.session.add(processed_market)
            stored_count += 1
            
            logger.info(f"Stored market '{question[:50]}...' with category '{category}'")
            
        except Exception as e:
            market_id_display = market_id if 'market_id' in locals() else f"batch_id_{batch_id}"
            logger.error(f"Error storing market {market_id_display}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            db.session.rollback()
            continue
    
    # Commit all changes
    db.session.commit()
    
    logger.info(f"Completed efficient batch categorization and stored {stored_count} markets")
    return stored_count

def main():
    """
    Main function to fetch and categorize markets.
    """
    with app.app_context():
        try:
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Step 1: Fetch markets from API
            markets = fetch_markets(limit=50)
            
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
            
            # Step 4: Categorize and store markets
            stored_count = store_categorized_markets(new_markets)
            
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