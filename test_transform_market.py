"""
Test script for transforming a real-world API response.
"""
import json
import requests
import logging
from utils.market_transformer import MarketTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Main test function that fetches real data and tests transformation.
    """
    logger.info("Fetching real market data from Polymarket API")
    
    # Use default API endpoint to fetch event-grouped markets
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    params = {
        "cat": "soccer",
        "q": "Champions League",
        "limit": 10
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()
        
        logger.info(f"Fetched {len(markets)} markets from API")
        
        # Print first market as example
        if markets:
            logger.info("Example of first market:")
            first_market = markets[0]
            logger.info(f"Question: {first_market.get('question')}")
            logger.info(f"Events: {[e.get('title') for e in first_market.get('events', [])]}")
            logger.info(f"EventId: {first_market.get('eventId')}")
            logger.info(f"Has outcomes: {'outcomes' in first_market}")
            logger.info(f"Has event_outcomes: {'event_outcomes' in first_market}")
            
            # Save first few markets to file for reference
            with open("sample_markets.json", "w") as f:
                json.dump(markets[:3], f, indent=2)
            logger.info("Saved sample markets to sample_markets.json")
        
        # Transform markets
        transformer = MarketTransformer()
        transformed = transformer.transform_markets(markets)
        
        logger.info(f"Transformed {len(transformed)} markets")
        logger.info(f"Multi-option markets: {sum(1 for m in transformed if m.get('is_multiple_option', False))}")
        
        # Print multi-option markets
        for market in transformed:
            if market.get("is_multiple_option", False):
                logger.info("\nFound multi-option market:")
                logger.info(f"Question: {market.get('question')}")
                outcomes = json.loads(market.get("outcomes", "[]")) if isinstance(market.get("outcomes"), str) else market.get("outcomes", [])
                logger.info(f"Options: {outcomes}")
                option_images = json.loads(market.get("option_images", "{}")) if isinstance(market.get("option_images"), str) else market.get("option_images", {})
                logger.info(f"Option images: {option_images}")
                
                # Check for generic options like "Another Team" or "Barcelona"
                for option in outcomes:
                    is_generic = "another" in option.lower() or "other" in option.lower() or option == "Barcelona"
                    if is_generic:
                        image = option_images.get(option)
                        event_image = market.get("event_image")
                        logger.info(f"GENERIC OPTION: {option}")
                        logger.info(f"Image: {image}")
                        logger.info(f"Event image: {event_image}")
                        logger.info(f"Using event image? {image == event_image}")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")

if __name__ == "__main__":
    main()