#!/usr/bin/env python3

"""
Simple Polymarket Pipeline for Production Testing

This is a simplified version of the pipeline that:
1. Fetches markets from Polymarket API
2. Uses keyword-based categorization (no OpenAI call)
3. Posts markets to Slack for approval

This script is intended for production testing of the approval workflow
without the complexity of the full pipeline.
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our utility modules
from utils.fallback_categorizer import fallback_categorize, detect_event
from utils.messaging import post_slack_message
from filter_active_markets import fetch_markets, filter_active_markets
from models import db, PendingMarket, ProcessedMarket, PipelineRun

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_pipeline")

# Import Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

def fetch_and_filter_markets():
    """
    Fetch markets from Polymarket API and filter active ones.
    
    Returns:
        list: Filtered market data
    """
    logger.info("Fetching markets from Polymarket API")
    markets = fetch_markets()
    
    if not markets:
        logger.error("Failed to fetch markets from API")
        return []
    
    logger.info(f"Fetched {len(markets)} markets from API")
    
    # Filter active markets
    filtered_markets = filter_active_markets(markets)
    logger.info(f"Filtered to {len(filtered_markets)} active markets")
    
    return filtered_markets

def categorize_markets(markets):
    """
    Categorize markets using the fallback keyword-based categorizer.
    Also extract event information from the Polymarket API response.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List of market dictionaries with added 'category', 'event_id', and 'event_name' fields
    """
    categorized_markets = []
    
    for i, market in enumerate(markets):
        question = market.get('question', '')
        if not question:
            logger.warning(f"Market at index {i} has no question, skipping")
            continue
        
        # Use fallback categorization
        category = fallback_categorize(question)
        
        # Extract event information from market data
        event_id = None
        event_name = None
        event_image = None
        event_icon = None
        event_questions = []
        event_outcomes = []
        
        # First check if event data is directly available
        if 'event_id' in market:
            event_id = market.get('event_id')
        
        if 'event_name' in market:
            event_name = market.get('event_name')
            
        if 'event_image' in market:
            event_image = market.get('event_image')
            
        if 'event_icon' in market:
            event_icon = market.get('event_icon')
        
        # Then check for detailed event data from API
        events = market.get('events', [])
        if events:
            for event in events:
                if 'id' in event:
                    event_id = event['id']
                if 'name' in event:
                    event_name = event['name']
                if 'image' in event:
                    event_image = event['image']
                if 'icon' in event:
                    event_icon = event['icon']
                if 'questions' in event:
                    event_questions = event['questions']
                if 'outcomes' in event:
                    event_outcomes = event['outcomes']
        
        # If event info is still not found, use fallback from text analysis
        if not event_id or not event_name:
            detected_id, detected_name = detect_event(question)
            event_id = event_id or detected_id
            event_name = event_name or detected_name
        
        logger.info(f"Categorized market {i+1}/{len(markets)}: '{question[:30]}...' as {category}")
        if event_id:
            logger.info(f"Detected event: {event_name or 'Unknown'} (ID: {event_id})")
            if event_image:
                logger.info(f"Event has banner image: {event_image[:50]}...")
        
        # Get market option images if available
        option_images = {}
        if 'option_images' in market:
            option_images = market.get('option_images', {})
        elif 'icon' in market:
            # If market has an icon, use it as default option image
            option_images = {"Yes": market.get('icon')}
        
        # Add category and event info to market
        market_copy = market.copy()
        market_copy['category'] = category
        market_copy['event_id'] = event_id
        market_copy['event_name'] = event_name
        market_copy['event_image'] = event_image
        market_copy['event_icon'] = event_icon
        market_copy['event_questions'] = event_questions
        market_copy['event_outcomes'] = event_outcomes
        market_copy['option_images'] = option_images
        
        categorized_markets.append(market_copy)
    
    return categorized_markets

def store_and_post_markets(markets):
    """
    Store markets in the database and post them to Slack.
    
    Args:
        markets: List of categorized market data
        
    Returns:
        int: Number of markets posted to Slack
    """
    posted_count = 0
    
    for market in markets:
        try:
            # Create a PendingMarket record
            pending_market = PendingMarket(
                poly_id=market.get('id'),
                question=market.get('question'),
                category=market.get('category'),
                options=json.dumps(["Yes", "No"]),  # Default binary options
                expiry=market.get('expiry_time'),
                event_id=market.get('event_id'),
                event_name=market.get('event_name'),
                posted=False  # Will be set to True after posting
            )
            
            # Add to database
            db.session.add(pending_market)
            db.session.commit()
            
            # Use our enhanced formatting function
            # This will include event banner and option images in the Slack message
            response = post_slack_message("", market_data=market)
            
            if response and response.get('ok'):
                # Update the PendingMarket record with Slack message info
                pending_market.slack_message_id = response.get('ts')
                pending_market.posted = True
                db.session.commit()
                
                logger.info(f"Posted market to Slack: {market.get('question', 'Unknown')[:50]}...")
                posted_count += 1
            else:
                logger.error(f"Failed to post market to Slack: {response}")
                
        except Exception as e:
            logger.error(f"Error storing/posting market: {str(e)}")
            db.session.rollback()
    
    return posted_count

def run_simple_pipeline():
    """
    Run the simplified pipeline.
    
    Returns:
        tuple: (fetched_count, categorized_count, posted_count)
    """
    pipeline_run = None
    try:
        # Create app context if needed
        if not app.app_context:
            with app.app_context():
                return _run_simple_pipeline_internal()
        else:
            return _run_simple_pipeline_internal()
    except Exception as e:
        logger.error(f"Error in simple pipeline: {str(e)}")
        try:
            if pipeline_run:
                pipeline_run.status = "failed"
                pipeline_run.end_time = datetime.utcnow()
                pipeline_run.error = str(e)
                db.session.commit()
        except Exception as e2:
            logger.error(f"Error updating pipeline run: {str(e2)}")
        return (0, 0, 0)

def _run_simple_pipeline_internal():
    """Internal function that runs with an app context"""
    # Record pipeline run
    pipeline_run = PipelineRun(
        start_time=datetime.utcnow(),
        status="running"
    )
    db.session.add(pipeline_run)
    db.session.commit()
    
    # Step 1: Fetch and filter markets
    markets = fetch_and_filter_markets()
    fetched_count = len(markets)
    logger.info(f"Fetched {fetched_count} markets")
    
    if not markets:
        pipeline_run.status = "completed" 
        pipeline_run.end_time = datetime.utcnow()
        pipeline_run.markets_processed = 0
        db.session.commit()
        return (0, 0, 0)
    
    # Step 2: Categorize markets
    categorized_markets = categorize_markets(markets)
    categorized_count = len(categorized_markets)
    logger.info(f"Categorized {categorized_count} markets")
    
    # Step 3: Store and post markets
    posted_count = store_and_post_markets(categorized_markets)
    logger.info(f"Posted {posted_count} markets to Slack")
    
    # Update pipeline run record
    pipeline_run.status = "completed"
    pipeline_run.end_time = datetime.utcnow()
    pipeline_run.markets_processed = fetched_count
    pipeline_run.markets_posted = posted_count
    db.session.commit()
    
    return (fetched_count, categorized_count, posted_count)

if __name__ == "__main__":
    with app.app_context():
        logger.info("Starting simple pipeline for production testing")
        fetched, categorized, posted = run_simple_pipeline()
        logger.info(f"Pipeline complete: {fetched} fetched, {categorized} categorized, {posted} posted")