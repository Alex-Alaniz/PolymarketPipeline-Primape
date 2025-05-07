"""
Inspect pending markets in the database to understand their structure.
"""
import os
import sys
import json
import logging
from datetime import datetime
from flask import Flask
from main import app
from models import db, PendingMarket

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("inspect_pending_markets")

def inspect_pending_markets():
    """Inspect pending markets in the database."""
    
    with app.app_context():
        # Get markets from database
        pending_markets = db.session.query(PendingMarket).all()
        
        if not pending_markets:
            logger.info("No pending markets in the database")
            return 0
        
        logger.info(f"Found {len(pending_markets)} pending markets in the database")
        
        # Inspect each market
        for i, market in enumerate(pending_markets):
            logger.info(f"Market {i+1}:")
            logger.info(f"  Poly ID: {market.poly_id}")
            logger.info(f"  Question: {market.question}")
            logger.info(f"  Category: {market.category}")
            logger.info(f"  Options type: {type(market.options)}")
            
            # If options is a string, try to parse it
            if isinstance(market.options, str):
                try:
                    options_dict = json.loads(market.options)
                    logger.info(f"  Options (parsed): {options_dict}")
                except json.JSONDecodeError:
                    logger.info(f"  Options (raw): {market.options}")
            else:
                logger.info(f"  Options (raw): {market.options}")
                # If it's a list or dict, print the first few items in detail
                if isinstance(market.options, (list, dict)) and market.options:
                    if isinstance(market.options, list):
                        for j, option in enumerate(market.options[:3]):  # Show first 3 options
                            logger.info(f"    Option {j+1} type: {type(option)}")
                            logger.info(f"    Option {j+1} content: {option}")
                    elif isinstance(market.options, dict):
                        for key, value in list(market.options.items())[:3]:  # Show first 3 key-value pairs
                            logger.info(f"    Key: {key}, Value type: {type(value)}")
                            logger.info(f"    Value: {value}")
            
            logger.info(f"  Event ID: {market.event_id}")
            logger.info(f"  Event Name: {market.event_name}")
            logger.info(f"  Banner URL: {market.banner_url}")
            logger.info(f"  Icon URL: {market.icon_url}")
            logger.info(f"  Posted: {market.posted}")
            logger.info(f"  Slack Message ID: {market.slack_message_id}")
            logger.info("---")
        
        return 0

if __name__ == "__main__":
    sys.exit(inspect_pending_markets())