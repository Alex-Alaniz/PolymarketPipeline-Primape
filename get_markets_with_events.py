#!/usr/bin/env python3

"""
Get Markets with Events API Endpoint

This script provides a simple API endpoint to retrieve markets grouped by events.
It demonstrates the event-based market structure for frontend integration.
"""

import json
import logging
from flask import jsonify

from models import db, Market
from main import app

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("get_markets_with_events")

def get_markets_by_events():
    """
    Get markets grouped by events.
    
    Returns:
        dict: Event-based market structure
    """
    try:
        with app.app_context():
            # Get all event markets
            event_markets = Market.query.filter_by(is_event=True).all()
            
            # Get all regular markets
            regular_markets = Market.query.filter_by(is_event=False).all()
            
            # Format the response
            events = []
            for event_market in event_markets:
                try:
                    # Parse option market IDs
                    option_market_ids = json.loads(event_market.option_market_ids) if event_market.option_market_ids else {}
                    
                    # Parse options
                    options = json.loads(event_market.options) if event_market.options else []
                    
                    # Parse option images
                    option_images = json.loads(event_market.option_images) if event_market.option_images else {}
                    
                    # Create event structure
                    event = {
                        "id": event_market.event_id,
                        "name": event_market.event_name,
                        "image": event_market.event_image,
                        "icon": event_market.event_icon,
                        "category": event_market.category,
                        "options": options,
                        "option_images": option_images,
                        "option_market_ids": option_market_ids,
                        "markets": []  # To be filled with related markets
                    }
                    
                    events.append(event)
                except Exception as e:
                    logger.error(f"Error processing event market {event_market.id}: {str(e)}")
            
            # Add standalone markets
            standalone_markets = []
            for market in regular_markets:
                try:
                    # Parse options
                    options = json.loads(market.options) if market.options else []
                    
                    # Create standalone market structure
                    standalone_market = {
                        "id": market.id,
                        "question": market.question,
                        "category": market.category,
                        "options": options,
                        "expiry": market.expiry,
                        "banner_uri": market.banner_uri,
                        "apechain_market_id": market.apechain_market_id,
                        "status": market.status
                    }
                    
                    standalone_markets.append(standalone_market)
                except Exception as e:
                    logger.error(f"Error processing regular market {market.id}: {str(e)}")
            
            # Return the grouped data
            return {
                "events": events,
                "markets": standalone_markets
            }
    except Exception as e:
        logger.error(f"Error getting markets by events: {str(e)}")
        return {"events": [], "markets": []}

@app.route('/api/markets-with-events', methods=['GET'])
def api_markets_with_events():
    """
    API endpoint to get markets grouped by events.
    
    Returns:
        JSON response with markets grouped by events
    """
    data = get_markets_by_events()
    return jsonify(data)

def main():
    """
    Main function to run the test.
    """
    with app.app_context():
        data = get_markets_by_events()
        print(json.dumps(data, indent=4))

if __name__ == "__main__":
    main()