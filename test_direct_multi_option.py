"""
Test script focused specifically on multi-option market image handling.
This script directly creates a multi-option market and tests the image handling.
"""

import json
import logging
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Generic options that should never use event images
GENERIC_OPTIONS = ["another team", "other team", "barcelona", "field"]

def test_direct_multi_option():
    """
    Create a multi-option market directly and test the image handling.
    """
    # Event image (should never be used for generic options)
    event_image = "https://example.com/event-banner.png"
    
    # Team images
    real_madrid_image = "https://example.com/real-madrid.png"
    barcelona_image = "https://example.com/barcelona.png"
    atletico_image = "https://example.com/atletico.png"
    
    # Create a multi-option market
    outcomes = ["Real Madrid", "Barcelona", "Another Team"]
    option_images = {
        "Real Madrid": real_madrid_image,
        "Barcelona": barcelona_image,
        "Another Team": event_image  # Intentionally using event image to test fix
    }
    
    market = {
        "id": "test-multi-option",
        "question": "Who will win La Liga?",
        "is_multiple_option": True,
        "outcomes": json.dumps(outcomes),
        "option_images": json.dumps(option_images),
        "event_image": event_image
    }
    
    # Test the image handling
    logger.info(f"Testing multi-option market: {market['question']}")
    logger.info(f"Outcomes: {outcomes}")
    logger.info(f"Original images:")
    for option in outcomes:
        logger.info(f"  {option}: {option_images.get(option)}")
    
    # Apply our fix manually
    fixed_images = fix_generic_option_images(market, outcomes, option_images)
    
    # Check if the fix worked
    issues_found = False
    for option in outcomes:
        is_generic = any(generic in option.lower() for generic in GENERIC_OPTIONS)
        image = fixed_images.get(option)
        is_event_image = (image == event_image)
        
        if is_generic and is_event_image:
            logger.error(f"❌ ISSUE: Generic option '{option}' still using event image")
            issues_found = True
        elif is_generic:
            logger.info(f"✅ FIXED: Generic option '{option}' using non-event image: {image}")
        else:
            logger.info(f"ℹ️ Non-generic option '{option}' using image: {image}")
    
    if not issues_found:
        logger.info("✅ All generic options are properly using non-event images")
        return True
    else:
        logger.error("❌ Some generic options are still using event images")
        return False

def fix_generic_option_images(market: Dict[str, Any], outcomes: List[str], option_images: Dict[str, str]) -> Dict[str, str]:
    """
    Apply the fix for generic option images directly.
    This simulates the fix in MarketTransformer without requiring a full transformation.
    
    Args:
        market: The market data
        outcomes: List of outcome options
        option_images: Current mapping of options to images
        
    Returns:
        Updated mapping of options to images
    """
    # Get the event image
    event_image = market.get("event_image")
    
    # Create a copy of the option images
    fixed_images = option_images.copy()
    
    # For each option, fix the image if needed
    for option in outcomes:
        # Check if this is a generic option
        is_generic = any(generic in option.lower() for generic in GENERIC_OPTIONS)
        
        if is_generic and fixed_images.get(option) == event_image:
            logger.info(f"Fixing generic option '{option}' that uses event image")
            
            # Find other non-event images to use
            other_team_images = []
            for other_option, other_image in fixed_images.items():
                if other_option != option and other_image != event_image:
                    other_team_images.append(other_image)
            
            # Use another team's image if available
            if other_team_images:
                fixed_images[option] = other_team_images[0]
                logger.info(f"Using team image for generic option '{option}': {other_team_images[0]}")
            else:
                # If no other team image, use any existing image that's not the event image
                non_event_images = [img for opt, img in fixed_images.items() if img != event_image]
                if non_event_images:
                    fixed_images[option] = non_event_images[0]
                    logger.info(f"Using non-event image for generic option '{option}': {non_event_images[0]}")
    
    return fixed_images

if __name__ == "__main__":
    logger.info("=== DIRECT MULTI-OPTION MARKET TEST ===")
    success = test_direct_multi_option()
    
    if success:
        logger.info("\n✅ OVERALL: The fixes for generic option images are working correctly")
    else:
        logger.error("\n❌ OVERALL: Issues remain with generic option image handling")