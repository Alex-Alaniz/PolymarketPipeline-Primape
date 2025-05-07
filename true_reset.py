"""
True Database Reset

This script performs a complete reset of the database with just one step:
1. Directly execute SQL to drop all tables and recreate them
2. This ensures sequences are reset and IDs start from 1

Use this for a true clean slate.
"""

import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def complete_reset():
    """
    Execute a complete reset by directly using SQL.
    """
    try:
        # Import within function to avoid circular dependencies
        from main import app
        from models import db, PipelineRun
        from sqlalchemy import text
        
        with app.app_context():
            # Get database name first for verification
            conn = db.engine.connect()
            db_name = db.engine.url.database
            logger.info(f"Connected to database: {db_name}")
            
            # Drop all tables in one SQL statement
            logger.info("Dropping all tables...")
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
            conn.commit()
            
            # Recreate all tables
            logger.info("Recreating all tables...")
            db.create_all()
            
            # Create an initial PipelineRun
            logger.info("Creating initial PipelineRun with ID 1...")
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
            db.session.commit()
            
            # Verify the reset worked
            runs = PipelineRun.query.all()
            if runs and len(runs) == 1 and runs[0].id == 1:
                logger.info(f"✅ Successfully created PipelineRun with ID: {runs[0].id}")
                return True
            else:
                logger.error(f"Verification failed. PipelineRun ID is not 1.")
                return False
    
    except Exception as e:
        logger.error(f"Error during complete reset: {str(e)}")
        return False

def main():
    """Main function to run the reset."""
    logger.info("Starting true database reset...")
    success = complete_reset()
    
    if success:
        logger.info("✅ Database has been completely reset!")
        logger.info("All tables recreated and sequences reset.")
        logger.info("PipelineRun ID is now starting from 1.")
        return 0
    else:
        logger.error("❌ Reset failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())