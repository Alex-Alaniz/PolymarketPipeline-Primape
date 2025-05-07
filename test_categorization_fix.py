"""
Test the categorization fix by categorizing a small batch of markets.
"""
import sys
import json
import logging
from datetime import datetime
from flask import Flask
from models import db, PendingMarket, PipelineRun, ProcessedMarket
from main import app
from utils.batch_categorizer import batch_categorize_markets

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_categorization")

def test_categorization():
    """Test the categorization fix on a small batch of markets."""
    with app.app_context():
        # Create a test batch of markets
        test_markets = [
            {
                "id": "test_market_1",
                "question": "Will Donald Trump win the 2024 US Election?",
                "category": None
            },
            {
                "id": "test_market_2",
                "question": "Will Bitcoin exceed $100,000 by the end of 2024?",
                "category": None
            },
            {
                "id": "test_market_3",
                "question": "Will the Kansas City Chiefs win the Super Bowl in 2025?",
                "category": None
            },
            {
                "id": "test_market_4",
                "question": "Will Tesla stock price exceed $1000 by the end of 2024?",
                "category": None
            },
            {
                "id": "test_market_5",
                "question": "Will Dune: Part 2 win an Oscar in 2025?",
                "category": None
            },
        ]
        
        # Batch categorize the markets
        logger.info(f"Categorizing {len(test_markets)} test markets with GPT-4o-mini...")
        categorized_markets = batch_categorize_markets(test_markets)
        
        # Log the results
        logger.info("Categorization results:")
        for market in categorized_markets:
            market_id = market.get("id")
            category = market.get("ai_category", "Unknown")
            question = next((m["question"] for m in test_markets if m["id"] == market_id), "Unknown")
            logger.info(f"Market '{question}' categorized as: {category}")
        
        # Store in database to verify persistence
        for market in categorized_markets:
            market_id = market.get("id")
            category = market.get("ai_category", "news")
            question = next((m["question"] for m in test_markets if m["id"] == market_id), "Unknown")
            
            # Get the PendingMarket model so we can inspect it
            from datetime import datetime, timedelta
            import json
            
            # Use current timestamp plus 1 year for expiry
            future_date = datetime.now() + timedelta(days=365)
            
            # Store as PendingMarket
            pending_market = PendingMarket(
                poly_id=market_id,
                question=question,
                category=category,
                banner_url="https://example.com/banner.jpg",
                options=json.dumps([{"id": "option_0", "value": "Yes"}, {"id": "option_1", "value": "No"}]),
                option_images=json.dumps({}),
                expiry=future_date.timestamp(),  # Use timestamp (numeric) for expiry
                raw_data=json.dumps({"id": market_id, "question": question}),
                needs_manual_categorization=False,
                posted=False,
                event_id=None,
                event_name=None
            )
            
            db.session.add(pending_market)
        
        db.session.commit()
        logger.info("Markets stored in database.")
        
        # Verify database storage
        logger.info("Database categories:")
        # Using poly_id instead of id
        categories = db.session.query(PendingMarket.category, db.func.count(PendingMarket.poly_id)).group_by(PendingMarket.category).all()
        for category, count in categories:
            logger.info(f"  - {category}: {count} markets")
            
        return 0

if __name__ == "__main__":
    sys.exit(test_categorization())