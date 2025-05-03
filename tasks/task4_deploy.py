"""
Task 4: Deployment to ApeChain + Frontend Push

This module handles:
1. Pushing approved banner images to the frontend repository
2. Deploying market data to ApeChain smart contracts
3. Updating the deployment status in the database
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple

# Import utility modules
from utils.github import GitHubClient
from utils.blockchain import BlockchainClient
from utils.database import update_market_status
from config import FRONTEND_IMG_PATH

# Setup logging
logger = logging.getLogger("task4")

class DeploymentManager:
    """
    Class for deploying markets to ApeChain and frontend.
    """
    
    def __init__(self, db=None, Market=None):
        """
        Initialize with optional database models for persistence.
        
        Args:
            db: SQLAlchemy database instance (optional)
            Market: Market model class (optional)
        """
        self.db = db
        self.Market = Market
        
        # Initialize components
        self.github_client = GitHubClient()
        self.blockchain_client = BlockchainClient()
        
        # Validation
        if not self.github_client:
            logger.error("Failed to initialize GitHub client")
            raise RuntimeError("GitHub client initialization failed")
            
        if not self.blockchain_client:
            logger.error("Failed to initialize blockchain client")
            raise RuntimeError("Blockchain client initialization failed")
    
    def run(self, final_approved_markets: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Run the task to deploy markets to ApeChain and frontend.
        
        Args:
            final_approved_markets (List[Dict[str, Any]]): List of markets with final approval
            
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: 
                (deployed_markets, failed_markets)
        """
        logger.info("Starting Task 4: Deploying markets to ApeChain and frontend")
        
        deployed_markets = []
        failed_markets = []
        
        for market in final_approved_markets:
            market_id = market.get("id")
            banner_path = market.get("banner_path")
            
            if not market_id or not banner_path:
                logger.warning(f"Market {market_id} missing required data, skipping")
                failed_markets.append(market)
                continue
            
            # Step 1: Deploy banner to frontend repository
            logger.info(f"Deploying banner for market {market_id} to frontend repository")
            banner_success, banner_result = self.deploy_banner(market_id, banner_path)
            
            if not banner_success:
                logger.error(f"Failed to deploy banner for market {market_id}: {banner_result}")
                market["status"] = "banner_deployment_failed"
                market["failure_reason"] = banner_result
                failed_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(
                        self.db, 
                        self.Market, 
                        market_id, 
                        "banner_deployment_failed", 
                        failure_reason=banner_result
                    )
                continue
            
            # Store GitHub commit URL
            market["github_commit_url"] = banner_result
            
            # Construct banner URI for the smart contract
            banner_uri = f"{FRONTEND_IMG_PATH}/{market_id}.png"
            
            # Step 2: Deploy market to blockchain
            logger.info(f"Deploying market {market_id} to blockchain")
            blockchain_success, blockchain_result = self.deploy_market(market, banner_uri)
            
            if not blockchain_success:
                logger.error(f"Failed to deploy market {market_id} to blockchain: {blockchain_result}")
                market["status"] = "blockchain_deployment_failed"
                market["failure_reason"] = blockchain_result
                failed_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(
                        self.db, 
                        self.Market, 
                        market_id, 
                        "blockchain_deployment_failed", 
                        github_commit=banner_result,
                        banner_uri=banner_uri,
                        failure_reason=blockchain_result
                    )
                continue
            
            # Store transaction hash
            market["blockchain_tx"] = blockchain_result
            
            # Market successfully deployed
            logger.info(f"Market {market_id} successfully deployed")
            market["status"] = "deployed"
            deployed_markets.append(market)
            
            # Update database if available
            if self.db and self.Market:
                update_market_status(
                    self.db, 
                    self.Market, 
                    market_id, 
                    "deployed", 
                    github_commit=banner_result,
                    banner_uri=banner_uri,
                    blockchain_tx=blockchain_result
                )
        
        # Log summary
        logger.info(f"Task 4 completed: {len(deployed_markets)} markets deployed, {len(failed_markets)} failed")
        
        return deployed_markets, failed_markets
    
    def deploy_banner(self, market_id: str, banner_path: str) -> Tuple[bool, str]:
        """
        Deploy a banner to the frontend repository.
        
        Args:
            market_id (str): Market ID
            banner_path (str): Path to banner image
            
        Returns:
            Tuple[bool, str]: Success status and commit URL or error message
        """
        try:
            return self.github_client.push_banner(market_id, banner_path)
        except Exception as e:
            logger.error(f"Error deploying banner: {str(e)}")
            return False, str(e)
    
    def deploy_market(self, market: Dict[str, Any], banner_uri: str) -> Tuple[bool, str]:
        """
        Deploy a market to ApeChain.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_uri (str): URI to banner image
            
        Returns:
            Tuple[bool, str]: Success status and transaction hash or error message
        """
        try:
            return self.blockchain_client.create_market(market, banner_uri)
        except Exception as e:
            logger.error(f"Error deploying market to blockchain: {str(e)}")
            return False, str(e)

# Standalone function for running this task
def run_task(final_approved_markets: List[Dict[str, Any]], db=None, Market=None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run Task 4: Deploy markets to ApeChain and frontend.
    
    Args:
        final_approved_markets (List[Dict[str, Any]]): List of markets with final approval
        db: SQLAlchemy database instance (optional)
        Market: Market model class (optional)
        
    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]: 
            (deployed_markets, failed_markets)
    """
    task = DeploymentManager(db, Market)
    return task.run(final_approved_markets)

# For standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Mock data for testing
    final_approved_markets = [
        {
            "id": "market1",
            "question": "Will Bitcoin reach $100,000 by the end of 2025?",
            "banner_path": "/tmp/market1.png",
            "category": "Crypto",
            "sub_category": "Bitcoin"
        }
    ]
    deployed, failed = run_task(final_approved_markets)