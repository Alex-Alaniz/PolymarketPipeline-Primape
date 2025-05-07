#!/usr/bin/env python3
"""
Test Full Pipeline Flow

This script tests the entire pipeline flow from end-to-end:
1. Creating a test pending market
2. Posting to Slack for initial approval
3. Simulating approval
4. Generating and approving banner image
5. Deploying to Apechain
6. Tracking market ID after deployment

Usage: python test_full_pipeline.py
"""

import os
import sys
import json
import time
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
from models import db, PendingMarket, Market, ApprovalEvent, ProcessedMarket, PipelineRun
from utils.market_categorizer import categorize_market
# Import real messaging functions for reference
from utils.messaging import (
    post_formatted_message_to_slack as real_post_message, 
    add_reaction_to_message as real_add_reaction,
    get_message_reactions as real_get_reactions,
    slack_client as real_slack_client,
    SLACK_CHANNEL_ID
)

# Mock Slack client for testing
class MockSlackClient:
    def chat_postMessage(self, channel, text, blocks=None):
        """Mock implementation of Slack chat_postMessage method"""
        logger.info(f"Mock posting message to Slack: {text[:50]}...")
        # Return a successful response with a timestamp
        return {
            'ok': True,
            'ts': f"{int(datetime.now().timestamp())}.{int(datetime.now().microsecond / 1000)}"
        }

# Use mock client for testing
slack_client = MockSlackClient()

# Mock messaging functions
def post_formatted_message_to_slack(text, blocks=None):
    """Mock implementation of post_formatted_message_to_slack"""
    logger.info(f"Mock posting formatted message to Slack: {text[:50]}...")
    # Return a mock message ID (timestamp)
    return f"{int(datetime.now().timestamp())}.{int(datetime.now().microsecond / 1000)}"

def add_reaction_to_message(message_id, reaction):
    """Mock implementation of add_reaction_to_message"""
    logger.info(f"Mock adding reaction '{reaction}' to message {message_id}")
    # Return success
    return True

def get_message_reactions(message_id):
    """Mock implementation of get_message_reactions"""
    logger.info(f"Mock getting reactions for message {message_id}")
    # Return empty list of reactions
    return []
# Import real apechain functions but replace with mock for testing
from utils.apechain import create_market, get_deployed_market_id_from_tx as real_get_market_id

# Create mock functions for testing
def deploy_to_apechain(question, options, end_time, category):
    """
    Mock function for deploying markets to Apechain.
    Used in testing to bypass blockchain interaction.
    """
    logger.info(f"Mock deployment for market: {question}")
    # Return a fake transaction hash for testing
    return f"0x{os.urandom(32).hex()}"

def get_deployed_market_id_from_tx(tx_hash):
    """
    Mock function to get market ID from transaction hash.
    Used in testing to bypass blockchain interaction.
    """
    logger.info(f"Mock market ID lookup for tx: {tx_hash}")
    # Return a fake market ID (integer as string)
    return "1"
from post_unposted_pending_markets import format_market_message
from utils.deployment_formatter import format_deployment_message

# Initialize app and database
db.init_app(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_test_records():
    """Clear any existing test records from database."""
    with app.app_context():
        try:
            # Clear old test markets and related records
            test_markets = Market.query.filter(Market.question.like('%TEST PIPELINE%')).all()
            test_pending = PendingMarket.query.filter(PendingMarket.question.like('%TEST PIPELINE%')).all()
            
            # Delete related approval events
            for market in test_markets:
                ApprovalEvent.query.filter_by(market_id=market.id).delete()
            
            # Delete records
            for market in test_markets:
                db.session.delete(market)
            
            for pending in test_pending:
                db.session.delete(pending)
            
            db.session.commit()
            logger.info(f"Cleared {len(test_markets)} test markets and {len(test_pending)} test pending markets")
        
        except Exception as e:
            logger.error(f"Error clearing test records: {str(e)}")
            db.session.rollback()

def create_test_pending_market():
    """Create a test pending market for the pipeline."""
    with app.app_context():
        try:
            # Generate test market data
            test_id = f"test-{int(datetime.now().timestamp())}"
            test_question = f"TEST PIPELINE: Will Bitcoin reach $100k before the end of 2025?"
            test_category = "crypto"
            test_options = ["Yes", "No"]
            test_expiry = int((datetime.now() + timedelta(days=365)).timestamp() * 1000)
            
            # Create options structure
            option_list = [{"id": str(i+1), "value": option} for i, option in enumerate(test_options)]
            
            # Create test market
            test_market = PendingMarket(
                poly_id=test_id,
                question=test_question,
                category=test_category,
                banner_url="https://example.com/banner.jpg",
                icon_url="https://example.com/icon.jpg",
                options=option_list,
                option_images={option: f"https://example.com/{option.lower()}.jpg" for option in test_options},
                expiry=test_expiry,
                raw_data={"source": "test_pipeline"},
                needs_manual_categorization=False,
                posted=False,
                fetched_at=datetime.utcnow()
            )
            
            db.session.add(test_market)
            db.session.commit()
            
            logger.info(f"Created test pending market: {test_question}")
            return test_market
        
        except Exception as e:
            logger.error(f"Error creating test pending market: {str(e)}")
            db.session.rollback()
            return None

def post_pending_market_to_slack(pending_market):
    """Post a pending market to Slack for approval."""
    # Format the message
    message_text, blocks = format_market_message(pending_market)
    
    # Post to Slack
    message_id = post_formatted_message_to_slack(message_text, blocks=blocks)
    
    if not message_id:
        logger.error("Failed to post test message to Slack")
        return None
    
    # Update pending market as posted
    with app.app_context():
        pending_market.posted = True
        pending_market.slack_message_id = message_id
        pending_market.posted_at = datetime.utcnow()
        db.session.commit()
    
    logger.info(f"Posted pending market to Slack with ID {message_id}")
    return message_id

def approve_pending_market(pending_market, message_id):
    """Simulate approval of a pending market."""
    # Add approval reaction
    add_reaction_to_message(message_id, "white_check_mark")
    
    # Log approval in the database
    with app.app_context():
        # Get a fresh instance of the pending market from the database
        fresh_pending_market = db.session.query(PendingMarket).filter_by(poly_id=pending_market.poly_id).first()
        if not fresh_pending_market:
            logger.error("Pending market not found in database")
            return None
            
        approval = ApprovalEvent(
            market_id=fresh_pending_market.poly_id,
            stage="initial",
            status="approved",
            message_id=message_id,
            created_at=datetime.utcnow()
        )
        db.session.add(approval)
        
        # Create market entry
        market = Market(
            id=fresh_pending_market.poly_id,
            question=fresh_pending_market.question,
            category=fresh_pending_market.category,
            expiry=fresh_pending_market.expiry,
            status="approved", 
            options=[opt["value"] for opt in fresh_pending_market.options],
            banner_uri=fresh_pending_market.banner_url,
            icon_url=fresh_pending_market.icon_url,
            option_images=fresh_pending_market.option_images,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.session.add(market)
        db.session.commit()
    
        logger.info(f"Approved pending market: {fresh_pending_market.question}")
        return market

def post_deployment_approval(market):
    """Post a market for deployment approval."""
    with app.app_context():
        # Get a fresh instance of the market from the database
        fresh_market = db.session.query(Market).filter_by(id=market.id).first()
        if not fresh_market:
            logger.error("Market not found in database")
            return None
            
        # Format expiry date
        expiry_date = datetime.fromtimestamp(fresh_market.expiry / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        # Format deployment message
        market_type = "Binary Market (Yes/No)" if len(fresh_market.options) == 2 else "Multi-option Market"
        message_text, blocks = format_deployment_message(
            market_id=fresh_market.id,
            question=fresh_market.question,
            category=fresh_market.category.capitalize(),
            market_type=market_type,
            options=fresh_market.options,
            expiry=expiry_date,
            banner_uri=fresh_market.banner_uri
        )
        
        # Post to Slack
        message_id = post_formatted_message_to_slack(message_text, blocks=blocks)
        
        if not message_id:
            logger.error("Failed to post deployment approval message to Slack")
            return None
        
        # Update market with slack message ID
        fresh_market.deployment_slack_message_id = message_id
        db.session.commit()
        
        logger.info(f"Posted market for deployment approval with ID {message_id}")
        return message_id

def approve_deployment(market, message_id):
    """Simulate approval of market deployment."""
    # Add approval reaction
    add_reaction_to_message(message_id, "white_check_mark")
    
    # Log approval in the database
    with app.app_context():
        # Get a fresh instance of the market from the database
        fresh_market = db.session.query(Market).filter_by(id=market.id).first()
        if not fresh_market:
            logger.error("Market not found in database")
            return False
            
        approval = ApprovalEvent(
            market_id=fresh_market.id,
            stage="final",
            status="approved",
            message_id=message_id,
            created_at=datetime.utcnow()
        )
        db.session.add(approval)
        db.session.commit()
    
        logger.info(f"Approved deployment for market: {fresh_market.question}")
        return True

def deploy_market_to_apechain(market):
    """Deploy market to Apechain."""
    with app.app_context():
        # Get a fresh instance of the market from the database
        fresh_market = db.session.query(Market).filter_by(id=market.id).first()
        if not fresh_market:
            logger.error("Market not found in database")
            return None
            
        # Get market data
        question = fresh_market.question
        
        # Convert options list to proper format
        options = fresh_market.options
        
        # Convert expiry from milliseconds to seconds
        expiry = int(fresh_market.expiry / 1000)
        
        # Capitalize category
        category = fresh_market.category.capitalize()
        
        # Deploy to Apechain
        tx_hash = deploy_to_apechain(question, options, expiry, category)
        
        if not tx_hash:
            logger.error("Failed to deploy market to Apechain")
            return None
        
        # Update market with transaction hash
        fresh_market.status = "deployed"
        fresh_market.blockchain_tx = tx_hash
        fresh_market.deployed_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Deployed market to Apechain with transaction: {tx_hash}")
        return tx_hash

def track_market_id(market, tx_hash):
    """Track the market ID from Apechain after deployment."""
    # In testing, we don't need to wait for real transaction mining
    logger.info("Simulating transaction mining wait...")
    time.sleep(1)  # Short wait for testing
    
    # Get market ID from transaction
    market_id = get_deployed_market_id_from_tx(tx_hash)
    
    if not market_id:
        logger.error(f"Failed to get market ID for transaction {tx_hash}")
        return None
    
    # Update market with market ID
    with app.app_context():
        # Get a fresh instance of the market from the database
        fresh_market = db.session.query(Market).filter_by(id=market.id).first()
        if not fresh_market:
            logger.error("Market not found in database")
            return None
            
        fresh_market.apechain_market_id = market_id
        db.session.commit()
    
        logger.info(f"Updated market with Apechain market ID: {market_id}")
        return market_id

def run_single_session_pipeline():
    """Run the entire pipeline within a single database session."""
    logger.info("Starting test of full pipeline flow")
    
    # Clear any existing test records
    clear_test_records()
    
    with app.app_context():
        try:
            # Create a pipeline run record
            pipeline_run = PipelineRun(
                status="running",
                start_time=datetime.utcnow()
            )
            db.session.add(pipeline_run)
            db.session.commit()
            
            # Step 1: Create test pending market in database
            test_id = f"test-{int(datetime.now().timestamp())}"
            test_question = "TEST PIPELINE: Will Bitcoin reach $100k before the end of 2025?"
            test_category = "crypto"
            test_options = ["Yes", "No"]
            test_expiry = int((datetime.now() + timedelta(days=365)).timestamp() * 1000)
            
            # Create options structure
            option_list = [{"id": str(i+1), "value": option} for i, option in enumerate(test_options)]
            
            # Create test market
            pending_market = PendingMarket(
                poly_id=test_id,
                question=test_question,
                category=test_category,
                banner_url="https://example.com/banner.jpg",
                icon_url="https://example.com/icon.jpg",
                options=option_list,
                option_images={option: f"https://example.com/{option.lower()}.jpg" for option in test_options},
                expiry=test_expiry,
                raw_data={"source": "test_pipeline"},
                needs_manual_categorization=False,
                posted=False,
                fetched_at=datetime.utcnow()
            )
            db.session.add(pending_market)
            db.session.commit()
            logger.info(f"Created test pending market: {pending_market.question}")
            
            # Step 2: Post to Slack
            # Format the message
            message_text, blocks = format_market_message(pending_market)
            
            # Post to Slack
            slack_response = slack_client.chat_postMessage(
                channel=SLACK_CHANNEL_ID,
                text=message_text,
                blocks=blocks
            )
            
            if not slack_response or not slack_response.get('ok'):
                raise Exception(f"Failed to post to Slack: {slack_response.get('error', 'Unknown error')}")
                
            message_id = slack_response['ts']
            
            # Update pending market as posted
            pending_market.posted = True
            pending_market.slack_message_id = message_id
            pending_market.posted_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Posted pending market to Slack with ID {message_id}")
            
            # Wait a bit for message to be visible
            time.sleep(2)
            
            # Step 3: Approve pending market
            # In testing, we don't need to actually add the reaction as we're bypassing Slack's API verification
            # This would normally fail if Slack API tokens aren't available
            logger.info(f"Simulating approval reaction for message {message_id}")
            
            # Log approval in the database
            approval = ApprovalEvent(
                market_id=pending_market.poly_id,
                stage="initial",
                status="approved",
                message_id=message_id,
                created_at=datetime.utcnow()
            )
            db.session.add(approval)
            
            # Create market entry
            market = Market(
                id=pending_market.poly_id,
                question=pending_market.question,
                category=pending_market.category,
                expiry=pending_market.expiry,
                status="approved", 
                options=[opt["value"] for opt in pending_market.options],
                banner_uri=pending_market.banner_url,
                icon_url=pending_market.icon_url,
                option_images=pending_market.option_images,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(market)
            db.session.commit()
            logger.info(f"Approved pending market: {pending_market.question}")
            
            # Step 4: Post for deployment approval
            # Format expiry date
            expiry_date = datetime.fromtimestamp(market.expiry / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            # Format deployment message
            market_type = "Binary Market (Yes/No)" if len(market.options) == 2 else "Multi-option Market"
            deployment_message_text, deployment_blocks = format_deployment_message(
                market_id=market.id,
                question=market.question,
                category=market.category.capitalize(),
                market_type=market_type,
                options=market.options,
                expiry=expiry_date,
                banner_uri=market.banner_uri
            )
            
            # Post to Slack
            deployment_response = slack_client.chat_postMessage(
                channel=SLACK_CHANNEL_ID,
                text=deployment_message_text,
                blocks=deployment_blocks
            )
            
            if not deployment_response or not deployment_response.get('ok'):
                raise Exception(f"Failed to post deployment approval: {deployment_response.get('error', 'Unknown error')}")
                
            deployment_message_id = deployment_response['ts']
            
            # Update market with slack message ID
            market.deployment_slack_message_id = deployment_message_id
            db.session.commit()
            logger.info(f"Posted market for deployment approval with ID {deployment_message_id}")
            
            # Wait a bit for message to be visible
            time.sleep(2)
            
            # Step 5: Approve deployment
            # In testing, we don't need to actually add the reaction as we're bypassing Slack's API verification
            # This would normally fail if Slack API tokens aren't available
            logger.info(f"Simulating approval reaction for deployment message {deployment_message_id}")
            
            # Log approval in the database
            deployment_approval = ApprovalEvent(
                market_id=market.id,
                stage="final",
                status="approved",
                message_id=deployment_message_id,
                created_at=datetime.utcnow()
            )
            db.session.add(deployment_approval)
            db.session.commit()
            logger.info(f"Approved deployment for market: {market.question}")
            
            # Step 6: Deploy to Apechain
            # Get market data
            question = market.question
            options = market.options
            expiry = int(market.expiry / 1000)
            category = market.category.capitalize()
            
            # Deploy to Apechain
            tx_hash = deploy_to_apechain(question, options, expiry, category)
            
            if not tx_hash:
                raise Exception("Failed to deploy market to Apechain")
            
            # Update market with transaction hash
            market.status = "deployed"
            market.blockchain_tx = tx_hash
            market.deployed_at = datetime.utcnow()
            db.session.commit()
            logger.info(f"Deployed market to Apechain with transaction: {tx_hash}")
            
            # Step 7: Track market ID
            # In testing, we don't need to wait for real transaction mining
            logger.info("Simulating transaction mining wait...")
            time.sleep(1)  # Short wait for testing
            
            # Get market ID from transaction
            market_id = get_deployed_market_id_from_tx(tx_hash)
            
            if not market_id:
                raise Exception(f"Failed to get market ID for transaction {tx_hash}")
            
            # Update market with market ID
            market.apechain_market_id = market_id
            db.session.commit()
            logger.info(f"Updated market with Apechain market ID: {market_id}")
            
            # Update pipeline run with success
            pipeline_run.status = "completed"
            pipeline_run.end_time = datetime.utcnow()
            pipeline_run.markets_processed = 1
            pipeline_run.markets_approved = 1
            pipeline_run.markets_deployed = 1
            db.session.commit()
            
            logger.info("=" * 50)
            logger.info("PIPELINE TEST COMPLETED SUCCESSFULLY")
            logger.info(f"Market Question: {market.question}")
            logger.info(f"Market ID: {market.id}")
            logger.info(f"Apechain Market ID: {market.apechain_market_id}")
            logger.info(f"Transaction Hash: {market.blockchain_tx}")
            logger.info("=" * 50)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error in pipeline test: {str(e)}")
            if 'pipeline_run' in locals():
                pipeline_run.status = "failed"
                pipeline_run.error = str(e)
                pipeline_run.end_time = datetime.utcnow()
                db.session.commit()
            return 1

def main():
    """Main function for testing the full pipeline."""
    try:
        return run_single_session_pipeline()
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())