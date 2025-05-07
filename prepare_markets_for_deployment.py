#!/usr/bin/env python3

"""
Prepare Markets for Deployment

This script marks approved markets as ready for deployment to Apechain,
changing their status from 'approved' to 'deployment_approved'.
"""

import os
import logging
import argparse
from datetime import datetime
from typing import List, Tuple

from main import app
from models import db, Market

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("prepare_deployment")

def mark_markets_for_deployment(market_ids=None, mark_all=False) -> Tuple[int, int]:
    """
    Mark markets as ready for deployment.
    
    Args:
        market_ids: List of specific market IDs to mark
        mark_all: If True, mark all approved markets
        
    Returns:
        Tuple[int, int]: Count of (processed, marked) markets
    """
    if not market_ids and not mark_all:
        logger.error("No markets specified to mark for deployment")
        return 0, 0
    
    try:
        # Find markets to mark
        if mark_all:
            markets = Market.query.filter_by(status='approved').all()
        else:
            markets = Market.query.filter(
                Market.id.in_(market_ids),
                Market.status == 'approved'
            ).all()
        
        logger.info(f"Found {len(markets)} approved markets to mark for deployment")
        
        # Mark markets for deployment
        processed = 0
        marked = 0
        
        for market in markets:
            processed += 1
            
            try:
                logger.info(f"Marking market {market.id} for deployment: {market.question}")
                market.status = 'deployment_approved'
                db.session.commit()
                marked += 1
                logger.info(f"Market {market.id} marked for deployment")
            except Exception as e:
                logger.error(f"Error marking market {market.id} for deployment: {str(e)}")
                db.session.rollback()
        
        return processed, marked
    
    except Exception as e:
        logger.error(f"Error finding markets for deployment: {str(e)}")
        return 0, 0

def list_approved_markets():
    """List all approved markets that can be marked for deployment."""
    markets = Market.query.filter_by(status='approved').all()
    
    print(f"\nFound {len(markets)} approved markets:")
    for market in markets:
        print(f"ID: {market.id}")
        print(f"Question: {market.question}")
        print(f"Category: {market.category}")
        print(f"Event ID: {market.event_id or 'None'}")
        print(f"Event Name: {market.event_name or 'None'}")
        print("---")
    
    return markets

def main():
    """Main function to prepare markets for deployment."""
    parser = argparse.ArgumentParser(description='Prepare markets for deployment')
    parser.add_argument('--list', action='store_true', help='List approved markets')
    parser.add_argument('--all', action='store_true', help='Mark all approved markets for deployment')
    parser.add_argument('--markets', nargs='+', help='Specific market IDs to mark for deployment')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.list:
            list_approved_markets()
            return 0
            
        if args.all:
            processed, marked = mark_markets_for_deployment(mark_all=True)
            print(f"Marked {marked} of {processed} markets for deployment")
        elif args.markets:
            processed, marked = mark_markets_for_deployment(market_ids=args.markets)
            print(f"Marked {marked} of {processed} specified markets for deployment")
        else:
            parser.print_help()
        
        return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())