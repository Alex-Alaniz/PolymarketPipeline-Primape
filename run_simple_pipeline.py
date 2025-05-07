#!/usr/bin/env python3

"""
Run Simple Pipeline

This script runs the simplified pipeline for production testing.
It's designed to be manually executed when needed.
"""

import os
import logging
import argparse
from datetime import datetime

from flask import Flask
from simple_pipeline import run_simple_pipeline
from check_pending_approvals import check_market_approvals
from models import db, PipelineRun

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("pipeline_runner")

# Import Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

def run_full_pipeline():
    """
    Run all steps of the simplified pipeline.
    """
    with app.app_context():
        logger.info("Starting full pipeline run")
        
        # Record pipeline run
        pipeline_run = PipelineRun(
            start_time=datetime.utcnow(),
            status="running"
        )
        db.session.add(pipeline_run)
        db.session.commit()
        
        try:
            # Step 1: Fetch, categorize, and post markets
            fetched, categorized, posted = run_simple_pipeline()
            logger.info(f"Pipeline results: {fetched} fetched, {categorized} categorized, {posted} posted")
            
            # Step 2: Check for approvals
            pending, approved, rejected = check_market_approvals()
            logger.info(f"Approval results: {pending} pending, {approved} approved, {rejected} rejected")
            
            # Update pipeline run record
            pipeline_run.status = "completed"
            pipeline_run.end_time = datetime.utcnow()
            pipeline_run.markets_processed = fetched
            pipeline_run.markets_posted = posted
            db.session.commit()
            
            return True
        except Exception as e:
            logger.error(f"Error in pipeline: {str(e)}")
            pipeline_run.status = "failed"
            pipeline_run.end_time = datetime.utcnow()
            pipeline_run.error = str(e)
            db.session.commit()
            return False

def run_fetch_only():
    """
    Run only the market fetching and posting part of the pipeline.
    """
    with app.app_context():
        logger.info("Starting fetch-only pipeline run")
        fetched, categorized, posted = run_simple_pipeline()
        logger.info(f"Pipeline results: {fetched} fetched, {categorized} categorized, {posted} posted")
        return fetched > 0 and posted > 0

def run_approval_only():
    """
    Run only the approval checking part of the pipeline.
    """
    with app.app_context():
        logger.info("Starting approval-only pipeline run")
        pending, approved, rejected = check_market_approvals()
        logger.info(f"Approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return True

def main():
    """
    Main function to run the pipeline.
    """
    parser = argparse.ArgumentParser(description="Run simple prediction market pipeline")
    parser.add_argument(
        "--mode", 
        choices=["full", "fetch", "approve"], 
        default="full",
        help="Pipeline mode to run (full, fetch-only, or approve-only)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "full":
        result = run_full_pipeline()
    elif args.mode == "fetch":
        result = run_fetch_only()
    elif args.mode == "approve":
        result = run_approval_only()
    else:
        logger.error(f"Invalid mode: {args.mode}")
        return 1
    
    return 0 if result else 1

if __name__ == "__main__":
    exit(main())