#!/usr/bin/env python3

"""
Reset Database for Testing

This script resets the database for testing the new auto-categorization flow
without affecting deployed markets.
"""

import os
import sys
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import inspect
from datetime import datetime

from models import db, Market, PendingMarket, ProcessedMarket, ApprovalLog

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("reset_db_testing")

def backup_deployed_markets() -> Optional[List[Dict[str, Any]]]:
    """
    Backup deployed markets before resetting the database.
    
    Returns:
        Optional[List[Dict[str, Any]]]: Backup of deployed markets data, or None if backup failed
    """
    try:
        # Find markets that have been deployed to Apechain (have apechain_market_id)
        deployed_markets = Market.query.filter(Market.apechain_market_id.isnot(None)).all()
        
        if not deployed_markets:
            logger.info("No deployed markets found, nothing to backup")
            return []
            
        logger.info(f"Backing up {len(deployed_markets)} deployed markets")
        
        # Create backup list as dictionaries
        deployed_markets_data = []
        for market in deployed_markets:
            try:
                market_data = {
                    'id': market.id,
                    'question': market.question,
                    'type': market.type,
                    'category': market.category,
                    'sub_category': market.sub_category,
                    'expiry': market.expiry,
                    'original_market_id': market.original_market_id,
                    'options': market.options,
                    'status': market.status,
                    'banner_path': market.banner_path,
                    'banner_uri': market.banner_uri,
                    'icon_url': market.icon_url,
                    'option_images': market.option_images,
                    'apechain_market_id': market.apechain_market_id,
                    'github_commit': market.github_commit,
                    'blockchain_tx': market.blockchain_tx,
                    'created_at': market.created_at.isoformat() if market.created_at else None,
                    'updated_at': market.updated_at.isoformat() if market.updated_at else None
                }
                deployed_markets_data.append(market_data)
            except Exception as e:
                logger.error(f"Error backing up market {market.id}: {str(e)}")
                
        logger.info(f"Successfully backed up {len(deployed_markets_data)} deployed markets")
        return deployed_markets_data
        
    except Exception as e:
        logger.error(f"Error backing up deployed markets: {str(e)}")
        return None

def restore_deployed_markets(deployed_markets_data: List[Dict[str, Any]]) -> bool:
    """
    Restore deployed markets after resetting the database.
    
    Args:
        deployed_markets_data: Backup of deployed markets data
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not deployed_markets_data:
            logger.info("No deployed markets to restore")
            return True
            
        logger.info(f"Restoring {len(deployed_markets_data)} deployed markets")
        
        # Restore markets
        for market_data in deployed_markets_data:
            try:
                # Parse dates
                created_at = None
                if market_data.get('created_at'):
                    created_at = datetime.fromisoformat(market_data['created_at'])
                
                updated_at = None
                if market_data.get('updated_at'):
                    updated_at = datetime.fromisoformat(market_data['updated_at'])
                
                # Create market
                market = Market(
                    id=market_data['id'],
                    question=market_data['question'],
                    type=market_data['type'],
                    category=market_data['category'],
                    sub_category=market_data['sub_category'],
                    expiry=market_data['expiry'],
                    original_market_id=market_data['original_market_id'],
                    options=market_data['options'],
                    status=market_data['status'],
                    banner_path=market_data['banner_path'],
                    banner_uri=market_data['banner_uri'],
                    icon_url=market_data['icon_url'],
                    option_images=market_data['option_images'],
                    apechain_market_id=market_data['apechain_market_id'],
                    github_commit=market_data['github_commit'],
                    blockchain_tx=market_data['blockchain_tx'],
                    created_at=created_at,
                    updated_at=updated_at
                )
                db.session.add(market)
            except Exception as e:
                logger.error(f"Error restoring market {market_data.get('id')}: {str(e)}")
                
        # Commit changes
        db.session.commit()
        logger.info(f"Successfully restored {len(deployed_markets_data)} deployed markets")
        return True
        
    except Exception as e:
        logger.error(f"Error restoring deployed markets: {str(e)}")
        return False

def reset_database(preserve_deployed_markets=True):
    """
    Reset the database for testing.
    
    Args:
        preserve_deployed_markets: If True, preserve deployed markets
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Backup deployed markets if needed
        deployed_markets_data = None
        if preserve_deployed_markets:
            deployed_markets_data = backup_deployed_markets()
            if deployed_markets_data is None:
                logger.error("Failed to backup deployed markets, aborting reset")
                return False
        
        logger.info("Dropping tables: pending_markets, approvals_log, processed_markets")
        
        # Drop tables but preserve market table for deployed markets
        db.session.execute('DROP TABLE IF EXISTS pending_markets CASCADE')
        db.session.execute('DROP TABLE IF EXISTS approvals_log CASCADE')
        db.session.execute('DROP TABLE IF EXISTS processed_markets CASCADE')
        
        # Drop market table only if we're not preserving deployed markets
        if not preserve_deployed_markets:
            logger.warning("Dropping markets table (including deployed markets)")
            db.session.execute('DROP TABLE IF EXISTS markets CASCADE')
        else:
            # If preserving deployed markets, delete only non-deployed markets
            if Market.__table__.exists(db.engine):
                logger.info("Deleting non-deployed markets")
                db.session.execute(
                    Market.__table__.delete().where(Market.apechain_market_id.is_(None))
                )
                
        # Commit changes
        db.session.commit()
        
        # Recreate tables
        logger.info("Recreating tables")
        db.create_all()
        
        # Restore deployed markets if needed
        if preserve_deployed_markets and deployed_markets_data is not None:
            restore_success = restore_deployed_markets(deployed_markets_data)
            if not restore_success:
                logger.error("Failed to restore deployed markets")
                return False
                
        logger.info("Database reset completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error resetting database: {str(e)}")
        return False

def main():
    """
    Main function to reset the database for testing.
    """
    # Import Flask app to get application context
    from main import app
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Reset database for testing")
    parser.add_argument("--drop-all", action="store_true", help="Drop all tables, including deployed markets")
    args = parser.parse_args()
    
    preserve_deployed = not args.drop_all
    
    # Use application context for database operations
    with app.app_context():
        logger.info(f"Resetting database (preserve_deployed_markets={preserve_deployed})")
        success = reset_database(preserve_deployed_markets=preserve_deployed)
        
        if success:
            print("Database reset successfully")
            return 0
        else:
            print("Error resetting database")
            return 1

if __name__ == "__main__":
    sys.exit(main())