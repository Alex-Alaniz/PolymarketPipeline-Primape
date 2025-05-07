"""
Reset Database and Clean Environment

This script performs a complete reset of the system by:
1. Dropping and recreating all tables
2. Resetting auto-increment sequences to 1
3. Creating a fresh PipelineRun with ID 1
4. Attempting to clean Slack messages (may fail for older messages)

Use this as a single command to prepare for a fresh test run.
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
    Reset the database completely.
    
    This function:
    1. Drops all tables
    2. Recreates all tables
    3. Resets sequences
    4. Creates a single PipelineRun with ID 1
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Import within function to avoid circular dependencies
        from main import app
        from models import db, ProcessedMarket, Market, PendingMarket, ApprovalEvent, ApprovalLog, PipelineRun
        from sqlalchemy import text
        
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
            except Exception as e:
                logger.warning(f"Error querying current state: {e}")
            
            # Step 1: Drop all tables
            logger.info("Step 1: Dropping all database tables...")
            db.drop_all()
            
            # Step 2: Re-create all tables
            logger.info("Step 2: Recreating all database tables...")
            db.create_all()
            
            # Step 3: Create a single PipelineRun with ID 1
            logger.info("Step 3: Creating initial PipelineRun record...")
            
            # First check if the sequences exist and reset them
            logger.info("Checking and resetting sequences...")
            try:
                # Get all sequences in the public schema
                seq_query = text("""
                SELECT 
                    sequence_name 
                FROM 
                    information_schema.sequences 
                WHERE 
                    sequence_schema = 'public'
                """)
                
                result = db.session.execute(seq_query)
                sequences = [row[0] for row in result]
                
                if sequences:
                    logger.info(f"Found {len(sequences)} sequences to reset:")
                    for sequence in sequences:
                        logger.info(f"  - {sequence}")
                        reset_query = text(f"ALTER SEQUENCE {sequence} RESTART WITH 1")
                        db.session.execute(reset_query)
                    
                    logger.info("All sequences reset to 1")
                else:
                    logger.info("No sequences found to reset")
            except Exception as e:
                logger.warning(f"Error resetting sequences: {e}")
            
            # Create a fresh initial PipelineRun
            try:
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
                
                # Verify the ID
                logger.info(f"Created initial PipelineRun with ID: {new_run.id}")
            except Exception as e:
                logger.error(f"Error creating initial PipelineRun: {e}")
                return False
            
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
            
            return True
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def clean_slack_channel(max_messages=50):
    """
    Attempt to clean recent messages from the Slack channel.
    Note: This may fail for messages older than 24 hours or posted by other users.
    
    Args:
        max_messages: Maximum number of messages to clean
        
    Returns:
        bool: True if operation completed (even with some failures), False on critical error
    """
    try:
        from utils.slack import slack_client, SLACK_CHANNEL_ID
        
        if not slack_client or not SLACK_CHANNEL_ID:
            logger.error("Slack client not initialized - check environment variables")
            return False
        
        # Get channel history
        response = slack_client.conversations_history(
            channel=SLACK_CHANNEL_ID,
            limit=max_messages
        )
        
        if not response.get('ok'):
            logger.error(f"Failed to get channel history: {response.get('error')}")
            return False
            
        messages = response.get('messages', [])
        logger.info(f"Found {len(messages)} messages to clean")
        
        # Delete each message
        deleted_count = 0
        for message in messages:
            try:
                result = slack_client.chat_delete(
                    channel=SLACK_CHANNEL_ID,
                    ts=message['ts']
                )
                
                if result.get('ok'):
                    deleted_count += 1
                    logger.info(f"Deleted message {message['ts']}")
                else:
                    logger.warning(f"Failed to delete message {message['ts']}: {result.get('error')}")
                    
            except Exception as e:
                logger.error(f"Error deleting message: {str(e)}")
        
        logger.info(f"Successfully cleaned {deleted_count} messages from Slack channel")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning Slack channel: {str(e)}")
        return False

def main():
    """Main function to run all reset and cleaning operations."""
    logger.info("Starting complete system reset...")
    
    # Step 1: Reset database
    logger.info("Step 1: Resetting database...")
    db_success = reset_database()
    
    # Step 2: Clean Slack
    logger.info("Step 2: Cleaning Slack channel...")
    slack_success = clean_slack_channel()
    
    # Report results
    if db_success:
        logger.info("✅ Database reset completed successfully!")
        logger.info("The database is now completely reset with fresh tables and sequences.")
        logger.info("A single PipelineRun record with ID 1 has been created.")
    else:
        logger.error("❌ Database reset failed.")
    
    if slack_success:
        logger.info("✅ Slack cleaning completed (some messages may remain).")
    else:
        logger.error("❌ Slack cleaning failed.")
    
    if db_success:
        logger.info("The system is ready for testing with real data.")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())