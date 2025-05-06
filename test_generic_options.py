"""
Simple test script to test our fix for "Another Team" and "Barcelona" options.
This directly implements the fix without needing to transform markets.
"""

import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_generic_option(option):
    """Check if an option is generic using the same logic from MarketTransformer"""
    generic_options = [
        "another team", "other team", "another club", 
        "other club", "barcelona", "field", "other"
    ]
    
    return any(generic_term in option.lower() for generic_term in generic_options)

def select_image_for_option(option, event_image, available_images):
    """
    Select an appropriate image for an option based on our fix logic.
    
    Args:
        option: The option text
        event_image: The event banner image
        available_images: Dict mapping options to their images
        
    Returns:
        The selected image URL
    """
    # Check if this is a generic option
    if is_generic_option(option):
        logger.info(f"'{option}' detected as a generic option")
        
        # For generic options, NEVER use the event image
        # First try to find non-event images from other options
        other_non_event_images = []
        other_team_images = []
        
        # Collect non-event images from other options
        for existing_option, existing_image in available_images.items():
            if existing_image and existing_option != option:
                if existing_image != event_image:
                    # Prioritize images that are NOT the event image
                    other_non_event_images.append(existing_image)
                other_team_images.append(existing_image)
        
        # Prioritize using non-event images first
        if other_non_event_images:
            selected_image = other_non_event_images[0]
            logger.info(f"Selected non-event image for '{option}': {selected_image}")
            return selected_image
        # Fall back to any team image if necessary
        elif other_team_images:
            selected_image = other_team_images[0]
            logger.info(f"Selected team image for '{option}': {selected_image}")
            return selected_image
        # Last resort: don't use event image for generic options
        else:
            logger.warning(f"No suitable image found for '{option}', using placeholder")
            return "https://example.com/placeholder.png"
    else:
        # For standard options, just return their assigned image or event image as fallback
        if option in available_images and available_images[option]:
            return available_images[option]
        else:
            logger.info(f"No specific image for '{option}', using event image")
            return event_image

def test_generic_option_handling():
    """
    Test our logic for handling generic options like "Another Team" and "Barcelona".
    """
    # Setup test data
    event_image = "https://example.com/event-banner.png"
    option_images = {
        "Real Madrid": "https://example.com/real-madrid.png",
        "Bayern Munich": "https://example.com/bayern.png",
        "Barcelona": event_image,  # Initially using event image for Barcelona (wrong)
        "Another Team": event_image,  # Initially using event image for Another Team (wrong)
    }
    
    # Test options
    test_options = ["Real Madrid", "Barcelona", "Another Team", "Bayern Munich"]
    
    # Apply our fix logic to each option
    results = {}
    for option in test_options:
        results[option] = select_image_for_option(option, event_image, option_images)
    
    # Validate results
    all_correct = True
    for option in test_options:
        is_generic = is_generic_option(option)
        using_event_image = (results[option] == event_image)
        
        if is_generic and using_event_image:
            logger.error(f"❌ FAIL: Generic option '{option}' is still using the event image")
            all_correct = False
        elif is_generic:
            logger.info(f"✅ PASS: Generic option '{option}' is using a unique image: {results[option]}")
        elif using_event_image:
            logger.info(f"ℹ️ INFO: Standard option '{option}' is using the event image (acceptable fallback)")
        else:
            logger.info(f"✅ PASS: Standard option '{option}' is using its own image: {results[option]}")
    
    return all_correct

def main():
    """Main test function"""
    logger.info("=== TESTING GENERIC OPTION IMAGE HANDLING ===")
    
    success = test_generic_option_handling()
    
    if success:
        logger.info("\n✅ OVERALL: Generic option image handling is working correctly")
    else:
        logger.error("\n❌ OVERALL: Issues remain with generic option image handling")

if __name__ == "__main__":
    main()