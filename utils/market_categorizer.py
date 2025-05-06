"""
Market categorization utility using OpenAI GPT-4o-mini.

This module provides functions for categorizing markets based on
their question and description, assigning them to one of the
standard categories: politics, crypto, sports, business, culture, news, tech.
"""

import os
import json
import logging
from typing import Tuple, Optional

import openai
from tenacity import retry, stop_after_attempt, wait_fixed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.warning("Missing OpenAI API key. Set OPENAI_API_KEY environment variable.")

openai_client = openai.OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

# Define valid categories (these should match the frontend categories)
VALID_CATEGORIES = [
    'politics',
    'crypto',
    'sports',
    'business',
    'culture',
    'news',
    'tech'
]

# System prompt for categorization
CATEGORIZATION_PROMPT = """
You are a market categorizer for a prediction market platform.
Given the question and description of a prediction market, assign exactly one category from the following list:
- politics: For markets related to elections, governance, political figures, or policy decisions
- crypto: For markets related to cryptocurrencies, blockchain, tokens, or digital assets
- sports: For markets related to sports teams, players, tournaments, or athletic events
- business: For markets related to companies, stock prices, earnings, or economic trends
- culture: For markets related to entertainment, celebrities, movies, music, or cultural events
- news: For markets related to current events that don't fit into other categories
- tech: For markets related to technology companies, products, or innovations

Respond with a JSON object containing:
1. "category": Your chosen category (lowercase, exactly as shown in the list)
2. "confidence": A number from 0 to 1 indicating your confidence level
3. "reasoning": A brief explanation of why you chose this category

If you're not sure, assign the market to the category that seems most appropriate based on the information provided.
"""

@retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
def categorize_market(question: str, description: Optional[str] = None) -> Tuple[str, bool]:
    """
    Categorize a market using GPT-4o-mini.
    
    Args:
        question: Market question
        description: Optional market description
        
    Returns:
        Tuple of (category, needs_manual_categorization)
    """
    if not openai_client:
        logger.error("OpenAI client not initialized - missing API key")
        return "news", True  # Default to news with manual flag if API unavailable
    
    try:
        # Combine question and description
        content = f"Question: {question}"
        if description:
            content += f"\n\nDescription: {description}"
        
        # Call GPT-4o-mini
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # The newest model from OpenAI
            messages=[
                {"role": "system", "content": CATEGORIZATION_PROMPT},
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for more consistent results
        )
        
        # Parse response
        result = json.loads(response.choices[0].message.content)
        
        category = result.get("category", "").lower()
        confidence = result.get("confidence", 0)
        
        # Validate category
        if category not in VALID_CATEGORIES:
            logger.warning(f"Invalid category '{category}' returned by model. Defaulting to 'news'.")
            category = "news"
        
        # Flag for manual review if confidence is low
        needs_manual = confidence < 0.7
        
        logger.info(f"Categorized market '{question[:30]}...' as '{category}' with confidence {confidence}")
        
        return category, needs_manual
    
    except Exception as e:
        logger.error(f"Error categorizing market: {str(e)}")
        return "news", True  # Default to news with manual flag on error