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
from utils.messaging import (
    post_formatted_message_to_slack, 
    add_reaction_to_message,
    get_message_reactions,
    slack_client,
    SLACK_CHANNEL_ID
)
from utils.apechain import create_market as deploy_to_apechain
from utils.apechain import get_deployed_market_id_from_tx
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
                ApprovalEvent.query.filter_by(entity_id=market.id).delete()
            
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
        fresh_pending_market = db.session.query(PendingMarket).filter_by(id=pending_market.id).first()
        if not fresh_pending_market:
            logger.error("Pending market not found in database")
            return None
            
        approval = ApprovalEvent(
            entity_id=fresh_pending_market.id,
            entity_type="pending_market",
            approved=True,
            approved_by="test_user",
            approval_date=datetime.utcnow(),
            slack_message_id=message_id
        )
        db.session.add(approval)
        
        # Create market entry
        market = Market(
            id=fresh_pending_market.poly_id,
            question=fresh_pending_market.question,
            category=fresh_pending_market.category,
            source="test_pipeline",
            expiry=fresh_pending_market.expiry,
            status="approved", 
            options=[opt["value"] for opt in fresh_pending_market.options],
            banner_uri=fresh_pending_market.banner_url,
            icon_uri=fresh_pending_market.icon_url,
            option_images=fresh_pending_market.option_images,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            approved_at=datetime.utcnow()
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
            entity_id=fresh_market.id,
            entity_type="market_deployment",
            approved=True,
            approved_by="test_user",
            approval_date=datetime.utcnow(),
            slack_message_id=message_id
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
    # Wait for transaction to be mined
    logger.info("Waiting for transaction to be mined...")
    time.sleep(10)  # Adjust as needed based on blockchain confirmation times
    
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
            # Add approval reaction
            add_reaction_to_message(message_id, "white_check_mark")
            
            # Log approval in the database
            approval = ApprovalEvent(
                entity_id=pending_market.id,
                entity_type="pending_market",
                approved=True,
                approved_by="test_user",
                approval_date=datetime.utcnow(),
                slack_message_id=message_id
            )
            db.session.add(approval)
            
            # Create market entry
            market = Market(
                id=pending_market.poly_id,
                question=pending_market.question,
                category=pending_market.category,
                source="test_pipeline",
                expiry=pending_market.expiry,
                status="approved", 
                options=[opt["value"] for opt in pending_market.options],
                banner_uri=pending_market.banner_url,
                icon_uri=pending_market.icon_url,
                option_images=pending_market.option_images,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                approved_at=datetime.utcnow()
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
            # Add approval reaction
            add_reaction_to_message(deployment_message_id, "white_check_mark")
            
            # Log approval in the database
            deployment_approval = ApprovalEvent(
                entity_id=market.id,
                entity_type="market_deployment",
                approved=True,
                approved_by="test_user",
                approval_date=datetime.utcnow(),
                slack_message_id=deployment_message_id
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
            # Wait for transaction to be mined
            logger.info("Waiting for transaction to be mined...")
            time.sleep(10)  # Adjust as needed based on blockchain confirmation times
            
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