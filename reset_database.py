"""
Reset Database Completely

This script completely resets the database by:
1. Dropping and recreating all tables
2. Resetting auto-increment counters to start from 1
3. Setting up a fresh environment for testing

Use this for a true database reset.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database():
    """
    Completely reset the database by dropping and recreating all tables.
    This ensures auto-increment IDs start from 1 again.
    """
    try:
        # Import within function to avoid circular dependencies
        from main import app
        from models import db, ProcessedMarket, Market, PendingMarket, ApprovalEvent, ApprovalLog, PipelineRun
        
        with app.app_context():
            # First report current state
            logger.info("Current database state before reset:")
            try:
                processed_count = ProcessedMarket.query.count()
                market_count = Market.query.count()
                pending_count = PendingMarket.query.count()
                approval_count = ApprovalEvent.query.count()
                approval_log_count = ApprovalLog.query.count()
                run_count = PipelineRun.query.count()
                
                logger.info(f"  - ProcessedMarket: {processed_count} records")
                logger.info(f"  - Market: {market_count} records")
                logger.info(f"  - PendingMarket: {pending_count} records")
                logger.info(f"  - ApprovalEvent: {approval_count} records")
                logger.info(f"  - ApprovalLog: {approval_log_count} records")
                logger.info(f"  - PipelineRun: {run_count} records")
                
                # Get the max ID from PipelineRun to show the current counter
                max_id_result = db.session.execute("SELECT MAX(id) FROM pipeline_runs").fetchone()
                max_id = max_id_result[0] if max_id_result and max_id_result[0] else 0
                logger.info(f"  - Max PipelineRun ID: {max_id}")
            except Exception as e:
                logger.warning(f"Error querying current state: {e}")
            
            # Drop all tables
            logger.info("Dropping all database tables...")
            db.drop_all()
            
            # Re-create all tables
            logger.info("Recreating all database tables...")
            db.create_all()
            
            # Create a fresh initial PipelineRun with ID 1
            logger.info("Creating initial PipelineRun record...")
            new_run = PipelineRun(
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                status="SUCCESS",
                markets_processed=0,
                markets_approved=0,
                markets_rejected=0,
                markets_failed=0,
                markets_deployed=0
            )
            db.session.add(new_run)
            
            # Commit changes
            db.session.commit()
            
            # Verify reset
            processed_count_after = ProcessedMarket.query.count()
            market_count_after = Market.query.count()
            pending_count_after = PendingMarket.query.count()
            approval_count_after = ApprovalEvent.query.count()
            approval_log_count_after = ApprovalLog.query.count()
            run_count_after = PipelineRun.query.count()
            
            logger.info("Database after reset:")
            logger.info(f"  - ProcessedMarket: {processed_count_after} records")
            logger.info(f"  - Market: {market_count_after} records")
            logger.info(f"  - PendingMarket: {pending_count_after} records")
            logger.info(f"  - ApprovalEvent: {approval_count_after} records")
            logger.info(f"  - ApprovalLog: {approval_log_count_after} records")
            logger.info(f"  - PipelineRun: {run_count_after} records")
            
            # Verify PipelineRun ID
            first_run = PipelineRun.query.first()
            if first_run:
                logger.info(f"  - First PipelineRun ID: {first_run.id}")
            
            return True
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def main():
    """Main function to reset database."""
    logger.info("Starting database reset process...")
    success = reset_database()
    
    if success:
        logger.info("✅ Database reset completed successfully!")
        logger.info("Auto-increment counters have been reset to 1.")
        logger.info("The system is ready for testing with real data.")
        return 0
    else:
        logger.error("❌ Database reset failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())