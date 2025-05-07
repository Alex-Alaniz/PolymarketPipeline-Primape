#!/usr/bin/env python3

"""
Deploy Approved Markets to Apechain

This script finds all markets that have been approved for deployment but not yet
deployed to Apechain, deploys them, and records the results in the database.

It handles the entire deployment process:
1. Finding markets approved for deployment
2. Deploying them to Apechain
3. Updating the database with the results (transaction hash and market ID)
4. Creating a pipeline run record for tracking
"""

import os
import logging
from datetime import datetime
import time
from typing import List, Tuple, Optional, Dict, Any

from main import app
from models import db, Market, PipelineRun
from utils.apechain import deploy_market_to_apechain, get_deployed_market_id_from_tx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("deploy_markets")

def create_pipeline_run(run_type: str = "market_deployment") -> Optional[PipelineRun]:
    """Create a new pipeline run record in the database."""
    try:
        pipeline_run = PipelineRun(
            run_type=run_type,
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

def deploy_markets(markets: List[Market]) -> Tuple[int, int, int]:
    """
    Deploy approved markets to Apechain.
    
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
        logger.info(f"Processing market {market.id} for deployment")
        
        try:
            # Deploy market to Apechain
            market_id, tx_hash = deploy_market_to_apechain(market)
            
            if market_id and tx_hash:
                # Successfully deployed with market ID
                logger.info(f"Successfully deployed market {market.id} with Apechain ID {market_id}")
                deployed += 1
            elif tx_hash:
                # Transaction sent but no market ID yet - will be picked up by tracker
                logger.info(f"Transaction sent for market {market.id}, waiting for confirmation")
                deployed += 1  # Still count as deployed since the tx was sent
            else:
                # Failed to deploy
                logger.error(f"Failed to deploy market {market.id}")
                failed += 1
            
            # Pause between deployments to avoid rate limiting
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Error deploying market {market.id}: {str(e)}")
            failed += 1
    
    return processed, deployed, failed

def check_pending_deployments() -> Tuple[int, int, int]:
    """
    Check markets with pending deployments to see if they have been mined.
    
    This function finds markets with a blockchain_tx but no apechain_market_id
    and attempts to retrieve the market ID from the blockchain.
    
    Returns:
        Tuple[int, int, int]: Count of (processed, updated, failed) markets
    """
    try:
        # Find markets with transactions but no market IDs
        markets = Market.query.filter(
            Market.blockchain_tx.isnot(None),
            Market.apechain_market_id.is_(None)
        ).all()
        
        logger.info(f"Found {len(markets)} markets with pending deployments")
        
        processed = 0
        updated = 0
        failed = 0
        
        for market in markets:
            processed += 1
            logger.info(f"Checking pending deployment for market {market.id}")
            
            try:
                # Get market ID from transaction
                apechain_id = get_deployed_market_id_from_tx(market.blockchain_tx)
                
                if apechain_id:
                    # Update market with Apechain market ID
                    market.apechain_market_id = apechain_id
                    market.status = "deployed"
                    db.session.commit()
                    
                    logger.info(f"Updated market {market.id} with Apechain ID {apechain_id}")
                    updated += 1
                else:
                    # Transaction still pending or failed
                    logger.warning(f"Transaction still pending for market {market.id}")
                    failed += 1
            except Exception as e:
                logger.error(f"Error checking pending deployment for market {market.id}: {str(e)}")
                failed += 1
        
        return processed, updated, failed
    except Exception as e:
        logger.error(f"Error checking pending deployments: {str(e)}")
        return 0, 0, 0

def main() -> int:
    """Main function to deploy approved markets."""
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
            
            # Step 2: Deploy approved markets
            processed, deployed, failed = deploy_markets(markets)
            
            # Step 3: Check any pending deployments
            check_processed, check_updated, check_failed = check_pending_deployments()
            
            # Step 4: Update pipeline run record
            if pipeline_run:
                total_processed = processed + check_processed
                total_deployed = deployed + check_updated
                total_failed = failed + check_failed
                
                status = "completed" if total_failed == 0 else "completed_with_errors"
                update_pipeline_run(
                    pipeline_run,
                    status=status,
                    markets_processed=total_processed,
                    markets_deployed=total_deployed,
                    markets_failed=total_failed
                )
            
            # Log results
            logger.info(f"Deployment results: {processed} processed, {deployed} deployed, {failed} failed")
            logger.info(f"Pending check results: {check_processed} processed, {check_updated} updated, {check_failed} failed")
            
            return 0
    except Exception as e:
        logger.error(f"Error in deployment script: {str(e)}")
        
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
    main()