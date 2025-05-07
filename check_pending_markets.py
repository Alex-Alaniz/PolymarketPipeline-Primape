#!/usr/bin/env python3

"""
Check the status of pending markets in the database.
"""

from main import app
from models import PendingMarket

def check_pending_markets():
    """Display all pending markets in the database."""
    pending_markets = PendingMarket.query.all()
    
    print(f"Found {len(pending_markets)} pending markets:")
    for market in pending_markets:
        print(f"ID: {market.poly_id}")
        print(f"Question: {market.question}")
        print(f"Category: {market.category}")
        print(f"Event ID: {market.event_id or 'None'}")
        print(f"Event Name: {market.event_name or 'None'}")
        print(f"Posted: {market.posted}")
        print(f"Slack Message ID: {market.slack_message_id or 'None'}")
        print("---")

if __name__ == "__main__":
    with app.app_context():
        check_pending_markets()