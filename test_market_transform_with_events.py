#!/usr/bin/env python3
"""
Test Market Transformation with Events

This script tests the transformation of markets from Polymarket
to our format with proper event extraction and option handling.
"""

import json
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('event_transform_test')

# Import our transformation utilities
from utils.transform_market_with_events import (
    extract_event_from_market,
    extract_market_options,
    transform_market_for_apechain,
    transform_markets_batch
)

def create_sample_gamma_market() -> Dict[str, Any]:
    """Create a sample market in Gamma API format"""
    return {
        "conditionId": "0x123456789abcdef",
        "question": "Will Arsenal win the UEFA Champions League?",
        "description": "This market resolves to YES if Arsenal wins the 2025 UEFA Champions League.",
        "outcomes": '["Yes", "No"]',
        "image": "https://example.com/banner.png",
        "icon": "https://example.com/icon.png",
        "category": "sports",
        "endDate": "2025-05-31T12:00:00Z",
        "active": True,
        "closed": False,
        "archived": False
    }

def create_sample_related_markets() -> List[Dict[str, Any]]:
    """Create multiple related markets that should be grouped in the same event"""
    return [
        {
            "conditionId": "0x111111",
            "question": "Will Arsenal win the UEFA Champions League?",
            "description": "This market resolves to YES if Arsenal wins the 2025 UEFA Champions League.",
            "outcomes": '["Yes", "No"]',
            "image": "https://example.com/ucl_banner.png",
            "icon": "https://example.com/arsenal_icon.png",
            "category": "sports",
            "endDate": "2025-05-31T12:00:00Z"
        },
        {
            "conditionId": "0x222222",
            "question": "Will Barcelona win the UEFA Champions League?",
            "description": "This market resolves to YES if Barcelona wins the 2025 UEFA Champions League.",
            "outcomes": '["Yes", "No"]',
            "image": "https://example.com/ucl_banner.png",
            "icon": "https://example.com/barca_icon.png",
            "category": "sports",
            "endDate": "2025-05-31T12:00:00Z"
        },
        {
            "conditionId": "0x333333",
            "question": "Will Inter Milan win the UEFA Champions League?",
            "description": "This market resolves to YES if Inter Milan wins the 2025 UEFA Champions League.",
            "outcomes": '["Yes", "No"]',
            "image": "https://example.com/ucl_banner.png",
            "icon": "https://example.com/inter_icon.png",
            "category": "sports",
            "endDate": "2025-05-31T12:00:00Z"
        }
    ]

def test_event_extraction():
    """Test event extraction from market data"""
    logger.info("Testing event extraction...")
    
    # Create sample market
    market = create_sample_gamma_market()
    
    # Extract event
    event_data, updated_market = extract_event_from_market(market)
    
    # Log results
    logger.info(f"Event ID: {event_data['id']}")
    logger.info(f"Event Name: {event_data['name']}")
    logger.info(f"Event Category: {event_data['category']}")
    logger.info(f"Original Market ID: {event_data['source_id']}")
    logger.info(f"Updated Market event_id: {updated_market['event_id']}")
    logger.info(f"Updated Market event_name: {updated_market['event_name']}")
    
    # Verify event extraction
    assert event_data['name'] == 'Champions League', "Failed to extract event name correctly"
    assert updated_market['event_id'] == event_data['id'], "Failed to update market with event ID"
    assert updated_market['event_name'] == event_data['name'], "Failed to update market with event name"
    
    logger.info("✓ Event extraction test passed")

def test_option_extraction():
    """Test option extraction from market data"""
    logger.info("Testing option extraction...")
    
    # Create sample market
    market = create_sample_gamma_market()
    
    # Extract options
    options = extract_market_options(market)
    
    # Log results
    logger.info(f"Number of options: {len(options)}")
    for i, option in enumerate(options):
        logger.info(f"Option {i+1}: ID={option['id']}, Value={option['value']}")
    
    # Verify option extraction
    assert len(options) == 2, "Failed to extract correct number of options"
    assert options[0]['value'] == 'Yes', "Failed to extract first option correctly"
    assert options[1]['value'] == 'No', "Failed to extract second option correctly"
    
    logger.info("✓ Option extraction test passed")

def test_full_market_transformation():
    """Test complete market transformation"""
    logger.info("Testing full market transformation...")
    
    # Create sample market
    market = create_sample_gamma_market()
    
    # Transform market
    event_data, transformed_market = transform_market_for_apechain(market)
    
    # Log results
    logger.info(f"Transformed Market ID: {transformed_market['id']}")
    logger.info(f"Transformed Market Question: {transformed_market['question']}")
    logger.info(f"Transformed Market Type: {transformed_market['type']}")
    logger.info(f"Transformed Market Event ID: {transformed_market['event_id']}")
    logger.info(f"Transformed Market Option Count: {len(transformed_market['options'])}")
    
    # Verify transformation
    assert transformed_market['id'] == market['conditionId'], "Failed to transform market ID correctly"
    assert transformed_market['question'] == market['question'], "Failed to transform market question correctly"
    assert transformed_market['type'] == 'binary', "Failed to determine market type correctly"
    assert transformed_market['event_id'] == event_data['id'], "Failed to link market to event correctly"
    assert len(transformed_market['options']) == 2, "Failed to transform options correctly"
    
    logger.info("✓ Full market transformation test passed")

def test_batch_transformation():
    """Test batch transformation of multiple related markets"""
    logger.info("Testing batch transformation...")
    
    # Create sample related markets
    markets = create_sample_related_markets()
    
    # Transform markets in batch
    events, transformed_markets = transform_markets_batch(markets)
    
    # Log results
    logger.info(f"Number of events: {len(events)}")
    logger.info(f"Number of transformed markets: {len(transformed_markets)}")
    
    if events:
        logger.info(f"Event: {events[0]['name']} (ID: {events[0]['id']})")
    
    for i, market in enumerate(transformed_markets):
        logger.info(f"Market {i+1}: {market['question'][:30]}... (Event ID: {market['event_id']})")
    
    # Verify batch transformation
    assert len(events) == 1, "Failed to group markets under one event"
    assert len(transformed_markets) == len(markets), "Failed to transform all markets"
    assert all(m['event_id'] == events[0]['id'] for m in transformed_markets), "Failed to assign the same event ID to all markets"
    
    logger.info("✓ Batch transformation test passed")

def run_all_tests():
    """Run all tests"""
    logger.info("Running all market transformation tests...")
    
    # Run tests
    test_event_extraction()
    test_option_extraction()
    test_full_market_transformation()
    test_batch_transformation()
    
    logger.info("All tests completed successfully!")

if __name__ == "__main__":
    run_all_tests()