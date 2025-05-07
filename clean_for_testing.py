"""
Clean Database and Slack for Fresh Testing

This script:
1. Cleans the database (removes all records from relevant tables)
2. Cleans the Slack channel (removes recent messages)
3. Resets pipeline stats

Use this before running pipeline tests with real data.
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add local path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def clean_database():
    """
    Clean the database by removing all records from relevant tables.
    """
    try:
        # Import within function to avoid circular dependencies
        from main import app
        from models import db, ProcessedMarket, Market, PendingMarket, ApprovalEvent, ApprovalLog, PipelineRun
        
        with app.app_context():
            # Get counts before cleaning
            processed_count = ProcessedMarket.query.count()
            market_count = Market.query.count()
            pending_count = PendingMarket.query.count()
            approval_count = ApprovalEvent.query.count()
            approval_log_count = ApprovalLog.query.count()
            run_count = PipelineRun.query.count()
            
            logger.info(f"Current database state:")
            logger.info(f"  - ProcessedMarket: {processed_count} records")
            logger.info(f"  - Market: {market_count} records")
            logger.info(f"  - PendingMarket: {pending_count} records")
            logger.info(f"  - ApprovalEvent: {approval_count} records")
            logger.info(f"  - ApprovalLog: {approval_log_count} records")
            logger.info(f"  - PipelineRun: {run_count} records")
            
            # Delete records from each table
            ApprovalEvent.query.delete()
            ApprovalLog.query.delete()
            PendingMarket.query.delete()
            Market.query.delete()
            ProcessedMarket.query.delete()
            
            # Don't delete pipeline runs, just add a new one with clean stats
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
            
            # Verify cleaning
            processed_count_after = ProcessedMarket.query.count()
            market_count_after = Market.query.count()
            pending_count_after = PendingMarket.query.count()
            approval_count_after = ApprovalEvent.query.count()
            approval_log_count_after = ApprovalLog.query.count()
            run_count_after = PipelineRun.query.count()
            
            logger.info(f"Database after cleaning:")
            logger.info(f"  - ProcessedMarket: {processed_count_after} records")
            logger.info(f"  - Market: {market_count_after} records")
            logger.info(f"  - PendingMarket: {pending_count_after} records")
            logger.info(f"  - ApprovalEvent: {approval_count_after} records")
            logger.info(f"  - ApprovalLog: {approval_log_count_after} records")
            logger.info(f"  - PipelineRun: {run_count_after} records")
            logger.info(f"  - Added new clean PipelineRun record")
            
            return True
    except Exception as e:
        logger.error(f"Error cleaning database: {str(e)}")
        return False

def clean_slack_channel(max_messages=50):
    """
    Clean recent messages from the Slack channel.
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
    """Main function to run all cleaning operations."""
    # Step 1: Clean database
    logger.info("Step 1: Cleaning database...")
    db_success = clean_database()
    
    # Step 2: Clean Slack
    logger.info("Step 2: Cleaning Slack channel...")
    slack_success = clean_slack_channel()
    
    # Report results
    if db_success and slack_success:
        logger.info("✅ All cleaning operations completed successfully!")
        logger.info("The system is ready for testing with real data.")
        return 0
    else:
        logger.error("❌ Some cleaning operations failed.")
        logger.error("  - Database: %s", "SUCCESS" if db_success else "FAILED")
        logger.error("  - Slack: %s", "SUCCESS" if slack_success else "FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())