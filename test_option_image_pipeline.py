#!/usr/bin/env python3
"""
Test the complete pipeline including option image fixes

This script tests the entire market transformation pipeline with our new
option image fixes integrated.
"""
import logging
import json
from typing import Dict, Any, List, Optional

from pipeline import PolymarketPipeline
from utils.option_image_fixer import apply_image_fixes, verify_option_images

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_pipeline")

def load_sample_markets() -> List[Dict[str, Any]]:
    """
    Load sample markets from the JSON file
    
    Returns:
        List of market data dictionaries
    """
    try:
        with open("sample_markets.json", "r") as f:
            markets = json.load(f)
        logger.info(f"Loaded {len(markets)} sample markets")
        return markets
    except Exception as e:
        logger.error(f"Error loading sample markets: {str(e)}")
        return []

def create_cl_and_laliga_samples() -> List[Dict[str, Any]]:
    """
    Create sample markets specifically for testing Champions League and La Liga
    
    Returns:
        List of sample market data dictionaries
    """
    # Define event data
    cl_event = {
        "id": "12585",
        "title": "Champions League Winner",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/champions-league-winner-2025-F-QYbKsrHt_E.jpg",
    }
    
    la_liga_event = {
        "id": "12672",
        "title": "La Liga Winner",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/la-liga-winner-0Gd3D1MaSklO.png",
    }
    
    # Create sample markets
    markets = []
    
    # Champions League markets
    markets.append({
        "id": "cl_arsenal",
        "question": "Will Arsenal win the UEFA Champions League?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-arsenal-win-the-uefa-champions-league-uNdX5G_OD3RZ.png",
        "events": [cl_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    markets.append({
        "id": "cl_inter",
        "question": "Will Inter Milan win the UEFA Champions League?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-inter-milan-win-the-uefa-champions-league-qLXmECEH1IMR.png",
        "events": [cl_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    markets.append({
        "id": "cl_psg",
        "question": "Will Paris Saint-Germain win the UEFA Champions League?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-paris-saint-germain-win-the-uefa-champions-league-NxlXl1qZffuf.png",
        "events": [cl_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    markets.append({
        "id": "cl_barcelona",
        "question": "Will Barcelona win the UEFA Champions League?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-the-uefa-champions-league-VeGFtY7rP2Qz.png",
        "events": [cl_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    # La Liga markets
    markets.append({
        "id": "laliga_real",
        "question": "Will Real Madrid win La Liga?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-real-madrid-win-la-liga-l82oJ7YPGB14.png",
        "events": [la_liga_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    markets.append({
        "id": "laliga_barcelona",
        "question": "Will Barcelona win La Liga?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-la-liga-vCC-C0S5sp4O.png",
        "events": [la_liga_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    markets.append({
        "id": "laliga_anotherteam",
        "question": "Will another team win La Liga?",
        "image": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-another-team-win-la-liga-zX8Vh6m3LkQp.png",
        "events": [la_liga_event],
        "active": True,
        "closed": False,
        "archived": False,
        "outcomes": [{"value": "Yes"}, {"value": "No"}],
    })
    
    logger.info(f"Created {len(markets)} sample markets for testing")
    return markets

def find_multi_option_market(markets: List[Dict[str, Any]], event_id: str) -> Optional[Dict[str, Any]]:
    """
    Find a multi-option market by event ID
    
    Args:
        markets: List of transformed market data dictionaries
        event_id: Event ID to search for
        
    Returns:
        Market data dictionary or None if not found
    """
    for market in markets:
        if market.get("is_multiple_option") and market.get("id") == f"group_{event_id}":
            return market
    return None

def inspect_option_images(market: Dict[str, Any]) -> None:
    """
    Inspect option images for a multi-option market
    
    Args:
        market: Market data dictionary
    """
    if not market:
        logger.error("No market provided")
        return
        
    question = market.get("question", "Unknown")
    logger.info(f"Inspecting option images for market: {question}")
    
    # Load options and images
    options = json.loads(market.get("outcomes", "[]"))
    option_images = json.loads(market.get("option_images", "{}"))
    
    logger.info(f"Options ({len(options)}): {options}")
    
    # Verify each option has an image
    for option in options:
        image = option_images.get(option)
        if image:
            logger.info(f"Option '{option}' has image: {image}")
        else:
            logger.error(f"Option '{option}' is missing an image")
    
    # Check for duplicate images
    used_images = {}
    for option, image in option_images.items():
        if image in used_images:
            logger.warning(f"Image {image} is used by multiple options: {used_images[image]} and {option}")
            if "Barcelona" in option or "Barcelona" in used_images.get(image, ""):
                logger.error("Barcelona is sharing an image with another option!")
            elif "another team" in option.lower() or "another team" in used_images.get(image, "").lower():
                logger.error("'another team' is sharing an image with another option!")
        else:
            used_images[image] = option

def test_pipeline():
    """
    Test the pipeline with our sample markets
    """
    logger.info("Testing pipeline with sample markets")
    
    # Create sample markets
    sample_markets = create_cl_and_laliga_samples()
    
    # Create a pipeline instance (without creating a database record)
    pipeline = PolymarketPipeline()
    
    # Set up a mock method to fetch and filter markets
    original_fetch_method = pipeline.fetch_and_filter_markets
    
    # Replace with our mock method
    def mock_fetch_and_filter_markets():
        logger.info("Using mock markets instead of fetching from API")
        return sample_markets
    
    # Monkey patch the method
    pipeline.fetch_and_filter_markets = mock_fetch_and_filter_markets
    
    # Run just the transformation part of the pipeline
    markets = pipeline.fetch_and_filter_markets()
    
    # Now manually apply our transformer
    from utils.market_transformer import MarketTransformer
    transformer = MarketTransformer()
    transformed_markets = transformer.transform_markets(markets)
    
    # Log transformation results
    multi_option_count = sum(1 for m in transformed_markets if m.get('is_multiple_option', False))
    logger.info(f"Created {multi_option_count} multi-option markets")
    
    # Check if our Champions League and La Liga markets were transformed correctly
    cl_market = find_multi_option_market(transformed_markets, "12585")
    la_liga_market = find_multi_option_market(transformed_markets, "12672")
    
    # Inspect option images before fix
    logger.info("\n=== Option images before fix ===")
    if cl_market:
        logger.info("Champions League market:")
        inspect_option_images(cl_market)
    else:
        logger.error("Champions League market not found")
        
    if la_liga_market:
        logger.info("\nLa Liga market:")
        inspect_option_images(la_liga_market)
    else:
        logger.error("La Liga market not found")
    
    # Apply our fix
    logger.info("\n=== Applying option image fix ===")
    fixed_markets = apply_image_fixes(transformed_markets)
    
    # Get the fixed markets
    fixed_cl_market = find_multi_option_market(fixed_markets, "12585")
    fixed_la_liga_market = find_multi_option_market(fixed_markets, "12672")
    
    # Inspect option images after fix
    logger.info("\n=== Option images after fix ===")
    if fixed_cl_market:
        logger.info("Champions League market after fix:")
        inspect_option_images(fixed_cl_market)
    else:
        logger.error("Fixed Champions League market not found")
        
    if fixed_la_liga_market:
        logger.info("\nLa Liga market after fix:")
        inspect_option_images(fixed_la_liga_market)
    else:
        logger.error("Fixed La Liga market not found")

def main():
    """
    Main function to run the test
    """
    # Import Flask app to get application context
    from main import app
    
    # Use application context for database operations
    with app.app_context():
        test_pipeline()

if __name__ == "__main__":
    main()