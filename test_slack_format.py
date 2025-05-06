#!/usr/bin/env python3
"""
Test Slack Message Format

This script creates a test pending market and formats a message for it
using the same function that will be used in the pipeline, to verify
that the formatting matches the required format.
"""

import json
import logging
from datetime import datetime, timedelta

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///test_format.db"

# Import models and utils
from models import db, PendingMarket
from post_unposted_pending_markets import format_market_message
from utils.messaging import post_formatted_message_to_slack, add_reaction_to_message

# Initialize app and database
db.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_market():
    """Create a test market for format testing."""
    test_market = PendingMarket(
        poly_id="test-market-123",
        question="Will Bitcoin reach $100k before the end of 2025?",
        category="crypto",  # Test with a specific category
        banner_url="https://example.com/banner.jpg",
        icon_url="https://example.com/icon.jpg",
        options=[
            {"id": "1", "value": "Yes"},
            {"id": "2", "value": "No"}
        ],
        option_images={
            "Yes": "https://example.com/yes.jpg",
            "No": "https://example.com/no.jpg"
        },
        expiry=int((datetime.now() + timedelta(days=30)).timestamp() * 1000),
        raw_data={"source": "test"},
        needs_manual_categorization=False,
        posted=False,
        fetched_at=datetime.utcnow()
    )
    return test_market

def test_format_only():
    """Test only the formatting, don't post to Slack."""
    # Create a test market
    test_market = create_test_market()
    
    # Format the message
    message_text, blocks = format_market_message(test_market)
    
    # Print the formatted message
    print("\n=== Formatted Message Text ===")
    print(message_text)
    
    print("\n=== Formatted Message Blocks ===")
    print(json.dumps(blocks, indent=2))
    
    return True

def test_post_to_slack():
    """Test formatting and posting to Slack."""
    # Create a test market
    test_market = create_test_market()
    
    # Format the message
    message_text, blocks = format_market_message(test_market)
    
    # Post to Slack
    message_id = post_formatted_message_to_slack(message_text, blocks=blocks)
    
    if not message_id:
        logger.error("Failed to post test message to Slack")
        return False
    
    # Add approval/rejection reactions
    add_reaction_to_message(message_id, "white_check_mark")
    add_reaction_to_message(message_id, "x")
    
    logger.info(f"Posted test message to Slack with ID {message_id}")
    return True

def main():
    """Main function for testing."""
    print("Testing Slack message formatting...")
    
    # Test only formatting without posting
    format_success = test_format_only()
    if not format_success:
        logger.error("Format test failed")
        return False
    
    # Ask if user wants to post to Slack
    post_to_slack = input("\nPost test message to Slack? (y/n): ").lower() == 'y'
    
    if post_to_slack:
        post_success = test_post_to_slack()
        if not post_success:
            logger.error("Slack posting test failed")
            return False
        logger.info("Test message posted to Slack successfully")
    
    return True

if __name__ == "__main__":
    with app.app_context():
        main()