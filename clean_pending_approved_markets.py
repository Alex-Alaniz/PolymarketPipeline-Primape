#!/usr/bin/env python3

"""
Clean Pending Approved Markets

This script removes pending markets that have already been approved and added to the main markets table.
This is typically done as part of the approval process but is being done separately here for testing.
"""

from main import app
from models import db, PendingMarket, Market

def clean_pending_approved_markets():
    """Remove pending markets that have already been approved and added to the main markets table."""
    
    # Get all markets from the main table
    approved_markets = Market.query.all()
    approved_ids = [market.id for market in approved_markets]
    
    # Find pending markets with IDs that match approved market IDs
    pending_to_remove = PendingMarket.query.filter(PendingMarket.poly_id.in_(approved_ids)).all()
    
    print(f"Found {len(pending_to_remove)} pending markets that have already been approved:")
    for pending in pending_to_remove:
        print(f"  - {pending.poly_id}: {pending.question}")
        db.session.delete(pending)
    
    db.session.commit()
    print(f"Removed {len(pending_to_remove)} pending markets that were already approved")

if __name__ == "__main__":
    with app.app_context():
        clean_pending_approved_markets()