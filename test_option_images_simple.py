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
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
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
            "id": "barcelona-market",
            "question": "Will Barcelona win the Champions League?",
            "image": event_banner,  # Using event banner for Barcelona
            "icon": event_banner,
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
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
    
    # La Liga test
    la_liga_markets = [
        {
            "id": "real-madrid-liga-market",
            "question": "Will Real Madrid win La Liga?",
            "image": "https://example.com/real-madrid.png",
            "icon": "https://example.com/real-madrid.png",
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": "la-liga-event",
            "events": [
                {
                    "id": "la-liga-event",
                    "title": "La Liga Winner 2025",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        },
        {
            "id": "another-team-liga-market",
            "question": "Will Another Team win La Liga?",
            "image": event_banner,  # Using event banner for Another Team
            "icon": event_banner,
            "active": True,
            "closed": False,
            "archived": False,
            "category": "sports",
            "subcategory": "soccer",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": "la-liga-event",
            "events": [
                {
                    "id": "la-liga-event",
                    "title": "La Liga Winner 2025",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        }
    ]
    
    return champions_league_markets + la_liga_markets

def main():
    """Run a simple test to check image handling"""
    # Create test data
    test_markets = create_test_data()
    print(f"Created test markets:\n")
    for i, market in enumerate(test_markets):
        print(f"Market {i+1}: {market['question']}")
        print(f"  Image: {market['image']}")
        print(f"  Events: {[e['title'] for e in market['events']]}")
        print(f"  Event image: {market['events'][0]['image']}")
        print()
    
    # Enable debug logging for MarketTransformer
    transformer = MarketTransformer()
    
    # Add debug hooks to see what's happening in the transformer
    orig_transform = transformer.transform_markets
    
    def debug_transform(markets):
        print("\n--- DEBUG: Starting market transformation ---")
        result = orig_transform(markets)
        print(f"\n--- DEBUG: Transformation complete, {len(result)} markets produced ---")
        return result
    
    transformer.transform_markets = debug_transform
    
    # Transform markets
    transformed = transformer.transform_markets(test_markets)
    
    # Find multi-option markets
    found_markets = False
    
    for market in transformed:
        if market.get("is_multiple_option", False):
            found_markets = True
            # Get details
            question = market.get("question", "")
            outcomes = json.loads(market.get("outcomes", "[]")) if isinstance(market.get("outcomes"), str) else market.get("outcomes", [])
            option_images_raw = market.get("option_images", "{}")
            option_images = json.loads(option_images_raw) if isinstance(option_images_raw, str) else option_images_raw
            event_image = market.get("event_image")
            
            print(f"\n=== MULTI-OPTION MARKET: {question} ===")
            print(f"Market ID: {market.get('id')}")
            print(f"Is multiple option: {market.get('is_multiple_option')}")
            print(f"Original question: {market.get('original_question')}")
            print(f"Original market IDs: {market.get('original_market_ids')}")
            print(f"Options ({len(outcomes)}): {outcomes}")
            print(f"Event image: {event_image}")
            print(f"Option images ({len(option_images)}): {option_images}")
            
            # Check each option's image
            print("\nOption by option check:")
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
    
    if not found_markets:
        print("\n❌ ERROR: No multi-option markets were created during transformation")
        
    # Print success message if everything seems to be working
    if found_markets:
        # Check for any remaining issues
        issues_found = False
        for market in transformed:
            if market.get("is_multiple_option", False):
                outcomes = json.loads(market.get("outcomes", "[]")) if isinstance(market.get("outcomes"), str) else market.get("outcomes", [])
                option_images_raw = market.get("option_images", "{}")
                option_images = json.loads(option_images_raw) if isinstance(option_images_raw, str) else option_images_raw
                event_image = market.get("event_image")
                
                for option in outcomes:
                    is_generic = "another" in option.lower() or "other" in option.lower() or option == "Barcelona"
                    image = option_images.get(option, "None")
                    is_event_image = (image == event_image)
                    
                    if is_generic and is_event_image:
                        issues_found = True
        
        if not issues_found:
            print("\n✅ SUCCESS: All generic options are properly using team-specific images instead of event images")
        else:
            print("\n❌ ISSUES REMAIN: Some generic options are still using event images")

if __name__ == "__main__":
    main()