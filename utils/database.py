"""
Database utility functions for the Polymarket pipeline.
"""
import os
from datetime import datetime
from typing import Dict, Any

# Models will be imported at the call site to prevent circular imports
# from models import db, Market, ApprovalEvent, PipelineRun

def store_market(db, Market, market_data: Dict[str, Any]) -> bool:
    """
    Store market data in the database.
    
    Args:
        db: SQLAlchemy database instance
        Market: Market model class
        market_data (Dict[str, Any]): Market data
        
    Returns:
        bool: Success status
    """
    try:
        # Check if market already exists
        market_id = market_data.get("id")
        existing_market = Market.query.get(market_id)
        
        if existing_market:
            # Update existing market
            existing_market.question = market_data.get("question")
            existing_market.type = market_data.get("type", "binary")
            existing_market.category = market_data.get("category")
            existing_market.sub_category = market_data.get("sub_category")
            existing_market.expiry = market_data.get("expiry")
            existing_market.original_market_id = market_data.get("original_market_id")
            existing_market.options = market_data.get("options")
            existing_market.updated_at = datetime.utcnow()
        else:
            # Create new market
            new_market = Market(
                id=market_id,
                question=market_data.get("question"),
                type=market_data.get("type", "binary"),
                category=market_data.get("category"),
                sub_category=market_data.get("sub_category"),
                expiry=market_data.get("expiry"),
                original_market_id=market_data.get("original_market_id", market_id),
                options=market_data.get("options"),
                status="new",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(new_market)
        
        # Commit changes
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error storing market in database: {str(e)}")
        return False

def update_market_status(db, Market, market_id: str, status: str, **kwargs) -> bool:
    """
    Update market status in the database.
    
    Args:
        db: SQLAlchemy database instance
        Market: Market model class
        market_id (str): Market ID
        status (str): New status
        **kwargs: Additional fields to update
        
    Returns:
        bool: Success status
    """
    try:
        # Get market from database
        market = Market.query.get(market_id)
        
        if not market:
            print(f"Market {market_id} not found in database")
            return False
        
        # Update status
        market.status = status
        
        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(market, key):
                setattr(market, key, value)
        
        # Update timestamp
        market.updated_at = datetime.utcnow()
        
        # Commit changes
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error updating market status in database: {str(e)}")
        return False

def store_approval_event(db, ApprovalEvent, market_id: str, stage: str, status: str, message_id: str, reason: str = None) -> bool:
    """
    Store approval event in the database.
    
    Args:
        db: SQLAlchemy database instance
        ApprovalEvent: ApprovalEvent model class
        market_id (str): Market ID
        stage (str): Approval stage (initial or final)
        status (str): Approval status
        message_id (str): Message ID
        reason (str, optional): Approval/rejection reason
        
    Returns:
        bool: Success status
    """
    try:
        # Create new approval event
        approval_event = ApprovalEvent(
            market_id=market_id,
            stage=stage,
            status=status,
            message_id=message_id,
            reason=reason,
            created_at=datetime.utcnow()
        )
        
        # Add to database
        db.session.add(approval_event)
        
        # Commit changes
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error storing approval event in database: {str(e)}")
        return False

def update_pipeline_run(db, PipelineRun, run_id: int, **kwargs) -> bool:
    """
    Update pipeline run in the database.
    
    Args:
        db: SQLAlchemy database instance
        PipelineRun: PipelineRun model class
        run_id (int): Run ID
        **kwargs: Fields to update
        
    Returns:
        bool: Success status
    """
    try:
        # Get pipeline run from database
        pipeline_run = PipelineRun.query.get(run_id)
        
        if not pipeline_run:
            print(f"Pipeline run {run_id} not found in database")
            return False
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(pipeline_run, key):
                setattr(pipeline_run, key, value)
        
        # Commit changes
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Error updating pipeline run in database: {str(e)}")
        return False