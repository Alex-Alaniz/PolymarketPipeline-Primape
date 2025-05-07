#!/usr/bin/env python3

"""
Check and validate image URLs for market events.

This script examines the URLs in event banners and option icons to ensure:
1. The event banner uses the EVENT-related image (not option image)
2. Each option icon uses the OPTION-related image (not event image)

This helps confirm we're using the right image for each event and option.
"""

import os
import json
import logging
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def validate_url(url: str) -> bool:
    """Check if a URL is valid and accessible.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not url or not isinstance(url, str):
        return False
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Check if it has a scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            logger.warning(f"Invalid URL format: {url}")
            return False
        
        # For more thorough validation, could try a HEAD request
        # But this is often too slow for our needs
        # r = requests.head(url, timeout=2)
        # return r.status_code == 200
        
        return True
    except Exception as e:
        logger.error(f"Error validating URL: {str(e)}")
        return False

def check_url_name_match(url: str, name: str, ignore_case: bool = True) -> bool:
    """Check if a name appears in a URL.
    
    This helps identify if we're using the correct images (e.g., team logos).
    
    Args:
        url: Image URL to check
        name: Name to look for in the URL
        ignore_case: Whether to ignore case when matching
        
    Returns:
        bool: True if the name appears in the URL, False otherwise
    """
    if not url or not name:
        return False
    
    try:
        # Extract the filename from the URL
        parsed = urlparse(url)
        path = parsed.path
        filename = os.path.basename(path)
        
        # Clean the name (remove spaces, convert to lowercase if needed)
        clean_name = name.lower().replace(" ", "-").replace("_", "-") if ignore_case else name.replace(" ", "-").replace("_", "-")
        clean_filename = filename.lower() if ignore_case else filename
        
        # Check if the cleaned name appears in the filename
        return clean_name in clean_filename
    except Exception as e:
        logger.error(f"Error checking URL name match: {str(e)}")
        return False

def validate_market_images(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate image URLs in market data and ensure proper usage.
    
    This function checks:
    1. Event banner uses event-related image (not option-specific)
    2. Option icons use option-related images
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Dict with validation results
    """
    results = {
        "valid_event_banner": False,
        "event_banner_url": None,
        "event_name": None,
        "option_images": {},
        "option_name_matches": {},
        "event_name_in_banner": False,
        "option_names_in_option_images": [],
        "option_names_in_wrong_images": [],
        "issues": []
    }
    
    # Get event name
    event_name = None
    if 'event_name' in market_data:
        event_name = market_data['event_name']
    elif 'events' in market_data and isinstance(market_data['events'], list) and len(market_data['events']) > 0:
        first_event = market_data['events'][0]
        event_name = first_event.get('title', first_event.get('name', None))
    
    results["event_name"] = event_name
    
    # Check event banner
    event_banner = None
    
    # First try proper pre-processed image
    if 'event_image' in market_data:
        event_banner = market_data['event_image']
    # For multi-option markets, should use events[0].image
    elif 'events' in market_data and isinstance(market_data['events'], list) and len(market_data['events']) > 0:
        first_event = market_data['events'][0]
        if 'image' in first_event:
            event_banner = first_event['image']
    # For binary markets, use market.image
    elif 'is_binary' in market_data and market_data['is_binary'] and 'image' in market_data:
        event_banner = market_data['image']
    
    results["event_banner_url"] = event_banner
    
    # Validate event banner URL
    if event_banner and validate_url(event_banner):
        results["valid_event_banner"] = True
        
        # Check if event name appears in banner URL filename
        if event_name and check_url_name_match(event_banner, event_name):
            results["event_name_in_banner"] = True
        else:
            # If event name is not in banner, flag as potential issue
            results["issues"].append(f"Event name '{event_name}' not found in banner URL: {event_banner}")
    else:
        results["issues"].append(f"Invalid or missing event banner URL: {event_banner}")
    
    # Get option images
    option_images = {}
    option_names = {}
    
    # First get from pre-processed data
    if 'option_images' in market_data and isinstance(market_data['option_images'], dict):
        option_images = market_data['option_images']
    
    # Get option names from outcomes
    outcomes_raw = market_data.get("outcomes", "[]")
    try:
        if isinstance(outcomes_raw, str):
            outcomes = json.loads(outcomes_raw)
        else:
            outcomes = outcomes_raw
            
        if isinstance(outcomes, list):
            for outcome in outcomes:
                if isinstance(outcome, str):
                    option_names[outcome] = outcome
    except Exception as e:
        logger.error(f"Error parsing outcomes: {str(e)}")
    
    # Get option names from events.outcomes
    if 'events' in market_data and isinstance(market_data['events'], list) and len(market_data['events']) > 0:
        first_event = market_data['events'][0]
        if 'outcomes' in first_event and isinstance(first_event['outcomes'], list):
            for outcome in first_event['outcomes']:
                if isinstance(outcome, dict):
                    outcome_id = outcome.get('id')
                    outcome_name = outcome.get('title', outcome.get('name'))
                    if outcome_id and outcome_name:
                        option_names[outcome_id] = outcome_name
    
    # Get option names from option_markets
    if 'option_markets' in market_data and isinstance(market_data['option_markets'], list):
        for option_market in market_data['option_markets']:
            if isinstance(option_market, dict):
                option_id = option_market.get('id')
                option_question = option_market.get('question')
                if option_id and option_question:
                    option_names[option_id] = option_question
    
    # Validate each option image and check name match
    for option_id, image_url in option_images.items():
        option_name = option_names.get(option_id, option_id)
        
        # Check URL validity
        if validate_url(image_url):
            results["option_images"][option_id] = image_url
            
            # Check if option name appears in image URL filename
            if check_url_name_match(image_url, option_name) or check_url_name_match(image_url, option_id):
                results["option_name_matches"][option_id] = True
                results["option_names_in_option_images"].append(option_id)
            else:
                results["option_name_matches"][option_id] = False
                results["issues"].append(f"Option name '{option_name}' not found in option image URL: {image_url}")
            
            # Check if event name appears in option image (potential wrong image)
            if event_name and check_url_name_match(image_url, event_name):
                results["option_names_in_wrong_images"].append(option_id)
                results["issues"].append(f"Event name '{event_name}' found in option image URL for '{option_name}': {image_url}")
        else:
            results["issues"].append(f"Invalid option image URL for '{option_name}': {image_url}")
    
    return results

def main():
    """
    Main function to test image URL validation with sample data.
    """
    # Try to load test data from a file
    try:
        logger.info("Looking for sample data in gamma_markets_response.json")
        with open("gamma_markets_response.json", "r") as f:
            data = json.load(f)
            
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Found {len(data)} markets in sample data")
                
                for i, market in enumerate(data[:5]):
                    logger.info(f"\n==== Checking Market {i+1}: {market.get('question', 'Unknown')} ====")
                    results = validate_market_images(market)
                    
                    logger.info(f"Event Name: {results['event_name']}")
                    logger.info(f"Valid Event Banner: {results['valid_event_banner']}")
                    logger.info(f"Event Banner URL: {results['event_banner_url']}")
                    logger.info(f"Event Name Found in Banner: {results['event_name_in_banner']}")
                    
                    if results['option_images']:
                        logger.info(f"Found {len(results['option_images'])} option images:")
                        for option_id, image_url in results['option_images'].items():
                            name_match = results['option_name_matches'].get(option_id, False)
                            option_name = "Unknown"
                            if 'events' in market and len(market['events']) > 0:
                                for outcome in market['events'][0].get('outcomes', []):
                                    if isinstance(outcome, dict) and outcome.get('id') == option_id:
                                        option_name = outcome.get('title', outcome.get('name', 'Unknown'))
                            
                            logger.info(f"  - {option_id} ({option_name}): {image_url}")
                            logger.info(f"    Name matches URL: {name_match}")
                    
                    if results['issues']:
                        logger.warning(f"Found {len(results['issues'])} issues:")
                        for issue in results['issues']:
                            logger.warning(f"  - {issue}")
                    else:
                        logger.info("No issues found - images are correctly assigned")
            else:
                logger.error("Invalid data format in sample file")
    except Exception as e:
        logger.error(f"Error processing sample data: {str(e)}")
        
        # Create some example data for testing
        logger.info("Using example data for testing")
        
        example_data = {
            "question": "La Liga Winner 2024-2025",
            "category": "sports",
            "is_multiple_option": True,
            "is_binary": False,
            "is_event": True,
            "events": [
                {
                    "id": "12672",
                    "title": "La Liga Winner",
                    "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8f/2021_La_Liga_logo.jpg/1200px-2021_La_Liga_logo.jpg",
                    "outcomes": [
                        {
                            "id": "real-madrid",
                            "title": "Real Madrid",
                            "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/5/56/Real_Madrid_CF.svg/1200px-Real_Madrid_CF.svg.png",
                        },
                        {
                            "id": "barcelona",
                            "title": "Barcelona",
                            "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/4/47/FC_Barcelona_%28crest%29.svg/1200px-FC_Barcelona_%28crest%29.svg.png",
                        },
                    ]
                }
            ],
            "option_markets": [
                {
                    "id": "507396",
                    "question": "Will Barcelona win La Liga?",
                    "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/4/47/FC_Barcelona_%28crest%29.svg/1200px-FC_Barcelona_%28crest%29.svg.png",
                },
                {
                    "id": "507395",
                    "question": "Will Real Madrid win La Liga?",
                    "icon": "https://upload.wikimedia.org/wikipedia/en/thumb/5/56/Real_Madrid_CF.svg/1200px-Real_Madrid_CF.svg.png",
                }
            ],
        }
        
        # Process with event filter first
        from utils.event_filter import process_event_images
        processed = process_event_images(example_data)
        
        # Validate processed data
        logger.info("\n==== Checking Example Data ====")
        results = validate_market_images(processed)
        
        logger.info(f"Event Name: {results['event_name']}")
        logger.info(f"Valid Event Banner: {results['valid_event_banner']}")
        logger.info(f"Event Banner URL: {results['event_banner_url']}")
        logger.info(f"Event Name Found in Banner: {results['event_name_in_banner']}")
        
        if results['option_images']:
            logger.info(f"Found {len(results['option_images'])} option images:")
            for option_id, image_url in results['option_images'].items():
                name_match = results['option_name_matches'].get(option_id, False)
                
                option_name = "Unknown"
                if option_id == "real-madrid":
                    option_name = "Real Madrid"
                elif option_id == "barcelona":
                    option_name = "Barcelona"
                elif option_id == "507396":
                    option_name = "Will Barcelona win La Liga?"
                elif option_id == "507395":
                    option_name = "Will Real Madrid win La Liga?"
                
                logger.info(f"  - {option_id} ({option_name}): {image_url}")
                logger.info(f"    Name matches URL: {name_match}")
        
        if results['issues']:
            logger.warning(f"Found {len(results['issues'])} issues:")
            for issue in results['issues']:
                logger.warning(f"  - {issue}")
        else:
            logger.info("No issues found - images are correctly assigned")
            
        # Now test a flawed example with mismatched images
        logger.info("\n==== Testing Flawed Example (Mismatched Images) ====")
        
        flawed_example = example_data.copy()
        # Intentionally use wrong image for event banner (team logo instead of event logo)
        flawed_example['events'][0]['image'] = "https://upload.wikimedia.org/wikipedia/en/thumb/5/56/Real_Madrid_CF.svg/1200px-Real_Madrid_CF.svg.png"
        # Process with event filter
        flawed_processed = process_event_images(flawed_example)
        
        # Validate flawed data
        flawed_results = validate_market_images(flawed_processed)
        
        logger.info(f"Event Name: {flawed_results['event_name']}")
        logger.info(f"Valid Event Banner: {flawed_results['valid_event_banner']}")
        logger.info(f"Event Banner URL: {flawed_results['event_banner_url']}")
        logger.info(f"Event Name Found in Banner: {flawed_results['event_name_in_banner']}")
        
        if flawed_results['issues']:
            logger.warning(f"Found {len(flawed_results['issues'])} issues with flawed data:")
            for issue in flawed_results['issues']:
                logger.warning(f"  - {issue}")
        else:
            logger.info("No issues found in flawed data - this is unexpected!")

if __name__ == "__main__":
    main()