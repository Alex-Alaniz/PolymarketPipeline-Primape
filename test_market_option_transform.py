#!/usr/bin/env python3
"""
Test the market option transformation functionality.

This script tests our ability to parse different formats of market options
from the Polymarket Gamma API.
"""

import json
import logging
from typing import Dict, Any, List, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('option_transform_test')

def transform_market_options(market_data: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Transform market options and extract option images.
    
    Args:
        market_data: Raw market data from API
        
    Returns:
        Tuple of (options list, option_images dict)
    """
    # Get outcomes from market data - handles both object and string formats
    api_outcomes_raw = market_data.get('outcomes')
    api_options_raw = market_data.get('options')
    
    # Format options for our database
    options = []
    option_images = {}
    
    # First try to parse the outcomes (in Gamma API, this is a JSON string)
    if api_outcomes_raw and isinstance(api_outcomes_raw, str):
        try:
            # Try to parse as JSON string
            outcomes = json.loads(api_outcomes_raw)
            
            # If successful, create option objects
            if isinstance(outcomes, list):
                for i, value in enumerate(outcomes):
                    options.append({
                        'id': str(i),
                        'value': value
                    })
                    
            logger.info(f"Parsed {len(options)} outcomes from JSON string")
            return options, option_images
            
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse outcomes as JSON: {api_outcomes_raw}")
    
    # If that didn't work, try the object format (for backward compatibility)
    api_options = []
    if isinstance(api_outcomes_raw, list):
        api_options = api_outcomes_raw
    elif isinstance(api_options_raw, list):
        api_options = api_options_raw
    
    # Process options in object format
    if api_options:
        for opt in api_options:
            if isinstance(opt, dict):
                option_id = opt.get('id', '')
                value = opt.get('value', '')
                image_url = opt.get('image', '')
                
                options.append({
                    'id': option_id,
                    'value': value
                })
                
                if image_url:
                    option_images[value] = image_url
    
    # If still no options, create default Yes/No options
    if not options:
        logger.warning(f"No options found or parsed, defaulting to Yes/No")
        options = [
            {"id": "0", "value": "Yes"},
            {"id": "1", "value": "No"}
        ]
    
    return options, option_images

def test_json_string_options():
    """Test parsing options from JSON string format"""
    logger.info("Testing JSON string options format...")
    
    # Test case 1: Simple Yes/No options
    market1 = {
        'question': 'Will Team A win?',
        'outcomes': '["Yes", "No"]'
    }
    
    options1, images1 = transform_market_options(market1)
    logger.info(f"Market 1 options: {options1}")
    
    # Test case 2: Multiple options
    market2 = {
        'question': 'Which team will win?',
        'outcomes': '["Team A", "Team B", "Team C", "Draw"]'
    }
    
    options2, images2 = transform_market_options(market2)
    logger.info(f"Market 2 options: {options2}")
    
    # Test case 3: Malformed JSON
    market3 = {
        'question': 'Will Team A win?',
        'outcomes': '[Yes, No]'  # Missing quotes
    }
    
    options3, images3 = transform_market_options(market3)
    logger.info(f"Market 3 options: {options3}")
    
    return (options1, options2, options3)

def test_list_object_options():
    """Test parsing options from list of objects format"""
    logger.info("Testing list of objects options format...")
    
    # Test case 4: Options as list of objects
    market4 = {
        'question': 'Will Team A win?',
        'options': [
            {'id': '1', 'value': 'Yes', 'image': 'https://example.com/yes.png'},
            {'id': '2', 'value': 'No', 'image': 'https://example.com/no.png'}
        ]
    }
    
    options4, images4 = transform_market_options(market4)
    logger.info(f"Market 4 options: {options4}")
    logger.info(f"Market 4 images: {images4}")
    
    return (options4, images4)

def test_no_options():
    """Test handling of markets with no options"""
    logger.info("Testing markets with no options...")
    
    # Test case 5: No options at all
    market5 = {
        'question': 'Will Team A win?'
    }
    
    options5, images5 = transform_market_options(market5)
    logger.info(f"Market 5 options: {options5}")
    
    # Test case 6: Empty options
    market6 = {
        'question': 'Will Team A win?',
        'outcomes': '[]'
    }
    
    options6, images6 = transform_market_options(market6)
    logger.info(f"Market 6 options: {options6}")
    
    return (options5, options6)

def run_all_tests():
    """Run all test cases"""
    logger.info("Running all option transform tests...")
    
    # Run all test cases
    json_results = test_json_string_options()
    object_results = test_list_object_options()
    empty_results = test_no_options()
    
    # Verify results
    all_passed = True
    
    # Check JSON string options (Yes/No)
    if len(json_results[0]) == 2 and json_results[0][0]['value'] == 'Yes' and json_results[0][1]['value'] == 'No':
        logger.info("✓ Simple Yes/No JSON string options test passed")
    else:
        logger.error("✗ Simple Yes/No JSON string options test failed")
        all_passed = False
    
    # Check JSON string options (multiple)
    if (len(json_results[1]) == 4 and 
        json_results[1][0]['value'] == 'Team A' and 
        json_results[1][3]['value'] == 'Draw'):
        logger.info("✓ Multiple options JSON string test passed")
    else:
        logger.error("✗ Multiple options JSON string test failed")
        all_passed = False
    
    # Check malformed JSON handling (should default to Yes/No)
    if len(json_results[2]) == 2 and json_results[2][0]['value'] == 'Yes' and json_results[2][1]['value'] == 'No':
        logger.info("✓ Malformed JSON handling test passed")
    else:
        logger.error("✗ Malformed JSON handling test failed")
        all_passed = False
    
    # Check object format options
    if (len(object_results[0]) == 2 and 
        object_results[0][0]['value'] == 'Yes' and 
        object_results[0][1]['value'] == 'No' and
        'Yes' in object_results[1] and 
        'No' in object_results[1]):
        logger.info("✓ Object format options test passed")
    else:
        logger.error("✗ Object format options test failed")
        all_passed = False
    
    # Check empty options handling
    if len(empty_results[0]) == 2 and empty_results[0][0]['value'] == 'Yes' and empty_results[0][1]['value'] == 'No':
        logger.info("✓ No options handling test passed")
    else:
        logger.error("✗ No options handling test failed")
        all_passed = False
    
    if all_passed:
        logger.info("All option transformation tests passed!")
    else:
        logger.error("Some option transformation tests failed.")
    
    return all_passed

if __name__ == "__main__":
    run_all_tests()