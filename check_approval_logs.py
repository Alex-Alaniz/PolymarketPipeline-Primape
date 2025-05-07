#!/usr/bin/env python3

"""
Check approval logs in the database.

This script displays the approval logs for markets.
"""

from main import app
from models import ApprovalLog, db, PendingMarket
import argparse

def check_approval_logs():
    """Display approval logs for markets."""
    logs = ApprovalLog.query.all()
    
    print(f"Found {len(logs)} approval log entries:")
    for log in logs:
        print(f"Market ID: {log.poly_id}")
        print(f"Reviewer: {log.reviewer}")
        print(f"Decision: {log.decision}")
        print(f"Timestamp: {log.created_at}")
        print("---")

def clear_pending_market(market_id):
    """Clear a specific pending market."""
    pending_market = PendingMarket.query.filter_by(poly_id=market_id).first()
    
    if pending_market:
        try:
            print(f"Deleting pending market: {pending_market.poly_id} - {pending_market.question}")
            db.session.delete(pending_market)
            db.session.commit()
            print("Market deleted successfully")
            return True
        except Exception as e:
            print(f"Error deleting market: {str(e)}")
            db.session.rollback()
            return False
    else:
        print(f"Market {market_id} not found")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Check approval logs and manage pending markets')
    parser.add_argument('--logs', action='store_true', help='Show approval logs')
    parser.add_argument('--delete', type=str, help='Delete pending market by ID')
    
    args = parser.parse_args()
    
    with app.app_context():
        if args.logs:
            check_approval_logs()
        
        if args.delete:
            clear_pending_market(args.delete)