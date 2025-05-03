"""
Pipeline Runner

This module orchestrates the execution of the different pipeline tasks
in the correct sequence with proper error handling and reporting.
"""

import os
import sys
import json
import logging
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

# Import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.messaging import MessagingClient
from config import TMP_DIR

# Import tasks
from tasks.task1_fetch_and_post import run_task as run_task1
from tasks.task2_capture_approvals import run_task as run_task2
from tasks.task3_generate_banners import run_task as run_task3
from tasks.task4_deploy import run_task as run_task4

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
        
        # Initialize messaging client
        self.messaging_client = MessagingClient()
        
        # Create output directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
    
    def run(self) -> Dict[str, Any]:
        """
        Run the complete pipeline from start to finish.
        
        Returns:
            Dict[str, Any]: Pipeline execution statistics
        """
        logger.info("Starting pipeline execution")
        
        # Start timing
        pipeline_start_time = time.time()
        
        # Statistics
        stats = {
            "start_time": datetime.now(timezone.utc).isoformat(),
            "task1_success": False,
            "task2_success": False,
            "task3_success": False,
            "task4_success": False,
            "markets_processed": 0,
            "markets_approved": 0,
            "markets_rejected": 0,
            "markets_deployed": 0,
            "errors": [],
            "status": "running"
        }
        
        try:
            # Run Task 1: Fetch and post markets
            logger.info("Running Task 1: Fetch and post markets")
            markets, task1_stats = run_task1(self.messaging_client)
            
            if task1_stats["status"] == "success":
                stats["task1_success"] = True
                stats["markets_processed"] = task1_stats.get("markets_posted", 0)
                logger.info(f"Task 1 completed successfully: {stats['markets_processed']} markets posted")
                
                # Save task1 results to file
                task1_file = os.path.join(TMP_DIR, f"task1_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(task1_file, 'w') as f:
                    json.dump(task1_stats, f, indent=2)
            else:
                stats["errors"].append(f"Task 1 failed: {', '.join(task1_stats.get('errors', []))}")
                logger.error(f"Task 1 failed: {', '.join(task1_stats.get('errors', []))}")
                stats["status"] = "failed_task1"
                return stats
            
            # Run Task 2: Capture approvals
            logger.info("Running Task 2: Capture approvals")
            approved_markets, task2_stats = run_task2(self.messaging_client, task1_stats)
            
            if task2_stats["status"] == "success":
                stats["task2_success"] = True
                stats["markets_approved"] = task2_stats.get("markets_approved", 0)
                stats["markets_rejected"] = task2_stats.get("markets_rejected", 0)
                logger.info(f"Task 2 completed successfully: {stats['markets_approved']} markets approved")
                
                # Save task2 results to file
                task2_file = os.path.join(TMP_DIR, f"task2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(task2_file, 'w') as f:
                    json.dump(task2_stats, f, indent=2)
            else:
                stats["errors"].append(f"Task 2 failed: {', '.join(task2_stats.get('errors', []))}")
                logger.error(f"Task 2 failed: {', '.join(task2_stats.get('errors', []))}")
                stats["status"] = "failed_task2"
                return stats
            
            # Run Task 3: Generate banners
            logger.info("Running Task 3: Generate banners")
            markets_with_banners, task3_stats = run_task3(self.messaging_client, task2_stats)
            
            if task3_stats["status"] == "success":
                stats["task3_success"] = True
                banners_generated = task3_stats.get("banners_generated", 0)
                banners_posted = task3_stats.get("banners_posted", 0)
                logger.info(f"Task 3 completed successfully: {banners_generated} banners generated, {banners_posted} posted")
                
                # Save task3 results to file
                task3_file = os.path.join(TMP_DIR, f"task3_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(task3_file, 'w') as f:
                    json.dump(task3_stats, f, indent=2)
            else:
                stats["errors"].append(f"Task 3 failed: {', '.join(task3_stats.get('errors', []))}")
                logger.error(f"Task 3 failed: {', '.join(task3_stats.get('errors', []))}")
                stats["status"] = "failed_task3"
                return stats
            
            # Run Task 4: Deploy markets
            logger.info("Running Task 4: Deploy markets")
            deployed_markets, task4_stats = run_task4(self.messaging_client, task3_stats)
            
            if task4_stats["status"] == "success":
                stats["task4_success"] = True
                stats["markets_deployed"] = task4_stats.get("markets_deployed", 0)
                logger.info(f"Task 4 completed successfully: {stats['markets_deployed']} markets deployed")
                
                # Save task4 results to file
                task4_file = os.path.join(TMP_DIR, f"task4_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
                with open(task4_file, 'w') as f:
                    json.dump(task4_stats, f, indent=2)
            else:
                stats["errors"].append(f"Task 4 failed: {', '.join(task4_stats.get('errors', []))}")
                logger.error(f"Task 4 failed: {', '.join(task4_stats.get('errors', []))}")
                stats["status"] = "failed_task4"
                return stats
            
            # Save final pipeline results
            pipeline_file = os.path.join(TMP_DIR, f"pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            with open(pipeline_file, 'w') as f:
                json.dump(stats, f, indent=2)
            
            # Calculate pipeline duration
            stats["duration"] = time.time() - pipeline_start_time
            
            # Set final status
            stats["status"] = "success"
            
            logger.info("Pipeline execution completed successfully")
            
            # Update database record if available
            if self.db and self.PipelineRun and self.run_id:
                try:
                    pipeline_run = self.PipelineRun.query.get(self.run_id)
                    if pipeline_run:
                        pipeline_run.end_time = datetime.now()
                        pipeline_run.status = "completed"
                        pipeline_run.markets_processed = stats["markets_processed"]
                        pipeline_run.markets_approved = stats["markets_approved"]
                        pipeline_run.markets_rejected = stats["markets_rejected"]
                        pipeline_run.markets_deployed = stats["markets_deployed"]
                        self.db.session.commit()
                except Exception as e:
                    logger.error(f"Error updating pipeline run record: {str(e)}")
            
            return stats
            
        except Exception as e:
            # Handle any unexpected errors
            error_msg = f"Unexpected error in pipeline execution: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            stats["status"] = "failed"
            stats["duration"] = time.time() - pipeline_start_time
            
            # Update database record if available
            if self.db and self.PipelineRun and self.run_id:
                try:
                    pipeline_run = self.PipelineRun.query.get(self.run_id)
                    if pipeline_run:
                        pipeline_run.end_time = datetime.now()
                        pipeline_run.status = "failed"
                        pipeline_run.error = error_msg
                        self.db.session.commit()
                except Exception as db_error:
                    logger.error(f"Error updating pipeline run record: {str(db_error)}")
            
            return stats

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
    # Create the pipeline runner
    runner = PipelineRunner(
        db=db,
        Market=Market,
        ApprovalEvent=ApprovalEvent,
        PipelineRun=PipelineRun,
        run_id=run_id,
        approval_timeout_minutes=approval_timeout_minutes
    )
    
    # Run the pipeline
    return runner.run()