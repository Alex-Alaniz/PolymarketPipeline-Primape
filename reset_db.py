#!/usr/bin/env python3

"""
Reset the database for the Polymarket pipeline.

This script drops all tables in the database and reinitializes them,
allowing for a clean state for testing the pipeline.
"""

import os
import sys
import logging
from sqlalchemy import text
from models import db, Market, ProcessedMarket, ApprovalEvent, PipelineRun

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("db_reset")

def reset_database(preserve_deployed_markets=True):
    """
    Reset the database by dropping all tables and recreating them.
    
    Args:
        preserve_deployed_markets: If True, backup and restore deployed markets
                                  to protect blockchain-deployed assets
    """
    # Import Flask app here to avoid circular imports
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        deployed_markets = []
        
        try:
            # Backup deployed markets if needed
            if preserve_deployed_markets:
                logger.info("Backing up deployed markets before reset...")
                deployed_markets = Market.query.filter_by(status="deployed").all()
                logger.info(f"Found {len(deployed_markets)} deployed markets to preserve")
                
                # Create deep copies of the markets to restore later
                deployed_markets_data = []
                for market in deployed_markets:
                    market_data = {
                        'id': market.id,
                        'question': market.question,
                        'description': market.description,
                        'category': market.category,
                        'subcategory': market.subcategory,
                        'event_category': market.event_category, 
                        'type': market.type,
                        'options': market.options,
                        'apechain_market_id': market.apechain_market_id,
                        'blockchain_tx': market.blockchain_tx,
                        'expiry': market.expiry,
                        'created_at': market.created_at,
                        'updated_at': market.updated_at,
                        'banner_uri': market.banner_uri,
                        'icon_uri': market.icon_uri,
                        'status': market.status,
                        'original_market_ids': market.original_market_ids,
                        'polymarket_image': market.polymarket_image,
                        'polymarket_icon': market.polymarket_icon,
                        'option_images': market.option_images
                    }
                    deployed_markets_data.append(market_data)
                
                logger.info("Successfully backed up deployed markets")
            
            # Get all tables
            tables = [Market.__table__, ProcessedMarket.__table__, 
                      ApprovalEvent.__table__, PipelineRun.__table__]
            
            # Drop all tables
            logger.info("Dropping all tables...")
            for table in tables:
                logger.info(f"Dropping table {table.name}...")
                db.session.execute(text(f"DROP TABLE IF EXISTS {table.name} CASCADE"))
            
            db.session.commit()
            logger.info("All tables dropped successfully")
            
            # Create all tables
            logger.info("Creating all tables...")
            db.create_all()
            logger.info("All tables created successfully")
            
            # Restore deployed markets if needed
            if preserve_deployed_markets and deployed_markets_data:
                logger.info(f"Restoring {len(deployed_markets_data)} deployed markets...")
                
                for market_data in deployed_markets_data:
                    # Create new market with preserved data
                    market = Market(
                        id=market_data['id'],
                        question=market_data['question'],
                        description=market_data['description'],
                        category=market_data['category'],
                        subcategory=market_data['subcategory'],
                        event_category=market_data['event_category'],
                        type=market_data['type'],
                        options=market_data['options'],
                        apechain_market_id=market_data['apechain_market_id'],
                        blockchain_tx=market_data['blockchain_tx'],
                        expiry=market_data['expiry'],
                        created_at=market_data['created_at'],
                        updated_at=market_data['updated_at'],
                        banner_uri=market_data['banner_uri'],
                        icon_uri=market_data['icon_uri'],
                        status=market_data['status'],
                        original_market_ids=market_data['original_market_ids'],
                        polymarket_image=market_data['polymarket_image'],
                        polymarket_icon=market_data['polymarket_icon'],
                        option_images=market_data['option_images']
                    )
                    
                    db.session.add(market)
                
                db.session.commit()
                logger.info(f"Successfully restored {len(deployed_markets_data)} deployed markets")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting database: {str(e)}")
            db.session.rollback()
            return False

def main():
    """
    Main function to run the database reset.
    """
    logger.info("Starting database reset...")
    
    success = reset_database()
    
    if success:
        logger.info("Database reset completed successfully")
        return 0
    else:
        logger.error("Database reset failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())