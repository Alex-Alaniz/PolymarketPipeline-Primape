#!/usr/bin/env python3

"""
Apechain Smart Contract Integration

This module provides utilities for interacting with the Apechain smart contract,
particularly for deploying approved markets to the blockchain.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import time
from web3 import Web3
from web3.exceptions import ContractLogicError

logger = logging.getLogger("apechain")

# Apechain contract address and ABI
CONTRACT_ADDRESS = "0x5Eb0aFd6CED124348eD44BDB955E26Ccb8fA613C"
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_question", "type": "string"},
            {"internalType": "string[]", "name": "_options", "type": "string[]"},
            {"internalType": "uint256", "name": "_duration", "type": "uint256"}
        ],
        "name": "createMarket",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
        "signature": "0xfbc529cb"
    }
]

# Initialize Web3 provider
def get_web3():
    """Get Web3 instance."""
    # ApeChain RPC URL
    apechain_rpc_url = os.environ.get("APECHAIN_RPC_URL")
    if not apechain_rpc_url:
        logger.error("APECHAIN_RPC_URL environment variable not set")
        return None
        
    try:
        w3 = Web3(Web3.HTTPProvider(apechain_rpc_url))
        if not w3.is_connected():
            logger.error(f"Failed to connect to ApeChain RPC at {apechain_rpc_url}")
            return None
        logger.info(f"Connected to ApeChain network: {w3.client_version}")
        return w3
    except Exception as e:
        logger.error(f"Error initializing Web3: {str(e)}")
        return None

def get_contract():
    """Get contract instance."""
    w3 = get_web3()
    if not w3:
        return None
    
    try:
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(CONTRACT_ADDRESS),
            abi=CONTRACT_ABI
        )
        logger.info(f"Contract instance created for address: {CONTRACT_ADDRESS}")
        return contract
    except Exception as e:
        logger.error(f"Error creating contract instance: {str(e)}")
        return None

def deploy_market_to_apechain(market) -> Tuple[Optional[str], Optional[str]]:
    """
    Deploy a market to Apechain smart contract.
    
    Args:
        market: Market model instance
        
    Returns:
        Tuple containing:
        - Apechain market ID (str) or None if failed
        - Transaction hash (str) or None if failed
    """
    if not market or not market.question:
        logger.error("Invalid market: missing required data")
        return None, None
    
    # Parse market options with better error handling
    try:
        logger.info(f"Parsing options from market {market.id}: {repr(market.options)}")
        
        if isinstance(market.options, str):
            try:
                options = json.loads(market.options)
                logger.info(f"Successfully parsed JSON options: {options}")
            except json.JSONDecodeError as e:
                logger.warning(f"JSON decode error for options string: {e}, using default options")
                options = ["Yes", "No"]
        else:
            options = market.options
            logger.info(f"Using non-string options directly: {options}")
        
        # Validate the options are in the correct format for the smart contract
        if not options:
            logger.warning("Empty options, using default")
            options = ["Yes", "No"]
        elif not isinstance(options, list):
            logger.warning(f"Options not a list ({type(options)}), using default")
            options = ["Yes", "No"]
        else:
            # Ensure all options are strings
            options = [str(option) for option in options]
            logger.info(f"Final validated options: {options}")
    except Exception as e:
        logger.error(f"Unexpected error parsing options: {str(e)}")
        options = ["Yes", "No"]  # Default if parsing fails
    
    # Calculate duration from expiry
    if market.expiry:
        # Calculate duration from now until expiry
        now = datetime.utcnow()
        expiry = datetime.fromtimestamp(market.expiry)
        duration = expiry - now
        duration_seconds = max(int(duration.total_seconds()), 86400)  # At least 1 day
    else:
        # Default to 30 days if no expiry provided
        duration_seconds = 30 * 24 * 60 * 60
    
    # Get contract instance
    contract = get_contract()
    if not contract:
        logger.error("Failed to get contract instance")
        return None, None
    
    # Get account details for the transaction
    private_key = os.environ.get("WALLET_PRIVATE_KEY")
    account_address = os.environ.get("WALLET_ADDRESS")
    
    if not private_key or not account_address:
        logger.error("Wallet credentials not configured")
        return None, None
    
    w3 = get_web3()
    if not w3:
        logger.error("Failed to connect to blockchain")
        return None, None
        
    account_address = Web3.to_checksum_address(account_address)
    
    try:
        # Build transaction
        tx = contract.functions.createMarket(
            market.question,
            options,
            duration_seconds
        ).build_transaction({
            'from': account_address,
            'nonce': w3.eth.get_transaction_count(account_address),
            'gas': 3000000,  # Adjust gas as needed
            'gasPrice': w3.eth.gas_price,
            'chainId': w3.eth.chain_id,  # Use the chain ID from the connected network
        })
        
        # Sign and send transaction
        try:
            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            # Check how the signed transaction looks
            logger.info(f"Signed transaction: {dir(signed_tx)}")
            
            # Get the raw transaction - naming might be different in different web3 versions
            raw_tx = None
            if hasattr(signed_tx, 'rawTransaction'):
                raw_tx = signed_tx.rawTransaction
            elif hasattr(signed_tx, 'raw_transaction'):
                raw_tx = signed_tx.raw_transaction
            elif hasattr(signed_tx, 'raw'):
                raw_tx = signed_tx.raw
            
            if not raw_tx:
                logger.error("Could not find raw transaction in signed transaction object")
                return None, None
                
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            tx_hash_hex = tx_hash.hex()
            logger.info(f"Transaction sent with hash: {tx_hash_hex}")
        except Exception as e:
            logger.error(f"Error during transaction signing or sending: {str(e)}")
            # Include more detailed error info
            logger.error(f"Transaction data: {tx}")
            return None, None
        
        # Wait for transaction receipt
        logger.info(f"Waiting for transaction receipt: {tx_hash_hex}")
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        
        # Check transaction status
        if receipt.status == 1:
            # Parse transaction logs to get market ID
            try:
                # Example log parsing - adjust based on actual contract event structure
                logs = contract.events.MarketCreated().process_receipt(receipt)
                if logs and len(logs) > 0:
                    market_id = logs[0]['args']['marketId']
                    logger.info(f"Market deployed to Apechain. Market ID: {market_id}")
                    return str(market_id), tx_hash_hex
                else:
                    # If we can't parse logs, use transaction hash as ID
                    logger.warning("Market created but couldn't extract market ID from logs")
                    return tx_hash_hex, tx_hash_hex
            except Exception as e:
                logger.warning(f"Error parsing transaction logs: {str(e)}")
                # Return transaction hash as identifier if we can't get the market ID
                return tx_hash_hex, tx_hash_hex
        else:
            logger.error(f"Transaction failed: {receipt}")
            return None, None
            
    except ContractLogicError as e:
        error_msg = str(e)
        logger.error(f"Contract logic error: {error_msg}")
        return None, None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error deploying market: {error_msg}")
        return None, None

def get_market_status(market_id: str) -> Dict[str, Any]:
    """
    Get the status of a market from Apechain.
    
    Args:
        market_id: Apechain market ID
        
    Returns:
        Dictionary with market status information
    """
    # This would be implemented to query the contract for market status
    # For now, just return a placeholder
    return {
        "id": market_id,
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }