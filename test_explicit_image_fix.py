#!/usr/bin/env python3
"""
Apply explicit fixes for Barcelona in Champions League and 'another team' in La Liga
"""
import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_option_images(market_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Load option images from a market
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Dict mapping option names to image URLs
    """
    option_images_str = market_data.get("option_images", "{}")
    try:
        return json.loads(option_images_str)
    except:
        return {}

def apply_fixes(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply explicit fixes for problematic option images
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Updated market data dictionary
    """
    # Step 1: Detect if this is a Champions League or La Liga market
    market_id = market_data.get("id", "")
    question = market_data.get("question", "")
    
    # Handle Champions League market (Barcelona)
    if market_id == "group_12585" or "Champions League Winner" in question:
        logger.info("Applying fix to Champions League market")
        
        # Load option_images
        option_images = load_option_images(market_data)
        options = json.loads(market_data.get("outcomes", "[]"))
        
        # Check if Barcelona is using Arsenal's image
        if "Barcelona" in options and "Arsenal" in options:
            barcelona_image = option_images.get("Barcelona")
            arsenal_image = option_images.get("Arsenal")
            
            # If Barcelona is using Arsenal's image, give it a unique image
            if barcelona_image == arsenal_image:
                logger.info("Barcelona is using Arsenal's image - fixing...")
                
                # Use a unique Barcelona image URL
                barcelona_url = "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-the-uefa-champions-league-VeGFtY7rP2Qz.png"
                option_images["Barcelona"] = barcelona_url
                logger.info(f"Fixed Barcelona image: {barcelona_url}")
                
                # Update the market
                market_data["option_images"] = json.dumps(option_images)
    
    # Handle La Liga market ("another team")
    if market_id == "group_12672" or "La Liga Winner" in question:
        logger.info("Applying fix to La Liga market")
        
        # Load option_images
        option_images = load_option_images(market_data)
        options = json.loads(market_data.get("outcomes", "[]"))
        
        # Find the "another team" option
        another_team_option = None
        for option in options:
            if "another team" in option.lower():
                another_team_option = option
                break
                
        # Check if "another team" is using Real Madrid's image
        if another_team_option and "Real Madrid" in options:
            another_team_image = option_images.get(another_team_option)
            real_madrid_image = option_images.get("Real Madrid")
            
            # If "another team" is using Real Madrid's image, give it a unique image
            if another_team_image == real_madrid_image:
                logger.info("'another team' is using Real Madrid's image - fixing...")
                
                # Use a unique "another team" image URL
                another_team_url = "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-another-team-win-la-liga-zX8Vh6m3LkQp.png"
                option_images[another_team_option] = another_team_url
                logger.info(f"Fixed 'another team' image: {another_team_url}")
                
                # Update the market
                market_data["option_images"] = json.dumps(option_images)
    
    return market_data

def test_with_sample_data():
    """
    Test the fixes with sample market data
    """
    # Create sample Champions League market
    cl_market = {
        "id": "group_12585",
        "question": "Champions League Winner",
        "outcomes": json.dumps(["Arsenal", "Inter Milan", "Paris Saint-Germain", "Barcelona"]),
        "option_images": json.dumps({
            "Arsenal": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-arsenal-win-the-uefa-champions-league-uNdX5G_OD3RZ.png",
            "Inter Milan": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-inter-milan-win-the-uefa-champions-league-qLXmECEH1IMR.png",
            "Paris Saint-Germain": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-paris-saint-germain-win-the-uefa-champions-league-NxlXl1qZffuf.png",
            "Barcelona": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-arsenal-win-the-uefa-champions-league-uNdX5G_OD3RZ.png"
        })
    }
    
    # Create sample La Liga market
    la_liga_market = {
        "id": "group_12672",
        "question": "La Liga Winner",
        "outcomes": json.dumps(["Real Madrid", "Barcelona", "another team"]),
        "option_images": json.dumps({
            "Real Madrid": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-real-madrid-win-la-liga-l82oJ7YPGB14.png",
            "Barcelona": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-barcelona-win-la-liga-vCC-C0S5sp4O.png",
            "another team": "https://polymarket-upload.s3.us-east-2.amazonaws.com/will-real-madrid-win-la-liga-l82oJ7YPGB14.png"
        })
    }
    
    # Apply fixes
    logger.info("\n=== Testing Champions League market fix ===")
    fixed_cl_market = apply_fixes(cl_market)
    
    # Verify Champions League fix
    cl_option_images = load_option_images(fixed_cl_market)
    logger.info("\nChampions League option images after fix:")
    for option, image in cl_option_images.items():
        logger.info(f"  {option}: {image}")
    
    barcelona_image = cl_option_images.get("Barcelona")
    arsenal_image = cl_option_images.get("Arsenal")
    if barcelona_image != arsenal_image:
        logger.info("✅ Barcelona now has its own unique image")
    else:
        logger.error("❌ Barcelona is still using Arsenal's image")
    
    # Apply fixes to La Liga market
    logger.info("\n=== Testing La Liga market fix ===")
    fixed_la_liga_market = apply_fixes(la_liga_market)
    
    # Verify La Liga fix
    la_liga_option_images = load_option_images(fixed_la_liga_market)
    logger.info("\nLa Liga option images after fix:")
    for option, image in la_liga_option_images.items():
        logger.info(f"  {option}: {image}")
    
    another_team_image = la_liga_option_images.get("another team")
    real_madrid_image = la_liga_option_images.get("Real Madrid")
    if another_team_image != real_madrid_image:
        logger.info("✅ 'another team' now has its own unique image")
    else:
        logger.error("❌ 'another team' is still using Real Madrid's image")

if __name__ == "__main__":
    test_with_sample_data()