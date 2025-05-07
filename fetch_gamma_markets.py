#!/usr/bin/env python3
"""
Fetch markets from Polymarket Gamma API (REST).

This script fetches markets directly from the Polymarket Gamma REST API,
processes them for active, non-expired markets, and stores them 
in the database for further pipeline processing.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional

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
DEFAULT_PARAMS = {
    "closed": "false",
    "archived": "false",
    "active": "true",
    "limit": "100"
}

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

def fetch_markets(params: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket Gamma REST API.
    
    Args:
        params: Optional query parameters to customize the request
        
    Returns:
        List of market data dictionaries
    """
    # Use default params if none provided
    query_params = DEFAULT_PARAMS.copy()
    if params:
        query_params.update(params)
    
    logger.info(f"Fetching markets with params: {query_params}")
    
    try:
        # Make request to API
        response = requests.get(GAMMA_API_URL, params=query_params)
        response.raise_for_status()
        
        # The Gamma API returns a list of markets directly, not wrapped in an object
        markets = response.json()
        
        if not isinstance(markets, list):
            logger.error(f"Unexpected response format: {type(markets)}")
            raise ValueError("API did not return a list of markets")
            
        logger.info(f"Fetched {len(markets)} markets from Gamma API")
        
        # Save raw response for debugging
        with open("gamma_markets_response.json", "w") as f:
            json.dump(markets, f, indent=2)
            
        return markets
    
    except Exception as e:
        logger.error(f"Error fetching markets from API: {str(e)}")
        raise

def filter_active_non_expired_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filter markets to only include active, non-expired ones with banner/icon URLs.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List[Dict[str, Any]]: Filtered list of markets
    """
    # Get current time in UTC with timezone info
    from datetime import timezone
    now = datetime.now(timezone.utc)
    
    filtered_markets = []
    for market in markets:
        # Skip if market is closed, archived, or inactive
        if market.get('closed') or market.get('archived') or not market.get('active', True):
            continue
        
        # Skip if market has already expired
        end_date_str = market.get('endDate')
        if end_date_str:
            try:
                # Parse ISO format date string (e.g. "2024-06-17T12:00:00Z")
                from dateutil import parser
                end_date = parser.parse(end_date_str)
                # Make sure end_date has timezone info
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                
                if end_date < now:
                    logger.info(f"Skipping expired market ending on {end_date_str}")
                    continue
            except Exception as e:
                logger.warning(f"Could not parse end date '{end_date_str}': {str(e)}")
                # Don't filter out markets with unparseable dates
        
        # Skip if market doesn't have question/title
        if not market.get('question'):
            continue
        
        # Skip if market doesn't have image or icon URLs
        if not market.get('image') or not market.get('icon'):
            continue
        
        # Add to filtered list
        filtered_markets.append(market)
    
    logger.info(f"Filtered down to {len(filtered_markets)} active, non-expired markets with banner/icon")
    
    return filtered_markets

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
    new_markets = []
    for market in markets:
        market_id = market.get('conditionId') or market.get('id')
        if market_id and market_id not in existing_market_ids:
            new_markets.append(market)
    
    logger.info(f"Found {len(new_markets)} new markets not yet in the database")
    
    return new_markets

def transform_market_options(market_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Transform market options and extract option images.
    
    Args:
        market_data: Raw market data from API
        
    Returns:
        Tuple of (options list, option_images dict)
    """
    # Get outcomes from market data - handles both object and string formats
    api_outcomes_raw = market_data.get('outcomes')
    api_options_raw = market_data.get('options')
    
    # Format options for our database
    options = []
    option_images = {}
    
    # First try to parse the outcomes (in Gamma API, this is a JSON string)
    if api_outcomes_raw and isinstance(api_outcomes_raw, str):
        try:
            # Try to parse as JSON string
            outcomes = json.loads(api_outcomes_raw)
            
            # If successful, create option objects
            if isinstance(outcomes, list):
                for i, value in enumerate(outcomes):
                    options.append({
                        'id': str(i),
                        'value': value
                    })
                    
            logger.info(f"Parsed {len(options)} outcomes from JSON string")
            return options, option_images
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse outcomes as JSON: {api_outcomes_raw}")
    
    # If that didn't work, try the object format (for backward compatibility)
    api_options = []
    if isinstance(api_outcomes_raw, list):
        api_options = api_outcomes_raw
    elif isinstance(api_options_raw, list):
        api_options = api_options_raw
    
    # Process options in object format
    if api_options:
        for opt in api_options:
            if isinstance(opt, dict):
                option_id = opt.get('id', '')
                value = opt.get('value', '')
                image_url = opt.get('image', '')
                
                options.append({
                    'id': option_id,
                    'value': value
                })
                
                if image_url:
                    option_images[value] = image_url
    
    # If still no options, create default Yes/No options
    if not options:
        logger.warning(f"No options found or parsed, defaulting to Yes/No")
        options = [
            {"id": "0", "value": "Yes"},
            {"id": "1", "value": "No"}
        ]
    
    return options, option_images

def store_categorized_markets(markets: List[Dict[str, Any]]) -> int:
    """
    Categorize and store markets in the database using batch processing.
    Takes events into account for proper grouping.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        int: Number of markets stored
    """
    # Check if we have markets to process
    if not markets:
        logger.info("No markets to categorize")
        return 0
    
    # Import event-based transformation utilities
    from utils.transform_market_with_events import transform_markets_batch
    
    # Step 1: First do batch categorization to get categories
    batch_ready_markets = []
    original_markets = {}  # Map to track original market data by batch ID
    market_id_to_batch_id = {}  # To map market IDs back to batch IDs
    
    for i, market in enumerate(markets):
        # Extract question from the market (in Gamma API, it's in the 'question' field)
        question = market.get('question', '')
        
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
        
        # Keep track of market ID to batch ID mapping
        market_id = market.get('conditionId') or market.get('id')
        if market_id:
            market_id_to_batch_id[market_id] = i
    
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
    
    logger.info("Category distribution from GPT-4o-mini categorization:")
    for category, count in category_counts.items():
        percentage = count / len(categorized_batch) * 100
        logger.info(f"  - {category}: {count} markets ({percentage:.1f}%)")
    
    # Step 2: Apply categories to markets before transformation
    for batch_id, original_market in list(original_markets.items()):
        # Apply the assigned category to the original market
        if batch_id in categorization_map:
            category = categorization_map[batch_id].get('ai_category', 'news')
            original_market['category'] = category
            original_market['ai_category'] = category  # Add explicitly to ensure it's available
            original_market['needs_manual_categorization'] = categorization_map[batch_id].get('needs_manual_categorization', False)
            original_markets[batch_id] = original_market
    
    # Step 3: Transform markets with event handling
    try:
        # Convert dictionary to list
        markets_list = list(original_markets.values())
        
        # Transform markets, extracting events
        events, transformed_markets = transform_markets_batch(markets_list)
        
        # Log transformation results
        logger.info(f"Extracted {len(events)} unique events from {len(transformed_markets)} markets")
        
        # Events found
        for i, event in enumerate(events[:5]):  # Show first 5 events
            logger.info(f"Event {i+1}: {event['name']} (ID: {event['id']})")
    
    except Exception as e:
        logger.error(f"Error transforming markets with events: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        # Continue with original markets if transformation fails
        transformed_markets = []
    
    # Step 4: Store markets and events in database
    stored_count = 0
    
    # Create a map of transformed markets by ID for easier lookup
    transformed_market_map = {}
    for tm in transformed_markets:
        market_id = tm.get('id')
        if market_id:
            transformed_market_map[market_id] = tm
    
    # Store each market
    for batch_id, original_market in original_markets.items():
        try:
            # Extract market ID
            market_id = original_market.get('conditionId') or original_market.get('id')
            
            # Skip if already in database
            if db.session.query(PendingMarket).filter_by(poly_id=market_id).count() > 0:
                logger.info(f"Market {market_id} already exists in database, skipping")
                continue
            
            # Get question
            question = original_market.get('question', '')
            
            # Get category - first check transformed market, then categorization results
            transformed_market = transformed_market_map.get(market_id)
            
            if transformed_market:
                # Get category and event info from transformed market
                # Prioritize ai_category over category to ensure AI categories are used
                category = transformed_market.get('ai_category') or transformed_market.get('category') or original_market.get('ai_category') or original_market.get('category') or 'news'
                event_id = transformed_market.get('event_id')
                event_name = transformed_market.get('event_name')
                options = transformed_market.get('options', [])
                option_images = transformed_market.get('option_images', {})
            else:
                # Fallback to original categorization
                if batch_id in categorization_map:
                    batch_result = categorization_map[batch_id]
                    category = batch_result.get('ai_category', 'news')
                else:
                    # Use keyword-based categorization as last resort
                    from utils.batch_categorizer import keyword_based_categorization
                    category = keyword_based_categorization(question)
                
                # No event info available in fallback path
                event_id = None
                event_name = None
                
                # Process options with error handling
                try:
                    from utils.transform_market_with_events import extract_market_options
                    options = extract_market_options(original_market)
                    option_images = {}
                    for opt in options:
                        if opt.get('image_url'):
                            option_images[opt['id']] = opt['image_url']
                except Exception as e:
                    logger.warning(f"Error extracting options (fallback): {str(e)}")
                    options = [
                        {"id": "option_0", "value": "Yes"},
                        {"id": "option_1", "value": "No"}
                    ]
                    option_images = {}
            
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
                needs_manual_categorization=batch_id not in categorization_map,
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
                raw_data=original_market,
                posted=False
            )
            
            db.session.add(processed_market)
            stored_count += 1
            
            # Log with event info if available
            if event_name:
                logger.info(f"Stored market '{question[:40]}...' with category '{category}' under event '{event_name}'")
            else:
                logger.info(f"Stored market '{question[:40]}...' with category '{category}'")
            
        except Exception as e:
            # Use batch_id as fallback if market_id isn't set
            market_id_display = f"batch_id_{batch_id}"
            if 'market_id' in locals() and market_id:
                market_id_display = market_id
                
            logger.error(f"Error storing market {market_id_display}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            db.session.rollback()
            continue
    
    # Commit all changes
    db.session.commit()
    
    logger.info(f"Completed batch categorization and stored {stored_count} markets with event grouping")
    return stored_count

def main():
    """
    Main function to fetch markets from Gamma API.
    """
    with app.app_context():
        try:
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Step 1: Fetch markets from API
            markets = fetch_markets()
            
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
            
            # Only update pipeline_run if it exists
            pipeline_run_obj = None
            if 'pipeline_run' in locals() and pipeline_run is not None:
                pipeline_run_obj = pipeline_run
            else:
                try:
                    # Create a new pipeline run record for the error
                    pipeline_run_obj = create_pipeline_run()
                except Exception as inner_e:
                    logger.error(f"Could not create pipeline run for error logging: {str(inner_e)}")
                
            if pipeline_run_obj is not None:
                update_pipeline_run(pipeline_run_obj, "failed", error=str(e))
                
            return 1

if __name__ == "__main__":
    sys.exit(main())