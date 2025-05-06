#!/usr/bin/env python3

"""
Test script to verify automatic reactions on Slack messages.
"""

import sys
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_slack_reactions")

# Import messaging module
from utils.messaging import post_market_for_approval, post_message_to_slack, add_reaction, get_message_reactions

def test_auto_reactions():
    """Test that reactions are automatically added when posting messages."""
    logger.info("Testing automatic reactions on Slack messages...")
    
    # Create a test market
    test_market = {
        "id": "test_market_id",
        "conditionId": "test_condition_id",
        "question": "Test Market Question?",
        "endDate": datetime.now().isoformat(),
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/champions-league-winner-2025-F-QYbKsrHt_E.jpg",
        "icon": "https://polymarket-upload.s3.us-east-2.amazonaws.com/champions-league-winner-2025-F-QYbKsrHt_E.jpg",
        "is_multiple_option": True,
        "outcomes": json.dumps(["Option 1", "Option 2", "Option 3"]),
        "original_market_ids": ["id1", "id2", "id3"],
        "event_category": "Test Category"
    }
    
    # Post the market for approval
    logger.info("Posting test market for approval...")
    message_id = post_market_for_approval(test_market)
    
    if not message_id:
        logger.error("Failed to post test market to Slack")
        return False
    
    logger.info(f"Posted test market to Slack with message ID: {message_id}")
    
    # Check if reactions were added
    logger.info("Checking for reactions...")
    reactions = get_message_reactions(message_id)
    
    if not reactions:
        logger.warning("No reactions found on test message")
        return False
    
    # Check for expected reactions
    found_check = False
    found_x = False
    
    for reaction in reactions:
        if reaction.get("name") == "white_check_mark":
            found_check = True
            logger.info("Found ✅ reaction")
        
        if reaction.get("name") == "x":
            found_x = True
            logger.info("Found ❌ reaction")
    
    if found_check and found_x:
        logger.info("Success! Both approval and rejection reactions were found")
        return True
    else:
        logger.warning(f"Missing reactions: check: {found_check}, x: {found_x}")
        return False

def main():
    """Main test function."""
    success = test_auto_reactions()
    
    if success:
        logger.info("✅ Test passed: Automatic reactions are working")
        return 0
    else:
        logger.error("❌ Test failed: Automatic reactions are not working")
        return 1

if __name__ == "__main__":
    sys.exit(main())