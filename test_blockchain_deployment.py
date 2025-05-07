#!/usr/bin/env python3

"""
Test Blockchain Deployment Functionality

This script tests the Apechain blockchain deployment functionality without
actually deploying any markets. It validates that the ABI files are loaded
correctly and that the blockchain connection is established.
"""

import os
import logging
import json
from datetime import datetime, timedelta
import time
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("blockchain_test")

def test_abi_loading():
    """Test loading of ABI files."""
    from utils.apechain import predictor_abi, market_abi, PREDICTOR_ABI_PATH, MARKET_ABI_PATH
    
    logger.info(f"Testing ABI loading...")
    
    # Check if ABI paths exist
    logger.info(f"Predictor ABI path: {PREDICTOR_ABI_PATH}, exists: {os.path.exists(PREDICTOR_ABI_PATH)}")
    logger.info(f"Market ABI path: {MARKET_ABI_PATH}, exists: {os.path.exists(MARKET_ABI_PATH)}")
    
    # Check ABI content
    logger.info(f"Predictor ABI length: {len(predictor_abi)}")
    logger.info(f"Market ABI length: {len(market_abi)}")
    
    return len(predictor_abi) > 0 and len(market_abi) > 0

def test_blockchain_connection():
    """Test blockchain connection."""
    from utils.apechain import w3, APECHAIN_RPC_URL, WALLET_ADDRESS
    
    logger.info(f"Testing blockchain connection...")
    
    # Check if environment variables are set
    logger.info(f"APECHAIN_RPC_URL set: {bool(APECHAIN_RPC_URL)}")
    logger.info(f"WALLET_ADDRESS set: {bool(WALLET_ADDRESS)}")
    
    # Check if Web3 is connected
    if w3:
        try:
            is_connected = w3.is_connected()
            logger.info(f"Web3 is connected: {is_connected}")
            
            if is_connected and WALLET_ADDRESS:
                # Try to get balance
                try:
                    balance = w3.eth.get_balance(WALLET_ADDRESS)
                    logger.info(f"Wallet balance: {balance}")
                except Exception as e:
                    logger.error(f"Error getting wallet balance: {str(e)}")
                    return False
                
            return is_connected
        except Exception as e:
            logger.error(f"Error testing connection: {str(e)}")
            return False
    else:
        logger.warning("Web3 instance not initialized")
        return False

def test_predictor_contract():
    """Test connecting to predictor contract."""
    from utils.apechain import w3, predictor_abi, PREDICTOR_ADDRESS
    
    logger.info(f"Testing predictor contract...")
    
    if not w3:
        logger.warning("Web3 instance not initialized")
        return False
        
    try:
        # Try to connect to the predictor contract
        predictor_contract = w3.eth.contract(address=PREDICTOR_ADDRESS, abi=predictor_abi)
        
        # Try to call a view function (market count)
        try:
            market_count = predictor_contract.functions.marketCount().call()
            logger.info(f"Market count: {market_count}")
            return True
        except Exception as e:
            logger.error(f"Error calling market count: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Error connecting to predictor contract: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Starting blockchain deployment test...")
    
    # Test ABI loading
    if not test_abi_loading():
        logger.error("ABI loading test failed")
        return 1
        
    # Test blockchain connection
    if not test_blockchain_connection():
        logger.warning("Blockchain connection test failed")
        # Continue with other tests, this might be due to missing environment variables
    
    # Test predictor contract (only if blockchain is connected)
    from utils.apechain import w3
    if w3 and w3.is_connected():
        if not test_predictor_contract():
            logger.error("Predictor contract test failed")
            return 1
    
    logger.info("Blockchain deployment test completed")
    return 0

if __name__ == "__main__":
    main()