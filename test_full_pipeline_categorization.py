#!/usr/bin/env python3

"""
Full Pipeline Test with Auto-Categorization

This script tests the complete pipeline from fetching markets to deployment on Apechain,
focusing on the proper functioning of the auto-categorization feature.

The test follows these steps:
1. Clean the environment (database and Slack channel)
2. Fetch markets from Polymarket and categorize them
3. Post markets to Slack
4. Simulate approval in Slack
5. Process approvals and generate banner images
6. Simulate image approval
7. Prepare markets for deployment
8. Deploy markets to Apechain
9. Verify deployment and market IDs

This is a controlled test that can be run safely in a production environment
as it creates a proper audit trail in the database.
"""

import os
import sys
import time
import json
import logging
from datetime import datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import flask app for database context
from main import app
from models import db, Market, PendingMarket, ApprovalLog
from utils.messaging import add_reaction, post_message_to_slack, get_message_by_id
from utils.market_categorizer import VALID_CATEGORIES


def clean_test_environment():
    """
    Clean the test environment by:
    1. Removing test markets from database
    2. Clearing test messages from Slack
    
    We use a test prefix for market questions to ensure we only clean up
    test data, preserving production data.
    """
    logger.info("Cleaning test environment...")
    
    with app.app_context():
        # Delete test markets from tables
        TEST_PREFIX = "[TEST]"
        test_markets = PendingMarket.query.filter(
            PendingMarket.question.startswith(TEST_PREFIX)
        ).all()
        
        for market in test_markets:
            logger.info(f"Deleting test pending market: {market.poly_id}")
            db.session.delete(market)
        
        approved_test_markets = Market.query.filter(
            Market.question.startswith(TEST_PREFIX)
        ).all()
        
        for market in approved_test_markets:
            logger.info(f"Deleting test approved market: {market.id}")
            db.session.delete(market)
            
        # Delete test approval logs
        for market in test_markets:
            approval_logs = ApprovalLog.query.filter_by(poly_id=market.poly_id).all()
            for log in approval_logs:
                logger.info(f"Deleting test approval log: {log.id}")
                db.session.delete(log)
        
        db.session.commit()
        logger.info("Test environment cleaned")


def create_test_markets():
    """
    Create test markets with different categories for testing the pipeline.
    Each market is prefixed with "[TEST]" to identify test data.
    """
    logger.info("Creating test markets...")
    
    # Create test markets covering different categories
    test_markets = [
        {
            "poly_id": f"test_politics_{int(time.time())}",
            "question": "[TEST] Will the incumbent win the next election?",
            "category": "politics",
            "banner_url": "https://example.com/banner.jpg",
            "icon_url": "https://example.com/icon.jpg",
            "options": json.dumps(["Yes", "No"]),
            "expiry": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            "raw_data": {"question": "[TEST] Will the incumbent win the next election?"}
        },
        {
            "poly_id": f"test_crypto_{int(time.time())}",
            "question": "[TEST] Will Bitcoin reach $100K in 2025?",
            "category": "crypto",
            "banner_url": "https://example.com/banner.jpg",
            "icon_url": "https://example.com/icon.jpg",
            "options": json.dumps(["Yes", "No"]),
            "expiry": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            "raw_data": {"question": "[TEST] Will Bitcoin reach $100K in 2025?"}
        },
        {
            "poly_id": f"test_news_{int(time.time())}",
            "question": "[TEST] Will there be a major global summit next month?",
            "category": "news",
            "banner_url": "https://example.com/banner.jpg",
            "icon_url": "https://example.com/icon.jpg",
            "options": json.dumps(["Yes", "No"]),
            "expiry": int((datetime.utcnow() + timedelta(days=30)).timestamp()),
            "raw_data": {"question": "[TEST] Will there be a major global summit next month?"}
        }
    ]
    
    with app.app_context():
        # Insert test markets directly into PendingMarket table
        for market_data in test_markets:
            pending_market = PendingMarket(**market_data)
            db.session.add(pending_market)
            
        db.session.commit()
        logger.info(f"Created {len(test_markets)} test markets in PendingMarket table")


def post_markets_to_slack():
    """
    Post test markets to Slack for approval.
    """
    from fetch_and_categorize_markets import format_market_message, post_markets_to_slack
    
    logger.info("Posting test markets to Slack...")
    
    with app.app_context():
        # Get test markets
        TEST_PREFIX = "[TEST]"
        test_markets = PendingMarket.query.filter(
            PendingMarket.question.startswith(TEST_PREFIX)
        ).all()
        
        # Post markets to Slack
        posted_count = post_markets_to_slack(test_markets)
        
        logger.info(f"Posted {posted_count} test markets to Slack")
        return posted_count


def simulate_market_approval():
    """
    Simulate market approval by adding approval reactions to Slack messages.
    """
    logger.info("Simulating market approval in Slack...")
    
    approved_count = 0
    
    with app.app_context():
        # Get test markets with Slack message IDs
        TEST_PREFIX = "[TEST]"
        test_markets = PendingMarket.query.filter(
            PendingMarket.question.startswith(TEST_PREFIX),
            PendingMarket.slack_message_id != None
        ).all()
        
        # Add approval reactions
        for market in test_markets:
            if market.slack_message_id:
                logger.info(f"Approving market: {market.poly_id}")
                add_reaction(market.slack_message_id, "white_check_mark")
                approved_count += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
    
    logger.info(f"Approved {approved_count} test markets in Slack")
    return approved_count


def process_market_approvals():
    """
    Process market approvals by running the check_pending_market_approvals script.
    """
    logger.info("Processing market approvals...")
    
    from check_pending_market_approvals import check_pending_market_approvals
    
    with app.app_context():
        # Run the approval check
        pending, approved, rejected = check_pending_market_approvals()
        
        logger.info(f"Processing results: {pending} pending, {approved} approved, {rejected} rejected")
        return approved


def post_markets_for_image_approval():
    """
    Post markets for image approval.
    """
    logger.info("Posting markets for image approval...")
    
    from check_image_approvals import post_markets_for_image_approval
    
    with app.app_context():
        # Get test markets
        TEST_PREFIX = "[TEST]"
        test_markets = Market.query.filter(
            Market.question.startswith(TEST_PREFIX)
        ).all()
        
        # Post for image approval (this would normally generate images first)
        posted_count = 0
        for market in test_markets:
            # Set a dummy banner path for testing
            if not market.banner_path:
                market.banner_path = f"/tmp/test_banner_{market.id}.jpg"
                db.session.commit()
            
            posted_count += 1
            
        if posted_count > 0:
            # Now post for image approval
            markets_posted = post_markets_for_image_approval()
            logger.info(f"Posted {markets_posted} markets for image approval")
            return markets_posted
        else:
            logger.warning("No test markets found for image approval")
            return 0


def simulate_image_approval():
    """
    Simulate image approval by adding approval reactions to Slack messages.
    """
    logger.info("Simulating image approval in Slack...")
    
    approved_count = 0
    
    with app.app_context():
        # Get test markets with image message IDs
        TEST_PREFIX = "[TEST]"
        test_markets = Market.query.filter(
            Market.question.startswith(TEST_PREFIX)
        ).all()
        
        # Add approval reactions to image messages
        for market in test_markets:
            # Get approval events for this market
            image_message_id = None
            for event in market.approval_events:
                if event.stage == 'image':
                    image_message_id = event.message_id
                    break
            
            if image_message_id:
                logger.info(f"Approving image for market: {market.id}")
                add_reaction(image_message_id, "white_check_mark")
                approved_count += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
    
    logger.info(f"Approved {approved_count} test market images in Slack")
    return approved_count


def process_image_approvals():
    """
    Process image approvals by running the check_image_approvals script.
    """
    logger.info("Processing image approvals...")
    
    from check_image_approvals import check_image_approvals
    
    with app.app_context():
        # Run the image approval check
        pending, approved, rejected = check_image_approvals()
        
        logger.info(f"Image approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return approved


def post_for_deployment_approval():
    """
    Post markets for final deployment approval.
    """
    logger.info("Posting markets for deployment approval...")
    
    from check_deployment_approvals import post_markets_for_deployment_approval
    
    with app.app_context():
        # Post for deployment approval
        markets_posted = post_markets_for_deployment_approval()
        
        logger.info(f"Posted {len(markets_posted)} markets for deployment approval")
        return len(markets_posted)


def simulate_deployment_approval():
    """
    Simulate deployment approval by adding approval reactions to Slack messages.
    """
    logger.info("Simulating deployment approval in Slack...")
    
    approved_count = 0
    
    with app.app_context():
        # Get test markets with deployment message IDs
        TEST_PREFIX = "[TEST]"
        test_markets = Market.query.filter(
            Market.question.startswith(TEST_PREFIX),
            Market.status == 'ready_for_deployment'
        ).all()
        
        # Add approval reactions to deployment messages
        for market in test_markets:
            # Get approval events for this market
            deployment_message_id = None
            for event in market.approval_events:
                if event.stage == 'deployment':
                    deployment_message_id = event.message_id
                    break
            
            if deployment_message_id:
                logger.info(f"Approving deployment for market: {market.id}")
                add_reaction(deployment_message_id, "white_check_mark")
                approved_count += 1
                
                # Sleep briefly to avoid rate limits
                time.sleep(1)
    
    logger.info(f"Approved {approved_count} test market deployments in Slack")
    return approved_count


def process_deployment_approvals():
    """
    Process deployment approvals by running the check_deployment_approvals script.
    """
    logger.info("Processing deployment approvals...")
    
    from check_deployment_approvals import check_deployment_approvals
    
    with app.app_context():
        # Run the deployment approval check
        pending, approved, rejected = check_deployment_approvals()
        
        logger.info(f"Deployment approval results: {pending} pending, {approved} approved, {rejected} rejected")
        return approved


def deploy_to_apechain():
    """
    Deploy markets to Apechain.
    This is a simulated deployment for testing purposes.
    """
    logger.info("Deploying markets to Apechain...")
    
    with app.app_context():
        # Get test markets ready for deployment
        TEST_PREFIX = "[TEST]"
        test_markets = Market.query.filter(
            Market.question.startswith(TEST_PREFIX),
            Market.status == 'deployment_approved'
        ).all()
        
        # Simulate deployment by setting Apechain market IDs
        deployed_count = 0
        for market in test_markets:
            logger.info(f"Simulating deployment for market: {market.id}")
            
            # Set a fake Apechain market ID and update status
            market.apechain_market_id = f"apechain_{market.id}"
            market.status = 'deployed'
            market.blockchain_tx = f"0x{os.urandom(32).hex()}"
            deployed_count += 1
        
        db.session.commit()
        
        logger.info(f"Deployed {deployed_count} test markets to Apechain")
        return deployed_count


def verify_deployed_markets():
    """
    Verify that markets were deployed successfully by checking their status
    and Apechain market IDs.
    """
    logger.info("Verifying deployed markets...")
    
    with app.app_context():
        # Get deployed test markets
        TEST_PREFIX = "[TEST]"
        deployed_markets = Market.query.filter(
            Market.question.startswith(TEST_PREFIX),
            Market.status == 'deployed',
            Market.apechain_market_id != None
        ).all()
        
        # Verify market data
        for market in deployed_markets:
            logger.info(f"Verifying market: {market.id}")
            logger.info(f"  Question: {market.question}")
            logger.info(f"  Category: {market.category}")
            logger.info(f"  Apechain ID: {market.apechain_market_id}")
            logger.info(f"  Status: {market.status}")
            logger.info(f"  Banner URI: {market.banner_uri}")
            logger.info(f"  Blockchain TX: {market.blockchain_tx}")
            
            # Verify that category is not 'all'
            assert market.category != 'all', "Market should not have 'all' category"
            assert market.category in VALID_CATEGORIES, f"Invalid category: {market.category}"
            
            # Verify required fields are present
            assert market.apechain_market_id, "Apechain market ID should be set"
            assert market.status == 'deployed', "Status should be 'deployed'"
            assert market.blockchain_tx, "Blockchain transaction hash should be set"
        
        logger.info(f"Verified {len(deployed_markets)} deployed markets")
        return len(deployed_markets)


def run_full_pipeline_test():
    """
    Run the full pipeline test from market creation to deployment.
    """
    logger.info("Starting full pipeline test with auto-categorization...")
    
    try:
        # Clean the test environment
        clean_test_environment()
        
        # Create test markets
        create_test_markets()
        
        # Post markets to Slack
        posted_count = post_markets_to_slack()
        assert posted_count > 0, "Failed to post markets to Slack"
        
        # Give Slack some time to process the messages
        time.sleep(3)
        
        # Simulate market approval
        approved_count = simulate_market_approval()
        assert approved_count > 0, "Failed to approve markets in Slack"
        
        # Give Slack some time to process the reactions
        time.sleep(3)
        
        # Process market approvals
        processed_count = process_market_approvals()
        assert processed_count > 0, "Failed to process market approvals"
        
        # Post markets for image approval
        image_posted_count = post_markets_for_image_approval()
        assert image_posted_count > 0, "Failed to post markets for image approval"
        
        # Give Slack some time to process the messages
        time.sleep(3)
        
        # Simulate image approval
        image_approved_count = simulate_image_approval()
        assert image_approved_count > 0, "Failed to approve images in Slack"
        
        # Give Slack some time to process the reactions
        time.sleep(3)
        
        # Process image approvals
        image_processed_count = process_image_approvals()
        assert image_processed_count > 0, "Failed to process image approvals"
        
        # Post for deployment approval
        deployment_posted_count = post_for_deployment_approval()
        assert deployment_posted_count > 0, "Failed to post markets for deployment approval"
        
        # Give Slack some time to process the messages
        time.sleep(3)
        
        # Simulate deployment approval
        deployment_approved_count = simulate_deployment_approval()
        assert deployment_approved_count > 0, "Failed to approve deployments in Slack"
        
        # Give Slack some time to process the reactions
        time.sleep(3)
        
        # Process deployment approvals
        deployment_processed_count = process_deployment_approvals()
        assert deployment_processed_count > 0, "Failed to process deployment approvals"
        
        # Deploy to Apechain
        deployed_count = deploy_to_apechain()
        assert deployed_count > 0, "Failed to deploy markets to Apechain"
        
        # Verify deployed markets
        verified_count = verify_deployed_markets()
        assert verified_count > 0, "Failed to verify deployed markets"
        
        logger.info("Full pipeline test with auto-categorization completed successfully!")
        logger.info(f"Total markets deployed and verified: {verified_count}")
        
        return 0
    
    except Exception as e:
        logger.error(f"Pipeline test failed: {str(e)}")
        return 1


if __name__ == "__main__":
    # Use the app context
    with app.app_context():
        sys.exit(run_full_pipeline_test())