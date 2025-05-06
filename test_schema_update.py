#!/usr/bin/env python3

"""
Test the database schema update for the PendingMarket model.
This script verifies that the 'posted' field has been properly added.
"""

import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Flask app for database context
from main import app
from models import db, PendingMarket

def test_pending_market_schema():
    """Test the PendingMarket schema by creating and querying a test record."""
    
    # Create a test market with posted=False
    test_market = PendingMarket(
        poly_id='test_schema_update',
        question='Test schema update - Is the posted field working?',
        category='tech',
        banner_url='https://example.com/test.jpg',
        icon_url='https://example.com/test-icon.jpg',
        options=['Yes', 'No'],
        expiry=int(datetime.now().timestamp()) + 86400,  # 1 day in future
        posted=False,
        needs_manual_categorization=False,
        raw_data={'test': True}
    )
    
    # Save to database
    db.session.add(test_market)
    db.session.commit()
    
    logger.info(f"Created test market with posted=False, ID={test_market.poly_id}")
    
    # Query the market back
    queried_market = PendingMarket.query.filter_by(poly_id='test_schema_update').first()
    
    if queried_market:
        logger.info(f"Retrieved test market: {queried_market.question}")
        logger.info(f"Posted value: {queried_market.posted}")
        
        # Test updating the posted field
        queried_market.posted = True
        db.session.commit()
        
        logger.info(f"Updated posted value to {queried_market.posted}")
        
        # Query again to confirm update
        updated_market = PendingMarket.query.filter_by(poly_id='test_schema_update').first()
        logger.info(f"Final posted value: {updated_market.posted}")
        
        # Clean up test data
        db.session.delete(updated_market)
        db.session.commit()
        logger.info("Test market removed from database")
        
        return True
    else:
        logger.error("Failed to retrieve test market")
        return False

def main():
    """Main function to test the schema update."""
    with app.app_context():
        success = test_pending_market_schema()
        
        if success:
            logger.info("Schema test completed successfully!")
            return 0
        else:
            logger.error("Schema test failed!")
            return 1

if __name__ == "__main__":
    main()