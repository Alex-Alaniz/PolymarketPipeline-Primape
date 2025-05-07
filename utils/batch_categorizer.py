"""
Batch Market Categorizer

This module provides a more efficient approach to categorizing multiple markets
by sending all markets in a single API call to GPT-4o-mini.
"""

import json
import logging
import os
from typing import Dict, List, Any, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import OpenAI client
from openai import OpenAI

# Initialize OpenAI client
openai_client = None
try:
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key:
        openai_client = OpenAI(api_key=openai_api_key)
    else:
        logger.warning("OPENAI_API_KEY not found in environment variables")
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {str(e)}")

# Valid categories - must match exactly what's in the prompt
VALID_CATEGORIES = ["politics", "crypto", "sports", "business", "culture", "news", "tech"]

# System prompt for batch categorization
BATCH_CATEGORIZATION_PROMPT = """
You are an expert market categorizer for a prediction market platform. Your task is to assign each market to exactly one of these categories:

- politics: Political events, elections, government actions, policy changes
- crypto: Cryptocurrency, blockchain technology, NFTs, DeFi developments
- sports: Sports events, tournaments, player performance, team standings
- business: Business news, company earnings, stock market events, mergers
- culture: Entertainment, celebrity news, music, film, TV, social trends
- news: General news that doesn't fit into other categories
- tech: Technology developments, product launches, AI advancements

I will provide you with a list of prediction markets. For each market, categorize it and provide a confidence score (0.0-1.0) indicating how confident you are in your categorization.

Your response should be a JSON array of objects, with each object containing:
1. "id" - The ID of the market (provided in the input)
2. "category" - One of the categories listed above (lowercase)
3. "confidence" - A number between 0 and 1 indicating your confidence

Example output format:
[
  {"id": "123", "category": "politics", "confidence": 0.95},
  {"id": "456", "category": "sports", "confidence": 0.88}
]

Keep your reasoning concise and focus on accurate categorization.
"""

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

def batch_categorize_markets(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Categorize multiple markets in a single API call to GPT-4o-mini.
    
    Args:
        markets: List of market data dictionaries with 'id', 'question', and optional 'description' fields
        
    Returns:
        List of market dictionaries with added 'ai_category' and 'needs_manual_categorization' fields
    """
    categorized_markets = []
    total_markets = len(markets)
    
    logger.info(f"Batch categorizing {total_markets} markets with GPT-4o-mini...")
    
    # Check if OpenAI client is available
    if not openai_client:
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
    
    # Prepare markets data for the API call
    formatted_markets = []
    for i, market in enumerate(markets):
        question = market.get('question', '')
        description = market.get('description', '')
        
        if not question:
            # Skip markets with no question in the API call
            logger.warning(f"Market at index {i} has no question, defaulting to 'news' category")
            market_copy = market.copy()
            market_copy['ai_category'] = 'news'
            market_copy['needs_manual_categorization'] = True
            categorized_markets.append(market_copy)
            continue
        
        # Add to formatted markets for API call
        formatted_markets.append({
            "id": str(i),  # Use index as temporary ID
            "question": question,
            "description": description if description else ""
        })
    
    # If all markets were skipped
    if not formatted_markets:
        logger.warning("No valid markets to categorize")
        return categorized_markets
    
    try:
        # Prepare the content for the API call
        content = json.dumps(formatted_markets, indent=2)
        
        # Make the API call
        logger.info(f"Sending batch of {len(formatted_markets)} markets to OpenAI API...")
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # The newest model from OpenAI
            messages=[
                {"role": "system", "content": BATCH_CATEGORIZATION_PROMPT},
                {"role": "user", "content": content}
            ],
            response_format={"type": "json_object"},
            temperature=0.1  # Low temperature for more consistent results
        )
        
        # Parse the response
        try:
            content = response.choices[0].message.content
            # Handle both array and object responses
            if isinstance(content, str):
                content = content.strip()
                if content.startswith('[') and content.endswith(']'):
                    # Standard JSON array response
                    result = json.loads(content)
                else:
                    # Try to extract JSON from the response text using various patterns
                    import re
                    # Try to find an array pattern first
                    json_match = re.search(r'\[.*\]', content, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group(0))
                    else:
                        # Try to find an object pattern if no array found
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            result = json.loads(json_match.group(0))
                        else:
                            # Fall back to parsing the whole content
                            try:
                                result = json.loads(content)
                            except:
                                # If all parsing fails, try to extract individual categories
                                categories = []
                                # Extract id-category pairs using regex
                                id_cat_matches = re.findall(r'id["\s:]+(\d+).*?category["\s:]+([a-z]+)', content, re.IGNORECASE | re.DOTALL)
                                for id_str, cat in id_cat_matches:
                                    try:
                                        market_id = int(id_str)
                                        categories.append({
                                            "id": market_id,
                                            "ai_category": cat.lower(),
                                            "confidence": 0.7
                                        })
                                    except:
                                        pass
                                
                                if categories:
                                    result = categories
                                else:
                                    # Last resort: manual text parsing
                                    lines = content.split('\n')
                                    for i, line in enumerate(lines):
                                        if ':' in line:
                                            parts = line.split(':')
                                            if len(parts) >= 2 and any(cat in parts[1].lower() for cat in VALID_CATEGORIES):
                                                for cat in VALID_CATEGORIES:
                                                    if cat in parts[1].lower():
                                                        categories.append({
                                                            "id": i,
                                                            "ai_category": cat,
                                                            "confidence": 0.6
                                                        })
                                                        break
                                    
                                    if categories:
                                        result = categories
                                    else:
                                        raise ValueError("Could not extract categories from response")
            else:
                result = content
                
            if not isinstance(result, list):
                # If we got an object instead of an array, wrap it in a list
                if isinstance(result, dict):
                    result = [result]
                else:
                    raise ValueError(f"Expected list result, got {type(result)}")
                    
            logger.info(f"Successfully received categorization for {len(result)} markets")
            
            # Validate categories in results
            for item in result:
                if isinstance(item, dict):
                    # Handle various field naming conventions in the API response
                    if "ai_category" not in item:
                        # Try other common field names
                        if "category" in item:
                            item["ai_category"] = item["category"]
                        elif "market_category" in item:
                            item["ai_category"] = item["market_category"]
                        
                    # Ensure category is lowercase and valid
                    if "ai_category" in item:
                        item["ai_category"] = item["ai_category"].lower()
                        # Validate against VALID_CATEGORIES
                        if item["ai_category"] not in VALID_CATEGORIES:
                            # Try to find closest match
                            for valid_cat in VALID_CATEGORIES:
                                if valid_cat in item["ai_category"] or item["ai_category"] in valid_cat:
                                    item["ai_category"] = valid_cat
                                    break
                            else:
                                # Default to news if no match found
                                item["ai_category"] = "news"
            
            # Create a map for quick lookups
            categorization_map = {}
            for item in result:
                if isinstance(item, dict) and 'id' in item:
                    item_id = item['id']
                    # Handle both string and int IDs
                    try:
                        categorization_map[int(item_id)] = item
                    except ValueError:
                        # If ID can't be converted to int, store with original key
                        categorization_map[item_id] = item
            
            # Process each market
            for i, market in enumerate(markets):
                # Skip markets already processed (those with no question)
                if any(m.get('id') == market.get('id') for m in categorized_markets):
                    continue
                
                market_copy = market.copy()
                
                # Look up the categorization
                if i in categorization_map:
                    category_info = categorization_map[i]
                    category = category_info.get('category', '').lower()
                    confidence = category_info.get('confidence', 0)
                    
                    # Validate category
                    if category in VALID_CATEGORIES:
                        market_copy['ai_category'] = category
                        # Flag for manual review if confidence is low
                        market_copy['needs_manual_categorization'] = confidence < 0.7
                        logger.info(f"Categorized market {i+1}/{total_markets}: '{market.get('question', '')[:30]}...' as {category}")
                    else:
                        # Use keyword-based categorization if model returns invalid category
                        question = market.get('question', '')
                        category = keyword_based_categorization(question)
                        market_copy['ai_category'] = category
                        market_copy['needs_manual_categorization'] = True
                        logger.warning(f"Invalid category from API, using keyword fallback for market {i+1} - {category}")
                else:
                    # Use keyword-based categorization if market not in results
                    question = market.get('question', '')
                    category = keyword_based_categorization(question)
                    market_copy['ai_category'] = category
                    market_copy['needs_manual_categorization'] = True
                    logger.warning(f"Market {i+1} not found in API results, using keyword fallback - {category}")
                
                categorized_markets.append(market_copy)
                
        except json.JSONDecodeError:
            logger.error("Failed to parse API response as JSON, falling back to keyword categorization")
            # API returned invalid JSON, use keyword categorization
            for i, market in enumerate(markets):
                # Skip markets already processed
                if any(m.get('id') == market.get('id') for m in categorized_markets):
                    continue
                
                question = market.get('question', '')
                category = keyword_based_categorization(question) if question else "news"
                
                market_copy = market.copy()
                market_copy['ai_category'] = category
                market_copy['needs_manual_categorization'] = True
                logger.info(f"API response error, using keyword categorization for market {i+1} - {category}")
                
                categorized_markets.append(market_copy)
                
    except Exception as e:
        logger.error(f"Error in batch categorization: {str(e)}")
        # Use keyword-based categorization for all remaining markets
        for i, market in enumerate(markets):
            # Skip markets already processed
            if any(m.get('id') == market.get('id') for m in categorized_markets):
                continue
            
            question = market.get('question', '')
            category = keyword_based_categorization(question) if question else "news"
            
            market_copy = market.copy()
            market_copy['ai_category'] = category
            market_copy['needs_manual_categorization'] = True
            logger.info(f"API error, using keyword categorization for market {i+1} - {category}")
            
            categorized_markets.append(market_copy)
    
    # Log category distribution
    categories = {}
    for market in categorized_markets:
        category = market.get('ai_category')
        if category in categories:
            categories[category] += 1
        else:
            categories[category] = 1
    
    logger.info("Category distribution:")
    for category, count in categories.items():
        percentage = count / len(categorized_markets) * 100
        logger.info(f"  - {category}: {count} markets ({percentage:.1f}%)")
    
    return categorized_markets