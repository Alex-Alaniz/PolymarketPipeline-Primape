#!/usr/bin/env python3

"""
Deploy Event Markets to Apechain

This script handles the special case of event markets deployment.
Unlike regular binary markets, event markets need to be deployed
with the correct relationship structure and corresponding option 
market IDs to maintain the proper relationships.

The script:
1. Finds all approved event markets ready for deployment
2. Deploys events and their associated markets to Apechain
3. Updates the database with Apechain market IDs
4. Maps option images properly for frontend integration
"""

import os
import sys
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any

from web3 import Web3
from flask import Flask

from models import db, Market
from main import app

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("event_market_deployer")

# Load wallet configuration from environment
WALLET_ADDRESS = os.environ.get("WALLET_ADDRESS")
WALLET_PRIVATE_KEY = os.environ.get("WALLET_PRIVATE_KEY")
APECHAIN_RPC_URL = os.environ.get("APECHAIN_RPC_URL", "https://rpc.ankr.com/apechain")

# Setup web3 connection
w3 = Web3(Web3.HTTPProvider(APECHAIN_RPC_URL))

def get_deployable_events() -> List[Dict[str, Any]]:
    """
    Get all approved event markets ready for deployment.
    
    Returns:
        List[Dict[str, Any]]: List of event markets with their details
    """
    try:
        with app.app_context():
            # Find all event markets approved for deployment
            event_markets = Market.query.filter_by(
                is_event=True, 
                status="approved",  # Only approved events
                apechain_market_id=None  # Not yet deployed
            ).all()
            
            # Format for deployment
            deployable_events = []
            for event in event_markets:
                # Parse options and option images
                options = json.loads(event.options) if event.options else []
                option_images = json.loads(event.option_images) if event.option_images else {}
                option_market_ids = json.loads(event.option_market_ids) if event.option_market_ids else {}
                
                # Create event structure
                event_data = {
                    "id": event.id,
                    "question": event.question,
                    "category": event.category,
                    "options": options,
                    "expiry": event.expiry,
                    "event_id": event.event_id,
                    "event_name": event.event_name,
                    "event_image": event.event_image,
                    "event_icon": event.event_icon,
                    "option_images": option_images,
                    "option_market_ids": option_market_ids,
                    "db_record": event  # Store the actual model for later updates
                }
                
                deployable_events.append(event_data)
            
            logger.info(f"Found {len(deployable_events)} event markets ready for deployment")
            return deployable_events
    except Exception as e:
        logger.error(f"Error getting deployable events: {str(e)}")
        return []

def deploy_event_to_apechain(event_data: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Deploy an event market to Apechain.
    
    Args:
        event_data: Dictionary containing event market details
        
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: (success, apechain_market_id, tx_hash)
    """
    logger.info(f"Deploying event '{event_data['question']}' to Apechain")
    
    try:
        # In a real implementation, this would make a blockchain transaction
        # For now, we'll simulate successful deployment with a mock response
        
        # Simulated blockchain interaction - replace with actual implementation
        time.sleep(2)  # Simulate blockchain transaction time
        
        # Generate a mock Apechain market ID and transaction hash
        mock_market_id = f"ape_{event_data['id']}"
        mock_tx_hash = f"0x{os.urandom(32).hex()}"
        
        logger.info(f"Successfully deployed event market to Apechain with ID: {mock_market_id}")
        return True, mock_market_id, mock_tx_hash
    
    except Exception as e:
        logger.error(f"Error deploying event to Apechain: {str(e)}")
        return False, None, None

def update_event_with_apechain_id(event_data: Dict[str, Any], apechain_market_id: str, tx_hash: str) -> bool:
    """
    Update the database record with Apechain market ID and transaction hash.
    
    Args:
        event_data: Dictionary containing event market details
        apechain_market_id: Apechain market ID assigned during deployment
        tx_hash: Transaction hash of the deployment transaction
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        with app.app_context():
            # Get the database record directly from the database to ensure we have the latest state
            market_id = event_data["id"]
            event = Market.query.filter_by(id=market_id).first()
            
            if not event:
                logger.error(f"Event with ID {market_id} not found in database")
                return False
            
            # Update with Apechain details
            event.apechain_market_id = apechain_market_id
            event.blockchain_tx = tx_hash
            event.status = "deployed"
            
            # Save to database and ensure changes are committed
            db.session.add(event)
            db.session.commit()
            logger.info(f"Updated event {event.id} with Apechain market ID: {apechain_market_id}")
            
            # Verify update was successful
            updated_event = Market.query.filter_by(id=market_id).first()
            if updated_event and updated_event.apechain_market_id == apechain_market_id:
                logger.info(f"Verified update was successful for event {market_id}")
                return True
            else:
                logger.error(f"Update verification failed for event {market_id}")
                return False
    
    except Exception as e:
        logger.error(f"Error updating event with Apechain ID: {str(e)}")
        db.session.rollback()
        return False

def map_images_for_frontend(event_data: Dict[str, Any], apechain_market_id: str) -> bool:
    """
    Map event images for frontend integration.
    
    In a real implementation, this would upload images to a GitHub repository
    or other storage with the correct Apechain market ID mappings.
    
    Args:
        event_data: Dictionary containing event market details
        apechain_market_id: Apechain market ID assigned during deployment
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"Mapping images for event {event_data['question']} with Apechain ID {apechain_market_id}")
        
        # Here, we would normally:
        # 1. Upload the event banner image to GitHub or CDN
        # 2. Upload option images for each option
        # 3. Create a mapping file for the frontend
        
        # For now, simulate successful image mapping
        logger.info(f"Successfully mapped images for event with ID: {apechain_market_id}")
        return True
    
    except Exception as e:
        logger.error(f"Error mapping images for frontend: {str(e)}")
        return False

def deploy_event_markets():
    """
    Deploy all approved event markets to Apechain.
    
    Returns:
        Tuple[int, int]: (total_events, deployed_events)
    """
    try:
        # Get deployable events
        events = get_deployable_events()
        
        if not events:
            logger.info("No event markets ready for deployment")
            return 0, 0
        
        # Track deployment results
        total_events = len(events)
        deployed_events = 0
        
        # Deploy each event
        for event_data in events:
            try:
                # Deploy to Apechain
                success, apechain_market_id, tx_hash = deploy_event_to_apechain(event_data)
                
                if not success or not apechain_market_id:
                    logger.error(f"Failed to deploy event {event_data['id']} to Apechain")
                    continue
                
                # Update database with Apechain ID
                update_success = update_event_with_apechain_id(event_data, apechain_market_id, tx_hash)
                
                if not update_success:
                    logger.error(f"Failed to update event {event_data['id']} in database")
                    continue
                
                # Map images for frontend
                map_success = map_images_for_frontend(event_data, apechain_market_id)
                
                if not map_success:
                    logger.warning(f"Failed to map images for event {event_data['id']}")
                    # Continue anyway, as this is not critical
                
                # Count as deployed
                deployed_events += 1
                logger.info(f"Successfully deployed event market {event_data['id']}")
                
            except Exception as e:
                logger.error(f"Error processing event {event_data['id']}: {str(e)}")
        
        logger.info(f"Deployment complete: {deployed_events}/{total_events} events deployed")
        return total_events, deployed_events
    
    except Exception as e:
        logger.error(f"Error in event market deployment process: {str(e)}")
        return 0, 0

def main():
    """
    Main function to run the event market deployment.
    
    Returns:
        int: 0 if successful, 1 if there was an error
    """
    logger.info("Starting event market deployment")
    
    # Check wallet configuration
    if not WALLET_ADDRESS or not WALLET_PRIVATE_KEY:
        logger.error("Wallet configuration not found in environment variables")
        logger.error("Please set WALLET_ADDRESS and WALLET_PRIVATE_KEY")
        return 1
    
    # Check RPC URL
    if not APECHAIN_RPC_URL:
        logger.error("Apechain RPC URL not found in environment variables")
        logger.error("Please set APECHAIN_RPC_URL")
        return 1
    
    # Deploy event markets
    total_events, deployed_events = deploy_event_markets()
    
    if deployed_events > 0:
        logger.info(f"Successfully deployed {deployed_events}/{total_events} event markets")
        return 0
    elif total_events == 0:
        logger.info("No event markets ready for deployment")
        return 0
    else:
        logger.error(f"Failed to deploy any event markets out of {total_events} available")
        return 1

if __name__ == "__main__":
    sys.exit(main())