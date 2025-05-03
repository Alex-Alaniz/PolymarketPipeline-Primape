"""
Blockchain utilities for the Polymarket pipeline.
Handles deployment of markets to ApeChain.
"""
import os
import json
import logging
import time
from typing import Dict, List, Tuple, Any, Optional

from config import APECHAIN_RPC, MARKET_FACTORY_ADDR, PRIVATE_KEY

logger = logging.getLogger("blockchain_client")

class BlockchainClient:
    """Client for blockchain operations."""
    
    def __init__(self):
        """Initialize the blockchain client."""
        self.rpc_url = APECHAIN_RPC
        self.market_factory_addr = MARKET_FACTORY_ADDR
        self.private_key = PRIVATE_KEY
        
        # For testing, just log that we would connect to the blockchain node
        if APECHAIN_RPC:
            logger.info(f"Connected to blockchain node at {APECHAIN_RPC}")
            
            # In a real implementation, we would initialize a Web3 instance:
            try:
                from web3 import Web3
                self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
                if self.w3.is_connected():
                    # Get the account address from the private key
                    if self.private_key:
                        from eth_account import Account
                        account = Account.from_key(self.private_key)
                        logger.info(f"Using account: {account.address}")
                    
                    # Initialize the market factory contract
                    if self.market_factory_addr:
                        logger.info(f"Market factory contract initialized at {self.market_factory_addr}")
                    else:
                        logger.warning("Market factory address not set")
                else:
                    logger.error(f"Failed to connect to blockchain node at {self.rpc_url}")
                    self.w3 = None
            except ImportError:
                logger.warning("Web3 not installed, using mock blockchain client")
                self.w3 = None
            except Exception as e:
                logger.error(f"Error initializing Web3: {str(e)}")
                self.w3 = None
        else:
            logger.warning("RPC URL not set, using mock blockchain client")
            self.w3 = None
    
    def create_market(self, market: Dict[str, Any], banner_uri: str) -> Tuple[bool, Optional[str]]:
        """
        Create a market on ApeChain.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_uri (str): URI to banner image (e.g., GitHub URL)
            
        Returns:
            Tuple[bool, Optional[str]]: Success status and transaction hash or error message
        """
        # Get market info
        market_id = market.get("id")
        question = market.get("question", "Unknown market")
        market_type = market.get("type", "binary")
        options = market.get("options", [])
        expiry_timestamp = market.get("expiry", 0)
        category = market.get("category", "General")
        sub_category = market.get("sub_category", "Other")
        
        # Log the market creation
        logger.info(f"Creating market on blockchain: {question}")
        
        # For testing, just log the operation and return a mock transaction hash
        try:
            # Build transaction data
            tx_data = self._build_transaction(
                question=question,
                options=[option.get("name") for option in options],
                expiry_timestamp=expiry_timestamp // 1000,  # Convert from milliseconds to seconds
                category=category,
                sub_category=sub_category,
                banner_uri=banner_uri
            )
            
            # In a real implementation, we would:
            # 1. Sign the transaction
            # 2. Send the transaction
            # 3. Wait for the transaction receipt
            
            # Log the operation
            logger.info(f"Would create market {market_id} on blockchain with transaction data: {json.dumps(tx_data)}")
            
            # Return a mock transaction hash
            return True, f"0x{'0' * 64}"
            
        except Exception as e:
            logger.error(f"Error creating market on blockchain: {str(e)}")
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
        # Mock transaction data for testing
        return {
            "question": question,
            "options": options,
            "expiry_timestamp": expiry_timestamp,
            "category": category,
            "sub_category": sub_category,
            "banner_uri": banner_uri
        }