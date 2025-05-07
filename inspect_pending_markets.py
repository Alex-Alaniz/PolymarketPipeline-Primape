#!/usr/bin/env python3

"""
Inspect pending markets in the database.

This script provides a detailed view of pending markets and their relationship to events.
"""

from main import app
from models import PendingMarket, Market, db
import argparse
import json

def list_pending_markets():
    """List all pending markets in the database."""
    pending_markets = PendingMarket.query.all()
    
    print(f"Found {len(pending_markets)} pending markets:")
    for market in pending_markets:
        print(f"\nID: {market.poly_id}")
        print(f"Question: {market.question}")
        print(f"Category: {market.category}")
        print(f"Event ID: {market.event_id or 'None'}")
        print(f"Event Name: {market.event_name or 'None'}")
        print(f"Posted: {market.posted}")
        print(f"Slack Message ID: {market.slack_message_id or 'None'}")
        
        # Check if this is related to any approved markets
        if market.event_id:
            approved_count = Market.query.filter_by(event_id=market.event_id).count()
            if approved_count > 0:
                print(f"Related to {approved_count} approved markets with same event")

def inspect_pending_market(market_id):
    """Display detailed information about a specific pending market."""
    market = PendingMarket.query.filter_by(poly_id=market_id).first()
    
    if not market:
        print(f"Pending market with ID {market_id} not found")
        return
    
    print(f"\nPending Market: {market.question}")
    print(f"ID: {market.poly_id}")
    print(f"Category: {market.category}")
    print(f"Event ID: {market.event_id or 'None'}")
    print(f"Event Name: {market.event_name or 'None'}")
    print(f"Posted: {market.posted}")
    print(f"Slack Message ID: {market.slack_message_id or 'None'}")
    
    # Display options
    if market.options:
        options = market.options
        if isinstance(options, str):
            try:
                options = json.loads(options)
            except json.JSONDecodeError:
                options = {"Error": "Could not parse options JSON"}
        
        print("\nOptions:")
        if isinstance(options, list):
            for i, option in enumerate(options):
                print(f"  {i+1}. {option}")
        else:
            print(f"  {options}")
    else:
        print("\nNo options available")
    
    # Display raw data
    if market.raw_data:
        print("\nRaw Data Sample (first 100 chars):")
        raw_data = market.raw_data
        if isinstance(raw_data, str):
            try:
                raw_data = json.loads(raw_data)
                print(f"  {str(raw_data)[:100]}...")
            except json.JSONDecodeError:
                print(f"  {raw_data[:100]}...")
        else:
            print(f"  {str(raw_data)[:100]}...")
    
    # Check if this is related to any approved markets
    if market.event_id:
        related_markets = Market.query.filter_by(event_id=market.event_id).all()
        if related_markets:
            print(f"\nRelated to {len(related_markets)} approved markets with same event:")
            for related in related_markets:
                print(f"  - {related.question} (ID: {related.id}, Status: {related.status})")

def main():
    """Main function to inspect pending markets."""
    parser = argparse.ArgumentParser(description='Inspect pending markets in the database')
    parser.add_argument('--list', action='store_true', help='List all pending markets')
    parser.add_argument('--market', type=str, help='Show details for a specific pending market ID')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.list:
            list_pending_markets()
        elif args.market:
            inspect_pending_market(args.market)
        else:
            # Default to listing all pending markets
            list_pending_markets()

if __name__ == "__main__":
    main()