#!/usr/bin/env python3

"""
Polymarket Pipeline

This script implements the complete pipeline for Polymarket data, from
fetching markets to deployment on ApeChain. It coordinates the various
steps in the pipeline and provides status reporting.

Steps in the pipeline:
1. Fetch active markets from Polymarket API (filter_active_markets.py)
2. Post markets to Slack for approval (fetch_active_markets_with_tracker.py)
3. Check for market approvals in Slack (check_market_approvals.py)
4. Generate banner images for approved markets (TODO)
5. Post banners to Slack for approval (TODO)
6. Check for banner approvals in Slack (check_image_approvals.py)
7. Deploy approved markets to ApeChain (TODO)
8. Update database with deployment status (TODO)
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import sqlalchemy as sa
from models import db, Market, ProcessedMarket, PipelineRun
from filter_active_markets import fetch_markets, filter_active_markets
from fetch_active_markets_with_tracker import post_new_markets, filter_new_markets
from check_market_approvals import check_market_approvals

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pipeline")

class PolymarketPipeline:
    """
    Polymarket Pipeline Orchestrator
    
    This class orchestrates the various steps in the Polymarket pipeline
    and tracks pipeline status and statistics.
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
            "new_markets": 0,
            "markets_posted": 0,
            "markets_approved": 0,
            "markets_rejected": 0,
            "images_generated": 0,
            "images_posted": 0,
            "images_approved": 0,
            "images_rejected": 0,
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
            run.markets_failed = self.stats.get("images_rejected", 0)
            run.markets_deployed = self.stats.get("markets_deployed", 0)
            
            # Save changes
            db.session.commit()
            logger.info(f"Updated PipelineRun record {self.db_run_id}")
            
        except Exception as e:
            logger.error(f"Error updating PipelineRun record: {str(e)}")
    
    def fetch_and_filter_markets(self):
        """
        Fetch markets from Polymarket API and filter active ones.
        
        Returns:
            list: Filtered market data
        """
        logger.info("Fetching markets from Polymarket API")
        markets = fetch_markets()
        
        if not markets:
            logger.error("Failed to fetch markets from API")
            return []
            
        self.update_stats(markets_fetched=len(markets))
        logger.info(f"Fetched {len(markets)} markets from API")
        
        # Filter active markets
        filtered_markets = filter_active_markets(markets)
        
        self.update_stats(markets_filtered=len(filtered_markets))
        logger.info(f"Filtered to {len(filtered_markets)} active markets")
        
        # Check category distribution
        categories = {}
        for market in filtered_markets:
            category = market.get("fetched_category", "general")
            categories[category] = categories.get(category, 0) + 1
        
        logger.info("Market category distribution:")
        for category, count in categories.items():
            logger.info(f"  - {category}: {count} markets")
            
        return filtered_markets
    
    def post_markets_for_approval(self, markets):
        """
        Post new markets to Slack for approval.
        
        Args:
            markets: List of filtered market data
        
        Returns:
            int: Number of markets posted
        """
        logger.info("Filtering new markets")
        new_markets = filter_new_markets(markets)
        
        self.update_stats(new_markets=len(new_markets))
        logger.info(f"Found {len(new_markets)} new markets")
        
        if not new_markets:
            return 0
            
        # Post markets to Slack
        logger.info("Posting new markets to Slack for approval")
        posted_markets = post_new_markets(new_markets)
        
        self.update_stats(markets_posted=len(posted_markets))
        logger.info(f"Posted {len(posted_markets)} markets to Slack")
        
        return len(posted_markets)
    
    def check_approvals(self):
        """
        Check for market approvals in Slack.
        
        Returns:
            tuple: (pending, approved, rejected) counts
        """
        logger.info("Checking for market approvals in Slack")
        pending, approved, rejected = check_market_approvals()
        
        self.update_stats(
            markets_approved=self.stats.get("markets_approved", 0) + approved,
            markets_rejected=self.stats.get("markets_rejected", 0) + rejected
        )
        
        logger.info(f"Approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return (pending, approved, rejected)
    
    def run(self) -> int:
        """
        Run the complete pipeline.
        
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        logger.info("Starting Polymarket pipeline")
        
        try:
            # Fetch and filter markets
            markets = self.fetch_and_filter_markets()
            
            if not markets:
                logger.error("No markets to process")
                self.update_run_record(status="completed", error="No markets to process")
                return 1
            
            # Post markets for approval
            posted = self.post_markets_for_approval(markets)
            
            # Check for approvals
            self.check_approvals()
            
            # TODO: Generate banner images
            
            # TODO: Post banners for approval
            
            # TODO: Check for banner approvals
            
            # TODO: Deploy approved markets
            
            # Update final statistics
            self.update_run_record(status="completed")
            
            # Log completion time
            end_time = datetime.now()
            duration = (end_time - self.start_time).total_seconds()
            logger.info(f"Pipeline completed in {duration:.2f} seconds")
            
            # Log final stats
            logger.info("Final pipeline statistics:")
            for key, value in self.stats.items():
                logger.info(f"  - {key}: {value}")
            
            return 0
            
        except Exception as e:
            logger.error(f"Pipeline failed with exception: {str(e)}")
            self.update_run_record(status="failed", error=str(e))
            return 1


def main():
    """
    Main function to run the pipeline.
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        # Create run record
        run = PipelineRun(
            start_time=datetime.now(),
            status="running"
        )
        db.session.add(run)
        db.session.commit()
        
        # Run pipeline
        pipeline = PolymarketPipeline(db_run_id=run.id)
        exit_code = pipeline.run()
        
        # Update final status
        run.end_time = datetime.now()
        run.status = "completed" if exit_code == 0 else "failed"
        db.session.commit()
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())