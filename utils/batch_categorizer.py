"""
Batch Market Categorizer

This module implements a batch categorization approach for markets,
sending multiple markets to the OpenAI API in a single request.
This is more efficient than sending individual requests for each market.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional

# Import OpenAI
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("batch_categorizer")

# Initialize the OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY environment variable not set. Categorization will fail.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def batch_categorize_markets(markets: List[Dict[str, Any]], batch_size: int = 10) -> List[Dict[str, Any]]:
    """
    Categorize multiple markets in a single batch request to OpenAI.
    
    Args:
        markets: List of market dictionaries with 'question' and 'description' fields
        batch_size: Maximum number of markets to include in a single API request
        
    Returns:
        List[Dict[str, Any]]: The input markets with additional 'ai_category' field
    """
    if not markets:
        logger.warning("No markets provided for categorization")
        return []
    
    # Process in batches to avoid hitting API limits
    all_categorized_markets = []
    for i in range(0, len(markets), batch_size):
        batch = markets[i:i+batch_size]
        logger.info(f"Processing batch {i // batch_size + 1} of {len(markets) // batch_size + 1} ({len(batch)} markets)")
        
        try:
            categorized_batch = _categorize_batch(batch)
            all_categorized_markets.extend(categorized_batch)
        except Exception as e:
            logger.error(f"Error processing batch {i // batch_size + 1}: {str(e)}")
            # Return the original batch without categorization
            all_categorized_markets.extend(batch)
    
    return all_categorized_markets

def _categorize_batch(markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Send a batch of markets to OpenAI for categorization.
    
    Args:
        markets: List of market dictionaries to categorize
        
    Returns:
        List[Dict[str, Any]]: The input markets with additional 'ai_category' field
    """
    # Prepare the input for the API
    markets_json = json.dumps(markets)
    
    # Define the system message to instruct the model
    system_message = """
    You are an expert at categorizing prediction markets.

    Categorize each market into one of these categories:
    - politics (elections, laws, political events)
    - crypto (cryptocurrency prices, adoption, events)
    - sports (sports matches, tournaments, player performance)
    - business (company performance, stocks, economic indicators) 
    - tech (product launches, technical milestones, technological achievements)
    - entertainment (movies, TV, celebrities, awards)
    - culture (social trends, cultural events)
    - science (scientific discoveries, space missions, medical breakthroughs)
    - world (global events, international relations, diplomacy)
    - news (current events, breaking news)
    
    For each market in the provided list, analyze the question and description to determine the most appropriate category.
    Output only valid JSON following the format of the input, but with an additional 'ai_category' field for each market.
    Also add an 'ai_confidence' field with a value between 0.0 and 1.0 indicating your confidence in the categorization.
    
    IMPORTANT: Keep all original fields intact in the response.
    """
    
    # Create prompt to the model
    user_message = f"""
    Categorize the following prediction markets:
    
    {markets_json}
    
    Return the complete list with added 'ai_category' and 'ai_confidence' fields for each market.
    Response must be valid JSON in the same format as the input.
    """
    
    # Call the OpenAI API with gpt-4o-mini for efficiency
    # The newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    # do not change this unless explicitly requested by the user
    try:
        completion = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o-mini for efficiency
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=4000
        )
    
        # Extract and parse the response
        response_content = completion.choices[0].message.content
        result = json.loads(response_content)
        
        # Check if the result contains a list of markets
        if isinstance(result, dict) and "0" in result:
            # Handle case where the JSON is an object with numeric keys instead of an array
            categorized_markets = [result[str(i)] for i in range(len(markets))]
        elif isinstance(result, list):
            # Direct list
            categorized_markets = result
        elif isinstance(result, dict) and "markets" in result:
            # Result wrapped in a container
            categorized_markets = result["markets"]
        else:
            # Unexpected format
            logger.error(f"Unexpected response format: {result}")
            return markets
        
        # Ensure we got the same number of markets back
        if len(categorized_markets) != len(markets):
            logger.warning(f"Expected {len(markets)} categorized markets but got {len(categorized_markets)}")
            
            # If we got fewer markets than we sent, pad the response with the original markets
            if len(categorized_markets) < len(markets):
                for i in range(len(categorized_markets), len(markets)):
                    markets[i]["ai_category"] = "news"  # Default category
                    markets[i]["ai_confidence"] = 0.5   # Default confidence
                categorized_markets = categorized_markets + markets[len(categorized_markets):]
            else:
                # If we got more markets than we sent, truncate the response
                categorized_markets = categorized_markets[:len(markets)]
        
        # Validate that each market has an ai_category
        for i, market in enumerate(categorized_markets):
            if not market.get("ai_category"):
                # Add a default category if none was provided
                categorized_markets[i]["ai_category"] = "news"
                categorized_markets[i]["ai_confidence"] = 0.5
                logger.warning(f"Market {market.get('id', i)} missing ai_category, assigned default")
        
        return categorized_markets
        
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {str(e)}")
        # Add default categories as fallback
        for market in markets:
            market["ai_category"] = "news"
            market["ai_confidence"] = 0.5
        return markets
        
# Test function for this module
def test_batch_categorizer():
    """
    Test the batch categorizer with sample markets.
    """
    test_markets = [
        {
            "id": "1",
            "question": "Will the price of Bitcoin exceed $100,000 by the end of 2025?",
            "description": "This market resolves to YES if the price of Bitcoin exceeds $100,000 at any point before December 31, 2025."
        },
        {
            "id": "2",
            "question": "Will the Democratic candidate win the 2024 US Presidential Election?",
            "description": "This market resolves to YES if the Democratic candidate wins the 2024 US Presidential Election in November 2024."
        },
        {
            "id": "3",
            "question": "Will Manchester United win the Premier League in the 2024-2025 season?",
            "description": "This market resolves to YES if Manchester United wins the Premier League in the 2024-2025 season."
        }
    ]
    
    categorized_markets = batch_categorize_markets(test_markets)
    
    logger.info("Test results:")
    for market in categorized_markets:
        logger.info(f"Market: {market['question']}")
        logger.info(f"Category: {market.get('ai_category', 'Unknown')}")
        logger.info(f"Confidence: {market.get('ai_confidence', 'Unknown')}")
        logger.info("---")
    
    return categorized_markets

if __name__ == "__main__":
    test_batch_categorizer()