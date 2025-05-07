#!/usr/bin/env python3

"""
Track Market IDs After Deployment

This script checks for markets that have been successfully deployed to Apechain
but don't yet have their Apechain market IDs recorded in the database. It retrieves
their market IDs from the blockchain and updates the database accordingly.

This is useful if a deployment transaction was successful but the script terminated
before the market ID could be retrieved and recorded.
"""

import os
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import flask
from models import db, Market, PipelineRun
from utils.apechain import get_deployed_market_id_from_tx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("track_market_id")

def create_pipeline_run():
    """Create a new pipeline run record in the database."""
    try:
        pipeline_run = PipelineRun(
            status="running",
            start_time=datetime.utcnow()
        )
        db.session.add(pipeline_run)
        db.session.commit()
        logger.info(f"Created pipeline run with ID {pipeline_run.id}")
        return pipeline_run
    except Exception as e:
        logger.error(f"Error creating pipeline run: {str(e)}")
        return None

def update_pipeline_run(pipeline_run, status, markets_processed=0, markets_updated=0, 
                       markets_failed=0, error=None):
    """Update the pipeline run record with results."""
    if not pipeline_run:
        return
        
    try:
        pipeline_run.status = status
        pipeline_run.end_time = datetime.utcnow()
        pipeline_run.markets_processed = markets_processed
        pipeline_run.markets_approved = markets_updated  # reuse this field
        pipeline_run.markets_failed = markets_failed
        
        if error:
            pipeline_run.error = str(error)
            
        db.session.commit()
        logger.info(f"Updated pipeline run {pipeline_run.id} with status {status}")
    except Exception as e:
        logger.error(f"Error updating pipeline run: {str(e)}")

def track_deployed_markets() -> Tuple[int, int, int]:
    """
    Track markets that have been deployed to Apechain.
    
    Returns:
        Tuple[int, int, int]: Count of (processed, updated, failed) markets
    """
    try:
        # Check if event_id and event_name columns exist
        has_event_fields = True
        try:
            # Try to access the event_id field on the Market model
            getattr(Market, 'event_id')
        except AttributeError:
            has_event_fields = False
            logger.warning("Market model does not have event_id field")
        
        # Build the query based on available columns
        query = Market.query.filter(
            Market.blockchain_tx.isnot(None),
            Market.apechain_market_id.is_(None)
        )
        
        # Execute the query
        markets_to_track = query.all()
        
        logger.info(f"Found {len(markets_to_track)} markets to track")
        
        processed = 0
        updated = 0
        failed = 0
        
        for market in markets_to_track:
            processed += 1
            logger.info(f"Processing market {market.id} with transaction {market.blockchain_tx}")
            
            try:
                # Get market ID from blockchain transaction
                apechain_id = get_deployed_market_id_from_tx(market.blockchain_tx)
                
                if apechain_id:
                    # Update market with Apechain market ID
                    market.apechain_market_id = apechain_id
                    market.status = "deployed"
                    
                    logger.info(f"Updated market {market.id} with Apechain ID {apechain_id}")
                    updated += 1
                else:
                    # Failed to get market ID
                    logger.error(f"Failed to get Apechain market ID for transaction {market.blockchain_tx}")
                    failed += 1
            except Exception as e:
                logger.error(f"Error tracking market {market.id}: {str(e)}")
                failed += 1
        
        # Save all changes
        db.session.commit()
        
        return processed, updated, failed
    except Exception as e:
        logger.error(f"Error in track_deployed_markets: {str(e)}")
        return 0, 0, 0

def main():
    """
    Main function to track deployed markets.
    """
    # Import Flask app to get application context
    from main import app
    
    try:
        # Use application context for database operations
        with app.app_context():
            # Create pipeline run record inside app context
            pipeline_run = create_pipeline_run()
            
            processed, updated, failed = track_deployed_markets()
            
            # Update pipeline run
            if pipeline_run:
                update_pipeline_run(
                    pipeline_run,
                    status="completed" if failed == 0 else "completed_with_errors",
                    markets_processed=processed,
                    markets_updated=updated,
                    markets_failed=failed
                )
            
            # Log results
            print(f"Tracking results: {processed} processed, {updated} updated, {failed} failed")
        
        return 0
    except Exception as e:
        logger.error(f"Error in tracking script: {str(e)}")
        return 1

if __name__ == "__main__":
    main()