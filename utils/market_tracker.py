"""
Market Tracker Utility

This module provides functionality for tracking processed markets in the database.
It helps prevent re-processing the same markets and keeps track of their status.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models import db, ProcessedMarket

logger = logging.getLogger("market_tracker")

class MarketTracker:
    """Class for tracking processed markets"""
    
    def __init__(self):
        """Initialize the market tracker"""
        self.initialized = True
    
    def is_market_processed(self, condition_id: str) -> bool:
        """
        Check if a market has already been processed
        
        Args:
            condition_id: Polymarket condition_id to check
            
        Returns:
            bool: True if market has been processed, False otherwise
        """
        try:
            market = ProcessedMarket.query.filter_by(condition_id=condition_id).first()
            return market is not None
        except SQLAlchemyError as e:
            logger.error(f"Database error checking if market is processed: {str(e)}")
            return False
    
    def get_processed_market_ids(self) -> Set[str]:
        """
        Get a set of all processed market condition_ids
        
        Returns:
            Set[str]: Set of condition_ids that have been processed
        """
        try:
            markets = ProcessedMarket.query.with_entities(ProcessedMarket.condition_id).all()
            return {market[0] for market in markets}
        except SQLAlchemyError as e:
            logger.error(f"Database error getting processed market IDs: {str(e)}")
            return set()
    
    def mark_market_as_processed(self, market_data: Dict[str, Any], posted: bool = False, message_id: str = None) -> bool:
        """
        Mark a market as processed in the database
        
        Args:
            market_data: Raw market data from Polymarket API
            posted: Whether the market was posted to Slack/Discord
            message_id: Slack/Discord message ID if posted
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            condition_id = market_data.get("condition_id")
            if not condition_id:
                logger.warning("Cannot mark market as processed: missing condition_id")
                return False
            
            # Check if market already exists
            existing_market = ProcessedMarket.query.filter_by(condition_id=condition_id).first()
            
            if existing_market:
                # Update existing market
                existing_market.last_processed = datetime.utcnow()
                existing_market.process_count += 1
                
                if posted and message_id:
                    existing_market.posted = True
                    existing_market.message_id = message_id
                
                db.session.commit()
                logger.info(f"Updated existing processed market: {condition_id}")
                return True
            else:
                # Create new processed market
                new_market = ProcessedMarket(
                    condition_id=condition_id,
                    question=market_data.get("question", "Unknown"),
                    posted=posted,
                    message_id=message_id,
                    raw_data=market_data
                )
                
                db.session.add(new_market)
                db.session.commit()
                logger.info(f"Added new processed market: {condition_id}")
                return True
                
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error marking market as processed: {str(e)}")
            return False
    
    def mark_market_approval(self, condition_id: str, approved: bool, approver: str = None) -> bool:
        """
        Mark a market as approved or rejected
        
        Args:
            condition_id: Polymarket condition_id
            approved: True if approved, False if rejected
            approver: User ID of the approver/rejecter
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            market = ProcessedMarket.query.filter_by(condition_id=condition_id).first()
            
            if not market:
                logger.warning(f"Cannot mark approval: market {condition_id} not found")
                return False
            
            market.approved = approved
            market.approval_date = datetime.utcnow()
            market.approver = approver
            
            db.session.commit()
            logger.info(f"Marked market {condition_id} as {'approved' if approved else 'rejected'}")
            return True
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error marking market approval: {str(e)}")
            return False
    
    def get_pending_markets(self) -> List[Dict[str, Any]]:
        """
        Get markets that have been posted but not yet approved/rejected
        
        Returns:
            List[Dict[str, Any]]: List of pending market dictionaries
        """
        try:
            # Query for markets that are posted but have no approval status
            markets = ProcessedMarket.query.filter_by(posted=True, approved=None).all()
            return [market.to_dict() for market in markets]
        except SQLAlchemyError as e:
            logger.error(f"Database error getting pending markets: {str(e)}")
            return []
    
    def get_approved_markets(self) -> List[Dict[str, Any]]:
        """
        Get markets that have been approved
        
        Returns:
            List[Dict[str, Any]]: List of approved market dictionaries
        """
        try:
            markets = ProcessedMarket.query.filter_by(approved=True).all()
            return [market.to_dict() for market in markets]
        except SQLAlchemyError as e:
            logger.error(f"Database error getting approved markets: {str(e)}")
            return []
    
    def get_rejected_markets(self) -> List[Dict[str, Any]]:
        """
        Get markets that have been rejected
        
        Returns:
            List[Dict[str, Any]]: List of rejected market dictionaries
        """
        try:
            markets = ProcessedMarket.query.filter_by(approved=False).all()
            return [market.to_dict() for market in markets]
        except SQLAlchemyError as e:
            logger.error(f"Database error getting rejected markets: {str(e)}")
            return []
    
    def get_market_raw_data(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the raw data for a specific market
        
        Args:
            condition_id: Polymarket condition_id
            
        Returns:
            Dict[str, Any]: Raw market data, or None if not found
        """
        try:
            market = ProcessedMarket.query.filter_by(condition_id=condition_id).first()
            
            if market and market.raw_data:
                return market.raw_data
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error getting market raw data: {str(e)}")
            return None

# Global market tracker instance
market_tracker = MarketTracker()