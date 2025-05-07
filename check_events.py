#!/usr/bin/env python3

"""
Check event relationships in the database.

This script shows how markets are grouped by events and demonstrates the
event-to-market relationship structure.
"""

from main import app
from models import Market, db
from sqlalchemy import func

def check_events():
    """Display markets grouped by events."""
    # Get unique event IDs and names
    events = db.session.query(Market.event_id, Market.event_name).filter(
        Market.event_id.isnot(None)
    ).distinct().all()
    
    print(f"Found {len(events)} unique events:")
    for event_id, event_name in events:
        print(f"\nEvent: {event_name} (ID: {event_id})")
        
        # Get markets for this event
        markets = Market.query.filter_by(event_id=event_id).all()
        
        print(f"This event has {len(markets)} markets:")
        for market in markets:
            print(f"  - {market.question} (ID: {market.id}, Category: {market.category})")

def check_event_categories():
    """Display events by category."""
    # Get categories with events
    categories = db.session.query(Market.category, func.count(Market.event_id.distinct())).filter(
        Market.event_id.isnot(None)
    ).group_by(Market.category).all()
    
    print("\nEvents by category:")
    for category, count in categories:
        print(f"{category}: {count} events")
        
        # Get events for this category
        events = db.session.query(Market.event_id, Market.event_name).filter(
            Market.category == category,
            Market.event_id.isnot(None)
        ).distinct().all()
        
        for event_id, event_name in events:
            # Count markets for this event
            market_count = Market.query.filter_by(event_id=event_id).count()
            print(f"  - {event_name}: {market_count} markets")

if __name__ == "__main__":
    with app.app_context():
        check_events()
        check_event_categories()