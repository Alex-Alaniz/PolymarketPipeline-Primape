#!/usr/bin/env python3
"""
Daily Pipeline Runner

This script runs the production pipeline and logs the execution.
It's designed to be called by a cron job for daily execution.
"""

import sys
import logging
import datetime
from pathlib import Path

# Configure logging to a dated log file
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"pipeline_{datetime.datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("daily_pipeline")

def main():
    """Run the production pipeline."""
    logger.info("Starting daily pipeline run")
    
    try:
        # Import and run the actual pipeline
        from run_pipeline_with_events import run_pipeline
        
        # Run with standard settings (fetch up to 20 markets, post up to 10 to Slack)
        result = run_pipeline(max_markets=20)
        
        if result == 0:
            logger.info("Pipeline completed successfully")
        else:
            logger.error(f"Pipeline failed with exit code {result}")
        
        return result
    
    except Exception as e:
        logger.exception(f"Unhandled exception in pipeline: {str(e)}")
        return 1
    
    finally:
        logger.info("Daily pipeline run completed")

if __name__ == "__main__":
    sys.exit(main())