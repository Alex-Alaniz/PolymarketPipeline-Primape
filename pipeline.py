#!/usr/bin/env python3
"""
Polymarket Pipeline

This script automates the process of extracting Polymarket data, facilitating approval via
Slack/Discord, generating banner images with OpenAI, and deploying markets to ApeChain.

The pipeline follows these steps:
1. Extract Polymarket data using transform_polymarket_data_capitalized.py
2. Post markets to Slack/Discord for initial approval
3. Generate banner images for approved markets using OpenAI
4. Post markets with banners to Slack/Discord for final approval
5. Deploy approved markets (push banner to frontend repo & create market on ApeChain)
6. Generate summary reports and logs
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Import configuration
from config import (
    POLYMARKET_BASE_URL, APPROVAL_WINDOW_MINUTES, MESSAGING_PLATFORM,
    DATA_DIR, TMP_DIR, LOGS_DIR, STATE_FILE
)

# Import utility modules
try:
    from utils.logging_utils import get_logger
    from utils.state import StateManager
    from utils.polymarket import PolymarketExtractor
    from utils.messaging import MessagingClient
    from utils.banner import BannerGenerator
    from utils.github import GitHubClient
    from utils.blockchain import BlockchainClient
except ImportError as e:
    print(f"Error importing utility modules: {e}")
    print("Creating basic utility modules...")
    # Create directory structure
    os.makedirs("utils", exist_ok=True)
    with open("utils/__init__.py", "w") as f:
        f.write('"""Utility modules for the Polymarket pipeline."""\n')

# Configure logger
try:
    logger = get_logger("pipeline")
except NameError:
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger("pipeline")

class PolymarketPipeline:
    """Main pipeline for processing Polymarket data."""
    
    def __init__(self):
        """Initialize the pipeline."""
        logger.info("Initializing Polymarket pipeline")
        
        # Create directories if they don't exist
        for directory in [DATA_DIR, TMP_DIR, LOGS_DIR]:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize components
        try:
            self.state_manager = StateManager()
        except:
            self.state_manager = None
            logger.error("Failed to initialize StateManager")
        
        try:
            self.polymarket_extractor = PolymarketExtractor()
        except:
            self.polymarket_extractor = None
            logger.error("Failed to initialize PolymarketExtractor")
        
        try:
            self.messaging_client = MessagingClient()
        except:
            self.messaging_client = None
            logger.error("Failed to initialize MessagingClient")
        
        try:
            self.banner_generator = BannerGenerator()
        except:
            self.banner_generator = None
            logger.error("Failed to initialize BannerGenerator")
        
        try:
            self.github_client = GitHubClient()
        except:
            self.github_client = None
            logger.error("Failed to initialize GitHubClient")
        
        try:
            self.blockchain_client = BlockchainClient()
        except:
            self.blockchain_client = None
            logger.error("Failed to initialize BlockchainClient")
        
        # Pipeline state
        self.markets = []
        self.summary = {
            "start_time": datetime.now().isoformat(),
            "markets_processed": 0,
            "markets_approved": 0,
            "markets_rejected": 0,
            "markets_deployed": 0,
            "markets_failed": 0,
            "markets": {}
        }
    
    def run(self):
        """Run the pipeline."""
        logger.info("Starting Polymarket pipeline")
        
        try:
            # Step 1: Extract Polymarket data
            logger.info("Extracting Polymarket data")
            if self.polymarket_extractor:
                self.markets = self.polymarket_extractor.extract_data()
                if not self.markets:
                    logger.error("No markets extracted from Polymarket")
                    return 1
                logger.info(f"Extracted {len(self.markets)} markets from Polymarket")
            else:
                logger.error("Polymarket extractor not available")
                return 1
            
            # Process each market
            for market in self.markets:
                market_id = market.get("id")
                if not market_id:
                    logger.warning("Market has no ID, skipping")
                    continue
                
                logger.info(f"Processing market {market_id}: {market.get('question', 'Unknown')}")
                self.summary["markets_processed"] += 1
                
                # Initialize market in summary
                self.summary["markets"][market_id] = {
                    "id": market_id,
                    "question": market.get("question"),
                    "status": "processing",
                    "timeline": [
                        {"step": "start", "time": datetime.now().isoformat()}
                    ]
                }
                
                # Step 2: Post market for initial approval
                logger.info(f"Posting market {market_id} for initial approval")
                approval_status, message_id = self.initial_approval(market)
                
                self.summary["markets"][market_id]["timeline"].append({
                    "step": "initial_approval",
                    "time": datetime.now().isoformat(),
                    "status": approval_status
                })
                
                if approval_status != "approved":
                    logger.info(f"Market {market_id} was not approved in the initial stage ({approval_status})")
                    self.summary["markets"][market_id]["status"] = approval_status
                    self.summary["markets_rejected"] += 1
                    continue
                
                # Step 3: Generate banner for approved market
                logger.info(f"Generating banner for market {market_id}")
                banner_path = self.generate_banner(market)
                
                if not banner_path:
                    logger.error(f"Failed to generate banner for market {market_id}")
                    self.summary["markets"][market_id]["status"] = "failed"
                    self.summary["markets"][market_id]["failure_reason"] = "banner_generation_failed"
                    self.summary["markets_failed"] += 1
                    continue
                
                self.summary["markets"][market_id]["timeline"].append({
                    "step": "banner_generation",
                    "time": datetime.now().isoformat(),
                    "status": "complete",
                    "banner_path": banner_path
                })
                
                # Step 4: Post market with banner for final approval
                logger.info(f"Posting market {market_id} with banner for final approval")
                approval_status, message_id = self.final_approval(market, banner_path)
                
                self.summary["markets"][market_id]["timeline"].append({
                    "step": "final_approval",
                    "time": datetime.now().isoformat(),
                    "status": approval_status
                })
                
                if approval_status != "approved":
                    logger.info(f"Market {market_id} was not approved in the final stage ({approval_status})")
                    self.summary["markets"][market_id]["status"] = approval_status
                    self.summary["markets_rejected"] += 1
                    continue
                
                # Step 5a: Deploy banner to frontend repository
                logger.info(f"Deploying banner for market {market_id}")
                banner_success, banner_result = self.deploy_banner(market_id, banner_path)
                
                if not banner_success:
                    logger.error(f"Failed to deploy banner for market {market_id}: {banner_result}")
                    self.summary["markets"][market_id]["status"] = "failed"
                    self.summary["markets"][market_id]["failure_reason"] = "banner_deployment_failed"
                    self.summary["markets_failed"] += 1
                    continue
                
                self.summary["markets"][market_id]["timeline"].append({
                    "step": "banner_deployment",
                    "time": datetime.now().isoformat(),
                    "status": "complete",
                    "commit_url": banner_result
                })
                
                # Construct banner URI for the smart contract
                banner_uri = f"{FRONTEND_IMG_PATH}/{market_id}.png"
                
                # Step 5b: Deploy market to blockchain
                logger.info(f"Deploying market {market_id} to blockchain")
                market_success, market_result = self.deploy_market(market, banner_uri)
                
                if not market_success:
                    logger.error(f"Failed to deploy market {market_id} to blockchain: {market_result}")
                    self.summary["markets"][market_id]["status"] = "failed"
                    self.summary["markets"][market_id]["failure_reason"] = "blockchain_deployment_failed"
                    self.summary["markets_failed"] += 1
                    continue
                
                self.summary["markets"][market_id]["timeline"].append({
                    "step": "market_deployment",
                    "time": datetime.now().isoformat(),
                    "status": "complete",
                    "tx_hash": market_result
                })
                
                # Market successfully deployed
                logger.info(f"Market {market_id} successfully deployed")
                self.summary["markets"][market_id]["status"] = "deployed"
                self.summary["markets_deployed"] += 1
            
            # Step 6: Post summary
            self.summary["end_time"] = datetime.now().isoformat()
            self.post_summary()
            
            logger.info("Pipeline completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            self.summary["end_time"] = datetime.now().isoformat()
            self.summary["status"] = "failed"
            self.summary["error"] = str(e)
            
            # Try to post summary even if pipeline failed
            try:
                self.post_summary()
            except:
                pass
            
            return 1
    
    def initial_approval(self, market: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """
        Post market for initial approval.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Tuple[str, Optional[str]]: Status and message ID
        """
        if not self.messaging_client:
            logger.error("Messaging client not available for initial approval")
            return "failed", None
        
        try:
            message_id = self.messaging_client.post_initial_market(market)
            if not message_id:
                logger.error("Failed to post market for initial approval")
                return "failed", None
            
            # Check for approval
            logger.info(f"Waiting for initial approval of market {market.get('id')}")
            approval_status, reason = self.messaging_client.check_approval(
                message_id, APPROVAL_WINDOW_MINUTES
            )
            
            logger.info(f"Initial approval status: {approval_status} ({reason})")
            return approval_status, message_id
            
        except Exception as e:
            logger.error(f"Error in initial approval: {str(e)}")
            return "failed", None
    
    def generate_banner(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Generate banner for market.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Path to banner image, or None if failed
        """
        if not self.banner_generator:
            logger.error("Banner generator not available")
            return None
        
        try:
            banner_path = self.banner_generator.generate_banner(market)
            return banner_path
        except Exception as e:
            logger.error(f"Error generating banner: {str(e)}")
            return None
    
    def final_approval(self, market: Dict[str, Any], banner_path: str) -> Tuple[str, Optional[str]]:
        """
        Post market with banner for final approval.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_path (str): Path to banner image
            
        Returns:
            Tuple[str, Optional[str]]: Status and message ID
        """
        if not self.messaging_client:
            logger.error("Messaging client not available for final approval")
            return "failed", None
        
        try:
            message_id = self.messaging_client.post_final_market(market, banner_path)
            if not message_id:
                logger.error("Failed to post market with banner for final approval")
                return "failed", None
            
            # Check for approval
            logger.info(f"Waiting for final approval of market {market.get('id')}")
            approval_status, reason = self.messaging_client.check_approval(
                message_id, APPROVAL_WINDOW_MINUTES
            )
            
            logger.info(f"Final approval status: {approval_status} ({reason})")
            return approval_status, message_id
            
        except Exception as e:
            logger.error(f"Error in final approval: {str(e)}")
            return "failed", None
    
    def deploy_banner(self, market_id: str, banner_path: str) -> Tuple[bool, Optional[str]]:
        """
        Deploy banner to frontend repository.
        
        Args:
            market_id (str): Market ID
            banner_path (str): Path to banner image
            
        Returns:
            Tuple[bool, str]: Success status and commit URL or error message
        """
        if not self.github_client:
            logger.error("GitHub client not available")
            return False, "GitHub client not available"
        
        try:
            success, result = self.github_client.push_banner(market_id, banner_path)
            return success, result
        except Exception as e:
            logger.error(f"Error deploying banner: {str(e)}")
            return False, str(e)
    
    def deploy_market(self, market: Dict[str, Any], banner_uri: str) -> Tuple[bool, Optional[str]]:
        """
        Deploy market to blockchain.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_uri (str): URI to banner image
            
        Returns:
            Tuple[bool, str]: Success status and transaction hash or error message
        """
        if not self.blockchain_client:
            logger.error("Blockchain client not available")
            return False, "Blockchain client not available"
        
        try:
            success, result = self.blockchain_client.create_market(market, banner_uri)
            return success, result
        except Exception as e:
            logger.error(f"Error deploying market: {str(e)}")
            return False, str(e)
    
    def post_summary(self):
        """Post summary to messaging platform."""
        if not self.messaging_client:
            logger.error("Messaging client not available for posting summary")
            return
        
        try:
            self.messaging_client.post_summary(self.summary)
            logger.info("Posted pipeline summary to messaging platform")
        except Exception as e:
            logger.error(f"Error posting summary: {str(e)}")

# For testing purposes
if __name__ == "__main__":
    pipeline = PolymarketPipeline()
    sys.exit(pipeline.run())