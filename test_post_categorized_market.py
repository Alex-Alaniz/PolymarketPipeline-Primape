#!/usr/bin/env python3
"""
Test posting a categorized market to Slack.

This script creates a test pending market with a category,
formats it, and posts it to Slack to verify that the formatting
and categorization work correctly together.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import models and utils
from models import db, PendingMarket
from utils.market_categorizer import categorize_market
from post_unposted_pending_markets import format_market_message
from utils.messaging import post_formatted_message_to_slack, add_reaction_to_message

# Initialize app and database
db.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test market questions with expected categories
TEST_MARKETS = [
    {
        "question": "Will Bitcoin reach $100k before the end of 2025?",
        "expected_category": "crypto",
        "options": ["Yes", "No"]
    },
    {
        "question": "Will Kamala Harris win the Democratic nomination?",
        "expected_category": "politics",
        "options": ["Yes", "No"]
    },
    {
        "question": "Will Apple release a new iPhone model in September?",
        "expected_category": "tech",
        "options": ["Yes", "No"]
    },
    {
        "question": "Will Manchester City win the Premier League?",
        "expected_category": "sports",
        "options": ["Yes", "No"]
    }
]

def create_test_market(market_data):
    """Create a test market for a given question and category."""
    question = market_data["question"]
    expected_category = market_data["expected_category"]
    options = market_data["options"]
    
    # Run the categorizer to test it
    actual_category, needs_manual = categorize_market(question)
    
    logger.info(f"Question: {question}")
    logger.info(f"Expected category: {expected_category}")
    logger.info(f"Actual category from GPT-4o-mini: {actual_category}")
    logger.info(f"Needs manual review: {needs_manual}")
    
    # Create options structure
    option_list = [{"id": str(i+1), "value": option} for i, option in enumerate(options)]
    
    # Create test market with actual category from GPT-4o-mini
    test_market = PendingMarket(
        poly_id=f"test-market-{datetime.now().timestamp()}",
        question=question,
        category=actual_category,  # Use the category from GPT-4o-mini
        banner_url="https://example.com/banner.jpg",
        icon_url="https://example.com/icon.jpg",
        options=option_list,
        option_images={option: f"https://example.com/{option.lower()}.jpg" for option in options},
        expiry=int((datetime.now() + timedelta(days=30)).timestamp() * 1000),
        raw_data={"source": "test"},
        needs_manual_categorization=needs_manual,
        posted=False,
        fetched_at=datetime.utcnow()
    )
    return test_market

def test_post_to_slack(market_data):
    """Test categorizing and posting to Slack."""
    # Create a test market
    test_market = create_test_market(market_data)
    
    # Format the message
    message_text, blocks = format_market_message(test_market)
    
    # Print the formatted message
    print("\n=== Formatted Message Text ===")
    print(message_text)
    
    # Post to Slack
    message_id = post_formatted_message_to_slack(message_text, blocks=blocks)
    
    if not message_id:
        logger.error("Failed to post test message to Slack")
        return False
    
    # Add approval/rejection reactions
    add_reaction_to_message(message_id, "white_check_mark")
    add_reaction_to_message(message_id, "x")
    
    logger.info(f"Posted categorized market to Slack with ID {message_id}")
    return True

def main():
    """Main function for testing."""
    with app.app_context():
        print("Testing market categorization and Slack posting...")
        
        # Choose a random test market
        import random
        market_data = random.choice(TEST_MARKETS)
        
        # Post the test market to Slack
        success = test_post_to_slack(market_data)
        
        if success:
            print("\nSuccessfully posted categorized market to Slack!")
            return 0
        else:
            print("\nFailed to post categorized market to Slack.")
            return 1

if __name__ == "__main__":
    sys.exit(main())