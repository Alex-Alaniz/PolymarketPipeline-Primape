#!/usr/bin/env python3

"""
Categorize approved markets before deployment approval.

This script adds categorization to markets after their initial Slack approval
but before they are posted for deployment approval. This ensures that market
categorization is available during the final deployment decision.
"""

import os
import logging
import sys
import json
from typing import List, Dict, Any

from utils.batch_categorizer import batch_categorize_markets
from models import db, Market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("categorize_approved_markets")

def get_uncategorized_approved_markets() -> List[Market]:
    """
    Get approved markets that haven't been categorized yet.
    
    Returns:
        List[Market]: Markets ready for categorization
    """
    # Find markets that are approved but don't have a category yet
    markets = Market.query.filter(
        Market.status == "new",  # New status means approved but not yet deployed
        (Market.category == None) | (Market.category == "")  # No category assigned
    ).all()
    
    return markets

def categorize_markets(markets: List[Market]) -> int:
    """
    Categorize a list of markets using the batch categorizer.
    
    Args:
        markets: List of Market model instances
        
    Returns:
        int: Number of markets successfully categorized
    """
    if not markets:
        logger.info("No markets to categorize")
        return 0
    
    logger.info(f"Categorizing {len(markets)} markets")
    
    # Convert Market objects to dictionaries for batch categorization
    market_dicts = []
    for market in markets:
        # Prepare options
        options = []
        if market.options:
            try:
                if isinstance(market.options, str):
                    options_data = json.loads(market.options)
                    for opt in options_data:
                        if isinstance(opt, dict) and 'value' in opt:
                            options.append(opt['value'])
                        else:
                            options.append(str(opt))
                elif isinstance(market.options, list):
                    for opt in market.options:
                        if isinstance(opt, dict) and 'value' in opt:
                            options.append(opt['value'])
                        else:
                            options.append(str(opt))
            except Exception as e:
                logger.error(f"Error parsing options for market {market.id}: {str(e)}")
                options = ["Yes", "No"]  # Fallback
                
        # Create dictionary with required fields
        market_dict = {
            "id": market.id,
            "question": market.question,
            "description": market.description or "",
            "options": options,
            "type": market.type or "binary",
            "event_name": getattr(market, "event_name", None)
        }
        market_dicts.append(market_dict)
    
    # Batch categorize the markets
    try:
        categorized_markets = batch_categorize_markets(market_dicts)
        
        # Update the original Market objects with categories
        categorized_count = 0
        for i, market_dict in enumerate(categorized_markets):
            if "ai_category" in market_dict and market_dict["ai_category"]:
                # Get the original market
                market = markets[i]
                
                # Update category
                market.category = market_dict["ai_category"]
                
                # Add an 'ai_confidence' field if available
                if "ai_confidence" in market_dict:
                    market.ai_confidence = market_dict["ai_confidence"]
                
                categorized_count += 1
                logger.info(f"Categorized market {market.id} as '{market.category}'")
        
        # Save all changes
        if categorized_count > 0:
            db.session.commit()
            logger.info(f"Saved {categorized_count} categorized markets")
        
        return categorized_count
    
    except Exception as e:
        logger.error(f"Error during batch categorization: {str(e)}")
        return 0

def main():
    """
    Main function to run the categorization process.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        try:
            # Get uncategorized approved markets
            markets = get_uncategorized_approved_markets()
            logger.info(f"Found {len(markets)} uncategorized approved markets")
            
            # Categorize markets
            categorized_count = categorize_markets(markets)
            logger.info(f"Successfully categorized {categorized_count} markets")
            
            return 0
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())