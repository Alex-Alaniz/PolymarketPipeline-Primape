#!/usr/bin/env python3
"""
Test script to verify and fix specific option images for Champions League and La Liga markets
"""
import json
import logging
from typing import Dict, Any, List

from utils.market_transformer import MarketTransformer

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load sample markets
with open("sample_markets.json", "r") as f:
    sample_markets = json.load(f)

# Create sample for Champions League and La Liga
cl_sample = []
la_liga_sample = []

for market in sample_markets:
    for event in market.get("events", []):
        event_id = event.get("id")
        if event_id == "12585":  # Champions League
            cl_sample.append(market)
        elif event_id == "12672":  # La Liga
            la_liga_sample.append(market)

def get_option_images(transformed_market: Dict[str, Any]) -> Dict[str, str]:
    """Extract and return option images from a transformed market"""
    option_images_json = transformed_market.get("option_images", "{}")
    return json.loads(option_images_json)

def analyze_cl_market(transformed_markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find and analyze the Champions League market"""
    for market in transformed_markets:
        market_id = market.get("id")
        question = market.get("question")
        
        if market_id == "group_12585" or "Champions League Winner" in question:
            logger.info("Found Champions League market")
            
            # Check if Barcelona has its own unique image
            option_images = get_option_images(market)
            outcomes = json.loads(market.get("outcomes", "[]"))
            
            logger.info("Current option images:")
            for option, image in option_images.items():
                logger.info(f"  {option}: {image}")
                
            # Check the Barcelona image
            if "Barcelona" in outcomes:
                barcelona_image = option_images.get("Barcelona")
                logger.info(f"Barcelona image: {barcelona_image}")
                
                # Check if it's unique (not using Arsenal's image)
                arsenal_image = None
                for opt, img in option_images.items():
                    if "Arsenal" in opt:
                        arsenal_image = img
                        break
                
                if barcelona_image == arsenal_image:
                    logger.warning("Barcelona is using Arsenal's image!")
                else:
                    logger.info("Barcelona has its unique image")
                    
            return market
    
    return None

def analyze_la_liga_market(transformed_markets: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Find and analyze the La Liga market"""
    for market in transformed_markets:
        market_id = market.get("id")
        question = market.get("question")
        
        if market_id == "group_12672" or "La Liga Winner" in question:
            logger.info("Found La Liga market")
            
            # Check if "another team" has its own unique image
            option_images = get_option_images(market)
            outcomes = json.loads(market.get("outcomes", "[]"))
            
            logger.info("Current option images:")
            for option, image in option_images.items():
                logger.info(f"  {option}: {image}")
                
            # Check the "another team" image
            if "another team" in outcomes:
                another_team_image = option_images.get("another team")
                logger.info(f"Another team image: {another_team_image}")
                
                # Check if it's unique (not using Real Madrid's image)
                real_madrid_image = None
                for opt, img in option_images.items():
                    if "Real Madrid" in opt:
                        real_madrid_image = img
                        break
                
                if another_team_image == real_madrid_image:
                    logger.warning("'another team' is using Real Madrid's image!")
                else:
                    logger.info("'another team' has its unique image")
                    
            return market
    
    return None

def set_original_market_id_attr(transformer: MarketTransformer):
    """Make sure MarketTransformer has the original_markets attribute"""
    if not hasattr(transformer, "original_markets"):
        transformer.original_markets = []

def main():
    """Main function to test and fix option images"""
    # Create combined sample
    combined_sample = cl_sample + la_liga_sample
    logger.info(f"Testing with {len(combined_sample)} markets (CL: {len(cl_sample)}, La Liga: {len(la_liga_sample)})")
    
    # Create market transformer
    transformer = MarketTransformer()
    set_original_market_id_attr(transformer)
    transformer.original_markets = combined_sample
    
    logger.info("\n=== Before transformation ===")
    logger.info(f"Original markets count: {len(combined_sample)}")
    
    # Transform markets
    transformed_markets = transformer.transform_markets(combined_sample)
    logger.info(f"Transformed to {len(transformed_markets)} markets")
    
    # Analyze the specific markets
    logger.info("\n=== After transformation ===")
    cl_market = analyze_cl_market(transformed_markets)
    la_liga_market = analyze_la_liga_market(transformed_markets)
    
    # Check if Barcelona and "another team" have their proper images
    if cl_market and "Barcelona" in json.loads(cl_market.get("outcomes", "[]")):
        option_images = get_option_images(cl_market)
        barcelona_image = option_images.get("Barcelona")
        
        # Check for Barcelona in the original markets
        barcelona_proper_image = None
        for market in combined_sample:
            q = market.get("question", "").lower()
            if "barcelona" in q and "champions league" in q and market.get("image"):
                barcelona_proper_image = market.get("image")
                break
                
        if barcelona_proper_image:
            logger.info(f"\nBarcelona should use this image from API: {barcelona_proper_image}")
            if barcelona_image != barcelona_proper_image:
                logger.warning(f"Barcelona is using incorrect image: {barcelona_image}")
            else:
                logger.info("Barcelona is correctly using its API image")
    
    if la_liga_market and any("another team" in o.lower() for o in json.loads(la_liga_market.get("outcomes", "[]"))):
        option_images = get_option_images(la_liga_market)
        for opt in json.loads(la_liga_market.get("outcomes", "[]")):
            if "another team" in opt.lower():
                another_team_image = option_images.get(opt)
                
                # Check for "another team" in the original markets
                another_team_proper_image = None
                for market in combined_sample:
                    q = market.get("question", "").lower()
                    if "another team" in q and "la liga" in q and market.get("image"):
                        another_team_proper_image = market.get("image")
                        break
                        
                if another_team_proper_image:
                    logger.info(f"\n'another team' should use this image from API: {another_team_proper_image}")
                    if another_team_image != another_team_proper_image:
                        logger.warning(f"'another team' is using incorrect image: {another_team_image}")
                    else:
                        logger.info("'another team' is correctly using its API image")
                break

if __name__ == "__main__":
    main()