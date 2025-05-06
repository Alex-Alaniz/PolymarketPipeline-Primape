#!/usr/bin/env python3
"""
Clean Environment Script

This script provides a convenient interface for cleaning the environment
before running the pipeline:
1. Reset database (removing old image generation tables)
2. Clean Slack channel
3. Test message formatting

Usage: python clean_script.py [options]
Options:
  --db-only       Only reset the database
  --slack-only    Only clean the Slack channel
  --test-format   Test message formatting without cleaning
  --check-format  Check existing message format
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('clean_script')

def reset_database():
    """Reset the database, removing image generation tables."""
    try:
        import reset_db_clean
        logger.info("Resetting database...")
        result = reset_db_clean.main()
        
        if result == 0:
            logger.info("Database reset completed successfully.")
            return True
        else:
            logger.error(f"Database reset failed with error code {result}.")
            return False
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def clean_slack():
    """Clean the Slack channel."""
    try:
        import clean_slack_channel
        logger.info("Cleaning Slack channel...")
        result = clean_slack_channel.main()
        
        if result == 0:
            logger.info("Slack channel cleaned successfully.")
            return True
        else:
            logger.error(f"Slack channel cleaning failed with error code {result}.")
            return False
    except Exception as e:
        logger.error(f"Error cleaning Slack channel: {str(e)}")
        return False

def test_message_format():
    """Test message formatting without posting to Slack."""
    try:
        logger.info("Testing message format...")
        
        # Create test market data
        test_market = {
            "question": "Will Bitcoin reach $100k before the end of 2025?",
            "category": "crypto",
            "options": ["Yes", "No"]
        }
        
        # Import the market message formatter
        from post_unposted_pending_markets import format_market_message
        from utils.deployment_formatter import format_deployment_message
        
        # Create a mock PendingMarket object
        class MockPendingMarket:
            def __init__(self, question, category, options):
                self.question = question
                self.category = category.lower()
                self.options = [{"value": opt} for opt in options]
        
        # Format market approval message
        mock_market = MockPendingMarket(
            test_market["question"],
            test_market["category"],
            test_market["options"]
        )
        market_text, market_blocks = format_market_message(mock_market)
        
        # Format deployment approval message
        deploy_text, deploy_blocks = format_deployment_message(
            market_id="0x1234567890abcdef",
            question=test_market["question"],
            category=test_market["category"].capitalize(),
            market_type="Binary Market (Yes/No)",
            options=test_market["options"],
            expiry="2025-12-31 12:00:00 UTC",
            banner_uri="https://example.com/banner.jpg"
        )
        
        # Print the results
        print("\n=== Market Approval Message Text ===")
        print(market_text)
        
        print("\n=== Market Approval Blocks ===")
        import json
        print(json.dumps(market_blocks, indent=2))
        
        print("\n=== Deployment Approval Message Text ===")
        print(deploy_text)
        
        print("\n=== Deployment Approval Blocks ===")
        print(json.dumps(deploy_blocks, indent=2))
        
        logger.info("Message format tests completed successfully.")
        return True
    except Exception as e:
        logger.error(f"Error testing message format: {str(e)}")
        return False

def check_format():
    """Check existing message format without modifying anything."""
    try:
        import check_slack_message_format
        logger.info("Checking message format...")
        result = check_slack_message_format.main()
        
        if result == 0:
            logger.info("Message format check completed successfully.")
            return True
        else:
            logger.error(f"Message format check failed with error code {result}.")
            return False
    except Exception as e:
        logger.error(f"Error checking message format: {str(e)}")
        return False

def main():
    """Main function to run the clean script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Clean environment script.')
    parser.add_argument('--db-only', action='store_true', help='Only reset the database')
    parser.add_argument('--slack-only', action='store_true', help='Only clean the Slack channel')
    parser.add_argument('--test-format', action='store_true', help='Test message formatting without cleaning')
    parser.add_argument('--check-format', action='store_true', help='Check existing message format')
    args = parser.parse_args()
    
    # Print banner
    print("=" * 60)
    print("POLYMARKET PIPELINE ENVIRONMENT CLEANER")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    # If no specific option is given, do everything
    do_all = not (args.db_only or args.slack_only or args.test_format or args.check_format)
    
    # Check if user wants to proceed with full cleanup
    if do_all:
        confirm = input("This will reset the database and clean the Slack channel. Proceed? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled.")
            return 0
    
    # Perform requested operations
    if args.db_only or do_all:
        if not reset_database():
            print("Database reset failed.")
            return 1
    
    if args.slack_only or do_all:
        if not clean_slack():
            print("Slack channel cleaning failed.")
            return 1
    
    if args.test_format or do_all:
        if not test_message_format():
            print("Message format testing failed.")
            return 1
    
    if args.check_format:
        if not check_format():
            print("Message format checking failed.")
            return 1
    
    # Print completion message
    print("-" * 60)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())