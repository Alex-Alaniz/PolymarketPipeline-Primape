#!/usr/bin/env python3

"""
Script to check for markets sharing the same events and analyze event categories
"""

from main import app
from models import Market, PendingMarket
from sqlalchemy import func, and_

def check_shared_events():
    """Check for markets sharing the same events"""
    print("== Checking approved markets sharing events ==")
    
    # Get events with multiple markets
    events_with_multiple_markets = db.session.query(
        Market.event_id, 
        Market.event_name, 
        func.count(Market.id).label('market_count')
    ).filter(
        Market.event_id.isnot(None)
    ).group_by(
        Market.event_id, 
        Market.event_name
    ).having(
        func.count(Market.id) > 1
    ).all()
    
    print(f"Found {len(events_with_multiple_markets)} events with multiple approved markets:")
    for event_id, event_name, count in events_with_multiple_markets:
        print(f"\nEvent: {event_name} (ID: {event_id})")
        print(f"Has {count} approved markets:")
        
        markets = Market.query.filter_by(event_id=event_id).all()
        for market in markets:
            print(f"  - {market.question} (ID: {market.id}, Category: {market.category})")
    
    print("\n== Checking for cross-category events ==")
    
    # Get events with markets in different categories
    cross_category_events = db.session.query(
        Market.event_id,
        Market.event_name,
        func.count(Market.category.distinct()).label('category_count')
    ).filter(
        Market.event_id.isnot(None)
    ).group_by(
        Market.event_id,
        Market.event_name
    ).having(
        func.count(Market.category.distinct()) > 1
    ).all()
    
    print(f"Found {len(cross_category_events)} events with markets in different categories:")
    for event_id, event_name, count in cross_category_events:
        print(f"\nEvent: {event_name} (ID: {event_id})")
        print(f"Has markets in {count} different categories:")
        
        # Get categories for this event
        categories = db.session.query(
            Market.category,
            func.count(Market.id).label('market_count')
        ).filter(
            Market.event_id == event_id
        ).group_by(
            Market.category
        ).all()
        
        for category, market_count in categories:
            print(f"  - {category}: {market_count} markets")
    
    print("\n== Checking pending markets sharing events with approved markets ==")
    
    # Find pending markets that share events with approved markets
    shared_events = db.session.query(
        Market.event_id,
        Market.event_name
    ).filter(
        Market.event_id.isnot(None)
    ).distinct().all()
    
    count = 0
    for event_id, event_name in shared_events:
        pending_markets = PendingMarket.query.filter_by(event_id=event_id).all()
        if pending_markets:
            count += 1
            print(f"\nEvent: {event_name} (ID: {event_id})")
            print(f"Has {len(pending_markets)} pending markets:")
            
            for pending in pending_markets:
                print(f"  - {pending.question} (ID: {pending.poly_id}, Category: {pending.category})")
            
            # Show approved markets for this event
            approved_markets = Market.query.filter_by(event_id=event_id).all()
            print(f"And {len(approved_markets)} approved markets:")
            for approved in approved_markets:
                print(f"  - {approved.question} (ID: {approved.id}, Category: {approved.category})")
                
    print(f"\nFound {count} events with both pending and approved markets")

if __name__ == "__main__":
    with app.app_context():
        from models import db
        check_shared_events()