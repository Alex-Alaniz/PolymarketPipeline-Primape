#!/usr/bin/env python3

"""
Check Deployed Markets

This script checks and displays information about markets
that have been deployed to the blockchain.
"""

from main import app
from models import Market

def check_deployed_markets():
    with app.app_context():
        # Get markets with apechain_market_id (deployed)
        deployed_markets = Market.query.filter(
            Market.apechain_market_id.isnot(None)
        ).all()
        
        print(f"Found {len(deployed_markets)} deployed markets:")
        
        # Show some details about each deployed market
        for i, market in enumerate(deployed_markets):
            print(f"\n{i+1}. Market ID: {market.id}")
            print(f"   Question: {market.question}")
            print(f"   Category: {market.category or 'None'}")
            print(f"   ApeChain ID: {market.apechain_market_id}")
            print(f"   Options: {market.options}")
            print(f"   Status: {market.status}")

if __name__ == "__main__":
    check_deployed_markets()