"""
Sample market transformation test script.
This script creates sample multi-option markets with generic options to test our fix.
"""
import json
import logging
from utils.market_transformer import MarketTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create sample test data with generic options"""
    # Sample event banner
    event_banner = "https://example.com/event-banner.png"
    
    # Champions League sample with "Barcelona" and "Another Team" options
    champions_league_markets = [
        {
            "id": "real-madrid-cl-market",
            "question": "Will Real Madrid win the Champions League?",
            "image": "https://example.com/real-madrid.png",
            "icon": "https://example.com/real-madrid.png",
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": ["Yes", "No"],
            "eventId": "champions-league-event",
            "events": [
                {
                    "id": "champions-league-event",
                    "title": "Champions League Winner 2025",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        },
        {
            "id": "barcelona-cl-market",
            "question": "Will Barcelona win the Champions League?",
            "image": event_banner,  # Using event banner for Barcelona (wrong)
            "icon": event_banner,
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": ["Yes", "No"],
            "eventId": "champions-league-event",
            "events": [
                {
                    "id": "champions-league-event",
                    "title": "Champions League Winner 2025",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        },
        {
            "id": "another-team-cl-market",
            "question": "Will Another Team win the Champions League?",
            "image": event_banner,  # Using event banner for Another Team (wrong)
            "icon": event_banner,
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": ["Yes", "No"],
            "eventId": "champions-league-event",
            "events": [
                {
                    "id": "champions-league-event",
                    "title": "Champions League Winner 2025",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        }
    ]
    
    return champions_league_markets

def test_market_transformation():
    """Test market transformation with sample data"""
    # Create sample test data
    test_markets = create_test_data()
    logger.info(f"Created {len(test_markets)} sample test markets")
    
    # Transform markets using our transformer
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(test_markets)
    logger.info(f"Transformed into {len(transformed)} markets")
    
    # Find multi-option markets
    multi_option_markets = [m for m in transformed if m.get("is_multiple_option", False)]
    logger.info(f"Found {len(multi_option_markets)} multi-option markets")
    
    # Check each multi-option market
    for market in multi_option_markets:
        logger.info(f"\nAnalyzing multi-option market: {market.get('question')}")
        
        # Get outcomes
        outcomes = market.get("outcomes", "[]")
        if isinstance(outcomes, str):
            try:
                decoded_outcomes = json.loads(outcomes)
            except:
                logger.error(f"Could not parse outcomes: {outcomes}")
                continue
        else:
            decoded_outcomes = outcomes
        
        # Get option images
        option_images = market.get("option_images", "{}")
        if isinstance(option_images, str):
            try:
                decoded_images = json.loads(option_images)
            except:
                logger.error(f"Could not parse option_images: {option_images}")
                continue
        else:
            decoded_images = option_images
        
        # Get event image
        event_image = market.get("event_image")
        logger.info(f"Event image: {event_image}")
        
        # Check each option
        for option in decoded_outcomes:
            # Is this a generic option?
            is_generic = ("another" in option.lower() or 
                         "other" in option.lower() or 
                         option.lower() == "barcelona")
            
            # What image is assigned?
            image = decoded_images.get(option)
            is_event_image = (image == event_image)
            
            status = "✅" if not (is_generic and is_event_image) else "❌"
            generic_label = "GENERIC" if is_generic else "Standard"
            image_label = "USING EVENT IMAGE" if is_event_image else "using unique image"
            
            logger.info(f"{status} {generic_label} option '{option}': {image_label}")
            logger.info(f"  Image: {image}")
            
            if is_generic and is_event_image:
                logger.error(f"ISSUE: Generic option '{option}' is still using event image")
            elif is_generic:
                logger.info(f"FIXED: Generic option '{option}' is correctly using non-event image")

def main():
    """Main function"""
    logger.info("=== SAMPLE MARKET TRANSFORMATION TEST ===")
    test_market_transformation()
    logger.info("=== TEST COMPLETE ===")

if __name__ == "__main__":
    main()