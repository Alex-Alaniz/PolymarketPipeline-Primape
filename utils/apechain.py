"""
Apechain utilities for interacting with the Apechain blockchain.

This module provides functions for deploying markets to Apechain,
querying market data from the blockchain, and handling transactions.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from web3 import Web3
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Connect to Apechain RPC
APECHAIN_RPC_URL = os.environ.get('APECHAIN_RPC_URL')
WALLET_PRIVATE_KEY = os.environ.get('WALLET_PRIVATE_KEY')
WALLET_ADDRESS = os.environ.get('WALLET_ADDRESS')

if not APECHAIN_RPC_URL:
    logger.warning("Missing Apechain RPC URL. Set APECHAIN_RPC_URL environment variable.")

# Initialize Web3 connection
w3 = Web3(Web3.HTTPProvider(APECHAIN_RPC_URL)) if APECHAIN_RPC_URL else None

# Load ABI files
PREDICTOR_ABI_PATH = './abi/predictor.json'
MARKET_ABI_PATH = './abi/market.json'

def load_abi(file_path: str) -> List[Dict[str, Any]]:
    """
    Load an ABI file.
    
    Args:
        file_path: Path to the ABI JSON file
        
    Returns:
        ABI list
    """
    try:
        with open(file_path, 'r') as f:
            abi = json.load(f)
        return abi
    except Exception as e:
        logger.error(f"Error loading ABI file {file_path}: {str(e)}")
        return []

# Load ABIs if files exist
predictor_abi = load_abi(PREDICTOR_ABI_PATH) if os.path.exists(PREDICTOR_ABI_PATH) else []
market_abi = load_abi(MARKET_ABI_PATH) if os.path.exists(MARKET_ABI_PATH) else []

# Predictor contract address (the factory for creating markets)
PREDICTOR_ADDRESS = '0xPredictorContractAddress'  # Replace with actual address

def create_market(question: str, options: List[str], end_time: int, category: str) -> Optional[str]:
    """
    Create a new prediction market on Apechain.
    
    Args:
        question: Market question
        options: List of options
        end_time: Expiry timestamp in seconds
        category: Market category
        
    Returns:
        Transaction hash if successful, None otherwise
    """
    if not w3 or not WALLET_PRIVATE_KEY:
        logger.error("Web3 connection not initialized or wallet private key missing")
        return None
    
    try:
        # Build predictor contract
        predictor_contract = w3.eth.contract(address=PREDICTOR_ADDRESS, abi=predictor_abi)
        
        # Build transaction
        nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
        tx = predictor_contract.functions.createMarket(
            question, 
            options, 
            end_time, 
            category
        ).build_transaction({
            'gas': 8000000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, WALLET_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        logger.info(f"Created market with transaction hash: {tx_hash.hex()}")
        
        return tx_hash.hex()
    
    except Exception as e:
        logger.error(f"Error creating market: {str(e)}")
        return None

def get_deployed_market_id_from_tx(tx_hash: str) -> Optional[str]:
    """
    Get the market ID from a transaction hash.
    
    Args:
        tx_hash: Transaction hash of the market creation
        
    Returns:
        Market ID if found, None otherwise
    """
    if not w3:
        logger.error("Web3 connection not initialized")
        return None
    
    try:
        # Wait for transaction receipt
        receipt = None
        for _ in range(10):  # Retry a few times
            try:
                receipt = w3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    break
            except:
                time.sleep(2)  # Wait and retry
        
        if not receipt:
            logger.error(f"Transaction receipt not found for hash: {tx_hash}")
            return None
        
        # Check if transaction was successful
        if receipt.status != 1:
            logger.error(f"Transaction failed: {tx_hash}")
            return None
        
        # Find market creation event in the logs
        predictor_contract = w3.eth.contract(address=PREDICTOR_ADDRESS, abi=predictor_abi)
        
        # Look for MarketCreated event in the logs
        logs = predictor_contract.events.MarketCreated().process_receipt(receipt)
        
        if not logs:
            logger.error(f"No MarketCreated events found in transaction: {tx_hash}")
            return None
        
        # Get market ID from the event (this depends on your contract's event structure)
        market_id = logs[0].args.marketId  # Adjust the field name based on your contract
        
        logger.info(f"Found market ID {market_id} from transaction {tx_hash}")
        return str(market_id)
    
    except Exception as e:
        logger.error(f"Error getting market ID from transaction {tx_hash}: {str(e)}")
        return None

def get_market_info(market_id: str) -> Optional[Dict[str, Any]]:
    """
    Get market information from Apechain.
    
    Args:
        market_id: Market ID on Apechain
        
    Returns:
        Dictionary of market information if successful, None otherwise
    """
    if not w3:
        logger.error("Web3 connection not initialized")
        return None
    
    try:
        # Get market address from predictor contract
        predictor_contract = w3.eth.contract(address=PREDICTOR_ADDRESS, abi=predictor_abi)
        market_address = predictor_contract.functions.markets(int(market_id)).call()
        
        if not market_address or market_address == '0x0000000000000000000000000000000000000000':
            logger.error(f"Market address not found for ID: {market_id}")
            return None
        
        # Get market details
        market_contract = w3.eth.contract(address=market_address, abi=market_abi)
        
        # Get market data (adjust these function calls based on your contract)
        question = market_contract.functions.question().call()
        category = market_contract.functions.category().call()
        end_time = market_contract.functions.endTime().call()
        num_options = market_contract.functions.numOptions().call()
        
        # Get options
        options = []
        for i in range(num_options):
            option = market_contract.functions.options(i).call()
            options.append(option)
        
        # Construct market info
        market_info = {
            'id': market_id,
            'address': market_address,
            'question': question,
            'category': category,
            'end_time': end_time,
            'options': options
        }
        
        return market_info
    
    except Exception as e:
        logger.error(f"Error getting market info for ID {market_id}: {str(e)}")
        return None