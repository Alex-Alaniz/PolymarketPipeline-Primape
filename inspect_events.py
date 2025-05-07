#!/usr/bin/env python3

"""
Inspect events in the database.

This script provides a detailed view of events and their associated markets.
"""

from main import app
from models import Market, PendingMarket, db
from sqlalchemy import func, union, select
import argparse

def get_all_events():
    """Get all unique events from both markets and pending markets."""
    # Get events from markets
    market_events = db.session.query(
        Market.event_id.label('event_id'),
        Market.event_name.label('event_name')
    ).filter(
        Market.event_id.isnot(None)
    ).distinct()
    
    # Get events from pending markets
    pending_events = db.session.query(
        PendingMarket.event_id.label('event_id'),
        PendingMarket.event_name.label('event_name')
    ).filter(
        PendingMarket.event_id.isnot(None)
    ).distinct()
    
    # Combine the queries
    all_events = market_events.union(pending_events).all()
    
    return all_events

def display_event_markets(event_id):
    """Display all markets (approved and pending) for a specific event."""
    event_name = None
    
    # Get approved markets for this event
    approved_markets = Market.query.filter_by(event_id=event_id).all()
    if approved_markets and approved_markets[0].event_name:
        event_name = approved_markets[0].event_name
    
    # Get pending markets for this event
    pending_markets = PendingMarket.query.filter_by(event_id=event_id).all()
    if not event_name and pending_markets and pending_markets[0].event_name:
        event_name = pending_markets[0].event_name
    
    print(f"\nEvent: {event_name} (ID: {event_id})")
    
    # Display approved markets
    print(f"Approved Markets ({len(approved_markets)}):")
    for market in approved_markets:
        print(f"  - {market.question}")
        print(f"    ID: {market.id}")
        print(f"    Category: {market.category}")
        print(f"    Status: {market.status}")
        print(f"    Apechain ID: {market.apechain_market_id or 'None'}")
    
    # Display pending markets
    print(f"\nPending Markets ({len(pending_markets)}):")
    for market in pending_markets:
        print(f"  - {market.question}")
        print(f"    ID: {market.poly_id}")
        print(f"    Category: {market.category}")
        print(f"    Posted: {market.posted}")

def list_all_events():
    """List all events in the database."""
    events = get_all_events()
    
    print(f"Found {len(events)} unique events:")
    for event_id, event_name in events:
        # Count approved markets
        approved_count = Market.query.filter_by(event_id=event_id).count()
        
        # Count pending markets
        pending_count = PendingMarket.query.filter_by(event_id=event_id).count()
        
        print(f"- {event_name} (ID: {event_id})")
        print(f"  {approved_count} approved markets, {pending_count} pending markets")

def main():
    """Main function to inspect events."""
    parser = argparse.ArgumentParser(description='Inspect events in the database')
    parser.add_argument('--list', action='store_true', help='List all events')
    parser.add_argument('--event', type=str, help='Show details for a specific event ID')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.list:
            list_all_events()
        elif args.event:
            display_event_markets(args.event)
        else:
            # Default to listing all events
            list_all_events()

if __name__ == "__main__":
    main()