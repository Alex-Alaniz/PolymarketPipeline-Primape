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
    # Polygon RPC URL
    polygon_rpc_url = os.environ.get("POLYGON_RPC_URL", "https://polygon-rpc.com")
    try:
        w3 = Web3(Web3.HTTPProvider(polygon_rpc_url))
        if not w3.is_connected():
            logger.error(f"Failed to connect to Polygon RPC at {polygon_rpc_url}")
            return None
        logger.info(f"Connected to Polygon network: {w3.client_version}")
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

def deploy_market_to_apechain(
    question: str,
    options: List[str],
    duration_days: int = 30
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Deploy a market to Apechain smart contract.
    
    Args:
        question: The market question
        options: List of market options (e.g., ["Yes", "No"])
        duration_days: Duration of the market in days
        
    Returns:
        Tuple containing:
        - Success status (bool)
        - Apechain market ID (str) or None if failed
        - Error message (str) or None if successful
    """
    if not question or not options:
        return False, None, "Invalid market data: question or options missing"
    
    # Convert duration to seconds
    duration_seconds = duration_days * 24 * 60 * 60
    
    # Get contract instance
    contract = get_contract()
    if not contract:
        return False, None, "Failed to get contract instance"
    
    # Get account details for the transaction
    private_key = os.environ.get("WALLET_PRIVATE_KEY")
    account_address = os.environ.get("WALLET_ADDRESS")
    
    if not private_key or not account_address:
        return False, None, "Wallet credentials not configured"
    
    w3 = get_web3()
    account_address = Web3.to_checksum_address(account_address)
    
    try:
        # Build transaction
        tx = contract.functions.createMarket(
            question,
            options,
            duration_seconds
        ).build_transaction({
            'from': account_address,
            'nonce': w3.eth.get_transaction_count(account_address),
            'gas': 3000000,  # Adjust gas as needed
            'gasPrice': w3.eth.gas_price,
            'chainId': 137,  # Polygon mainnet
        })
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        logger.info(f"Waiting for transaction receipt: {tx_hash.hex()}")
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
                    return True, str(market_id), None
                else:
                    # If we can't parse logs, return success but no ID
                    logger.warning("Market created but couldn't extract market ID from logs")
                    return True, receipt.transactionHash.hex(), None
            except Exception as e:
                logger.warning(f"Error parsing transaction logs: {str(e)}")
                # Return transaction hash as identifier if we can't get the market ID
                return True, receipt.transactionHash.hex(), None
        else:
            logger.error(f"Transaction failed: {receipt}")
            return False, None, f"Transaction failed with status: {receipt.status}"
            
    except ContractLogicError as e:
        error_msg = str(e)
        logger.error(f"Contract logic error: {error_msg}")
        return False, None, f"Contract error: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error deploying market: {error_msg}")
        return False, None, f"Error: {error_msg}"

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