"""
Test the image handling logic for multi-option markets, particularly 
for "Another Team" option and Barcelona team.

This script:
1. Creates mock markets with problematic options
2. Verifies the MarketTransformer logic handles them properly
"""
import json
import logging
from typing import Dict, List, Any, Tuple

from utils.market_transformer import MarketTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_mock_europa_league_markets() -> List[Dict[str, Any]]:
    """Create mock Europa League markets with 'Another Team' option"""
    
    # Event ID for connecting markets
    event_id = "europa-league-2025"
    
    # Team data - each has a market and image
    teams = [
        {"name": "Arsenal", "id": "arsenal-europa", 
         "image": "https://example.com/arsenal.png"},
        {"name": "Roma", "id": "roma-europa", 
         "image": "https://example.com/roma.png"},
        {"name": "Sevilla", "id": "sevilla-europa", 
         "image": "https://example.com/sevilla.png"},
    ]
    
    # Event image (different from team images)
    event_image = "https://example.com/europa-league.png"
    
    # Create markets with proper structure
    markets = []
    
    # Add markets for each team
    for team in teams:
        markets.append({
            "id": team["id"],
            "question": f"Will {team['name']} win the 2025 Europa League?",
            "image": team["image"],
            "icon": team["image"],  # Same as image for simplicity
            "active": True,
            "closed": False,
            "archived": False,
            "liquidity": 10000,
            "category": "sports",
            "subcategory": "soccer",
            "conditionId": f"{team['id']}-condition",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": event_id,
            "events": [
                {
                    "id": event_id,
                    "title": "UEFA Europa League 2025 Winner",
                    "image": event_image,
                    "icon": event_image,
                    "category": "soccer"
                }
            ]
        })
    
    # Add Another Team market
    markets.append({
        "id": "another-team-europa",
        "question": "Will Another Team win the 2025 Europa League?",
        "image": event_image,  # This is the problem - using event image
        "icon": event_image,
        "active": True,
        "closed": False,
        "archived": False,
        "liquidity": 10000,
        "category": "sports",
        "subcategory": "soccer",
        "conditionId": "another-team-europa-condition",
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
        "eventId": event_id,
        "events": [
            {
                "id": event_id,
                "title": "UEFA Europa League 2025 Winner",
                "image": event_image,
                "icon": event_image,
                "category": "soccer"
            }
        ]
    })
    
    return markets

def create_mock_champions_league_markets() -> List[Dict[str, Any]]:
    """Create mock Champions League markets with Barcelona option"""
    
    # Event ID for connecting markets
    event_id = "champions-league-2025"
    
    # Team data - each has a market and image
    teams = [
        {"name": "Real Madrid", "id": "real-madrid-champions", 
         "image": "https://example.com/real-madrid.png"},
        {"name": "Bayern Munich", "id": "bayern-munich-champions", 
         "image": "https://example.com/bayern.png"},
        {"name": "Manchester City", "id": "man-city-champions", 
         "image": "https://example.com/man-city.png"},
    ]
    
    # Event image (different from team images)
    event_image = "https://example.com/champions-league.png"
    
    # Create markets with proper structure
    markets = []
    
    # Add markets for each team
    for team in teams:
        markets.append({
            "id": team["id"],
            "question": f"Will {team['name']} win the 2025 Champions League?",
            "image": team["image"],
            "icon": team["image"],  # Same as image for simplicity
            "active": True,
            "closed": False,
            "archived": False,
            "liquidity": 10000,
            "category": "sports",
            "subcategory": "soccer",
            "conditionId": f"{team['id']}-condition",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": event_id,
            "events": [
                {
                    "id": event_id,
                    "title": "UEFA Champions League 2025 Winner",
                    "image": event_image,
                    "icon": event_image,
                    "category": "soccer"
                }
            ]
        })
    
    # Add Barcelona market with event image instead of team image
    markets.append({
        "id": "barcelona-champions",
        "question": "Will Barcelona win the 2025 Champions League?",
        "image": event_image,  # This is the problem - using event image
        "icon": event_image,
        "active": True,
        "closed": False,
        "archived": False,
        "liquidity": 10000,
        "category": "sports",
        "subcategory": "soccer",
        "conditionId": "barcelona-champions-condition",
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
        "eventId": event_id,
        "events": [
            {
                "id": event_id,
                "title": "UEFA Champions League 2025 Winner",
                "image": event_image,
                "icon": event_image,
                "category": "soccer"
            }
        ]
    })
    
    # Add Another Team market
    markets.append({
        "id": "another-team-champions",
        "question": "Will Another Team win the 2025 Champions League?",
        "image": event_image,  # This is the problem - using event image
        "icon": event_image,
        "active": True,
        "closed": False,
        "archived": False,
        "liquidity": 10000,
        "category": "sports",
        "subcategory": "soccer",
        "conditionId": "another-team-champions-condition",
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
        "eventId": event_id,
        "events": [
            {
                "id": event_id,
                "title": "UEFA Champions League 2025 Winner",
                "image": event_image,
                "icon": event_image,
                "category": "soccer"
            }
        ]
    })
    
    return markets

def create_mock_la_liga_markets() -> List[Dict[str, Any]]:
    """Create mock La Liga markets with 'Another Team' option"""
    
    # Event ID for connecting markets
    event_id = "la-liga-2025"
    
    # Team data - each has a market and image
    teams = [
        {"name": "Real Madrid", "id": "real-madrid-la-liga", 
         "image": "https://example.com/real-madrid.png"},
        {"name": "Barcelona", "id": "barcelona-la-liga", 
         "image": "https://example.com/barcelona.png"},
        {"name": "Atletico Madrid", "id": "atletico-la-liga", 
         "image": "https://example.com/atletico.png"},
    ]
    
    # Event image (different from team images)
    event_image = "https://example.com/la-liga.png"
    
    # Create markets with proper structure
    markets = []
    
    # Add markets for each team
    for team in teams:
        markets.append({
            "id": team["id"],
            "question": f"Will {team['name']} win La Liga 2025?",
            "image": team["image"],
            "icon": team["image"],  # Same as image for simplicity
            "active": True,
            "closed": False,
            "archived": False,
            "liquidity": 10000,
            "category": "sports",
            "subcategory": "soccer",
            "conditionId": f"{team['id']}-condition",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": event_id,
            "events": [
                {
                    "id": event_id,
                    "title": "La Liga 2025 Winner",
                    "image": event_image,
                    "icon": event_image,
                    "category": "soccer"
                }
            ]
        })
    
    # Add Another Team market
    markets.append({
        "id": "another-team-la-liga",
        "question": "Will Another Team win La Liga 2025?",
        "image": event_image,  # This is the problem - using event image
        "icon": event_image,
        "active": True,
        "closed": False,
        "archived": False,
        "liquidity": 10000,
        "category": "sports",
        "subcategory": "soccer",
        "conditionId": "another-team-la-liga-condition",
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
        "eventId": event_id,
        "events": [
            {
                "id": event_id,
                "title": "La Liga 2025 Winner",
                "image": event_image,
                "icon": event_image,
                "category": "soccer"
            }
        ]
    })
    
    return markets

def analyze_multi_option_market(market: Dict[str, Any], title: str) -> bool:
    """
    Analyze a multi-option market for proper image handling.
    
    Args:
        market: Transformed market data
        title: Title for logging
        
    Returns:
        True if all images are properly handled, False otherwise
    """
    logger.info(f"\n{'=' * 80}")
    logger.info(f"ANALYSIS OF {title}")
    logger.info(f"{'=' * 80}")
    
    # Basic market info
    logger.info(f"Market question: {market.get('question')}")
    
    # Check if multi-option
    is_multi = market.get("is_multiple_option", False)
    if not is_multi:
        logger.error("Not a multi-option market!")
        return False
    
    # Get options
    outcomes = json.loads(market.get("outcomes", "[]"))
    logger.info(f"Options ({len(outcomes)}): {outcomes}")
    
    # Get option images
    option_images = json.loads(market.get("option_images", "{}"))
    
    # Check event image
    event_image = market.get("event_image")
    logger.info(f"Event image: {event_image}")
    
    # Check for problematic options
    problematic_options = []
    
    # Track success status
    all_images_correct = True
    
    # Check each option's image
    for option in outcomes:
        # Check if this is a generic option
        is_generic = "another" in option.lower() or "other" in option.lower()
        is_barcelona = "barcelona" in option.lower()
        
        # Get image
        image_url = option_images.get(option)
        
        # Check if using event image
        using_event_image = (image_url == event_image) if image_url and event_image else False
        
        # Determine if this is correct behavior
        if (is_generic or is_barcelona) and using_event_image:
            logger.error(f"Option '{option}': FAILING - Using event image!")
            problematic_options.append(option)
            all_images_correct = False
        else:
            logger.info(f"Option '{option}': OK - Has appropriate image")
    
    # Summary
    if problematic_options:
        logger.error(f"Found {len(problematic_options)} problematic options: {problematic_options}")
    else:
        logger.info("All options have appropriate images")
    
    logger.info(f"{'=' * 80}\n")
    return all_images_correct

def test_option_image_handling():
    """Test the option image handling logic"""
    logger.info("Testing option image handling in multi-option markets")
    
    # Create mock markets
    europa_markets = create_mock_europa_league_markets()
    champions_markets = create_mock_champions_league_markets()
    la_liga_markets = create_mock_la_liga_markets()
    
    # Combine all markets
    all_markets = europa_markets + champions_markets + la_liga_markets
    
    # Transform with our enhanced MarketTransformer
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(all_markets)
    
    # Find multi-option markets
    europa_market = None
    champions_market = None
    la_liga_market = None
    
    for market in transformed:
        if not market.get("is_multiple_option", False):
            continue
            
        question = market.get("question", "").lower()
        
        if "europa league" in question:
            europa_market = market
        elif "champions league" in question:
            champions_market = market
        elif "la liga" in question:
            la_liga_market = market
    
    # Analyze each market
    all_passing = True
    
    if europa_market:
        logger.info("Found Europa League multi-option market")
        if not analyze_multi_option_market(europa_market, "EUROPA LEAGUE"):
            all_passing = False
    else:
        logger.error("No Europa League multi-option market found")
        all_passing = False
    
    if champions_market:
        logger.info("Found Champions League multi-option market")
        if not analyze_multi_option_market(champions_market, "CHAMPIONS LEAGUE"):
            all_passing = False
    else:
        logger.error("No Champions League multi-option market found")
        all_passing = False
    
    if la_liga_market:
        logger.info("Found La Liga multi-option market")
        if not analyze_multi_option_market(la_liga_market, "LA LIGA"):
            all_passing = False
    else:
        logger.error("No La Liga multi-option market found")
        all_passing = False
    
    # Final result
    if all_passing:
        logger.info("✅ ALL TESTS PASSED - Image handling fixes are working correctly!")
    else:
        logger.error("❌ TESTS FAILED - Some issues remain with image handling")

def main():
    """Main function to run the tests"""
    logger.info("Starting option image handling tests")
    
    # Run tests
    test_option_image_handling()
    
    logger.info("Tests completed")

if __name__ == "__main__":
    main()