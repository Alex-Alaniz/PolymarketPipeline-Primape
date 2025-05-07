#!/usr/bin/env python3

"""
Check event relationships in the database.

This script shows how markets are grouped by events and demonstrates the
event-to-market relationship structure.
"""

from main import app
from models import Market
from sqlalchemy import func
from collections import defaultdict

def check_events():
    """Display markets grouped by events."""
    
    # Get count of markets by event
    event_counts = db.session.query(
        Market.event_id,
        Market.event_name,
        func.count(Market.id).label('market_count')
    ).group_by(
        Market.event_id,
        Market.event_name
    ).order_by(
        func.count(Market.id).desc()
    ).all()
    
    print(f"Found {len(event_counts)} events:")
    for event_id, event_name, count in event_counts:
        print(f"Event ID: {event_id or 'None'}")
        print(f"Event Name: {event_name or 'None'}")
        print(f"Market Count: {count}")
        
        # Get markets for this event
        markets = Market.query.filter_by(event_id=event_id).all()
        for i, market in enumerate(markets, 1):
            print(f"  {i}. {market.question} (Category: {market.category})")
        
        print("---")

    # Check for orphaned markets (no event)
    orphaned = Market.query.filter(Market.event_id.is_(None)).all()
    if orphaned:
        print(f"\nFound {len(orphaned)} markets without events:")
        for market in orphaned:
            print(f"- {market.question} (ID: {market.id}, Category: {market.category})")

def check_event_categories():
    """Display events by category."""
    # Get events by category
    event_categories = defaultdict(list)
    
    events = db.session.query(
        Market.event_id,
        Market.event_name,
        Market.category
    ).distinct().all()
    
    for event_id, event_name, category in events:
        if event_id:  # Skip null events
            event_categories[category].append((event_id, event_name))
    
    print("\nEvents by Category:")
    for category, events in event_categories.items():
        print(f"\n{category.upper()} ({len(events)} events):")
        for event_id, event_name in events:
            count = Market.query.filter_by(event_id=event_id).count()
            print(f"- {event_name} ({count} markets)")

if __name__ == "__main__":
    from models import db
    
    with app.app_context():
        print("\n--- MARKETS BY EVENT ---\n")
        check_events()
        
        print("\n--- EVENTS BY CATEGORY ---\n")
        check_event_categories()