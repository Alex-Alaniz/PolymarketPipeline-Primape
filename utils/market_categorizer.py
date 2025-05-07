"""
Market categorization utility using OpenAI GPT-4o-mini.

This module provides functions for categorizing markets based on
their question and description, assigning them to one of the
standard categories: politics, crypto, sports, business, culture, news, tech.
"""

import os
import json
import logging
from typing import Tuple, Optional, List, Dict, Any

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
    # Check if OpenAI client is available
    if not openai_client:
        logger.error("OpenAI client not initialized - missing API key")
        # Use keyword-based categorization instead of defaulting to news
        category = keyword_based_categorization(question)
        logger.warning(f"Using keyword-based categorization for '{question[:30]}...' - {category}")
        return category, True
    
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
            logger.warning(f"Invalid category '{category}' returned by model. Using keyword fallback.")
            # Use keyword-based categorization if model returns invalid category
            category = keyword_based_categorization(question)
        
        # Flag for manual review if confidence is low
        needs_manual = confidence < 0.7
        
        logger.info(f"Categorized market '{question[:30]}...' as '{category}' with confidence {confidence}")
        
        return category, needs_manual
    
    except Exception as e:
        logger.error(f"Error categorizing market: {str(e)}")
        # Default to a more specific error message and flag for manual review
        error_type = str(e).lower()
        
        # If the error is due to OpenAI API connectivity, log clearly
        if "openai" in error_type or "api" in error_type or "connection" in error_type:
            logger.error("OpenAI API connectivity issue - check API key and network")
        
        # Use the unified keyword-based categorization function
        category = keyword_based_categorization(question)
        logger.info(f"Using error fallback for '{question[:30]}...' - {category}")
        return category, True

def keyword_based_categorization(question: str) -> str:
    """
    Categorize a market based on keywords in the question.
    
    Args:
        question: Market question
        
    Returns:
        Category string
    """
    question_lower = question.lower() if question else ""
    
    # Politics keywords
    if any(keyword in question_lower for keyword in 
          ["biden", "president", "election", "vote", "congress", "political", 
           "government", "senate", "house", "supreme court", "justice"]):
        return "politics"
    
    # Crypto keywords
    elif any(keyword in question_lower for keyword in 
            ["bitcoin", "eth", "ethereum", "crypto", "blockchain", "token", 
             "defi", "nft", "cryptocurrency", "btc"]):
        return "crypto"
    
    # Sports keywords
    elif any(keyword in question_lower for keyword in 
            ["team", "game", "match", "player", "sport", "win", "championship", 
             "tournament", "league", "nba", "nfl", "mlb", "soccer", "football"]):
        return "sports"
    
    # Business keywords
    elif any(keyword in question_lower for keyword in 
            ["stock", "company", "price", "market", "business", "earnings", 
             "profit", "ceo", "investor", "economy", "financial", "trade"]):
        return "business"
    
    # Tech keywords
    elif any(keyword in question_lower for keyword in 
            ["ai", "tech", "technology", "software", "app", "computer", "device", 
             "release", "launch", "update", "apple", "google", "microsoft"]):
        return "tech"
    
    # Culture keywords
    elif any(keyword in question_lower for keyword in 
            ["movie", "actor", "actress", "celebrity", "award", "album", "song", 
             "artist", "show", "event", "festival", "entertainment"]):
        return "culture"
    
    # Default to news
    else:
        return "news"

def categorize_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Categorize multiple markets using GPT-4o-mini.
    
    Args:
        markets: List of market data dictionaries with 'question' and optional 'description' fields
        
    Returns:
        List of market dictionaries with added 'ai_category' and 'needs_manual_categorization' fields
    """
    categorized_markets = []
    total_markets = len(markets)
    
    logger.info(f"Categorizing {total_markets} markets with GPT-4o-mini...")
    
    # Check if OpenAI client is available
    openai_unavailable = openai_client is None
    
    # If API is unavailable, use keyword-based categorization
    if openai_unavailable:
        logger.warning("OpenAI API unavailable - using keyword-based categorization for all markets")
        
        for i, market in enumerate(markets):
            question = market.get('question', '')
            if not question:
                logger.warning(f"Market at index {i} has no question, defaulting to 'news' category")
                category = "news"
            else:
                # Use keyword-based categorization
                category = keyword_based_categorization(question)
                logger.info(f"Used keyword categorization for market {i+1}/{total_markets}: '{question[:30]}...' as {category}")
            
            # Create a copy of the market with the category added
            market_copy = market.copy()
            market_copy['ai_category'] = category
            market_copy['needs_manual_categorization'] = True
            categorized_markets.append(market_copy)
        
        return categorized_markets
    
    # If API is available, use GPT-4o-mini with fallback to keywords
    for i, market in enumerate(markets):
        try:
            question = market.get('question', '')
            description = market.get('description', '')
            
            if not question:
                logger.warning(f"Market at index {i} has no question, defaulting to 'news' category")
                market_copy = market.copy()
                market_copy['ai_category'] = 'news'
                market_copy['needs_manual_categorization'] = True
                categorized_markets.append(market_copy)
                continue
                
            # Call the single market categorization function
            category, needs_manual = categorize_market(question, description)
            
            # Create a copy of the market with the category added
            market_copy = market.copy()
            market_copy['ai_category'] = category
            market_copy['needs_manual_categorization'] = needs_manual
            
            categorized_markets.append(market_copy)
            
            logger.info(f"Categorized market {i+1}/{total_markets}: '{question[:30]}...' as {category}")
            
        except Exception as e:
            logger.error(f"Error categorizing market at index {i}: {str(e)}")
            
            # Extract question for keyword matching
            question = market.get('question', '')
            
            # Add with smart fallback category based on keywords
            market_copy = market.copy()
            
            if question:
                # Use keyword-based categorization
                category = keyword_based_categorization(question)
                logger.info(f"Using keyword fallback for market {i+1} - {category}")
                market_copy['ai_category'] = category
            else:
                # Last resort fallback
                logger.info(f"Using default fallback for market {i+1} - news")
                market_copy['ai_category'] = 'news'
                
            market_copy['needs_manual_categorization'] = True
            categorized_markets.append(market_copy)
    
    return categorized_markets