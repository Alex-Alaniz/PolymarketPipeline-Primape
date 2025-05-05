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
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from sqlalchemy import or_

from models import db, Market, PipelineRun, ProcessedMarket
from filter_active_markets import fetch_markets, filter_active_markets
from fetch_active_markets_with_tracker import filter_new_markets, post_new_markets
from check_market_approvals import check_market_approvals

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
            
            # Update database run record if available
            self._update_db_run()
            
            # Step 4: Post summary report
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
