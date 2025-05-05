#!/usr/bin/env python3

"""
Polymarket Pipeline

This script automates the process of extracting Polymarket data, facilitating approval via
Slack/Discord, and deploying markets to ApeChain.

The pipeline follows these steps:
1. Extract Polymarket data using filter_active_markets.py
2. Post markets to Slack for approval
3. Process approvals using check_market_approvals.py
4. Deploy approved markets to ApeChain
5. Generate summary reports and logs
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import or_

from models import db, Market, PipelineRun, ProcessedMarket
from filter_active_markets import fetch_markets, filter_active_markets
from fetch_active_markets_with_tracker import filter_new_markets, post_new_markets
from check_market_approvals import check_market_approvals
from utils.apechain import deploy_market_to_apechain

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("pipeline")

class PolymarketPipeline:
    """Main pipeline for processing Polymarket data."""
    
    def __init__(self, db_run_id=None):
        """
        Initialize the pipeline.
        
        Args:
            db_run_id (int, optional): Database run ID for tracking in the database
        """
        self.db_run_id = db_run_id
        self.stats = {
            "markets_processed": 0,
            "markets_posted": 0,
            "markets_approved": 0,
            "markets_rejected": 0,
            "markets_deployed": 0,
            "markets_failed": 0
        }
    
    def run(self):
        """
        Run the pipeline.
        
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        logger.info("Starting Polymarket pipeline")
        
        # Import Flask app to get application context
        from main import app
        
        try:
            # Step 1: Extract Polymarket data
            logger.info("Step 1: Extracting Polymarket data")
            raw_markets = fetch_markets(limit=100)
            
            if not raw_markets:
                logger.error("Failed to fetch market data from Polymarket API")
                raise Exception("No market data available from API")
                
            active_markets = filter_active_markets(raw_markets)
            self.stats["markets_processed"] = len(active_markets)
            
            if not active_markets:
                logger.error("No active markets found after filtering")
                raise Exception("No active markets available")
            
            logger.info(f"Found {len(active_markets)} active markets from Polymarket")
            
            # Use application context for database operations
            with app.app_context():
                # Step 2: Post markets for approval in Slack
                logger.info("Step 2: Posting markets for approval")
                new_markets = filter_new_markets(active_markets)
                
                if not new_markets:
                    logger.info("No new markets to post for approval")
                else:
                    posted_markets = post_new_markets(new_markets, max_to_post=5)
                    self.stats["markets_posted"] = len(posted_markets)
                    logger.info(f"Posted {len(posted_markets)} markets for approval")
                
                # Step 3: Check for market approvals
                logger.info("Step 3: Checking market approvals")
                pending, approved, rejected = check_market_approvals()
                self.stats["markets_approved"] = approved
                self.stats["markets_rejected"] = rejected
                logger.info(f"Approval status: {approved} approved, {rejected} rejected, {pending} pending")
                
                # Step 4: Deploy approved markets to Apechain
                if approved > 0:
                    logger.info("Step 4: Deploying approved markets to Apechain")
                    self._deploy_markets_to_apechain()
                else:
                    logger.info("Step 4: No markets to deploy")
                
                # Update database run record if available
                self._update_db_run()
            
            # Step 5: Post summary report
            self._post_summary()
            
            logger.info("Pipeline completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            return 1
    
    def _update_db_run(self):
        """
        Update the pipeline run record in the database.
        """
        if not self.db_run_id:
            return
            
        try:
            pipeline_run = PipelineRun.query.get(self.db_run_id)
            if pipeline_run:
                pipeline_run.markets_processed = self.stats["markets_processed"]
                pipeline_run.markets_approved = self.stats["markets_approved"]
                pipeline_run.markets_rejected = self.stats["markets_rejected"]
                pipeline_run.markets_failed = self.stats["markets_failed"]
                pipeline_run.markets_deployed = self.stats["markets_deployed"]
                db.session.commit()
                logger.info(f"Updated pipeline run record #{self.db_run_id}")
        except Exception as e:
            logger.error(f"Failed to update pipeline run record: {str(e)}")
    
    def _deploy_markets_to_apechain(self):
        """
        Deploy approved markets to Apechain smart contract.
        """
        # Query for markets that are approved but not yet deployed to Apechain
        approved_markets = Market.query.filter(
            Market.status == "new",
            Market.apechain_market_id.is_(None)
        ).all()
        
        logger.info(f"Found {len(approved_markets)} approved markets ready for deployment")
        
        deployed_count = 0
        failed_count = 0
        
        for market in approved_markets:
            logger.info(f"Deploying market: {market.id} - {market.question}")
            
            # Parse options from JSON string
            try:
                options = json.loads(market.options) if isinstance(market.options, str) else market.options
            except:
                options = ["Yes", "No"]  # Default to binary market if options can't be parsed
                
            # Calculate duration based on expiry
            if market.expiry:
                now = int(datetime.utcnow().timestamp())
                duration_seconds = max(1, market.expiry - now)  # Ensure at least 1 second
                duration_days = int(duration_seconds / (24 * 60 * 60)) + 1  # Round up to days
            else:
                duration_days = 30  # Default 30 days if no expiry
                
            # Deploy to Apechain
            success, market_id, error = deploy_market_to_apechain(
                question=market.question,
                options=options,
                duration_days=duration_days
            )
            
            if success and market_id:
                # Update market with Apechain ID and status
                market.apechain_market_id = market_id
                market.status = "deployed"
                market.updated_at = datetime.utcnow()
                deployed_count += 1
                logger.info(f"Successfully deployed market to Apechain: {market_id}")
            else:
                # Update market with failure status
                market.status = "failed"
                market.updated_at = datetime.utcnow()
                failed_count += 1
                logger.error(f"Failed to deploy market: {error}")
                
        # Commit all updates
        db.session.commit()
        
        # Update stats
        self.stats["markets_deployed"] = deployed_count
        self.stats["markets_failed"] = failed_count
        
        logger.info(f"Deployment results: {deployed_count} successful, {failed_count} failed")
    
    def _post_summary(self):
        """
        Post summary to logging output.
        """
        logger.info("\n=== PIPELINE SUMMARY ===")
        logger.info(f"Markets processed:   {self.stats['markets_processed']}")
        logger.info(f"New markets posted:  {self.stats['markets_posted']}")
        logger.info(f"Markets approved:    {self.stats['markets_approved']}")
        logger.info(f"Markets rejected:    {self.stats['markets_rejected']}")
        logger.info(f"Markets deployed:    {self.stats['markets_deployed']}")
        logger.info(f"Failed deployments:  {self.stats['markets_failed']}")
        logger.info("======================\n")

# Run the pipeline directly if executed as a script
if __name__ == "__main__":
    pipeline = PolymarketPipeline()
    exit_code = pipeline.run()
    sys.exit(exit_code)
