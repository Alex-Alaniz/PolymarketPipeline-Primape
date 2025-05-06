#!/usr/bin/env python3
"""
Track and update Apechain market IDs after deployment.

This script checks for markets that have been deployed to Apechain
but don't have their market ID saved in the database. It then
queries the blockchain to get the market ID and updates the database.
This ensures proper frontend mapping of banner images and option icons.
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Local imports
from models import db, Market, PipelineRun
from utils.apechain import get_deployed_market_id_from_tx

# Initialize app
db.init_app(app)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("track_market_ids.log")
    ]
)
logger = logging.getLogger('track_market_ids')

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

def get_markets_needing_id_update():
    """
    Get markets that have been deployed but don't have their Apechain market ID stored.
    
    Returns:
        List of Market objects that need Apechain market ID updates
    """
    # Find markets that have transaction hashes but no Apechain market ID
    markets = Market.query.filter(
        Market.blockchain_tx.isnot(None),
        (Market.apechain_market_id.is_(None) | (Market.apechain_market_id == ''))
    ).all()
    
    logger.info(f"Found {len(markets)} markets needing Apechain market ID updates")
    return markets

def update_market_ids(markets: List[Market]) -> int:
    """
    Update market IDs by querying the blockchain.
    
    Args:
        markets: List of Market objects to update
        
    Returns:
        int: Number of markets successfully updated
    """
    updated_count = 0
    
    for market in markets:
        try:
            if not market.blockchain_tx:
                logger.warning(f"Market {market.id} has no blockchain transaction hash")
                continue
            
            # Get Apechain market ID from transaction hash
            market_id = get_deployed_market_id_from_tx(market.blockchain_tx)
            
            if not market_id:
                logger.warning(f"Failed to get market ID for transaction {market.blockchain_tx}")
                continue
            
            # Update market
            market.apechain_market_id = market_id
            db.session.commit()
            
            logger.info(f"Updated market {market.id} with Apechain market ID {market_id}")
            updated_count += 1
            
        except Exception as e:
            logger.error(f"Error updating market {market.id}: {str(e)}")
            db.session.rollback()
    
    return updated_count

def main():
    """
    Main function to track and update Apechain market IDs.
    """
    with app.app_context():
        try:
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Get markets needing ID updates
            markets = get_markets_needing_id_update()
            
            if not markets:
                logger.info("No markets need Apechain market ID updates")
                update_pipeline_run(pipeline_run, "completed")
                return 0
            
            # Update market IDs
            updated_count = update_market_ids(markets)
            
            logger.info(f"Updated {updated_count} out of {len(markets)} markets with Apechain market IDs")
            update_pipeline_run(
                pipeline_run, 
                "completed", 
                markets_processed=len(markets),
                markets_deployed=updated_count
            )
            
            return 0
        
        except Exception as e:
            logger.error(f"Error in main function: {str(e)}")
            if 'pipeline_run' in locals():
                update_pipeline_run(pipeline_run, "failed", error=str(e))
            return 1

if __name__ == "__main__":
    sys.exit(main())