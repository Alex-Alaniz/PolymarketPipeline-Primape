"""
Reset Database Sequences

This script resets the auto-increment sequences in PostgreSQL
to 1 for all tables, ensuring that new records start with ID 1.
"""

import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_sequences():
    """
    Reset all sequences in PostgreSQL to 1.
    """
    try:
        # Import within function to avoid circular dependencies
        from main import app
        from models import db, PipelineRun
        
        with app.app_context():
            # First, get a list of all tables and their sequences
            logger.info("Identifying sequences to reset...")
            
            # Get all sequences in the public schema
            query = """
            SELECT 
                sequence_name 
            FROM 
                information_schema.sequences 
            WHERE 
                sequence_schema = 'public'
            """
            
            result = db.session.execute(query)
            sequences = [row[0] for row in result]
            
            if not sequences:
                logger.info("No sequences found to reset.")
                return True
            
            logger.info(f"Found {len(sequences)} sequences to reset:")
            for sequence in sequences:
                logger.info(f"  - {sequence}")
            
            # Reset each sequence
            for sequence in sequences:
                logger.info(f"Resetting sequence: {sequence}")
                reset_query = f"ALTER SEQUENCE {sequence} RESTART WITH 1"
                db.session.execute(reset_query)
            
            # Commit the changes
            db.session.commit()
            
            # Create a test PipelineRun to verify reset
            from datetime import datetime
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
            
            # Verify the ID of the new PipelineRun
            logger.info(f"Created test PipelineRun with ID: {new_run.id}")
            
            return True
    except Exception as e:
        logger.error(f"Error resetting sequences: {str(e)}")
        return False

def main():
    """Main function to reset sequences."""
    logger.info("Starting sequence reset process...")
    success = reset_sequences()
    
    if success:
        logger.info("✅ Sequence reset completed successfully!")
        logger.info("Auto-increment counters have been reset to 1.")
        return 0
    else:
        logger.error("❌ Sequence reset failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())