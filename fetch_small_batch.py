#!/usr/bin/env python3

"""
Fetch a small batch of markets from Polymarket for testing.

This script fetches a small number of markets from Polymarket's API,
categorizes them, and adds them to the pending_markets table for the pipeline.
"""

import os
import sys
import argparse
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("fetch_small_batch")

from main import app
from models import db, PendingMarket, PipelineRun
from utils.polymarket import PolymarketExtractor
# We'll implement our own categorization function since we're having issues with imports

# Valid categories - must match exactly what's in the prompt
VALID_CATEGORIES = ["politics", "crypto", "sports", "business", "culture", "news", "tech"]

def keyword_based_categorization(question: str) -> str:
    """
    Categorize a market based on keywords in the question.
    
    Args:
        question: Market question
        
    Returns:
        Category string
    """
    question_lower = question.lower() if question else ""
    
    # Politics keywords
    if any(keyword in question_lower for keyword in 
          ["biden", "president", "election", "vote", "congress", "political", 
           "government", "senate", "house", "supreme court", "justice"]):
        return "politics"
    
    # Crypto keywords
    elif any(keyword in question_lower for keyword in 
            ["bitcoin", "eth", "ethereum", "crypto", "blockchain", "token", 
             "defi", "nft", "cryptocurrency", "btc"]):
        return "crypto"
    
    # Sports keywords
    elif any(keyword in question_lower for keyword in 
            ["team", "game", "match", "player", "sport", "win", "championship", 
             "tournament", "league", "nba", "nfl", "mlb", "soccer", "football"]):
        return "sports"
    
    # Business keywords
    elif any(keyword in question_lower for keyword in 
            ["stock", "company", "price", "market", "business", "earnings", 
             "profit", "ceo", "investor", "economy", "financial", "trade"]):
        return "business"
    
    # Tech keywords
    elif any(keyword in question_lower for keyword in 
            ["ai", "tech", "technology", "software", "app", "computer", "device", 
             "release", "launch", "update", "apple", "google", "microsoft"]):
        return "tech"
    
    # Culture keywords
    elif any(keyword in question_lower for keyword in 
            ["movie", "film", "show", "tv", "actor", "actress", "director", 
             "music", "song", "album", "artist", "celebrity", "award"]):
        return "culture"
    
    # Default to news
    else:
        return "news"

def categorize_markets(markets: list) -> list:
    """
    Categorize a batch of markets using keyword-based categorization.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List of categorized market data dictionaries
    """
    if not markets:
        logger.warning("No markets to categorize")
        return []
    
    logger.info(f"Batch categorizing {len(markets)} markets")
    categorized_markets = []
    
    try:
        # First try the keyword-based categorization as a fallback
        for market in markets:
            question = market.get('question', '')
            category = keyword_based_categorization(question)
            market_copy = market.copy()
            market_copy['category'] = category
            categorized_markets.append(market_copy)
            logger.info(f"Categorized market '{question[:50]}...' as '{category}'")
        
        return categorized_markets
        
    except Exception as e:
        logger.error(f"Error in categorization: {str(e)}")
        return []

def create_pipeline_run():
    """Create a new pipeline run record."""
    try:
        pipeline_run = PipelineRun(
            start_time=datetime.utcnow(),
            status="running",
            component="fetch_markets"
        )
        db.session.add(pipeline_run)
        db.session.commit()
        logger.info(f"Created pipeline run with ID {pipeline_run.id}")
        return pipeline_run.id
    except Exception as e:
        logger.error(f"Error creating pipeline run: {str(e)}")
        return None

def update_pipeline_run(run_id, status, **kwargs):
    """Update the pipeline run record."""
    try:
        pipeline_run = PipelineRun.query.get(run_id)
        if pipeline_run:
            pipeline_run.status = status
            pipeline_run.end_time = datetime.utcnow() if status != "running" else None
            
            for key, value in kwargs.items():
                if hasattr(pipeline_run, key):
                    setattr(pipeline_run, key, value)
            
            db.session.commit()
            logger.info(f"Updated pipeline run {run_id} with status {status}")
    except Exception as e:
        logger.error(f"Error updating pipeline run: {str(e)}")

def fetch_and_categorize(api_limit=10, process_limit=5):
    """
    Fetch and categorize a small batch of markets.
    
    Args:
        api_limit: Number of markets to fetch from the API
        process_limit: Maximum number of markets to process
        
    Returns:
        bool: True if successful, False otherwise
    """
    run_id = create_pipeline_run()
    
    try:
        # Fetch markets from Polymarket API using PolymarketExtractor
        logger.info(f"Fetching markets from Polymarket API")
        extractor = PolymarketExtractor()
        
        data = extractor.extract_data()
        if not data:
            logger.error("Failed to fetch markets from Polymarket API")
            update_pipeline_run(run_id, "failed", error="API fetch failed")
            return False
        
        # Limit the number of markets to process
        data = data[:api_limit] if len(data) > api_limit else data
        logger.info(f"Fetched {len(data)} markets from Polymarket API")
        
        # Filter markets to keep only non-expired ones
        filtered_markets = []
        for market in data:
            if 'endDate' in market and market['endDate']:
                try:
                    # Parse end date
                    end_date = datetime.fromisoformat(market['endDate'].replace('Z', '+00:00'))
                    
                    # Skip expired markets
                    if end_date < datetime.utcnow():
                        logger.info(f"Skipping expired market ending on {market['endDate']}")
                        continue
                except Exception as e:
                    logger.warning(f"Error parsing end date '{market.get('endDate')}': {str(e)}")
            
            # Keep only markets with banner and options images
            if 'questionImage' in market and market['questionImage']:
                filtered_markets.append(market)
            
            # Limit the number of markets to process
            if len(filtered_markets) >= process_limit:
                break
        
        logger.info(f"Filtered down to {len(filtered_markets)} active, non-expired markets with banner")
        
        # Check for existing markets
        market_ids = [m['id'] for m in filtered_markets]
        existing_markets = PendingMarket.query.filter(PendingMarket.poly_id.in_(market_ids)).all()
        existing_ids = {m.poly_id for m in existing_markets}
        
        new_markets = [m for m in filtered_markets if m['id'] not in existing_ids]
        logger.info(f"Found {len(new_markets)} new markets not yet in the database")
        
        if not new_markets:
            logger.info("No new markets to process")
            update_pipeline_run(run_id, "completed", markets_fetched=len(data), markets_filtered=len(filtered_markets))
            return True
        
        # Categorize the markets
        logger.info(f"Categorizing {len(new_markets)} markets with keyword-based categorization...")
        categorized_markets = categorize_markets(new_markets)
        
        if not categorized_markets:
            logger.error("Failed to categorize markets")
            update_pipeline_run(run_id, "failed", markets_fetched=len(data), markets_filtered=len(filtered_markets), error="Categorization failed")
            return False
        
        logger.info(f"Successfully categorized {len(categorized_markets)} markets")
        
        # Add markets to the database
        added_count = 0
        for market in categorized_markets:
            try:
                # Create options array
                options = []
                if 'outcomes' in market and market['outcomes']:
                    if isinstance(market['outcomes'], str):
                        try:
                            options = json.loads(market['outcomes'])
                        except:
                            options = ["Yes", "No"]
                    else:
                        options = market['outcomes']
                else:
                    options = ["Yes", "No"]
                
                # Parse expiry timestamp
                expiry = None
                if 'endDate' in market and market['endDate']:
                    try:
                        expiry = int(datetime.fromisoformat(
                            market['endDate'].replace("Z", "+00:00")
                        ).timestamp())
                    except Exception as e:
                        logger.error(f"Error parsing endDate: {str(e)}")
                
                # Extract event info if available
                event_id = market.get('eventId')
                event_name = market.get('eventName')
                
                # Create pending market
                pending_market = PendingMarket(
                    poly_id=market['id'],
                    question=market.get('question', ''),
                    category=market.get('category', 'news'),
                    options=json.dumps(options) if isinstance(options, list) else options,
                    expiry=expiry,
                    raw_data=market,
                    posted=False,
                    event_id=event_id,
                    event_name=event_name
                )
                
                db.session.add(pending_market)
                added_count += 1
                
            except Exception as e:
                logger.error(f"Error adding market {market.get('id')}: {str(e)}")
        
        db.session.commit()
        logger.info(f"Added {added_count} new markets to pending_markets table")
        
        update_pipeline_run(
            run_id, 
            "completed", 
            markets_fetched=len(data),
            markets_filtered=len(filtered_markets),
            new_markets=added_count
        )
        
        return True
    
    except Exception as e:
        logger.error(f"Error in fetch_and_categorize: {str(e)}")
        update_pipeline_run(run_id, "failed", error=str(e))
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Fetch a small batch of markets from Polymarket.')
    parser.add_argument('--api-limit', type=int, default=10, help='Number of markets to fetch from API (default: 10)')
    parser.add_argument('--process-limit', type=int, default=5, help='Maximum number of markets to process (default: 5)')
    
    args = parser.parse_args()
    
    with app.app_context():
        success = fetch_and_categorize(args.api_limit, args.process_limit)
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())