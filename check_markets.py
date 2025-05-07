#!/usr/bin/env python3

"""
Check the status of markets in the database.
"""

from main import app
from models import Market

def check_markets():
    """Display all markets in the database."""
    markets = Market.query.all()
    
    print(f"Found {len(markets)} markets:")
    for market in markets:
        print(f"ID: {market.id}")
        print(f"Question: {market.question}")
        print(f"Category: {market.category}")
        print(f"Event ID: {market.event_id or 'None'}")
        print(f"Event Name: {market.event_name or 'None'}")
        print(f"Status: {market.status}")
        print(f"Apechain Market ID: {market.apechain_market_id or 'None'}")
        print("---")

if __name__ == "__main__":
    with app.app_context():
        check_markets()