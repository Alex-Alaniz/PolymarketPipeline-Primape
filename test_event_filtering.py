"""
Test the event filtering functionality.

This script creates some sample market data with events and tests the
filtering to ensure only active, non-closed events are included.
"""

import logging
import json
from utils.event_filter import filter_inactive_events, process_event_images

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_market():
    """Create a test market with mixed active and inactive events."""
    return {
        "id": "test_market_123",
        "question": "Which team will win the Champions League 2025?",
        "category": "sports",
        "endDate": "2025-05-31T23:59:59Z",
        "is_multiple_option": True,
        "is_event": True,
        "events": [
            {
                "id": "event1",
                "title": "Champions League 2025",
                "category": "sports",
                "active": True,
                "closed": False,
                "image": "https://blog.replit.com/images/site/logo.png",
                "icon": "https://blog.replit.com/images/site/logo.png",
                "outcomes": [
                    {
                        "title": "Real Madrid",
                        "image": "https://blog.replit.com/images/site/logo.png"
                    },
                    {
                        "title": "Manchester City",
                        "image": "https://blog.replit.com/images/site/logo.png"
                    }
                ]
            },
            {
                "id": "event2",
                "title": "Closed Event",
                "category": "sports",
                "active": True,
                "closed": True,  # This event should be filtered out
                "image": "https://example.com/closed.png",
                "icon": "https://example.com/closed.png",
                "outcomes": [
                    {
                        "title": "Filtered Option 1",
                        "image": "https://example.com/filtered1.png"
                    }
                ]
            },
            {
                "id": "event3",
                "title": "Inactive Event",
                "category": "sports",
                "active": False,  # This event should be filtered out
                "closed": False,
                "image": "https://example.com/inactive.png",
                "icon": "https://example.com/inactive.png",
                "outcomes": [
                    {
                        "title": "Filtered Option 2",
                        "image": "https://example.com/filtered2.png"
                    }
                ]
            }
        ],
        "outcomes": json.dumps(["Real Madrid", "Manchester City", "Bayern Munich", "PSG"])
    }

def test_event_filtering():
    """Test the event filtering functionality."""
    # Create a test market
    market = create_test_market()
    
    logger.info("Original market has %d events:", len(market.get("events", [])))
    for i, event in enumerate(market.get("events", [])):
        logger.info("  Event %d: %s (active=%s, closed=%s)", 
                   i+1, event.get("title"), event.get("active"), event.get("closed"))
    
    # Filter inactive events
    filtered_market = filter_inactive_events(market)
    
    # Check filtered events
    filtered_events = filtered_market.get("events", [])
    logger.info("After filtering, market has %d events:", len(filtered_events))
    for i, event in enumerate(filtered_events):
        logger.info("  Event %d: %s (active=%s, closed=%s)", 
                   i+1, event.get("title"), event.get("active"), event.get("closed"))
    
    # Verify only active=true, closed=false events remain
    assert all(event.get("active", False) for event in filtered_events), "All events should be active"
    assert all(not event.get("closed", True) for event in filtered_events), "No events should be closed"
    
    # Process images from filtered events
    processed_market = process_event_images(filtered_market)
    
    # Check extracted images
    logger.info("After image processing:")
    logger.info("  Event ID: %s", processed_market.get("event_id"))
    logger.info("  Event Name: %s", processed_market.get("event_name"))
    logger.info("  Event Image: %s", processed_market.get("event_image"))
    logger.info("  Event Icon: %s", processed_market.get("event_icon"))
    
    # Check option images
    option_images = processed_market.get("option_images", {})
    logger.info("  Option Images: %d", len(option_images))
    for option, image in option_images.items():
        logger.info("    %s: %s", option, image)
    
    logger.info("Event filtering test completed successfully!")
    return True

if __name__ == "__main__":
    test_event_filtering()