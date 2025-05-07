#!/usr/bin/env python3

"""
Test Market ID Retrieval from Transaction

This script tests the get_deployed_market_id_from_tx function
to make sure it can retrieve a market ID from a transaction hash.
"""

import os
import logging
from main import app
from utils.apechain import get_deployed_market_id_from_tx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_get_market_id")

# Test transaction hash
# This should be a real transaction hash from a deployed market
TX_HASH = "0x8d55d21c98e1c3c98b9d79edc054e7ad8e55de01a445a51b1f8f154aeabbccb1"

def main():
    """Main function to test market ID retrieval."""
    try:
        market_id = get_deployed_market_id_from_tx(TX_HASH)
        
        if market_id:
            logger.info(f"Successfully retrieved market ID from transaction: {market_id}")
            return 0
        else:
            logger.error(f"Failed to retrieve market ID from transaction {TX_HASH}")
            return 1
    except Exception as e:
        logger.error(f"Error retrieving market ID: {str(e)}")
        return 1

if __name__ == "__main__":
    main()