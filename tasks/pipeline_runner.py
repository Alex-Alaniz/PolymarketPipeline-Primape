"""
Pipeline Runner

This module orchestrates the execution of the different pipeline tasks
in the correct sequence with proper error handling and reporting.
"""
import os
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Import task modules
from tasks.task1_fetch_and_post import run_task as run_task1
from tasks.task2_capture_approvals import run_task as run_task2
from tasks.task3_generate_banners import run_task as run_task3
from tasks.task4_deploy import run_task as run_task4

# Database functions
from utils.database import update_pipeline_run

# Setup logging
logger = logging.getLogger("pipeline_runner")

class PipelineRunner:
    """
    Orchestrates the execution of pipeline tasks.
    """
    
    def __init__(self, db=None, Market=None, ApprovalEvent=None, PipelineRun=None, run_id=None, approval_timeout_minutes=30):
        """
        Initialize the pipeline runner.
        
        Args:
            db: SQLAlchemy database instance (optional)
            Market: Market model class (optional)
            ApprovalEvent: ApprovalEvent model class (optional)
            PipelineRun: PipelineRun model class (optional)
            run_id (int): Pipeline run ID in the database (optional)
            approval_timeout_minutes (int): Timeout in minutes for approvals
        """
        self.db = db
        self.Market = Market
        self.ApprovalEvent = ApprovalEvent
        self.PipelineRun = PipelineRun
        self.run_id = run_id
        self.approval_timeout_minutes = approval_timeout_minutes
        
        # Pipeline stats
        self.stats = {
            "start_time": datetime.now().isoformat(),
            "end_time": None,
            "status": "running",
            "markets_processed": 0,
            "markets_approved": 0,
            "markets_rejected": 0,
            "markets_deployed": 0,
            "markets_failed": 0
        }
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete pipeline from start to finish.
        
        Returns:
            Dict[str, Any]: Pipeline execution statistics
        """
        try:
            logger.info("Starting Polymarket pipeline")
            
            # Task 1: Fetch market data and post to Slack
            logger.info("Running Task 1: Fetch market data and post to Slack")
            pending_markets = run_task1(self.db, self.Market, self.ApprovalEvent)
            self.stats["markets_processed"] = len(pending_markets)
            
            # Update database if available
            if self.db and self.PipelineRun and self.run_id:
                update_pipeline_run(
                    self.db,
                    self.PipelineRun,
                    self.run_id,
                    markets_processed=len(pending_markets)
                )
            
            if not pending_markets:
                logger.warning("No markets to process, pipeline ending early")
                self.stats["status"] = "completed"
                self.stats["end_time"] = datetime.now().isoformat()
                return self.stats
            
            # Task 2: Capture approvals from Slack
            logger.info("Running Task 2: Capture approvals from Slack")
            approved_markets, rejected_markets, timed_out_markets = run_task2(
                pending_markets, 
                self.db, 
                self.Market, 
                self.ApprovalEvent,
                self.approval_timeout_minutes
            )
            
            self.stats["markets_approved"] = len(approved_markets)
            self.stats["markets_rejected"] = len(rejected_markets) + len(timed_out_markets)
            
            # Update database if available
            if self.db and self.PipelineRun and self.run_id:
                update_pipeline_run(
                    self.db,
                    self.PipelineRun,
                    self.run_id,
                    markets_approved=len(approved_markets),
                    markets_rejected=len(rejected_markets) + len(timed_out_markets)
                )
            
            if not approved_markets:
                logger.warning("No approved markets, pipeline ending early")
                self.stats["status"] = "completed"
                self.stats["end_time"] = datetime.now().isoformat()
                return self.stats
            
            # Task 3: Generate banners and get final approvals
            logger.info("Running Task 3: Generate banners and get final approvals")
            final_approved_markets, final_rejected_markets, failed_banner_markets = run_task3(
                approved_markets,
                self.db,
                self.Market,
                self.ApprovalEvent,
                self.approval_timeout_minutes
            )
            
            # Adjust stats with final approval counts
            self.stats["markets_approved"] = len(final_approved_markets)
            self.stats["markets_rejected"] += len(final_rejected_markets)
            self.stats["markets_failed"] = len(failed_banner_markets)
            
            # Update database if available
            if self.db and self.PipelineRun and self.run_id:
                update_pipeline_run(
                    self.db,
                    self.PipelineRun,
                    self.run_id,
                    markets_approved=len(final_approved_markets),
                    markets_rejected=self.stats["markets_rejected"],
                    markets_failed=len(failed_banner_markets)
                )
            
            if not final_approved_markets:
                logger.warning("No markets with final approval, pipeline ending early")
                self.stats["status"] = "completed"
                self.stats["end_time"] = datetime.now().isoformat()
                return self.stats
            
            # Task 4: Deploy markets to ApeChain and frontend
            logger.info("Running Task 4: Deploy markets to ApeChain and frontend")
            deployed_markets, deploy_failed_markets = run_task4(
                final_approved_markets,
                self.db,
                self.Market
            )
            
            # Update stats with deployment counts
            self.stats["markets_deployed"] = len(deployed_markets)
            self.stats["markets_failed"] += len(deploy_failed_markets)
            
            # Update database if available
            if self.db and self.PipelineRun and self.run_id:
                update_pipeline_run(
                    self.db,
                    self.PipelineRun,
                    self.run_id,
                    markets_deployed=len(deployed_markets),
                    markets_failed=self.stats["markets_failed"]
                )
            
            # Pipeline completed successfully
            logger.info("Pipeline completed successfully")
            self.stats["status"] = "completed"
            self.stats["end_time"] = datetime.now().isoformat()
            
            # Final database update
            if self.db and self.PipelineRun and self.run_id:
                update_pipeline_run(
                    self.db,
                    self.PipelineRun,
                    self.run_id,
                    status="completed",
                    end_time=datetime.now()
                )
            
            return self.stats
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            self.stats["status"] = "failed"
            self.stats["error"] = str(e)
            self.stats["end_time"] = datetime.now().isoformat()
            
            # Update database if available
            if self.db and self.PipelineRun and self.run_id:
                update_pipeline_run(
                    self.db,
                    self.PipelineRun,
                    self.run_id,
                    status="failed",
                    error=str(e),
                    end_time=datetime.now()
                )
            
            return self.stats

# Standalone function for running the pipeline
def run_pipeline(db=None, Market=None, ApprovalEvent=None, PipelineRun=None, run_id=None, approval_timeout_minutes=30) -> Dict[str, Any]:
    """
    Run the complete Polymarket pipeline.
    
    Args:
        db: SQLAlchemy database instance (optional)
        Market: Market model class (optional)
        ApprovalEvent: ApprovalEvent model class (optional)
        PipelineRun: PipelineRun model class (optional)
        run_id (int): Pipeline run ID in the database (optional)
        approval_timeout_minutes (int): Timeout in minutes for approvals
        
    Returns:
        Dict[str, Any]: Pipeline execution statistics
    """
    runner = PipelineRunner(db, Market, ApprovalEvent, PipelineRun, run_id, approval_timeout_minutes)
    return runner.run()

# For standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stats = run_pipeline()
    print(json.dumps(stats, indent=2))