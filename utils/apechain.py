"""
Apechain utilities for interacting with the Apechain blockchain.

This module provides functions for deploying markets to Apechain,
querying market data from the blockchain, and handling transactions.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
import time

# Import Web3 with better error handling
try:
    from web3 import Web3
    web3_available = True
except ImportError:
    web3_available = False
    logging.warning("Web3 package not found. Blockchain functions will be unavailable.")

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
w3 = None
if web3_available and APECHAIN_RPC_URL:
    try:
        w3 = Web3(Web3.HTTPProvider(APECHAIN_RPC_URL))
        logger.info(f"Connected to Apechain RPC: {APECHAIN_RPC_URL}")
    except Exception as e:
        logger.error(f"Failed to initialize Web3 connection: {str(e)}")
        w3 = None

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
PREDICTOR_ADDRESS = '0x90b92F7ec91bAa3E6e7a62A9209bC4041b17F813'  # Freshly deployed contract

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

def deploy_market_to_apechain(market) -> Tuple[Optional[str], Optional[str]]:
    """
    Deploy a market to Apechain.
    
    Args:
        market: Market model instance
        
    Returns:
        Tuple[str, str]: (market_id, transaction_hash) if successful, (None, None) otherwise
    """
    if not web3_available:
        logger.error("Web3 package not available. Cannot deploy market.")
        return None, None
        
    if not w3 or not WALLET_PRIVATE_KEY:
        logger.error("Web3 connection not initialized or wallet private key missing")
        return None, None
    
    try:
        # Parse options
        options = []
        if market.options:
            try:
                if isinstance(market.options, str):
                    options_data = json.loads(market.options)
                    # Handle different options formats
                    if isinstance(options_data, list):
                        if options_data and isinstance(options_data[0], dict) and 'value' in options_data[0]:
                            # Options in [{"id": "...", "value": "..."}, ...] format
                            options = [opt.get('value', 'Unknown') for opt in options_data]
                        else:
                            # Options in ["Option1", "Option2", ...] format
                            options = [str(opt) for opt in options_data]
                            
                elif isinstance(market.options, list):
                    options = [str(opt) for opt in market.options]
            except Exception as e:
                logger.error(f"Error parsing options for market {market.id}: {str(e)}")
                return None, None
        
        # Fallback to Yes/No if no options found
        if not options:
            logger.warning(f"No options found for market {market.id}, using Yes/No")
            options = ["Yes", "No"]
        
        # Get expiry timestamp
        if not market.expiry:
            logger.error(f"No expiry timestamp found for market {market.id}")
            return None, None
        
        # Get category (capitalize for consistency)
        category = market.category
        if not category:
            logger.warning(f"No category found for market {market.id}, using 'Other'")
            category = "Other"
        
        # Capitalize first letter of category
        category = category[0].upper() + category[1:] if category else "Other"
        
        # Create market on Apechain
        logger.info(f"Deploying market '{market.question}' to Apechain with {len(options)} options")
        tx_hash = create_market(
            question=market.question,
            options=options,
            end_time=market.expiry,
            category=category
        )
        
        if not tx_hash:
            logger.error(f"Failed to create market on Apechain: {market.id}")
            return None, None
        
        logger.info(f"Created market transaction: {tx_hash}")
        
        # Wait for transaction to be mined and get market ID
        logger.info("Waiting for transaction to be mined...")
        market_id = get_deployed_market_id_from_tx(tx_hash)
        
        if not market_id:
            logger.error(f"Failed to get market ID from transaction: {tx_hash}")
            return None, tx_hash
        
        logger.info(f"Successfully deployed market {market.id} to Apechain with ID {market_id}")
        return market_id, tx_hash
        
    except Exception as e:
        logger.error(f"Error deploying market {market.id} to Apechain: {str(e)}")
        return None, None