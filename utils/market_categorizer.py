#!/usr/bin/env python3

"""
Market Categorizer using OpenAI

This module provides functionality to automatically categorize markets
using OpenAI's GPT-4o-mini model before they are posted to Slack.
"""

import os
import logging
import json
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

from openai import OpenAI

# Configure logging
logger = logging.getLogger("market_categorizer")

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

VALID_CATEGORIES = ["politics", "crypto", "sports", "business", "culture", "news", "tech", "all"]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def categorize_market(question: str) -> Optional[str]:
    """
    Categorize a market question using OpenAI's GPT-4o-mini model.
    
    Args:
        question: The market question to categorize
        
    Returns:
        A category string from the valid categories list, or None if categorization failed
    """
    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY not set. Market categorization is disabled.")
        return None
        
    if not question:
        logger.error("Cannot categorize empty question")
        return None
        
    try:
        logger.info(f"Categorizing market question: {question}")
        
        # Create the prompt for GPT-4o-mini
        prompt = f"Market: {question}.\nPick ONE: {VALID_CATEGORIES}.\nReturn the word only."
        
        # Call the OpenAI API with GPT-4o-mini
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1  # Minimal tokens to save cost
        )
        
        # Extract the category from the response
        category = response.choices[0].message.content.strip().lower()
        
        # Validate the category
        if category in VALID_CATEGORIES:
            logger.info(f"Market categorized as: {category}")
            return category
        else:
            logger.warning(f"Invalid category returned: {category}. Defaulting to 'all'")
            return "all"
            
    except Exception as e:
        logger.error(f"Error categorizing market: {str(e)}")
        # Let the retry mechanism handle the error
        raise

def categorize_markets(markets: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """
    Categorize a list of markets and add categories to each market.
    
    Args:
        markets: List of market data dictionaries
        
    Returns:
        The same list of markets with added 'ai_category' field
    """
    if not markets:
        return markets
        
    logger.info(f"Categorizing {len(markets)} markets")
    
    categorized_markets = []
    
    for market in markets:
        try:
            question = market.get('question', '')
            # Attempt to categorize the market
            category = categorize_market(question)
            
            # Add the category to the market data
            market['ai_category'] = category or 'all'  # Default to 'all' if categorization failed
            categorized_markets.append(market)
            
        except Exception as e:
            logger.error(f"Failed to categorize market {market.get('question', 'Unknown')}: {str(e)}")
            # Still include the market, but with default category
            market['ai_category'] = 'all'
            market['ai_category_error'] = str(e)
            market['needs_manual_categorization'] = True
            categorized_markets.append(market)
    
    return categorized_markets