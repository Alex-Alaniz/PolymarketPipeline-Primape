"""
Task 3: Image Generation + Final Approval

This module handles:
1. Generating banner images for approved markets using OpenAI
2. Posting markets with banners to Slack for final approval
3. Tracking which markets receive final approval
"""
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

# Import utility modules
from utils.banner import BannerGenerator
from utils.messaging import MessagingClient
from utils.database import update_market_status, store_approval_event

# Setup logging
logger = logging.getLogger("task3")

class BannerGenerationApproval:
    """
    Class for generating banners and getting final approvals.
    """
    
    def __init__(self, db=None, Market=None, ApprovalEvent=None, approval_timeout_minutes=30):
        """
        Initialize with optional database models for persistence.
        
        Args:
            db: SQLAlchemy database instance (optional)
            Market: Market model class (optional)
            ApprovalEvent: ApprovalEvent model class (optional)
            approval_timeout_minutes (int): Timeout in minutes for approval
        """
        self.db = db
        self.Market = Market
        self.ApprovalEvent = ApprovalEvent
        self.approval_timeout_minutes = approval_timeout_minutes
        
        # Initialize components
        self.banner_generator = BannerGenerator()
        self.messaging_client = MessagingClient()
        
        # Validation
        if not self.banner_generator:
            logger.error("Failed to initialize banner generator")
            raise RuntimeError("Banner generator initialization failed")
            
        if not self.messaging_client:
            logger.error("Failed to initialize messaging client")
            raise RuntimeError("Messaging client initialization failed")
    
    def run(self, approved_markets: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Run the task to generate banners and get final approvals.
        
        Args:
            approved_markets (List[Dict[str, Any]]): List of markets with initial approval
            
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]: 
                (final_approved_markets, rejected_markets, failed_markets)
        """
        logger.info("Starting Task 3: Generating banners and getting final approvals")
        
        # Step 1: Generate banners for each approved market
        markets_with_banners = []
        failed_banner_markets = []
        
        for market in approved_markets:
            market_id = market.get("id")
            
            if not market_id:
                logger.warning("Market has no ID, skipping")
                continue
            
            # Generate banner
            logger.info(f"Generating banner for market {market_id}")
            banner_path = self.generate_banner(market)
            
            if banner_path:
                market["banner_path"] = banner_path
                market["status"] = "banner_generated"
                markets_with_banners.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(
                        self.db, 
                        self.Market, 
                        market_id, 
                        "banner_generated",
                        banner_path=banner_path
                    )
            else:
                logger.error(f"Failed to generate banner for market {market_id}")
                market["status"] = "banner_failed"
                failed_banner_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "banner_failed")
        
        # Step 2: Post markets with banners for final approval
        pending_final_markets = []
        
        for market in markets_with_banners:
            market_id = market.get("id")
            banner_path = market.get("banner_path")
            
            # Post market with banner for final approval
            logger.info(f"Posting market {market_id} with banner for final approval")
            message_id = self.post_market_with_banner(market, banner_path)
            
            if message_id:
                market["final_slack_message_id"] = message_id
                market["status"] = "pending_final_approval"
                pending_final_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(
                        self.db, 
                        self.Market, 
                        market_id, 
                        "pending_final_approval",
                        final_message_id=message_id
                    )
            else:
                logger.error(f"Failed to post market {market_id} with banner to Slack")
                market["status"] = "final_post_failed"
                failed_banner_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "final_post_failed")
        
        # Step 3: Check final approvals
        final_approved_markets = []
        final_rejected_markets = []
        
        for market in pending_final_markets:
            market_id = market.get("id")
            message_id = market.get("final_slack_message_id")
            
            # Check approval status
            logger.info(f"Checking final approval status for market {market_id}")
            approval_status, reason = self.check_final_approval(message_id)
            
            # Update market status based on approval
            if approval_status == "approved":
                logger.info(f"Market {market_id} received final approval: {reason}")
                market["status"] = "final_approved"
                market["final_approval_reason"] = reason
                final_approved_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "final_approved")
                
                # Store approval event
                if self.db and self.ApprovalEvent:
                    store_approval_event(
                        self.db,
                        self.ApprovalEvent,
                        market_id,
                        "final",
                        "approved",
                        message_id,
                        reason
                    )
                    
            elif approval_status == "rejected":
                logger.info(f"Market {market_id} was rejected in final approval: {reason}")
                market["status"] = "final_rejected"
                market["final_rejection_reason"] = reason
                final_rejected_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "final_rejected")
                
                # Store approval event
                if self.db and self.ApprovalEvent:
                    store_approval_event(
                        self.db,
                        self.ApprovalEvent,
                        market_id,
                        "final",
                        "rejected",
                        message_id,
                        reason
                    )
                    
            else:  # timeout or error
                logger.warning(f"Market {market_id} final approval timed out or errored: {reason}")
                market["status"] = "final_timeout"
                market["final_timeout_reason"] = reason
                final_rejected_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "final_timeout")
                
                # Store approval event
                if self.db and self.ApprovalEvent:
                    store_approval_event(
                        self.db,
                        self.ApprovalEvent,
                        market_id,
                        "final",
                        "timeout",
                        message_id,
                        reason
                    )
        
        # Log summary
        logger.info(
            f"Task 3 completed: {len(final_approved_markets)} final approved, "
            f"{len(final_rejected_markets)} final rejected, {len(failed_banner_markets)} failed"
        )
        
        return final_approved_markets, final_rejected_markets, failed_banner_markets
    
    def generate_banner(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Generate a banner for a market.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Path to banner image, or None if failed
        """
        try:
            return self.banner_generator.generate_banner(market)
        except Exception as e:
            logger.error(f"Error generating banner: {str(e)}")
            return None
    
    def post_market_with_banner(self, market: Dict[str, Any], banner_path: str) -> Optional[str]:
        """
        Post a market with banner to Slack for final approval.
        
        Args:
            market (Dict[str, Any]): Market data
            banner_path (str): Path to banner image
            
        Returns:
            Optional[str]: Message ID if successful, None otherwise
        """
        try:
            return self.messaging_client.post_final_market(market, banner_path)
        except Exception as e:
            logger.error(f"Error posting market with banner to Slack: {str(e)}")
            return None
    
    def check_final_approval(self, message_id: str) -> Tuple[str, Optional[str]]:
        """
        Check if a market has received final approval.
        
        Args:
            message_id (str): Slack message ID to check
            
        Returns:
            Tuple[str, Optional[str]]: Status and reason
                Status can be: "approved", "rejected", "timeout", "error"
        """
        try:
            # Use the messaging client to check approval
            status, reason = self.messaging_client.check_approval(
                message_id, 
                self.approval_timeout_minutes
            )
            return status, reason
            
        except Exception as e:
            logger.error(f"Error checking final approval: {str(e)}")
            return "error", str(e)

# Standalone function for running this task
def run_task(approved_markets: List[Dict[str, Any]], db=None, Market=None, ApprovalEvent=None, 
             approval_timeout_minutes=30) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run Task 3: Generate banners and get final approvals.
    
    Args:
        approved_markets (List[Dict[str, Any]]): List of markets with initial approval
        db: SQLAlchemy database instance (optional)
        Market: Market model class (optional)
        ApprovalEvent: ApprovalEvent model class (optional)
        approval_timeout_minutes (int): Timeout in minutes for approval
        
    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]: 
            (final_approved_markets, rejected_markets, failed_markets)
    """
    task = BannerGenerationApproval(db, Market, ApprovalEvent, approval_timeout_minutes)
    return task.run(approved_markets)

# For standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Mock data for testing
    approved_markets = [
        {
            "id": "market1",
            "question": "Will Bitcoin reach $100,000 by the end of 2025?",
            "category": "Crypto",
            "sub_category": "Bitcoin"
        }
    ]
    final_approved, final_rejected, failed = run_task(approved_markets)