#!/usr/bin/env python3

"""
Polymarket Pipeline with Auto-Categorization

This script implements the complete pipeline for Polymarket data, now with
automatic categorization of markets using GPT-4o-mini before posting to Slack.

Steps in the pipeline:
1. Fetch active markets from Polymarket API
2. Filter active, non-expired markets with banner/icon URLs
3. Categorize markets using GPT-4o-mini
4. Store in pending_markets table with assigned categories
5. Post to Slack with category badges for approval
6. Check for approvals/rejections in Slack
7. Move approved markets to the Market table
8. Generate images for approved markets (if needed)
9. Deploy to Apechain blockchain
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from models import db, Market, PendingMarket, ProcessedMarket, PipelineRun, ApprovalLog
from fetch_and_categorize_markets import (
    fetch_markets, 
    filter_active_non_expired_markets,
    filter_new_markets,
    categorize_markets,
    store_pending_markets,
    post_markets_to_slack
)
from check_pending_market_approvals import check_pending_market_approvals
from utils.market_transformer import MarketTransformer
from utils.option_image_fixer import apply_image_fixes, verify_option_images

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pipeline")

class NewPolymarketPipeline:
    """
    Polymarket Pipeline Orchestrator with Auto-Categorization
    
    This class orchestrates the various steps in the Polymarket pipeline
    with the new auto-categorization flow and tracks pipeline status.
    """
    
    def __init__(self, db_run_id: Optional[int] = None):
        """
        Initialize the pipeline.
        
        Args:
            db_run_id: Optional ID of an existing PipelineRun database record
        """
        self.start_time = datetime.now()
        self.db_run_id = db_run_id
        
        # Initialize pipeline statistics
        self.stats = {
            "markets_fetched": 0,
            "markets_filtered": 0,
            "markets_categorized": 0,
            "new_markets": 0,
            "markets_posted": 0,
            "markets_approved": 0,
            "markets_rejected": 0,
            "markets_deployed": 0
        }
        
    def update_stats(self, **kwargs):
        """
        Update pipeline statistics.
        
        Args:
            **kwargs: Statistics to update
        """
        for key, value in kwargs.items():
            if key in self.stats:
                self.stats[key] = value
    
    def update_run_record(self, status: Optional[str] = None, error: Optional[str] = None):
        """
        Update the PipelineRun database record.
        
        Args:
            status: Optional new status value
            error: Optional error message
        """
        if not self.db_run_id:
            return
            
        try:
            # Get the record
            run = PipelineRun.query.get(self.db_run_id)
            
            if not run:
                logger.warning(f"PipelineRun record {self.db_run_id} not found")
                return
                
            # Update fields
            if status:
                run.status = status
                
            if error:
                run.error = error
                
            # Update statistics
            run.markets_processed = self.stats.get("markets_fetched", 0)
            run.markets_approved = self.stats.get("markets_approved", 0)
            run.markets_rejected = self.stats.get("markets_rejected", 0)
            run.markets_deployed = self.stats.get("markets_deployed", 0)
            
            # Save changes
            db.session.commit()
            logger.info(f"Updated PipelineRun record {self.db_run_id}")
            
        except Exception as e:
            logger.error(f"Error updating PipelineRun record: {str(e)}")
    
    def fetch_and_categorize_markets(self):
        """
        Fetch markets from Polymarket API, filter them, and categorize them.
        
        Returns:
            int: Number of markets successfully categorized and posted to Slack
        """
        try:
            # 1. Fetch markets
            markets = fetch_markets(page=1, page_size=100)
            self.update_stats(markets_fetched=len(markets))
            logger.info(f"Fetched {len(markets)} markets from Polymarket API")
            
            # 2. Filter active, non-expired markets
            filtered_markets = filter_active_non_expired_markets(markets)
            self.update_stats(markets_filtered=len(filtered_markets))
            logger.info(f"Filtered down to {len(filtered_markets)} active, non-expired markets")
            
            # 3. Filter new markets (not already in database)
            new_markets = filter_new_markets(filtered_markets)
            self.update_stats(new_markets=len(new_markets))
            logger.info(f"Found {len(new_markets)} new markets not in database")
            
            if not new_markets:
                logger.info("No new markets to process")
                return 0
                
            # 4. Categorize markets with GPT-4o-mini
            categorized_markets = categorize_markets(new_markets)
            self.update_stats(markets_categorized=len(categorized_markets))
            logger.info(f"Categorized {len(categorized_markets)} markets with GPT-4o-mini")
            
            # 5. Store in pending_markets table
            pending_markets = store_pending_markets(categorized_markets)
            logger.info(f"Stored {len(pending_markets)} markets in pending_markets table")
            
            # 6. Post to Slack with category badges
            posted_count = post_markets_to_slack(pending_markets, max_to_post=20)
            self.update_stats(markets_posted=posted_count)
            logger.info(f"Posted {posted_count} markets to Slack for approval")
            
            return posted_count
            
        except Exception as e:
            logger.error(f"Error in fetch_and_categorize_markets: {str(e)}")
            return 0
    
    def check_market_approvals(self):
        """
        Check for market approvals and rejections in Slack.
        
        Returns:
            Tuple[int, int, int]: Count of (pending, approved, rejected) markets
        """
        try:
            # Check pending market approvals
            pending, approved, rejected = check_pending_market_approvals()
            
            # Update stats
            self.update_stats(
                markets_approved=self.stats.get("markets_approved", 0) + approved,
                markets_rejected=self.stats.get("markets_rejected", 0) + rejected
            )
            
            logger.info(f"Approval check results: {pending} pending, {approved} approved, {rejected} rejected")
            return (pending, approved, rejected)
            
        except Exception as e:
            logger.error(f"Error checking market approvals: {str(e)}")
            return (0, 0, 0)
    
    def count_pending_markets(self) -> int:
        """
        Count the number of pending markets in the database.
        
        Returns:
            int: Number of pending markets
        """
        try:
            count = PendingMarket.query.count()
            logger.info(f"Found {count} pending markets in database")
            return count
        except Exception as e:
            logger.error(f"Error counting pending markets: {str(e)}")
            return 0
            
    def count_approved_markets(self) -> int:
        """
        Count the number of approved markets ready for deployment.
        
        Returns:
            int: Number of approved markets
        """
        try:
            # Markets that have been approved but not yet deployed to blockchain
            count = Market.query.filter(
                Market.status == "new",
                Market.apechain_market_id.is_(None)
            ).count()
            logger.info(f"Found {count} approved markets ready for deployment")
            return count
        except Exception as e:
            logger.error(f"Error counting approved markets: {str(e)}")
            return 0
    
    def run_pipeline(self, force_fetch: bool = False):
        """
        Run the complete pipeline.
        
        Args:
            force_fetch: Force fetching new markets even if pending markets exist
            
        Returns:
            bool: True if pipeline completed successfully, False otherwise
        """
        try:
            logger.info("Starting Polymarket pipeline run")
            self.update_run_record(status="running")
            
            # Step 1: Check if we need to fetch new markets
            pending_count = self.count_pending_markets()
            
            if pending_count == 0 or force_fetch:
                # Fetch and categorize new markets
                logger.info("Fetching and categorizing new markets")
                posted_count = self.fetch_and_categorize_markets()
                
                if posted_count == 0 and not force_fetch:
                    logger.info("No new markets posted and force_fetch not enabled, skipping approval check")
                else:
                    # Step 2: Check for market approvals
                    logger.info("Checking for market approvals")
                    pending, approved, rejected = self.check_market_approvals()
            else:
                # Just check for approvals of existing pending markets
                logger.info(f"Found {pending_count} pending markets, skipping fetch and categorize")
                logger.info("Checking for market approvals")
                pending, approved, rejected = self.check_market_approvals()
            
            # Step 3: Log final statistics
            logger.info("Pipeline run completed")
            logger.info(f"Final statistics: {self.stats}")
            
            # Update run record
            self.update_run_record(status="completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in pipeline run: {str(e)}")
            self.update_run_record(status="failed", error=str(e))
            return False
            

def create_run_record() -> Optional[int]:
    """
    Create a new PipelineRun database record.
    
    Returns:
        Optional[int]: ID of the new record, or None if creation failed
    """
    try:
        run = PipelineRun(
            start_time=datetime.utcnow(),
            status="initializing"
        )
        db.session.add(run)
        db.session.commit()
        
        logger.info(f"Created PipelineRun record with ID {run.id}")
        return run.id
        
    except Exception as e:
        logger.error(f"Error creating PipelineRun record: {str(e)}")
        return None

def main():
    """
    Main function to run the Polymarket pipeline.
    """
    # Import Flask app to get application context
    from main import app
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Run the Polymarket pipeline")
    parser.add_argument("--force-fetch", action="store_true", help="Force fetching new markets")
    args = parser.parse_args()
    
    # Use application context for database operations
    with app.app_context():
        # Create database run record
        run_id = create_run_record()
        
        # Initialize and run pipeline
        pipeline = NewPolymarketPipeline(run_id)
        success = pipeline.run_pipeline(force_fetch=args.force_fetch)
        
        # Return status code
        return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())