"""
Test script to verify the fix for Champions League options with Barcelona.
"""
import json
import logging
import os
import sys
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
sys.path.append('.')
from utils.market_transformer import MarketTransformer
from filter_active_markets import filter_active_markets

def create_sample_champions_league_markets():
    """Create sample Champions League markets for testing"""
    # Create a sample Champions League event
    event_id = "cl_event_2025"
    event_data = {
        "id": event_id,
        "title": "Champions League Winner 2025",
        "image": "https://example.com/champions-league-banner.png",
        "icon": "https://example.com/champions-league-icon.png"
    }
    
    # Create sample markets
    markets = [
        {
            "id": "real-madrid-cl",
            "question": "Will Real Madrid win the Champions League?",
            "conditionId": "real-madrid-condition",
            "image": "https://example.com/real-madrid.png",
            "icon": "https://example.com/real-madrid-icon.png",
            "events": [event_data],
            "outcomes": [{"name": "Yes"}, {"name": "No"}]
        },
        {
            "id": "barcelona-cl",
            "question": "Will Barcelona win the Champions League?",
            "conditionId": "barcelona-condition",
            "image": "https://example.com/barcelona.png",
            "icon": "https://example.com/barcelona-icon.png", 
            "events": [event_data],
            "outcomes": [{"name": "Yes"}, {"name": "No"}]
        },
        {
            "id": "bayern-cl",
            "question": "Will Bayern Munich win the Champions League?",
            "conditionId": "bayern-condition",
            "image": "https://example.com/bayern.png",
            "icon": "https://example.com/bayern-icon.png",
            "events": [event_data],
            "outcomes": [{"name": "Yes"}, {"name": "No"}]
        },
        {
            "id": "another-team-cl",
            "question": "Will Another Team win the Champions League?",
            "conditionId": "another-team-condition",
            "image": "https://example.com/champions-league-banner.png",  # Uses event image
            "icon": "https://example.com/champions-league-icon.png",
            "events": [event_data],
            "outcomes": [{"name": "Yes"}, {"name": "No"}]
        }
    ]
    
    logger.info(f"Created {len(markets)} sample Champions League markets")
    return markets

def analyze_transformation_results(transformed_markets):
    """Analyze the results of market transformation"""
    logger.info(f"Transformed into {len(transformed_markets)} markets")
    
    # Look for multi-option markets
    multi_option_markets = [m for m in transformed_markets if m.get("is_multiple_option")]
    logger.info(f"Found {len(multi_option_markets)} multi-option markets")
    
    if not multi_option_markets:
        logger.warning("No multi-option markets found")
        return False
    
    success = True
    
    # Check each multi-option market
    for market in multi_option_markets:
        logger.info(f"\nAnalyzing multi-option market: {market.get('question')}")
        
        # Get event image for comparison
        event_image = market.get("event_image")
        
        if event_image:
            logger.info(f"Event image: {event_image}")
        else:
            logger.info("No event image found")
        
        # Get options and their images
        try:
            options = json.loads(market.get("outcomes", "[]"))
            option_images = json.loads(market.get("option_images", "{}"))
        except json.JSONDecodeError:
            logger.error("Failed to parse options or option images")
            continue
        
        # Generic options to check
        generic_options = ["barcelona", "another team", "other team", "the field"]
        
        # Check each option
        for option in options:
            image = option_images.get(option)
            
            is_generic = any(generic_term in option.lower() for generic_term in generic_options)
            
            if is_generic:
                logger.info(f"CHECK: GENERIC option '{option}': {'using unique image' if image else 'NO IMAGE'}")
                logger.info(f"  Image: {image}")
                
                # Verify it's not using the event image
                if image == event_image:
                    logger.error(f"FAIL: Generic option '{option}' is using event image")
                    success = False
                else:
                    logger.info(f"FIXED: Generic option '{option}' is correctly using non-event image")
            else:
                logger.info(f"CHECK: Standard option '{option}': {'using unique image' if image else 'NO IMAGE'}")
                logger.info(f"  Image: {image}")
    
    return success

def main():
    """Main function for testing Champions League option fix"""
    logger.info("=== CHAMPIONS LEAGUE OPTION IMAGE FIX TEST ===")
    
    # Create sample markets
    markets = create_sample_champions_league_markets()
    
    # Transform markets using the market transformer
    transformer = MarketTransformer()
    transformed_markets = transformer.transform(markets)
    
    # Analyze the results
    success = analyze_transformation_results(transformed_markets)
    
    if success:
        logger.info("=== TEST PASSED: Generic options correctly use non-event images ===")
    else:
        logger.error("=== TEST FAILED: Some generic options using event images ===")
    
    return success

if __name__ == "__main__":
    main()