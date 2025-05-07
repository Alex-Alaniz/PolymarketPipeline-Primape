#!/usr/bin/env python3

"""
Polymarket Pipeline

This script implements the complete pipeline for Polymarket data, from
fetching markets to deployment on ApeChain. It coordinates the various
steps in the pipeline and provides status reporting.

Steps in the pipeline:
1. Fetch markets from Polymarket Gamma API (fetch_gamma_markets.py)
2. Transform markets with proper event detection (utils/transform_market_with_events.py)
3. Post pending markets to Slack for approval (post_unposted_pending_markets.py)
4. Check for market approvals in Slack (check_pending_market_approvals.py)
5. Generate banner images for approved markets
6. Post banners to Slack for approval
7. Check for banner approvals in Slack (check_image_approvals.py)
8. Final deployment approval and deploy to ApeChain (check_deployment_approvals.py)
9. Track market IDs after deployment (track_market_id_after_deployment.py)
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

import sqlalchemy as sa

from utils.batch_categorizer import batch_categorize_markets
from models import db, Market, ProcessedMarket, PipelineRun
from filter_active_markets import fetch_markets, filter_active_markets
from fetch_active_markets_with_tracker import post_new_markets, filter_new_markets
from check_market_approvals import check_market_approvals
from utils.market_transformer import MarketTransformer
from utils.option_image_fixer import apply_image_fixes, verify_option_images

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
    
    def get_run_count(self) -> int:
        """
        Get the count of previous successful pipeline runs.
        Used to vary parameters across runs to maximize market diversity.
        
        Returns:
            int: Number of previous runs (including current)
        """
        try:
            # Count previous successful runs
            run_count = PipelineRun.query.filter(
                PipelineRun.status.in_(["completed", "running"])
            ).count()
            
            # Add 1 for current run (starts at 0)
            return run_count
        except Exception as e:
            logger.error(f"Error getting run count: {str(e)}")
            return 0
            
    def fetch_and_filter_markets(self):
        """
        Fetch markets from Polymarket API and filter active ones.
        Then transform markets to combine related ones into multi-option markets.
        
        Returns:
            list: Filtered and transformed market data
        """
        # Use run_count to vary the fetch parameters
        run_count = self.get_run_count()
        logger.info(f"Starting pipeline run #{run_count}")
        
        logger.info(f"Fetching markets from Polymarket API (variant: {run_count})")
        markets = fetch_markets(variant=run_count)
        
        if not markets:
            logger.error("Failed to fetch markets from API")
            return []
            
        self.update_stats(markets_fetched=len(markets))
        logger.info(f"Fetched {len(markets)} markets from API")
        
        # Filter active markets
        filtered_markets = filter_active_markets(markets)
        
        self.update_stats(markets_filtered=len(filtered_markets))
        logger.info(f"Filtered to {len(filtered_markets)} active markets")
        
        # Check initial category distribution
        categories = {}
        for market in filtered_markets:
            # Use event_category when available, otherwise leave as "uncategorized"
            category = market.get("event_category", "uncategorized")
            categories[category] = categories.get(category, 0) + 1
        
        logger.info("Initial market category distribution:")
        for category, count in categories.items():
            logger.info(f"  - {category}: {count} markets")
        
        # Batch categorize markets using GPT-4o-mini
        logger.info("Categorizing markets with GPT-4o-mini")
        categorized_markets = batch_categorize_markets(filtered_markets)
        
        # Update markets with their AI categories
        for i, market in enumerate(filtered_markets):
            if i < len(categorized_markets):
                market["ai_category"] = categorized_markets[i].get("ai_category", "news")
                market["needs_manual_categorization"] = categorized_markets[i].get("needs_manual_categorization", False)
        
        # Check final category distribution after AI categorization
        categories = {}
        for market in filtered_markets:
            category = market.get("ai_category", "news")
            categories[category] = categories.get(category, 0) + 1
        
        logger.info("Final market category distribution after AI categorization:")
        for category, count in categories.items():
            logger.info(f"  - {category}: {count} markets")
        
        # Now transform markets to combine related ones into multi-option markets
        logger.info("Transforming markets to combine related ones")
        transformer = MarketTransformer()
        transformed_markets = transformer.transform_markets(filtered_markets)
        
        # Apply fixes to ensure each option has its own unique image
        logger.info("Applying option image fixes to ensure unique images for all options")
        transformed_markets = apply_image_fixes(transformed_markets)
        
        # Verify and log option images
        for market in transformed_markets:
            if market.get('is_multiple_option', False):
                verify_option_images(market)
        
        # Check how many multi-option markets were created
        multi_option_count = sum(1 for m in transformed_markets if m.get('is_multiple_option', False))
        logger.info(f"Created {multi_option_count} multi-option markets")
        
        # Log a few examples of multi-option markets
        logger.info("Examples of multi-option markets:")
        multi_option_examples = [m for m in transformed_markets if m.get('is_multiple_option', False)]
        for i, market in enumerate(multi_option_examples[:3]):  # Log up to 3 examples
            logger.info(f"Multi-option market {i+1}:")
            logger.info(f"  - Question: {market.get('question', 'Unknown')}")
            logger.info(f"  - ID: {market.get('id')}")
            outcomes_raw = market.get("outcomes", "[]")
            try:
                if isinstance(outcomes_raw, str):
                    import json
                    outcomes = json.loads(outcomes_raw)
                else:
                    outcomes = outcomes_raw
                logger.info(f"  - Options ({len(outcomes)}): {outcomes}")
            except Exception as e:
                logger.error(f"Error parsing outcomes: {str(e)}")
            
        logger.info(f"Original markets count: {len(filtered_markets)}, transformed markets count: {len(transformed_markets)}")
        return transformed_markets
    
    def post_markets_for_approval(self, markets):
        """
        Post new markets to Slack for approval.
        
        Args:
            markets: List of filtered market data
        
        Returns:
            int: Number of markets posted
        """
        # First, log which markets we have before filtering
        logger.info("Initial markets before filtering:")
        for i, market in enumerate(markets[:5]):  # Just log the first 5 to avoid too much output
            logger.info(f"Market {i+1}:")
            logger.info(f"  - Type: {'Multiple-option' if market.get('is_multiple_option') else 'Binary'}")
            logger.info(f"  - Question: {market.get('question', 'Unknown')}")
            if market.get('is_multiple_option'):
                logger.info(f"  - ID: {market.get('id')}")
                # Parse outcomes which come as a JSON string
                outcomes_raw = market.get("outcomes", "[]")
                outcomes = []
                try:
                    if isinstance(outcomes_raw, str):
                        import json
                        outcomes = json.loads(outcomes_raw)
                    else:
                        outcomes = outcomes_raw
                    logger.info(f"  - Options ({len(outcomes)}): {outcomes}")
                except Exception as e:
                    logger.error(f"Error parsing outcomes: {str(e)}")
        
        logger.info("Filtering new markets")
        new_markets = filter_new_markets(markets)
        
        # Log which markets we have after filtering
        logger.info("Markets after filtering:")
        for i, market in enumerate(new_markets[:5]):  # Just log the first 5 to avoid too much output
            logger.info(f"Market {i+1}:")
            logger.info(f"  - Type: {'Multiple-option' if market.get('is_multiple_option') else 'Binary'}")
            logger.info(f"  - Question: {market.get('question', 'Unknown')}")
            if market.get('is_multiple_option'):
                logger.info(f"  - ID: {market.get('id')}")
                # Parse outcomes which come as a JSON string
                outcomes_raw = market.get("outcomes", "[]")
                outcomes = []
                try:
                    if isinstance(outcomes_raw, str):
                        import json
                        outcomes = json.loads(outcomes_raw)
                    else:
                        outcomes = outcomes_raw
                    logger.info(f"  - Options ({len(outcomes)}): {outcomes}")
                except Exception as e:
                    logger.error(f"Error parsing outcomes: {str(e)}")
        
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
        
        # Import Flask app here to avoid circular imports
        from main import app
        
        # Use application context for database operations
        with app.app_context():
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
                
                # Note: Deployment to Apechain is now a separate step
                # It's not part of the main pipeline to allow for final QA
                # Run check_deployment_approvals.py manually to process deployments
                
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