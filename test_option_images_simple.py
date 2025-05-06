"""
Simple test script to check if the image handling for Another Team and Barcelona options is working
"""
import json
import logging
from utils.market_transformer import MarketTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create minimal test data to test the fix"""
    # Common event banner
    event_banner = "https://example.com/event-banner.png"
    
    # Champions League test
    champions_league_markets = [
        {
            "id": "real-madrid-market",
            "question": "Will Real Madrid win the Champions League?",
            "image": "https://example.com/real-madrid.png",
            "icon": "https://example.com/real-madrid.png",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "events": [
                {
                    "id": "champions-league-event",
                    "title": "Champions League Winner 2025",
                    "image": event_banner,
                    "icon": event_banner
                }
            ]
        },
        {
            "id": "barcelona-market",
            "question": "Will Barcelona win the Champions League?",
            "image": event_banner,  # Using event banner for Barcelona
            "icon": event_banner,
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "events": [
                {
                    "id": "champions-league-event",
                    "title": "Champions League Winner 2025",
                    "image": event_banner,
                    "icon": event_banner
                }
            ]
        }
    ]
    
    # La Liga test
    la_liga_markets = [
        {
            "id": "real-madrid-liga-market",
            "question": "Will Real Madrid win La Liga?",
            "image": "https://example.com/real-madrid.png",
            "icon": "https://example.com/real-madrid.png",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "events": [
                {
                    "id": "la-liga-event",
                    "title": "La Liga Winner 2025",
                    "image": event_banner,
                    "icon": event_banner
                }
            ]
        },
        {
            "id": "another-team-liga-market",
            "question": "Will Another Team win La Liga?",
            "image": event_banner,  # Using event banner for Another Team
            "icon": event_banner,
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "events": [
                {
                    "id": "la-liga-event",
                    "title": "La Liga Winner 2025",
                    "image": event_banner,
                    "icon": event_banner
                }
            ]
        }
    ]
    
    return champions_league_markets + la_liga_markets

def main():
    """Run a simple test to check image handling"""
    # Create test data
    test_markets = create_test_data()
    
    # Transform markets
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(test_markets)
    
    # Find multi-option markets
    for market in transformed:
        if market.get("is_multiple_option", False):
            # Get details
            question = market.get("question", "")
            outcomes = json.loads(market.get("outcomes", "[]"))
            option_images = json.loads(market.get("option_images", "{}"))
            event_image = market.get("event_image")
            
            print(f"\n=== MULTI-OPTION MARKET: {question} ===")
            print(f"Options: {outcomes}")
            print(f"Event image: {event_image}")
            
            # Check each option's image
            for option in outcomes:
                image = option_images.get(option, "None")
                is_event_image = (image == event_image)
                
                # Highlight generic options
                is_generic = "another" in option.lower() or "other" in option.lower() or option == "Barcelona"
                option_type = "GENERIC" if is_generic else "Standard"
                
                status = "❌ USING EVENT IMAGE" if is_event_image else "✅ USING UNIQUE IMAGE"
                print(f"  {option_type} Option '{option}': {status}")
                print(f"    Image: {image}")
                
                if is_generic and is_event_image:
                    print("    ❌ ISSUE: Generic option should not use event image")
                elif is_generic and not is_event_image:
                    print("    ✅ FIXED: Generic option correctly using unique image")

if __name__ == "__main__":
    main()