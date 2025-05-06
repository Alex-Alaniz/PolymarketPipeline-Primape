"""
Option Image Fixer

This module provides fixes for option images, ensuring each option
has its own unique image URL from the API data.
"""
import json
import logging
from typing import Dict, Any, List, Optional

# Set up logger
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

def apply_image_fixes(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Apply fixes to ensure each option has its proper image
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        List of updated market data dictionaries
    """
    fixed_markets = []
    
    for market in markets:
        fixed_market = fix_specific_market_images(market)
        fixed_markets.append(fixed_market)
        
    return fixed_markets

def fix_specific_market_images(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fix specific known image issues for particular markets
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Updated market data dictionary
    """
    # Handle non-multi-option markets
    if not market_data.get("is_multiple_option"):
        return market_data
        
    market_id = market_data.get("id", "")
    question = market_data.get("question", "")
    
    # Champions League market fix (Barcelona)
    if market_id == "group_12585" or "Champions League Winner" in question:
        logger.info(f"Checking Champions League market for image fixes: {question}")
        
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
    
    # La Liga market fix ("another team")
    if market_id == "group_12672" or "La Liga Winner" in question:
        logger.info(f"Checking La Liga market for image fixes: {question}")
        
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

def verify_option_images(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify that all options have unique images and log the results
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        The market data, unchanged
    """
    if not market_data.get("is_multiple_option"):
        return market_data
        
    market_id = market_data.get("id", "")
    question = market_data.get("question", "")
    
    # Load option_images
    option_images = load_option_images(market_data)
    options = json.loads(market_data.get("outcomes", "[]"))
    
    # Log all option images
    logger.info(f"Verifying option images for market: {question} (ID: {market_id})")
    logger.info(f"Total options: {len(options)}")
    logger.info(f"Total option images: {len(option_images)}")
    
    # Verify each option has a unique image
    image_to_options = {}
    for option in options:
        image = option_images.get(option)
        if image:
            if image not in image_to_options:
                image_to_options[image] = []
            image_to_options[image].append(option)
    
    # Log any duplicated images
    for image, duplicated_options in image_to_options.items():
        if len(duplicated_options) > 1:
            logger.warning(f"Image {image} is used by multiple options: {duplicated_options}")
    
    return market_data