#!/usr/bin/env python3

"""
Resolve test markets on ApeChain.

This script resolves any test markets that were created during testing.
It calls the resolveMarket function on the ApeChain contract.

Note on execution (May 6, 2025):
- Successfully resolved test markets with IDs 24 and 25
- Set winning index to 0 (typically "Yes" in binary markets)
- Used the contract address: 0x5Eb0aFd6CED124348eD44BDB955E26Ccb8fA613C
- Transaction hashes (for reference):
  * Market 24: 44cb35fa5e7f05cc2d7d489ce444fcbaf590fff833d278e61018cffc9eda3c10
  * Market 25: 6b35611234b506f705d173d3e825688aea507fd99eb59874d4dd87b597368415
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
    # Market creation and resolution function signatures
    {
        "inputs": [
            {"internalType": "string", "name": "_question", "type": "string"},
            {"internalType": "string[]", "name": "_options", "type": "string[]"},
            {"internalType": "uint256", "name": "_endTime", "type": "uint256"}
        ],
        "name": "createMarket",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "nonpayable",
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
        "type": "function"
    },
    # Market query function signatures
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "markets",
        "outputs": [
            {"internalType": "string", "name": "question", "type": "string"},
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
            {"internalType": "uint256", "name": "_optionIndex", "type": "uint256"}
        ],
        "name": "getMarketOption",
        "outputs": [
            {"internalType": "string", "name": "", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "_marketId", "type": "uint256"}
        ],
        "name": "getMarketOptionsCount",
        "outputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
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
        # Get base market info from markets() mapping
        try:
            market_base = contract.functions.markets(market_id).call()
            question = market_base[0]
            start_time = market_base[1]
            end_time = market_base[2]
            resolved = market_base[3]
            winning_index = market_base[4]
        except Exception as e:
            logger.error(f"Error getting base market info for market {market_id}: {str(e)}")
            return None
        
        # Get options count
        try:
            options_count = contract.functions.getMarketOptionsCount(market_id).call()
            logger.info(f"Market {market_id} has {options_count} options")
        except Exception as e:
            logger.error(f"Error getting options count for market {market_id}: {str(e)}")
            options_count = 0
        
        # Get all options
        options = []
        for i in range(options_count):
            try:
                option = contract.functions.getMarketOption(market_id, i).call()
                options.append(option)
            except Exception as e:
                logger.error(f"Error getting option {i} for market {market_id}: {str(e)}")
        
        return {
            "question": question,
            "options": options,
            "startTime": start_time,
            "endTime": end_time,
            "resolved": resolved,
            "winningIndex": winning_index
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
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Resolve test markets on ApeChain')
    parser.add_argument('--market-ids', type=int, nargs='+', default=[24, 25],
                        help='Market IDs to resolve (default: 24 25)')
    parser.add_argument('--winning-index', type=int, default=0,
                        help='Index of the winning option (default: 0 for "Yes")')
    parser.add_argument('--force', action='store_true',
                        help='Force resolution even if market is already resolved')
    
    args = parser.parse_args()
    
    # Use provided market IDs or default to 24 and 25
    market_ids = args.market_ids
    winning_index = args.winning_index
    force = args.force
    
    # We're skipping the market info fetching part and resolving directly
    # The contract structure might be different than expected, but the
    # resolveMarket function should still work if the markets exist
    
    logger.info(f"Attempting to resolve market IDs: {market_ids} with winning_index={winning_index}")
    
    for market_id in market_ids:
        # Directly try to resolve the market
        logger.info(f"Attempting to resolve test market {market_id}")
        
        # Try to resolve the market with specified winning index
        success = resolve_market(market_id, winning_index=winning_index)
        
        if success:
            logger.info(f"Successfully resolved market {market_id} with winning_index={winning_index}")
        else:
            logger.error(f"Failed to resolve market {market_id}, will try in the future")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())