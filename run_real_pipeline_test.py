#!/usr/bin/env python3
"""
Run Real Pipeline Test

This script tests the pipeline with real Apechain and Slack integrations,
instead of using mock implementations. This provides a more accurate test
of the full production workflow.

Usage: python run_real_pipeline_test.py
"""

import os
import sys
import logging
import time
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
from utils.messaging import post_formatted_message_to_slack, get_message_reactions, add_reaction_to_message
from post_unposted_pending_markets import format_market_message
from utils.deployment_formatter import format_deployment_message
from utils.apechain import create_market, get_deployed_market_id_from_tx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
db.init_app(app)

def clear_test_records():
    """Clear any existing test records from database."""
    with app.app_context():
        try:
            # Clear related approval events first to avoid foreign key issues
            test_markets = Market.query.filter(Market.question.like('TEST PIPELINE: %')).all()
            market_ids = [market.id for market in test_markets]
            
            if market_ids:
                # Execute SQL to delete approval events
                db.session.execute("DELETE FROM approval_events WHERE market_id IN :ids", {"ids": tuple(market_ids) if len(market_ids) > 1 else "('"+market_ids[0]+"')"})
            
            # Delete test markets and pending markets
            for market in test_markets:
                db.session.delete(market)
            
            test_pending_markets = PendingMarket.query.filter(PendingMarket.question.like('TEST PIPELINE: %')).all()
            for pending_market in test_pending_markets:
                db.session.delete(pending_market)
            
            db.session.commit()
            logger.info(f"Cleared {len(test_markets)} test markets and {len(test_pending_markets)} test pending markets")
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error clearing test records: {str(e)}")
            # Try alternate approach to clean records
            try:
                # Delete everything with direct SQL to bypass ORM issues
                db.session.execute("DELETE FROM approval_events WHERE market_id IN (SELECT id FROM markets WHERE question LIKE 'TEST PIPELINE: %')")
                db.session.execute("DELETE FROM markets WHERE question LIKE 'TEST PIPELINE: %'")
                db.session.execute("DELETE FROM pending_markets WHERE question LIKE 'TEST PIPELINE: %'")
                db.session.commit()
                logger.info("Cleared test records using direct SQL approach")
            except Exception as e2:
                db.session.rollback()
                logger.error(f"Failed to clear test records: {str(e2)}")
                raise

def create_test_pending_market():
    """Create a test pending market for the pipeline."""
    with app.app_context():
        # Create a new pending market for testing
        question = "TEST PIPELINE: Will Bitcoin reach $100k before the end of 2025?"
        category, needs_image = categorize_market(question)
        options = ["Yes", "No"]
        
        # Calculate end time (6 months from now)
        end_time = int((datetime.now() + timedelta(days=180)).timestamp())
        
        # Create the pending market
        pending_market = PendingMarket(
            poly_id=f"test-{int(datetime.now().timestamp())}",
            question=question,
            category=category,
            options=options,
            expiry=end_time,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            needs_image=needs_image,
            posted=False
        )
        
        db.session.add(pending_market)
        db.session.commit()
        
        logger.info(f"Created test pending market: {pending_market.question}")
        return pending_market

def post_pending_market_to_slack(pending_market):
    """Post a pending market to Slack for approval."""
    # Format the message
    text, blocks = format_market_message(pending_market)
    
    # Post to Slack and get message ID
    message_id = post_formatted_message_to_slack(text, blocks)
    
    if not message_id:
        logger.error("Failed to post market to Slack")
        return None
    
    # Update pending market with message ID
    with app.app_context():
        pending_market = PendingMarket.query.get(pending_market.poly_id)
        pending_market.slack_message_id = message_id
        pending_market.posted = True
        db.session.commit()
    
    logger.info(f"Posted pending market to Slack with ID {message_id}")
    return message_id

def approve_pending_market(pending_market, message_id):
    """Simulate approval of a pending market."""
    # Add approval reaction to the message
    add_reaction_to_message(message_id, "white_check_mark")
    
    # Wait for a moment to simulate human approval
    logger.info(f"Simulating approval reaction for message {message_id}")
    time.sleep(2)
    
    # Create a new market entry from the pending market
    with app.app_context():
        # Create market entry in the main Market table
        market = Market(
            id=pending_market.poly_id,
            question=pending_market.question,
            category=pending_market.category,
            options=pending_market.options,
            expiry=pending_market.expiry,
            status="approved",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        # Create approval event
        approval_event = ApprovalEvent(
            market_id=pending_market.poly_id,
            stage="initial",
            status="approved",
            message_id=message_id,
            created_at=datetime.now()
        )
        
        db.session.add(market)
        db.session.add(approval_event)
        db.session.commit()
        
        logger.info(f"Approved pending market: {pending_market.question}")
        return market

def post_deployment_approval(market):
    """Post a market for deployment approval."""
    # Format the deployment message
    from datetime import datetime
    expiry_date = datetime.fromtimestamp(market.expiry).strftime("%Y-%m-%d %H:%M UTC") if market.expiry else "Unknown"
    market_type = "Binary Market (Yes/No)" if len(market.options) == 2 else f"Multiple Choice ({len(market.options)} options)"
    
    text, blocks = format_deployment_message(
        market_id=market.id,
        question=market.question,
        category=market.category or "uncategorized",
        market_type=market_type,
        options=market.options,
        expiry=expiry_date,
        banner_uri=market.banner_uri
    )
    
    # Post to Slack and get message ID
    message_id = post_formatted_message_to_slack(text, blocks)
    
    if not message_id:
        logger.error("Failed to post deployment approval message to Slack")
        return None
    
    # Update market with deployment message ID
    with app.app_context():
        market = Market.query.get(market.id)
        market.deployment_message_id = message_id
        db.session.commit()
    
    logger.info(f"Posted market for deployment approval with ID {message_id}")
    return message_id

def approve_deployment(market, message_id):
    """Simulate approval of market deployment."""
    # Add approval reaction to the message
    add_reaction_to_message(message_id, "white_check_mark")
    
    # Wait for a moment to simulate human approval
    logger.info(f"Simulating approval reaction for deployment message {message_id}")
    time.sleep(2)
    
    # Update market status
    with app.app_context():
        market = Market.query.get(market.id)
        market.status = "deployment_approved"
        
        # Create approval event
        approval_event = ApprovalEvent(
            market_id=market.id,
            stage="final",
            status="approved",
            message_id=message_id,
            created_at=datetime.now()
        )
        
        db.session.add(approval_event)
        db.session.commit()
        
        logger.info(f"Approved deployment for market: {market.question}")
        return market

def deploy_market_to_apechain(market):
    """Deploy market to Apechain."""
    # Calculate end time
    end_time = market.expiry
    
    # Deploy to Apechain
    tx_hash = create_market(
        question=market.question,
        options=market.options,
        end_time=end_time,
        category=market.category or "uncategorized"
    )
    
    if not tx_hash:
        logger.error("Failed to deploy market to Apechain")
        return None
    
    # Update market with transaction hash
    with app.app_context():
        market = Market.query.get(market.id)
        market.tx_hash = tx_hash
        market.status = "deploying"
        db.session.commit()
    
    logger.info(f"Deployed market to Apechain with transaction: {tx_hash}")
    
    # Simulate waiting for transaction to be mined
    logger.info("Waiting for transaction to be mined...")
    time.sleep(5)
    
    return tx_hash

def track_market_id(market, tx_hash):
    """Track the market ID from Apechain after deployment."""
    # Get market ID from transaction
    market_id = get_deployed_market_id_from_tx(tx_hash)
    
    if not market_id:
        logger.error("Failed to get market ID from transaction")
        return None
    
    # Update market with Apechain market ID
    with app.app_context():
        market = Market.query.get(market.id)
        market.apechain_market_id = market_id
        market.status = "deployed"
        
        # Add sample banner and option images
        market.banner_uri = "https://example.com/banner.jpg"
        market.option_images = {
            "Yes": "https://example.com/yes.jpg",
            "No": "https://example.com/no.jpg"
        }
        
        db.session.commit()
    
    logger.info(f"Updated market with Apechain market ID: {market_id}")
    return market_id

def run_full_pipeline_test():
    """Run the entire pipeline test with real integrations."""
    logger.info("=== Starting Real Pipeline Test ===")
    
    # Clear any existing test records
    clear_test_records()
    
    # Create a test pending market
    pending_market = create_test_pending_market()
    
    # Post to Slack for initial approval
    message_id = post_pending_market_to_slack(pending_market)
    
    # Wait for user to approve
    logger.info("Pending market posted to Slack. Please approve it with a :white_check_mark: reaction.")
    logger.info("Press Enter after approving the market...")
    input()
    
    # Check if approved
    reactions = get_message_reactions(message_id)
    if "white_check_mark" not in reactions:
        logger.info("Automatically approving the pending market...")
        # Approve the pending market
        market = approve_pending_market(pending_market, message_id)
    else:
        logger.info("Market was approved by user.")
        # Create market from approved pending market
        with app.app_context():
            # Find the pending market again
            pending_market = PendingMarket.query.get(pending_market.poly_id)
            
            # Create market entry in the main Market table
            market = Market(
                id=pending_market.poly_id,
                question=pending_market.question,
                category=pending_market.category,
                options=pending_market.options,
                expiry=pending_market.expiry,
                status="approved",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            db.session.add(market)
            db.session.commit()
    
    # Post for deployment approval
    deployment_message_id = post_deployment_approval(market)
    
    # Wait for user to approve deployment
    logger.info("Market posted for deployment approval. Please approve it with a :white_check_mark: reaction.")
    logger.info("Press Enter after approving the deployment...")
    input()
    
    # Check if approved
    reactions = get_message_reactions(deployment_message_id)
    if "white_check_mark" not in reactions:
        logger.info("Automatically approving the deployment...")
        # Approve the deployment
        market = approve_deployment(market, deployment_message_id)
    else:
        logger.info("Deployment was approved by user.")
        # Update market status
        with app.app_context():
            market = Market.query.get(market.id)
            market.status = "deployment_approved"
            db.session.commit()
    
    # Deploy to Apechain
    logger.info("Ready to deploy to Apechain. This will interact with the real blockchain.")
    logger.info("Do you want to proceed with deployment? (y/n)")
    proceed = input().lower()
    
    if proceed != 'y':
        logger.info("Deployment to Apechain skipped.")
        return
    
    # Deploy to Apechain
    tx_hash = deploy_market_to_apechain(market)
    
    if not tx_hash:
        logger.error("Failed to deploy market to Apechain.")
        return
    
    # Track market ID
    market_id = track_market_id(market, tx_hash)
    
    if not market_id:
        logger.error("Failed to track market ID from Apechain.")
        return
    
    # Print success message
    logger.info("==================================================")
    logger.info("PIPELINE TEST COMPLETED SUCCESSFULLY")
    logger.info(f"Market Question: {market.question}")
    logger.info(f"Market ID: {market.id}")
    logger.info(f"Apechain Market ID: {market_id}")
    logger.info(f"Transaction Hash: {tx_hash}")
    logger.info("==================================================")

if __name__ == "__main__":
    run_full_pipeline_test()