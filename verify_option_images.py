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
from typing import Dict, List, Any, Optional, Tuple

from utils.market_transformer import MarketTransformer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_test_data() -> List[Dict[str, Any]]:
    """Create test data that simulates the problematic scenarios"""
    
    # Common event data
    event_banner = "https://example.com/event-banner.png"
    
    # Champions League test
    cl_event_id = "test-champions-league-event"
    cl_markets = []
    
    # Teams with proper images
    cl_teams = [
        {"name": "Real Madrid", "image": "https://example.com/real-madrid.png"},
        {"name": "Manchester City", "image": "https://example.com/manchester-city.png"},
        {"name": "Bayern Munich", "image": "https://example.com/bayern.png"},
    ]
    
    # Add team markets
    for team in cl_teams:
        cl_markets.append({
            "id": f"will-{team['name'].lower().replace(' ', '-')}-win-cl",
            "question": f"Will {team['name']} win the Champions League?",
            "image": team["image"],
            "icon": team["image"],
            "active": True,
            "closed": False,
            "archived": False,
            "liquidity": 10000,
            "category": "sports",
            "subcategory": "soccer",
            "conditionId": f"{team['name'].lower().replace(' ', '-')}-cl-condition",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": cl_event_id,
            "events": [
                {
                    "id": cl_event_id,
                    "title": "Champions League Winner",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        })
    
    # Add Barcelona with event image (the problematic case)
    cl_markets.append({
        "id": "will-barcelona-win-cl",
        "question": "Will Barcelona win the Champions League?",
        "image": event_banner,  # Using event banner - this is the issue
        "icon": event_banner,
        "active": True,
        "closed": False,
        "archived": False,
        "liquidity": 10000,
        "category": "sports",
        "subcategory": "soccer",
        "conditionId": "barcelona-cl-condition",
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
        "eventId": cl_event_id,
        "events": [
            {
                "id": cl_event_id,
                "title": "Champions League Winner",
                "image": event_banner,
                "icon": event_banner,
                "category": "soccer"
            }
        ]
    })
    
    # La Liga test with "Another Team" issue
    liga_event_id = "test-la-liga-event"
    liga_markets = []
    
    # Teams with proper images
    liga_teams = [
        {"name": "Real Madrid", "image": "https://example.com/real-madrid.png"},
        {"name": "Barcelona", "image": "https://example.com/barcelona.png"},
        {"name": "Atletico Madrid", "image": "https://example.com/atletico.png"},
    ]
    
    # Add team markets
    for team in liga_teams:
        liga_markets.append({
            "id": f"will-{team['name'].lower().replace(' ', '-')}-win-liga",
            "question": f"Will {team['name']} win La Liga?",
            "image": team["image"],
            "icon": team["image"],
            "active": True,
            "closed": False,
            "archived": False,
            "liquidity": 10000,
            "category": "sports",
            "subcategory": "soccer",
            "conditionId": f"{team['name'].lower().replace(' ', '-')}-liga-condition",
            "outcomes": [{"value": "Yes"}, {"value": "No"}],
            "eventId": liga_event_id,
            "events": [
                {
                    "id": liga_event_id,
                    "title": "La Liga Winner",
                    "image": event_banner,
                    "icon": event_banner,
                    "category": "soccer"
                }
            ]
        })
    
    # Add "Another Team" with event image (the problematic case)
    liga_markets.append({
        "id": "will-another-team-win-liga",
        "question": "Will Another Team win La Liga?",
        "image": event_banner,  # Using event banner - this is the issue
        "icon": event_banner,
        "active": True,
        "closed": False,
        "archived": False,
        "liquidity": 10000,
        "category": "sports",
        "subcategory": "soccer",
        "conditionId": "another-team-liga-condition",
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
        "eventId": liga_event_id,
        "events": [
            {
                "id": liga_event_id,
                "title": "La Liga Winner",
                "image": event_banner,
                "icon": event_banner,
                "category": "soccer"
            }
        ]
    })
    
    # Combine all test markets
    return cl_markets + liga_markets

def analyze_market(market: Dict[str, Any], target_option: str) -> Tuple[bool, str]:
    """
    Analyze a market to see if the target option is using a team image instead of event banner.
    
    Args:
        market: Transformed market data
        target_option: The specific option to check (e.g., "Barcelona" or "Another Team")
        
    Returns:
        Tuple of (is_fixed, details)
    """
    if not market.get("is_multiple_option", False):
        return False, "Not a multi-option market"
    
    # Print all keys for debugging
    logger.info(f"Market keys: {list(market.keys())}")
    
    # Get outcomes as a list (handle both string and list formats)
    outcomes_raw = market.get("outcomes", "[]")
    outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
    logger.info(f"Outcomes: {outcomes}")
    
    # Get option images (handle both string and dict formats)
    option_images_raw = market.get("option_images", "{}")
    option_images = json.loads(option_images_raw) if isinstance(option_images_raw, str) else option_images_raw
    logger.info(f"Option images: {option_images}")
    
    # Get event image
    event_image = market.get("event_image", "")
    logger.info(f"Event image: {event_image}")
    
    # Print debug info about the target option
    logger.info(f"Checking target option: '{target_option}'")
    
    # Check if the target option exists
    if target_option not in outcomes:
        logger.info(f"Target option '{target_option}' not found in outcomes")
        return False, f"Target option '{target_option}' not found in outcomes"
    
    # Check if the target option has an image
    if target_option not in option_images:
        logger.info(f"Target option '{target_option}' has no image")
        return False, f"Target option '{target_option}' has no image"
    
    # Check if it's using the event image
    image_url = option_images[target_option]
    logger.info(f"Target option '{target_option}' image URL: {image_url}")
    
    # Check against event image
    using_event_image = (image_url == event_image) if image_url and event_image else False
    logger.info(f"Is using event image? {using_event_image}")
    
    if using_event_image:
        return False, f"Target option '{target_option}' is still using the event image"
    else:
        # Get details about what image it's using instead
        if image_url in [option_images.get(opt) for opt in outcomes if opt != target_option]:
            return True, f"Target option '{target_option}' is using another team's image correctly"
        else:
            return True, f"Target option '{target_option}' is using a unique image (not event image)"

def verify_fix_with_test_data():
    """Verify our fix with controlled test data"""
    logger.info("\n=== VERIFYING FIX WITH TEST DATA ===")
    
    # Create test data
    test_markets = create_test_data()
    logger.info(f"Created {len(test_markets)} test markets")
    
    # Transform markets
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(test_markets)
    logger.info(f"Transformed {len(transformed)} markets")
    
    # Find our multi-option markets
    cl_market = None
    liga_market = None
    
    for market in transformed:
        if market.get("is_multiple_option", False):
            question = market.get("question", "").lower()
            if "champions league" in question:
                cl_market = market
            elif "la liga" in question:
                liga_market = market
    
    # Analysis results
    results = []
    
    # Analyze Champions League market for Barcelona
    if cl_market:
        logger.info("\n* Found Champions League multi-option market:")
        logger.info(f"  Question: {cl_market.get('question')}")
        
        barcelona_fixed, details = analyze_market(cl_market, "Barcelona")
        results.append(("Barcelona in Champions League", barcelona_fixed, details))
    else:
        logger.error("No Champions League multi-option market found")
        results.append(("Barcelona in Champions League", False, "Market not found"))
    
    # Analyze La Liga market for "Another Team"
    if liga_market:
        logger.info("\n* Found La Liga multi-option market:")
        logger.info(f"  Question: {liga_market.get('question')}")
        
        another_team_fixed, details = analyze_market(liga_market, "Another Team")
        results.append(("Another Team in La Liga", another_team_fixed, details))
    else:
        logger.error("No La Liga multi-option market found")
        results.append(("Another Team in La Liga", False, "Market not found"))
    
    # Print summary
    logger.info("\n=== TEST RESULTS ===")
    all_fixed = True
    
    for issue, fixed, details in results:
        status = "✅ FIXED" if fixed else "❌ NOT FIXED"
        logger.info(f"{status} - {issue}: {details}")
        if not fixed:
            all_fixed = False
    
    # Additional debugging for CL market
    if cl_market:
        logger.info("\n=== DETAILED CL MARKET DEBUG ===")
        logger.info(f"Event image: {cl_market.get('event_image')}")
        option_images = json.loads(cl_market.get("option_images", "{}"))
        for option, image in option_images.items():
            logger.info(f"Option '{option}' image: {image}")
            if option == "Barcelona":
                logger.info(f"Barcelona image matches event image: {image == cl_market.get('event_image')}")
    
    # Additional debugging for La Liga market
    if liga_market:
        logger.info("\n=== DETAILED LA LIGA MARKET DEBUG ===")
        logger.info(f"Event image: {liga_market.get('event_image')}")
        option_images = json.loads(liga_market.get("option_images", "{}"))
        for option, image in option_images.items():
            logger.info(f"Option '{option}' image: {image}")
            if "another" in option.lower():
                logger.info(f"Another Team image matches event image: {image == liga_market.get('event_image')}")
    
    if all_fixed:
        logger.info("\n✅ ALL ISSUES FIXED! The image handling for Barcelona and 'Another Team' options is working correctly.")
    else:
        logger.error("\n❌ ISSUES REMAIN! Some problems with image handling still exist.")
    
    return all_fixed

def verify_fix_with_real_data():
    """Verify our fix with real data from Polymarket API"""
    logger.info("\n=== VERIFYING FIX WITH REAL API DATA ===")
    
    # Try to fetch real data from Polymarket API
    real_markets = []
    
    try:
        # Try to get Champions League markets
        url = "https://gamma-api.polymarket.com/markets"
        params = {"limit": 30, "q": "Champions League", "cat": "soccer"}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        cl_markets = response.json()
        logger.info(f"Fetched {len(cl_markets)} Champions League markets from Polymarket API")
        real_markets.extend(cl_markets)
        
        # Try to get La Liga markets
        params = {"limit": 30, "q": "La Liga", "cat": "soccer"}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        liga_markets = response.json()
        logger.info(f"Fetched {len(liga_markets)} La Liga markets from Polymarket API")
        real_markets.extend(liga_markets)
    
    except Exception as e:
        logger.error(f"Failed to fetch real data from Polymarket API: {e}")
        logger.info("Continuing with only test data verification")
        return None
    
    # Transform markets
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(real_markets)
    logger.info(f"Transformed {len(transformed)} real markets")
    
    # Find multi-option markets
    multi_option_markets = [m for m in transformed if m.get("is_multiple_option", False)]
    logger.info(f"Found {len(multi_option_markets)} multi-option markets in real data")
    
    if not multi_option_markets:
        logger.warning("No multi-option markets found in real data, can't verify with real data")
        return None
    
    # Find markets with Barcelona or "Another Team" options
    results = []
    
    for market in multi_option_markets:
        outcomes = json.loads(market.get("outcomes", "[]"))
        question = market.get("question", "")
        
        # Check for Barcelona
        if "Barcelona" in outcomes:
            barcelona_fixed, details = analyze_market(market, "Barcelona")
            results.append((f"Barcelona in '{question}'", barcelona_fixed, details))
        
        # Check for Another Team
        for outcome in outcomes:
            if "another" in outcome.lower() or "other" in outcome.lower():
                another_fixed, details = analyze_market(market, outcome)
                results.append((f"'{outcome}' in '{question}'", another_fixed, details))
    
    # Print summary
    if results:
        logger.info("\n=== REAL DATA RESULTS ===")
        all_fixed = True
        
        for issue, fixed, details in results:
            status = "✅ FIXED" if fixed else "❌ NOT FIXED"
            logger.info(f"{status} - {issue}: {details}")
            if not fixed:
                all_fixed = False
        
        if all_fixed:
            logger.info("\n✅ REAL DATA VERIFICATION PASSED! Images are handled correctly for real Polymarket data.")
        else:
            logger.error("\n❌ REAL DATA VERIFICATION FAILED! Some issues persist with real data.")
        
        return all_fixed
    else:
        logger.warning("No markets with Barcelona or 'Another Team' options found in real data")
        return None

def main():
    """Main verification function"""
    logger.info("Starting verification of 'Another Team' and Barcelona image fix")
    
    # Verify with test data
    test_passed = verify_fix_with_test_data()
    
    # Verify with real data if available
    real_passed = verify_fix_with_real_data()
    
    # Final verdict
    logger.info("\n=== FINAL VERIFICATION RESULTS ===")
    
    if test_passed:
        logger.info("✅ TEST DATA VERIFICATION: PASSED")
    else:
        logger.error("❌ TEST DATA VERIFICATION: FAILED")
    
    if real_passed is not None:
        if real_passed:
            logger.info("✅ REAL DATA VERIFICATION: PASSED")
        else:
            logger.error("❌ REAL DATA VERIFICATION: FAILED")
    else:
        logger.warning("⚠️ REAL DATA VERIFICATION: SKIPPED (no suitable data)")
    
    # Overall conclusion
    if test_passed and (real_passed is None or real_passed):
        logger.info("\n🎉 CONCLUSION: FIX IS WORKING CORRECTLY!")
        logger.info("The issue with 'Another Team' and Barcelona options using event banner images has been fixed.")
    else:
        logger.error("\n❌ CONCLUSION: FIX NEEDS IMPROVEMENT")
        logger.error("Some issues remain with the image handling for 'Another Team' or Barcelona options.")

if __name__ == "__main__":
    main()