#!/usr/bin/env python3

"""
Test script for auto-categorization functionality.

This script tests the market categorization feature to ensure:
1. Markets are correctly categorized into one of the valid categories
2. "all" is never used as a category
3. The fallback category is "news" when categorization fails
"""

import sys
import json
import logging
from datetime import datetime
from random import sample

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import categorizer
from utils.market_categorizer import categorize_market, categorize_markets, VALID_CATEGORIES

# Import flask app for database context
from main import app


def test_individual_categorization():
    """Test that individual market questions are categorized correctly"""
    
    # Sample market questions covering different categories
    sample_questions = [
        "Will Donald Trump win the 2024 US Presidential Election?",  # politics
        "Will Bitcoin exceed $100,000 before the end of 2025?",      # crypto
        "Will the Golden State Warriors win the 2025 NBA Finals?",   # sports
        "Will Apple's market cap exceed $4 trillion in 2025?",       # business
        "Will Taylor Swift release a new album in 2025?",            # culture
        "Will there be a peace agreement in Ukraine by 2026?",       # news
        "Will SpaceX successfully land humans on Mars by 2030?",     # tech
    ]
    
    logger.info("Testing individual market categorization...")
    
    # Test each question
    for question in sample_questions:
        category = categorize_market(question)
        logger.info(f"Question: {question}")
        logger.info(f"Category: {category}")
        
        # Verify the category is valid
        assert category in VALID_CATEGORIES, f"Invalid category: {category}"
        
        # Verify the category is never 'all'
        assert category != 'all', "Category should never be 'all'"
        
        # Add a separator for clarity
        logger.info("-" * 40)
    
    logger.info("Individual categorization tests passed!")


def test_batch_categorization():
    """Test that a batch of markets are categorized correctly"""
    
    # Create a batch of fake market data
    markets = [
        {"question": "Will Donald Trump win the 2024 US Presidential Election?"},
        {"question": "Will Bitcoin exceed $100,000 before the end of 2025?"},
        {"question": "Will the Golden State Warriors win the 2025 NBA Finals?"},
        {"question": "Will Apple's market cap exceed $4 trillion in 2025?"},
        {"question": "Will Taylor Swift release a new album in 2025?"},
        {"question": "Will there be a peace agreement in Ukraine by 2026?"},
        {"question": "Will SpaceX successfully land humans on Mars by 2030?"},
    ]
    
    logger.info("Testing batch market categorization...")
    
    # Categorize the markets
    categorized_markets = categorize_markets(markets)
    
    # Verify each market has a category
    for market in categorized_markets:
        assert 'ai_category' in market, "Market missing ai_category field"
        assert market['ai_category'] in VALID_CATEGORIES, f"Invalid category: {market['ai_category']}"
        assert market['ai_category'] != 'all', "Category should never be 'all'"
        
        logger.info(f"Question: {market['question']}")
        logger.info(f"Category: {market['ai_category']}")
        logger.info("-" * 40)
    
    logger.info("Batch categorization tests passed!")


def test_fallback_behavior():
    """Test that the fallback behavior is correct"""
    
    # Create a market with an empty question to force fallback
    empty_market = {"question": ""}
    
    logger.info("Testing fallback behavior...")
    
    # Categorize the market
    categorized_markets = categorize_markets([empty_market])
    
    # Verify the fallback category is 'news'
    assert categorized_markets[0]['ai_category'] == 'news', "Fallback category should be 'news'"
    assert categorized_markets[0].get('needs_manual_categorization', False) is True, "Market should be flagged for manual review"
    
    logger.info(f"Empty question fallback category: {categorized_markets[0]['ai_category']}")
    logger.info(f"Needs manual review flag: {categorized_markets[0].get('needs_manual_categorization')}")
    logger.info("Fallback behavior test passed!")


def main():
    """Main test function"""
    try:
        # Run the tests
        test_individual_categorization()
        test_batch_categorization()
        test_fallback_behavior()
        
        logger.info("All auto-categorization tests passed!")
        return 0
    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        return 1


if __name__ == "__main__":
    # Use the app context
    with app.app_context():
        sys.exit(main())