#!/usr/bin/env python3

"""
Check the status of test markets in the database.
"""

from main import app
from models import db, Market

with app.app_context():
    market = Market.query.filter(Market.id.like('test-market-%')).first()
    
    if market:
        print(f'Market ID: {market.id}')
        print(f'Status: {market.status}')
        print(f'ApeChain ID: {market.apechain_market_id}')
        print(f'Blockchain Tx: {market.blockchain_tx}')
    else:
        print('No test market found in database')