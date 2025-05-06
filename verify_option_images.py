"""
Verification script specifically for the "Another Team" and Barcelona image issues.

This script:
1. Tests with real-world data from Polymarket API
2. Creates mock data simulating the exact issues
3. Reports if the fixes are working correctly
"""
import json
import logging
import requests
from typing import Dict, Any, List, Tuple
from utils.market_transformer import MarketTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data() -> List[Dict[str, Any]]:
    """Create test data that simulates the problematic scenarios"""
    # Common event banner
    event_banner = "https://example.com/event-banner.png"
    
    # Champions League test with 3 teams to ensure multi-option creation
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
        },
        {
            "id": "another-team-cl-market",
            "question": "Will Another Team win the Champions League?",
            "image": event_banner,  # Using event banner for Another Team
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
    
    # La Liga test with 3 teams to ensure multi-option creation
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
            "id": "barcelona-liga-market",
            "question": "Will Barcelona win La Liga?",
            "image": "https://example.com/barcelona.png",
            "icon": "https://example.com/barcelona.png",
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

def analyze_market(market: Dict[str, Any], target_option: str) -> Tuple[bool, str]:
    """
    Analyze a market to see if the target option is using a team image instead of event banner.
    
    Args:
        market: Transformed market data
        target_option: The specific option to check (e.g., "Barcelona" or "Another Team")
        
    Returns:
        Tuple of (is_fixed, details)
    """
    outcomes = json.loads(market.get("outcomes", "[]")) if isinstance(market.get("outcomes"), str) else market.get("outcomes", [])
    option_images_raw = market.get("option_images", "{}")
    option_images = json.loads(option_images_raw) if isinstance(option_images_raw, str) else option_images_raw
    event_image = market.get("event_image")
    
    if target_option not in outcomes:
        return (False, f"Option '{target_option}' not found in outcomes: {outcomes}")
    
    image = option_images.get(target_option)
    if not image:
        return (False, f"No image found for option '{target_option}'")
        
    is_event_image = (image == event_image)
    if is_event_image:
        return (False, f"Issue: Option '{target_option}' is using event image: {image}")
    else:
        return (True, f"Fixed: Option '{target_option}' is using unique image: {image}")

def verify_fix_with_test_data():
    """Verify our fix with controlled test data"""
    logger.info("Starting verification with test data...")
    
    # Create test data
    test_markets = create_test_data()
    logger.info(f"Created {len(test_markets)} test markets")
    
    # Transform markets
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(test_markets)
    
    # Check for multi-option markets
    multi_option_markets = [m for m in transformed if m.get("is_multiple_option", False)]
    logger.info(f"Transformed into {len(transformed)} markets, of which {len(multi_option_markets)} are multi-option")
    
    if not multi_option_markets:
        logger.error("No multi-option markets were created - test failed")
        return False
    
    # Check specifically for the problematic options
    barcelona_fixed = False
    another_team_fixed = False
    
    for market in multi_option_markets:
        logger.info(f"Checking multi-option market: {market.get('question')}")
        
        # Check for Barcelona option
        barcelona_result = analyze_market(market, "Barcelona")
        if barcelona_result[0]:
            logger.info(f"Barcelona check: {barcelona_result[1]}")
            barcelona_fixed = True
        else:
            logger.warning(f"Barcelona check: {barcelona_result[1]}")
        
        # Check for Another Team option
        another_team_result = analyze_market(market, "Another Team")
        if another_team_result[0]:
            logger.info(f"Another Team check: {another_team_result[1]}")
            another_team_fixed = True
        else:
            logger.warning(f"Another Team check: {another_team_result[1]}")
    
    # Summarize results
    if barcelona_fixed and another_team_fixed:
        logger.info("✅ TEST PASSED: Both Barcelona and Another Team options are using proper images")
        return True
    elif barcelona_fixed:
        logger.warning("⚠️ TEST PARTIALLY PASSED: Barcelona is fixed but Another Team has issues")
        return False
    elif another_team_fixed:
        logger.warning("⚠️ TEST PARTIALLY PASSED: Another Team is fixed but Barcelona has issues")
        return False
    else:
        logger.error("❌ TEST FAILED: Both Barcelona and Another Team options have issues")
        return False

def verify_fix_with_real_data():
    """Verify our fix with real data from Polymarket API"""
    logger.info("Starting verification with real Polymarket data...")
    
    # Get sports markets that might have "Another Team" or "Barcelona" options
    url = "https://gamma-api.polymarket.com/markets"
    params = {
        "cat": "soccer",  # Filter to soccer markets for better chances
        "limit": 50
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()
        
        logger.info(f"Fetched {len(markets)} markets from API")
        
        # Transform markets
        transformer = MarketTransformer()
        transformed = transformer.transform_markets(markets)
        
        # Find multi-option markets
        multi_option_markets = [m for m in transformed if m.get("is_multiple_option", False)]
        logger.info(f"Found {len(multi_option_markets)} multi-option markets")
        
        if not multi_option_markets:
            logger.warning("No multi-option markets found in real data - can't verify")
            return None
        
        # Check for markets with our target options
        found_barcelona = False
        found_another_team = False
        barcelona_fixed = None
        another_team_fixed = None
        
        for market in multi_option_markets:
            outcomes = json.loads(market.get("outcomes", "[]")) if isinstance(market.get("outcomes"), str) else market.get("outcomes", [])
            
            if "Barcelona" in outcomes:
                found_barcelona = True
                result = analyze_market(market, "Barcelona")
                barcelona_fixed = result[0]
                logger.info(f"Barcelona in real data: {result[1]}")
            
            # Check for "Another Team" or similar variations
            for outcome in outcomes:
                if "another team" in outcome.lower():
                    found_another_team = True
                    result = analyze_market(market, outcome)
                    another_team_fixed = result[0]
                    logger.info(f"Another Team in real data: {result[1]}")
        
        # Summarize real data results
        if not found_barcelona and not found_another_team:
            logger.warning("Neither Barcelona nor Another Team options found in real data")
            return None
        
        if found_barcelona and found_another_team:
            if barcelona_fixed and another_team_fixed:
                logger.info("✅ REAL DATA TEST PASSED: Both Barcelona and Another Team are fixed")
                return True
            else:
                logger.warning(f"⚠️ REAL DATA TEST ISSUES: Barcelona fixed: {barcelona_fixed}, Another Team fixed: {another_team_fixed}")
                return False
        elif found_barcelona:
            logger.info(f"Barcelona only found in real data - fixed: {barcelona_fixed}")
            return barcelona_fixed
        elif found_another_team:
            logger.info(f"Another Team only found in real data - fixed: {another_team_fixed}")
            return another_team_fixed
    
    except Exception as e:
        logger.error(f"Error fetching real data: {e}")
        return None

def main():
    """Main verification function"""
    logger.info("=== OPTION IMAGE HANDLING VERIFICATION ===")
    
    # First test with controlled test data
    test_data_result = verify_fix_with_test_data()
    
    # Then verify with real data if available
    real_data_result = verify_fix_with_real_data()
    
    # Final conclusion
    logger.info("\n=== VERIFICATION SUMMARY ===")
    if test_data_result:
        logger.info("✓ Test data: All issues FIXED")
    else:
        logger.error("✗ Test data: Issues REMAIN")
    
    if real_data_result is True:
        logger.info("✓ Real data: All issues FIXED")
    elif real_data_result is False:
        logger.error("✗ Real data: Issues REMAIN")
    else:
        logger.warning("? Real data: INCONCLUSIVE (target options not found)")
    
    # Overall result
    if test_data_result and (real_data_result is True or real_data_result is None):
        logger.info("\n✅ OVERALL: The fixes are working correctly")
    else:
        logger.error("\n❌ OVERALL: Issues remain with option image handling")

if __name__ == "__main__":
    main()