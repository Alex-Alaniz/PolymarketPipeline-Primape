"""
Task 2: Capture Approvals from Slack

This module handles:
1. Monitoring reactions on posted market entries
2. Identifying which markets were approved or rejected
3. Updating market status in database
"""
import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple

# Import utility modules
from utils.messaging import MessagingClient
from utils.database import update_market_status, store_approval_event

# Setup logging
logger = logging.getLogger("task2")

class SlackApprovalMonitor:
    """
    Class for monitoring Slack approvals.
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
        
        # Initialize messaging client
        self.messaging_client = MessagingClient()
        
        # Validation
        if not self.messaging_client:
            logger.error("Failed to initialize messaging client")
            raise RuntimeError("Messaging client initialization failed")
    
    def run(self, pending_markets: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Run the task to monitor approvals from Slack.
        
        Args:
            pending_markets (List[Dict[str, Any]]): List of markets pending approval, with slack_message_id
            
        Returns:
            Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]: 
                (approved_markets, rejected_markets, timed_out_markets)
        """
        logger.info("Starting Task 2: Monitoring Slack for approvals")
        
        approved_markets = []
        rejected_markets = []
        timed_out_markets = []
        
        for market in pending_markets:
            market_id = market.get("id")
            message_id = market.get("slack_message_id")
            
            if not market_id or not message_id:
                logger.warning(f"Market {market_id} missing required data, skipping")
                continue
            
            # Check approval status in Slack
            logger.info(f"Checking approval status for market {market_id}")
            approval_status, reason = self.check_market_approval(message_id)
            
            # Update market status based on approval
            if approval_status == "approved":
                logger.info(f"Market {market_id} was approved: {reason}")
                market["status"] = "initial_approved"
                market["approval_reason"] = reason
                approved_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "initial_approved")
                
                # Store approval event
                if self.db and self.ApprovalEvent:
                    store_approval_event(
                        self.db,
                        self.ApprovalEvent,
                        market_id,
                        "initial",
                        "approved",
                        message_id,
                        reason
                    )
                    
            elif approval_status == "rejected":
                logger.info(f"Market {market_id} was rejected: {reason}")
                market["status"] = "initial_rejected"
                market["rejection_reason"] = reason
                rejected_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "initial_rejected")
                
                # Store approval event
                if self.db and self.ApprovalEvent:
                    store_approval_event(
                        self.db,
                        self.ApprovalEvent,
                        market_id,
                        "initial",
                        "rejected",
                        message_id,
                        reason
                    )
                    
            else:  # timeout or error
                logger.warning(f"Market {market_id} approval timed out or errored: {reason}")
                market["status"] = "initial_timeout"
                market["timeout_reason"] = reason
                timed_out_markets.append(market)
                
                # Update database if available
                if self.db and self.Market:
                    update_market_status(self.db, self.Market, market_id, "initial_timeout")
                
                # Store approval event
                if self.db and self.ApprovalEvent:
                    store_approval_event(
                        self.db,
                        self.ApprovalEvent,
                        market_id,
                        "initial",
                        "timeout",
                        message_id,
                        reason
                    )
        
        # Log summary
        logger.info(f"Task 2 completed: {len(approved_markets)} approved, {len(rejected_markets)} rejected, {len(timed_out_markets)} timed out")
        
        return approved_markets, rejected_markets, timed_out_markets
    
    def check_market_approval(self, message_id: str) -> Tuple[str, Optional[str]]:
        """
        Check if a market has been approved or rejected in Slack.
        
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
            logger.error(f"Error checking approval: {str(e)}")
            return "error", str(e)

# Standalone function for running this task
def run_task(pending_markets: List[Dict[str, Any]], db=None, Market=None, ApprovalEvent=None, 
             approval_timeout_minutes=30) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Run Task 2: Monitor Slack for approvals.
    
    Args:
        pending_markets (List[Dict[str, Any]]): List of markets pending approval
        db: SQLAlchemy database instance (optional)
        Market: Market model class (optional)
        ApprovalEvent: ApprovalEvent model class (optional)
        approval_timeout_minutes (int): Timeout in minutes for approval
        
    Returns:
        Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]: 
            (approved_markets, rejected_markets, timed_out_markets)
    """
    task = SlackApprovalMonitor(db, Market, ApprovalEvent, approval_timeout_minutes)
    return task.run(pending_markets)

# For standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # Mock data for testing
    pending_markets = [
        {
            "id": "market1",
            "question": "Will Bitcoin reach $100,000 by the end of 2025?",
            "slack_message_id": "12345.67890"
        }
    ]
    approved, rejected, timed_out = run_task(pending_markets)