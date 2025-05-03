"""
Task 1: Slack Integration + Market Data Fetching

This module handles:
1. Connecting to Slack and setting up the client
2. Fetching market data from Polymarket
3. Posting formatted market data to Slack for initial approval
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional

# Import utility modules
from utils.polymarket import PolymarketExtractor
from utils.messaging import MessagingClient
from utils.database import store_market

# Setup logging
logger = logging.getLogger("task1")

class SlackMarketPoster:
    """
    Class for fetching market data and posting to Slack.
    """
    
    def __init__(self, db=None, Market=None, ApprovalEvent=None):
        """
        Initialize with optional database models for persistence.
        
        Args:
            db: SQLAlchemy database instance (optional)
            Market: Market model class (optional)
            ApprovalEvent: ApprovalEvent model class (optional)
        """
        self.db = db
        self.Market = Market
        self.ApprovalEvent = ApprovalEvent
        
        # Initialize components
        self.polymarket_extractor = PolymarketExtractor()
        self.messaging_client = MessagingClient()
        
        # Validation
        if not self.polymarket_extractor:
            logger.error("Failed to initialize Polymarket extractor")
            raise RuntimeError("Polymarket extractor initialization failed")
            
        if not self.messaging_client:
            logger.error("Failed to initialize messaging client")
            raise RuntimeError("Messaging client initialization failed")
    
    def run(self) -> List[Dict[str, Any]]:
        """
        Run the task to fetch market data and post to Slack.
        
        Returns:
            List[Dict[str, Any]]: List of processed markets with message IDs
        """
        logger.info("Starting Task 1: Fetching market data and posting to Slack")
        
        # Step 1: Fetch market data from Polymarket
        markets = self.fetch_market_data()
        
        if not markets:
            logger.warning("No markets fetched from Polymarket")
            return []
        
        logger.info(f"Fetched {len(markets)} markets from Polymarket")
        
        # Step 2: Post each market to Slack for initial approval
        posted_markets = []
        
        for market in markets:
            market_id = market.get("id")
            
            if not market_id:
                logger.warning("Market has no ID, skipping")
                continue
            
            # Post market to Slack
            logger.info(f"Posting market {market_id} to Slack")
            message_id = self.post_market_to_slack(market)
            
            if message_id:
                # Add message ID to market data
                market["slack_message_id"] = message_id
                market["status"] = "pending_initial_approval"
                posted_markets.append(market)
                
                # Store in database if available
                if self.db and self.Market:
                    store_market(self.db, self.Market, market)
            else:
                logger.error(f"Failed to post market {market_id} to Slack")
        
        logger.info(f"Posted {len(posted_markets)} markets to Slack")
        return posted_markets
    
    def fetch_market_data(self) -> List[Dict[str, Any]]:
        """
        Fetch market data from Polymarket.
        
        Returns:
            List[Dict[str, Any]]: List of market data dictionaries
        """
        try:
            return self.polymarket_extractor.extract_data()
        except Exception as e:
            logger.error(f"Error fetching market data: {str(e)}")
            return []
    
    def post_market_to_slack(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Post a market to Slack for initial approval.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        try:
            return self.messaging_client.post_initial_market(market)
        except Exception as e:
            logger.error(f"Error posting market to Slack: {str(e)}")
            return None

# Standalone function for running this task
def run_task(db=None, Market=None, ApprovalEvent=None) -> List[Dict[str, Any]]:
    """
    Run Task 1: Fetch market data and post to Slack.
    
    Args:
        db: SQLAlchemy database instance (optional)
        Market: Market model class (optional)
        ApprovalEvent: ApprovalEvent model class (optional)
        
    Returns:
        List[Dict[str, Any]]: List of processed markets with message IDs
    """
    task = SlackMarketPoster(db, Market, ApprovalEvent)
    return task.run()

# For standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    markets = run_task()
    print(f"Posted {len(markets)} markets to Slack")