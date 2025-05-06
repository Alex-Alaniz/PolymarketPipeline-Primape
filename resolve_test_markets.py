#!/usr/bin/env python3

"""
Resolve test markets on ApeChain.

This script resolves any test markets that were created during testing.
It calls the resolveMarket function on the ApeChain contract.
"""

import os
import sys
import logging
from web3 import Web3
from web3.exceptions import ContractLogicError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("market_resolver")

# ApeChain contract details
CONTRACT_ADDRESS = "0x5Eb0aFd6CED124348eD44BDB955E26Ccb8fA613C"
CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "_marketId", "type": "uint256"}
        ],
        "name": "getMarketInfo",
        "outputs": [
            {"internalType": "string", "name": "question", "type": "string"},
            {"internalType": "string[]", "name": "options", "type": "string[]"},
            {"internalType": "uint256", "name": "startTime", "type": "uint256"},
            {"internalType": "uint256", "name": "endTime", "type": "uint256"},
            {"internalType": "bool", "name": "resolved", "type": "bool"},
            {"internalType": "uint256", "name": "winningIndex", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_marketId", "type": "uint256"},
            {"internalType": "uint256", "name": "_winningIndex", "type": "uint256"}
        ],
        "name": "resolveMarket",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
        "signature": "0x60557333"
    }
]

def get_web3():
    """Get Web3 instance."""
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

def get_market_info(market_id):
    """
    Get information about a market.
    
    Args:
        market_id: Market ID
        
    Returns:
        Dictionary with market information or None if failed
    """
    contract = get_contract()
    if not contract:
        return None
    
    try:
        market_info = contract.functions.getMarketInfo(market_id).call()
        return {
            "question": market_info[0],
            "options": market_info[1],
            "startTime": market_info[2],
            "endTime": market_info[3],
            "resolved": market_info[4],
            "winningIndex": market_info[5]
        }
    except Exception as e:
        logger.error(f"Error getting market info for market {market_id}: {str(e)}")
        return None

def resolve_market(market_id, winning_index=0):
    """
    Resolve a market.
    
    Args:
        market_id: Market ID
        winning_index: Index of the winning option (default: 0 for "Yes")
        
    Returns:
        Bool indicating success
    """
    # Get contract
    w3 = get_web3()
    contract = get_contract()
    if not contract or not w3:
        return False
    
    # Get account details for the transaction
    private_key = os.environ.get("WALLET_PRIVATE_KEY")
    account_address = os.environ.get("WALLET_ADDRESS")
    
    if not private_key or not account_address:
        logger.error("Wallet credentials not configured")
        return False
        
    account_address = Web3.to_checksum_address(account_address)
    
    try:
        # Build transaction
        tx = contract.functions.resolveMarket(
            market_id,
            winning_index
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
                return False
                
            tx_hash = w3.eth.send_raw_transaction(raw_tx)
            tx_hash_hex = tx_hash.hex()
            logger.info(f"Transaction sent with hash: {tx_hash_hex}")
            
            # Wait for transaction receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            
            if receipt.status == 1:
                logger.info(f"Market {market_id} resolved successfully")
                return True
            else:
                logger.error(f"Failed to resolve market {market_id}: {receipt}")
                return False
                
        except Exception as e:
            logger.error(f"Error during transaction signing or sending: {str(e)}")
            return False
            
    except ContractLogicError as e:
        logger.error(f"Contract logic error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error resolving market: {str(e)}")
        return False

def main():
    """
    Main function to resolve test markets.
    """
    # List of test market IDs (24 and 25)
    market_ids = [24, 25]
    
    for market_id in market_ids:
        # Get market info
        market_info = get_market_info(market_id)
        
        if not market_info:
            logger.error(f"Could not get market info for market {market_id}")
            continue
            
        logger.info(f"Market {market_id}:")
        logger.info(f"  - Question: {market_info['question']}")
        logger.info(f"  - Options: {market_info['options']}")
        logger.info(f"  - Resolved: {market_info['resolved']}")
        
        # Check if already resolved
        if market_info['resolved']:
            logger.info(f"Market {market_id} is already resolved")
            continue
            
        # Resolve market
        success = resolve_market(market_id)
        if success:
            logger.info(f"Successfully resolved market {market_id}")
        else:
            logger.error(f"Failed to resolve market {market_id}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())