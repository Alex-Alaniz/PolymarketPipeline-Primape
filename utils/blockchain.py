"""
Blockchain utilities for the Polymarket pipeline.
Handles deployment of markets to ApeChain.
"""
import os
import json
import time
from typing import Dict, Tuple, Any, Optional, List

from config import APECHAIN_RPC, MARKET_FACTORY_ADDR, PRIVATE_KEY

# Try to import Web3
try:
    from web3 import Web3
    from web3.exceptions import TransactionNotFound
    WEB3_AVAILABLE = bool(APECHAIN_RPC and MARKET_FACTORY_ADDR and PRIVATE_KEY)
except ImportError:
    WEB3_AVAILABLE = False
    print("Warning: web3 not installed, blockchain integration disabled")

# Market factory ABI (simplified version)
MARKET_FACTORY_ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "question", "type": "string"},
            {"internalType": "string[]", "name": "options", "type": "string[]"},
            {"internalType": "uint256", "name": "expiryTimestamp", "type": "uint256"},
            {"internalType": "string", "name": "category", "type": "string"},
            {"internalType": "string", "name": "subCategory", "type": "string"},
            {"internalType": "string", "name": "bannerURI", "type": "string"}
        ],
        "name": "createMarket",
        "outputs": [{"internalType": "uint256", "name": "marketId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class BlockchainClient:
    """Client for blockchain operations."""
    
    def __init__(self):
        """Initialize the blockchain client."""
        self.web3 = None
        self.contract = None
        self.account = None
        
        if WEB3_AVAILABLE:
            try:
                # Initialize Web3 connection to ApeChain
                self.web3 = Web3(Web3.HTTPProvider(APECHAIN_RPC))
                
                # Check connection
                if self.web3.is_connected():
                    print(f"Connected to blockchain node at {APECHAIN_RPC}")
                    
                    # Set up account from private key
                    self.account = self.web3.eth.account.from_key(PRIVATE_KEY)
                    print(f"Using account: {self.account.address}")
                    
                    # Initialize contract
                    self.contract = self.web3.eth.contract(
                        address=self.web3.to_checksum_address(MARKET_FACTORY_ADDR),
                        abi=MARKET_FACTORY_ABI
                    )
                    print(f"Market factory contract initialized at {MARKET_FACTORY_ADDR}")
                else:
                    print(f"Failed to connect to blockchain node at {APECHAIN_RPC}")
            except Exception as e:
                print(f"Error initializing Web3 connection: {str(e)}")
    
    def create_market(self, market: Dict[str, Any], banner_uri: str) -> Tuple[bool, Optional[str]]:
        """
        Create a market on ApeChain.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_uri (str): URI to banner image (e.g., GitHub URL)
            
        Returns:
            Tuple[bool, Optional[str]]: Success status and transaction hash or error message
        """
        if not WEB3_AVAILABLE or not self.web3 or not self.contract or not self.account:
            print("Web3 not available, blockchain integration disabled")
            # For testing/demo purposes, simulate success
            return True, f"0x{'0'*64}"
        
        try:
            # Extract market information
            question = market.get("question")
            market_type = market.get("type", "binary")
            options = [option.get("name") for option in market.get("options", [])]
            
            # For binary markets, make sure options are Yes/No
            if market_type == "binary" and (not options or len(options) != 2):
                options = ["Yes", "No"]
            
            # Get expiry timestamp (in seconds)
            expiry = market.get("expiry")
            if expiry:
                # Convert from milliseconds to seconds if needed
                if expiry > 1000000000000:  # If in milliseconds
                    expiry = expiry // 1000
            else:
                # Default to 30 days from now
                expiry = int(time.time()) + (30 * 24 * 60 * 60)
            
            # Get category and sub-category
            category = market.get("category", "Other")
            sub_category = market.get("sub_category", "Other")
            
            # Build transaction
            transaction = self._build_transaction(
                question=question,
                options=options,
                expiry_timestamp=expiry,
                category=category,
                sub_category=sub_category,
                banner_uri=banner_uri
            )
            
            # Sign and send transaction
            signed_tx = self.web3.eth.account.sign_transaction(transaction, self.account.key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            print(f"Transaction sent: {tx_hash_hex}")
            
            # Wait for transaction to be mined
            receipt = self._wait_for_transaction_receipt(tx_hash_hex)
            
            if receipt and receipt.get("status") == 1:
                print(f"Transaction successful: {tx_hash_hex}")
                return True, tx_hash_hex
            else:
                print(f"Transaction failed: {tx_hash_hex}")
                return False, f"Transaction failed: {tx_hash_hex}"
            
        except Exception as e:
            print(f"Error creating market on blockchain: {str(e)}")
            return False, str(e)
    
    def _build_transaction(self, question: str, options: List[str], expiry_timestamp: int,
                          category: str, sub_category: str, banner_uri: str) -> Dict[str, Any]:
        """
        Build a transaction to create a market.
        
        Args:
            question (str): Market question
            options (List[str]): Market options
            expiry_timestamp (int): Expiry timestamp in seconds
            category (str): Market category
            sub_category (str): Market sub-category
            banner_uri (str): URI to banner image
            
        Returns:
            Dict[str, Any]: Transaction data
        """
        # Get function data for createMarket
        function_data = self.contract.functions.createMarket(
            question,
            options,
            expiry_timestamp,
            category,
            sub_category,
            banner_uri
        ).build_transaction({
            "from": self.account.address,
            "nonce": self.web3.eth.get_transaction_count(self.account.address),
            "gas": 3000000,  # Gas limit
            "gasPrice": self.web3.eth.gas_price,
            "chainId": self.web3.eth.chain_id
        })
        
        return function_data
    
    def _wait_for_transaction_receipt(self, tx_hash: str, timeout: int = 120, poll_interval: int = 0.1) -> Optional[Dict[str, Any]]:
        """
        Wait for a transaction receipt.
        
        Args:
            tx_hash (str): Transaction hash
            timeout (int): Timeout in seconds
            poll_interval (int): Poll interval in seconds
            
        Returns:
            Optional[Dict[str, Any]]: Transaction receipt or None if timeout
        """
        start_time = time.time()
        while time.time() < start_time + timeout:
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt:
                    return receipt
            except TransactionNotFound:
                pass
            
            time.sleep(poll_interval)
        
        return None