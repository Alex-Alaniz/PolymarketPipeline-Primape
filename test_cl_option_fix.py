"""
Script to test the fix for generic options (Barcelona, Another Team) in sports markets.
"""
import json
import logging
import os
import sys
from typing import Dict, Any, List, Tuple

from utils.market_transformer import MarketTransformer
import filter_active_markets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fetch_and_transform_markets():
    """
    Fetch markets from Polymarket API, filter, and transform them.
    """
    # Fetch markets from Polymarket API
    logger.info("Fetching markets from Polymarket API...")
    markets = filter_active_markets.fetch_markets()
    
    # Filter active markets
    logger.info(f"Filtering {len(markets)} markets...")
    filtered_markets = filter_active_markets.filter_active_markets(markets)
    logger.info(f"Filtered to {len(filtered_markets)} active markets")
    
    # Transform markets
    transformer = MarketTransformer()
    # Call transform_markets on the instance, not the class
    transformed_markets = filter_active_markets.transform_markets(filtered_markets)
    logger.info(f"Transformed to {len(transformed_markets)} markets")
    
    # Find specific markets we're interested in
    cl_market = None
    laliga_market = None
    epl_market = None
    
    for market in transformed_markets:
        market_id = market.get("id")
        question = market.get("question")
        
        if market_id == "group_12585" or "Champions League Winner" in question:
            cl_market = market
            logger.info(f"Found Champions League market: {question}")
        
        if market_id == "group_12672" or "La Liga Winner" in question:
            laliga_market = market
            logger.info(f"Found La Liga market: {question}")
            
        if "English Premier League Top Scorer" in question:
            epl_market = market
            logger.info(f"Found EPL Top Scorer market: {question}")
    
    return cl_market, laliga_market, epl_market

def analyze_option_images(market: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    """
    Analyze the option images in a market to see if we have unique images for generic options.
    """
    if not market:
        return False, {}
    
    question = market.get("question", "Unknown")
    outcomes_str = market.get("outcomes", "[]")
    option_images_str = market.get("option_images", "{}")
    event_image = market.get("event_image")
    
    try:
        outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
        option_images = json.loads(option_images_str) if isinstance(option_images_str, str) else option_images_str
    except json.JSONDecodeError:
        logger.error(f"Error parsing JSON for {question}")
        return False, {}
    
    # Count how many times each image is used
    image_usage = {}
    for option, image in option_images.items():
        image_usage[image] = image_usage.get(image, 0) + 1
    
    # Check if we have generic options
    generic_keywords = ["another team", "other team", "field", "barcelona", "other"]
    generic_options = []
    
    for option in outcomes:
        if any(keyword in option.lower() for keyword in generic_keywords):
            generic_options.append(option)
    
    # Check if generic options have unique images
    unique_images = True
    results = {
        "question": question,
        "outcomes": outcomes,
        "option_images": option_images,
        "generic_options": generic_options,
        "image_usage": image_usage,
        "event_image": event_image,
        "using_event_image": []
    }
    
    # Check if any option is using the event image
    for option, image in option_images.items():
        if image == event_image:
            results["using_event_image"].append(option)
    
    # Check if any generic option is using a non-unique image
    for option in generic_options:
        if option in option_images:
            image = option_images[option]
            if image_usage[image] > 1:
                logger.warning(f"Generic option '{option}' using non-unique image: {image} (used {image_usage[image]} times)")
                unique_images = False
    
    return unique_images, results

def fix_market_manually(market: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply manual fix to a market's option images.
    """
    if not market:
        return {}
    
    question = market.get("question", "Unknown")
    outcomes_str = market.get("outcomes", "[]")
    option_images_str = market.get("option_images", "{}")
    
    try:
        outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
        option_images = json.loads(option_images_str) if isinstance(option_images_str, str) else option_images_str
    except json.JSONDecodeError:
        logger.error(f"Error parsing JSON for {question}")
        return market
    
    # Get available team images
    team_images = []
    for option, image in option_images.items():
        # Only add unique team-specific images
        if image not in team_images and "team" not in option.lower() and "barcelona" not in option.lower():
            team_images.append(image)
    
    # Assign unique images to generic options
    generic_keywords = ["another team", "other team", "field", "barcelona", "other"]
    
    if "Champions League Winner" in question:
        # For Champions League, give Barcelona a unique image
        for i, option in enumerate(outcomes):
            if "barcelona" in option.lower() and i < len(team_images):
                # Use the second team's image for Barcelona (not Arsenal's)
                # This ensures Barcelona uses a different image than the one used for the first option
                option_found = False
                # Look specifically for Inter Milan's image since we know it exists
                for opt, img in option_images.items():
                    if "inter milan" in opt.lower():
                        option_images[option] = img
                        logger.info(f"Manually assigned Inter Milan's image to Barcelona: {img}")
                        option_found = True
                        break
                        
                # Fallback to Paris Saint-Germain if Inter Milan not found
                if not option_found:
                    for opt, img in option_images.items():
                        if "paris" in opt.lower():
                            option_images[option] = img
                            logger.info(f"Manually assigned PSG's image to Barcelona: {img}")
                            option_found = True
                            break
                            
                # Last resort, use any team image that's not Arsenal's
                if not option_found and len(team_images) > 1:
                    option_images[option] = team_images[1]
                    logger.info(f"Manually assigned image to Barcelona as fallback: {team_images[1]}")
    
    elif "La Liga Winner" in question:
        # For La Liga, give "another team" a unique image
        for i, option in enumerate(outcomes):
            if "another team" in option.lower() and i < len(team_images):
                # Use Barcelona's image for "another team" if it exists
                # This ensures "another team" uses a different image than Real Madrid
                barcelona_image = None
                for opt, img in option_images.items():
                    if "barcelona" in opt.lower():
                        barcelona_image = img
                
                if barcelona_image:
                    option_images[option] = barcelona_image
                    logger.info(f"Manually assigned Barcelona's image to 'another team': {barcelona_image}")
    
    # Update the market with fixed option images
    fixed_market = market.copy()
    fixed_market["option_images"] = json.dumps(option_images)
    
    return fixed_market

def main():
    """Main function to test the fix for Champions League Barcelona option."""
    # Fetch and transform markets
    cl_market, laliga_market, epl_market = fetch_and_transform_markets()
    
    if not cl_market or not laliga_market:
        logger.error("Failed to find the necessary markets")
        return
    
    # Analyze Champions League market
    logger.info("\n=== Champions League Market Analysis ===")
    unique_images, cl_results = analyze_option_images(cl_market)
    
    if not unique_images:
        logger.warning("Champions League market has generic options without unique images")
        for option in cl_results.get("generic_options", []):
            image = cl_results.get("option_images", {}).get(option)
            if image:
                usage_count = cl_results.get("image_usage", {}).get(image, 0)
                logger.info(f"  - {option}: {image} (used {usage_count} times)")
    else:
        logger.info("Champions League market has unique images for all generic options")
    
    # Analyze La Liga market
    logger.info("\n=== La Liga Market Analysis ===")
    unique_images, laliga_results = analyze_option_images(laliga_market)
    
    if not unique_images:
        logger.warning("La Liga market has generic options without unique images")
        for option in laliga_results.get("generic_options", []):
            image = laliga_results.get("option_images", {}).get(option)
            if image:
                usage_count = laliga_results.get("image_usage", {}).get(image, 0)
                logger.info(f"  - {option}: {image} (used {usage_count} times)")
    else:
        logger.info("La Liga market has unique images for all generic options")
    
    # Manually fix the markets
    logger.info("\n=== Applying Manual Fix ===")
    fixed_cl_market = fix_market_manually(cl_market)
    fixed_laliga_market = fix_market_manually(laliga_market)
    
    # Analyze fixed markets
    logger.info("\n=== Champions League Market After Fix ===")
    unique_images, fixed_cl_results = analyze_option_images(fixed_cl_market)
    
    if not unique_images:
        logger.warning("Champions League market still has generic options without unique images after fix")
        for option in fixed_cl_results.get("generic_options", []):
            image = fixed_cl_results.get("option_images", {}).get(option)
            if image:
                usage_count = fixed_cl_results.get("image_usage", {}).get(image, 0)
                logger.info(f"  - {option}: {image} (used {usage_count} times)")
    else:
        logger.info("Champions League market now has unique images for all generic options")
    
    logger.info("\n=== La Liga Market After Fix ===")
    unique_images, fixed_laliga_results = analyze_option_images(fixed_laliga_market)
    
    if not unique_images:
        logger.warning("La Liga market still has generic options without unique images after fix")
        for option in fixed_laliga_results.get("generic_options", []):
            image = fixed_laliga_results.get("option_images", {}).get(option)
            if image:
                usage_count = fixed_laliga_results.get("image_usage", {}).get(image, 0)
                logger.info(f"  - {option}: {image} (used {usage_count} times)")
    else:
        logger.info("La Liga market now has unique images for all generic options")

if __name__ == "__main__":
    main()