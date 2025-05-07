#!/usr/bin/env python3

"""
Test Market Deployment

This script simulates deploying approved markets to Apechain without actually
sending transactions to the blockchain. It's used for testing the deployment
workflow and database updates.
"""

import os
import logging
import random
import string
from datetime import datetime
from typing import List, Tuple, Optional

from main import app
from models import db, Market, PipelineRun

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_deployment")

def generate_mock_tx_hash() -> str:
    """Generate a mock transaction hash for testing."""
    # Generate a random hex string of 64 characters
    return '0x' + ''.join(random.choice(string.hexdigits.lower()) for _ in range(64))

def generate_mock_market_id() -> str:
    """Generate a mock Apechain market ID for testing."""
    # In production, these would be sequential numbers 
    # but for testing, we'll use small random numbers
    return str(random.randint(1, 10000))

def create_pipeline_run() -> Optional[PipelineRun]:
    """Create a new pipeline run record in the database."""
    try:
        pipeline_run = PipelineRun(
            start_time=datetime.utcnow(),
            status="running"
        )
        db.session.add(pipeline_run)
        db.session.commit()
        logger.info(f"Created pipeline run with ID {pipeline_run.id}")
        return pipeline_run
    except Exception as e:
        logger.error(f"Error creating pipeline run: {str(e)}")
        return None

def update_pipeline_run(
    pipeline_run: PipelineRun,
    status: str,
    markets_processed: int = 0,
    markets_deployed: int = 0,
    markets_failed: int = 0,
    error: Optional[str] = None
) -> None:
    """Update the pipeline run record with results."""
    try:
        pipeline_run.end_time = datetime.utcnow()
        pipeline_run.status = status
        pipeline_run.markets_processed = markets_processed
        pipeline_run.markets_approved = markets_deployed  # reuse this field
        pipeline_run.markets_failed = markets_failed
        
        if error:
            pipeline_run.error = str(error)
            
        db.session.commit()
        logger.info(f"Updated pipeline run {pipeline_run.id} with status {status}")
    except Exception as e:
        logger.error(f"Error updating pipeline run: {str(e)}")

def find_markets_for_deployment() -> List[Market]:
    """
    Find markets that have been approved for deployment but not yet deployed.
    
    Returns:
        List of Market objects ready for deployment
    """
    try:
        # Query markets that have been approved for deployment but not yet deployed
        # Status should be 'deployment_approved' and no blockchain_tx
        markets = Market.query.filter(
            Market.status == 'deployment_approved',
            Market.blockchain_tx.is_(None)
        ).all()
        
        logger.info(f"Found {len(markets)} markets approved for deployment")
        return markets
    except Exception as e:
        logger.error(f"Error finding markets for deployment: {str(e)}")
        return []

def test_deploy_markets(markets: List[Market]) -> Tuple[int, int, int]:
    """
    Simulate deploying markets to Apechain (test mode).
    
    Args:
        markets: List of Market objects to deploy
        
    Returns:
        Tuple[int, int, int]: Count of (processed, deployed, failed) markets
    """
    processed = 0
    deployed = 0
    failed = 0
    
    for market in markets:
        processed += 1
        logger.info(f"Processing market {market.id} for test deployment")
        
        try:
            # Generate mock transaction hash and market ID
            tx_hash = generate_mock_tx_hash()
            market_id = generate_mock_market_id()
            
            # Simulate a small chance of failure
            if random.random() < 0.1:  # 10% chance of failure
                logger.warning(f"Simulating deployment failure for market {market.id}")
                failed += 1
                continue
                
            # Update the market with simulated blockchain data
            market.blockchain_tx = tx_hash
            market.apechain_market_id = market_id
            market.status = "deployed"  # Mark as deployed
            db.session.commit()
            
            logger.info(f"Test deployed market {market.id} with Apechain ID {market_id}")
            logger.info(f"Transaction hash: {tx_hash}")
            deployed += 1
            
        except Exception as e:
            logger.error(f"Error in test deployment for market {market.id}: {str(e)}")
            failed += 1
    
    return processed, deployed, failed

def main() -> int:
    """Main function to test deploy approved markets."""
    pipeline_run = None
    try:
        with app.app_context():
            # Create pipeline run record
            pipeline_run = create_pipeline_run()
            
            # Step 1: Find markets approved for deployment
            markets = find_markets_for_deployment()
            
            if not markets:
                logger.info("No markets found for deployment")
                if pipeline_run:
                    update_pipeline_run(pipeline_run, "completed", 0, 0, 0)
                return 0
            
            # Step 2: Test deploy markets
            processed, deployed, failed = test_deploy_markets(markets)
            
            # Step 3: Update pipeline run record
            if pipeline_run:
                status = "completed" if failed == 0 else "completed_with_errors"
                update_pipeline_run(
                    pipeline_run,
                    status=status,
                    markets_processed=processed,
                    markets_deployed=deployed,
                    markets_failed=failed
                )
            
            # Log results
            logger.info(f"Test deployment results: {processed} processed, {deployed} deployed, {failed} failed")
            
            return 0
    except Exception as e:
        logger.error(f"Error in test deployment script: {str(e)}")
        
        # Update pipeline run with error
        if pipeline_run:
            try:
                with app.app_context():
                    update_pipeline_run(
                        pipeline_run,
                        status="failed",
                        error=str(e)
                    )
            except Exception as update_error:
                logger.error(f"Error updating pipeline run: {str(update_error)}")
        
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())