#!/usr/bin/env python3
"""
Categorize approved markets before deployment approval.

This script adds categorization to markets after their initial Slack approval
but before they are posted for deployment approval. This ensures that market
categorization is available during the final deployment decision.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('categorize_approved_markets')

# Import required modules
from utils.batch_categorizer import batch_categorize_markets

# Flask app for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

from models_updated import db, Market, PendingMarket
db.init_app(app)

def get_uncategorized_approved_markets() -> List[Market]:
    """
    Get approved markets that haven't been categorized yet.
    
    Returns:
        List[Market]: Markets ready for categorization
    """
    with app.app_context():
        # Find markets that:
        # 1. Have been approved (status == 'approved')
        # 2. Have not been categorized (category is null or needs_manual_categorization is True)
        # 3. Have not been deployed (deployment_status is null)
        markets = Market.query.filter(
            Market.status == 'approved',
            (Market.category.is_(None) | Market.needs_manual_categorization == True),
            Market.deployment_status.is_(None)
        ).all()
        
        logger.info(f"Found {len(markets)} approved markets needing categorization")
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
    
    # Prepare market data for batch categorization
    market_data_list = []
    for market in markets:
        market_data_list.append({
            'id': market.id,  # Use database ID as identifier
            'question': market.question,
            'description': market.description if hasattr(market, 'description') else ''
        })
    
    # Batch categorize markets
    logger.info(f"Categorizing {len(market_data_list)} markets")
    categorized_markets = batch_categorize_markets(market_data_list)
    
    # Create a map for quick lookup
    category_map = {}
    for categorized in categorized_markets:
        market_id = categorized.get('id')
        if market_id:
            category_map[market_id] = {
                'category': categorized.get('ai_category', 'news'),
                'needs_manual': categorized.get('needs_manual_categorization', False)
            }
    
    # Update markets with categories
    updated_count = 0
    with app.app_context():
        for market in markets:
            if market.id in category_map:
                category_info = category_map[market.id]
                
                # Update market category
                market.category = category_info['category']
                market.needs_manual_categorization = category_info['needs_manual']
                market.categorized_at = datetime.utcnow()
                
                updated_count += 1
                logger.info(f"Categorized market {market.id} as '{market.category}'")
        
        # Commit all changes at once
        db.session.commit()
        logger.info(f"Updated {updated_count} markets with categories")
    
    return updated_count

def main():
    """
    Main function to run the categorization process.
    """
    try:
        # Get markets that need categorization
        markets = get_uncategorized_approved_markets()
        
        # Categorize markets
        updated_count = categorize_markets(markets)
        
        logger.info(f"Successfully categorized {updated_count} markets")
        return 0
    
    except Exception as e:
        logger.error(f"Error in categorize_approved_markets: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())