#!/usr/bin/env python3
"""
Check the status of the pipeline.

This script displays information about the current state of the pipeline,
including counts of markets at different stages and recent pipeline runs.
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy import desc

# Initialize Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import database models
from models_updated import db, Event, Market, PendingMarket, ProcessedMarket
db.init_app(app)

def check_pipeline_status():
    """Display the current status of the pipeline."""
    with app.app_context():
        # Get counts of markets at different stages
        total_events = db.session.query(Event).count()
        total_markets = db.session.query(Market).count()
        pending_markets = db.session.query(PendingMarket).count()
        pending_unposted = db.session.query(PendingMarket).filter_by(posted=False).count()
        pending_posted = db.session.query(PendingMarket).filter_by(posted=True).count()
        
        # Get counts by category
        category_counts = db.session.query(
            Market.category, 
            db.func.count(Market.id)
        ).group_by(Market.category).all()
        
        # Get counts of markets by status
        status_counts = db.session.query(
            Market.status, 
            db.func.count(Market.id)
        ).group_by(Market.status).all()
        
        # Get recent pipeline runs (if available)
        recent_runs = []
        try:
            from models_updated import PipelineRun
            recent_runs = db.session.query(PipelineRun).order_by(
                desc(PipelineRun.started_at)
            ).limit(5).all()
        except:
            pass
        
        # Get markets ready for deployment
        deployable_markets = db.session.query(PendingMarket).filter_by(
            posted=True, 
            status='approved'
        ).count()
        
        # Print status information
        print("\n=== PIPELINE STATUS ===")
        print(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n--- Database Stats ---")
        print(f"Total events: {total_events}")
        print(f"Total deployed markets: {total_markets}")
        print(f"Pending markets: {pending_markets}")
        print(f"  - Unposted: {pending_unposted}")
        print(f"  - Posted to Slack: {pending_posted}")
        print(f"  - Ready for deployment: {deployable_markets}")
        
        print("\n--- Category Distribution ---")
        for category, count in sorted(category_counts, key=lambda x: x[1], reverse=True):
            print(f"  {category or 'uncategorized'}: {count}")
        
        print("\n--- Market Status Distribution ---")
        for status, count in sorted(status_counts, key=lambda x: x[1], reverse=True):
            print(f"  {status}: {count}")
        
        if recent_runs:
            print("\n--- Recent Pipeline Runs ---")
            for run in recent_runs:
                duration = (run.completed_at - run.started_at).total_seconds() if run.completed_at else None
                status = "Completed" if run.completed_at else "Running"
                print(f"  {run.started_at.strftime('%Y-%m-%d %H:%M:%S')} - {status}")
                if duration:
                    print(f"    Duration: {duration:.2f} seconds")
                print(f"    Markets processed: {run.markets_processed}")
                print(f"    Markets posted: {run.markets_posted}")
        
        print("\n--- Next Steps ---")
        if pending_unposted > 0:
            print(f"Post {pending_unposted} markets to Slack for approval:")
            print("  python post_unposted_pending_markets.py")
        
        if pending_posted > 0:
            print(f"Check {pending_posted} posted markets for approvals/rejections:")
            print("  python check_pending_approvals.py")
        
        if deployable_markets > 0:
            print(f"Deploy {deployable_markets} approved markets to Apechain:")
            print("  python deploy_event_markets.py")
        
        if pending_unposted == 0 and pending_posted == 0 and deployable_markets == 0:
            print("Run the pipeline to fetch new markets:")
            print("  python run_pipeline_with_events.py")
        
        print("\n======================\n")

def main():
    """Main function."""
    check_pipeline_status()
    return 0

if __name__ == "__main__":
    sys.exit(main())