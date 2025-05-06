#!/usr/bin/env python3
"""
Clean Environment for Pipeline Testing

This script provides a clean slate for testing the pipeline by:
1. Resetting the database (dropping and recreating all tables)
2. Cleaning the Slack channel (removing all messages)

Use this script before running end-to-end tests of the pipeline.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('clean_environment')

def run_db_reset():
    """Run the database reset script."""
    logger.info("Starting database reset...")
    
    try:
        import reset_db_clean
        result = reset_db_clean.main()
        
        if result == 0:
            logger.info("Database reset completed successfully")
            return True
        else:
            logger.error("Database reset failed with exit code {}".format(result))
            return False
    
    except Exception as e:
        logger.error(f"Error running database reset: {str(e)}")
        return False

def run_slack_cleanup():
    """Run the Slack channel cleanup script."""
    logger.info("Starting Slack channel cleanup...")
    
    try:
        import clean_slack_channel
        result = clean_slack_channel.main()
        
        if result == 0:
            logger.info("Slack channel cleanup completed successfully")
            return True
        else:
            logger.error("Slack channel cleanup failed with exit code {}".format(result))
            return False
    
    except Exception as e:
        logger.error(f"Error running Slack cleanup: {str(e)}")
        return False

def main():
    """Main function to run environment cleaning."""
    logger.info("=== Starting Environment Cleanup ===")
    
    # Step 1: Reset the database
    db_success = run_db_reset()
    
    # Step 2: Clean the Slack channel
    slack_success = run_slack_cleanup()
    
    # Report results
    if db_success and slack_success:
        logger.info("Environment cleanup completed successfully")
        return 0
    elif not db_success and not slack_success:
        logger.error("Both database reset and Slack cleanup failed")
        return 3
    elif not db_success:
        logger.error("Database reset failed, but Slack cleanup succeeded")
        return 1
    else:
        logger.error("Database reset succeeded, but Slack cleanup failed")
        return 2

if __name__ == "__main__":
    sys.exit(main())