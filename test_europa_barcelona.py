"""
Test script to specifically check Europa League and Barcelona options.

This script directly targets the problematic markets:
1. Europa League Winner - "Another Team" option
2. Champions League - Barcelona option
"""
import json
import logging
import os
import requests
import sys
from typing import List, Dict, Any, Optional

from utils.market_transformer import MarketTransformer
# Removed import for post_message_with_reactions as it's not available

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global constants
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

def fetch_europa_league_markets() -> List[Dict[str, Any]]:
    """Fetch Europa League markets from Polymarket"""
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    params = {"limit": 30, "q": "Europa League", "cat": "soccer"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()
        logger.info(f"Fetched {len(markets)} Europa League markets")
        
        # Look for markets specifically about Europa League Winner
        europa_winner_markets = []
        for market in markets:
            question = market.get("question", "").lower()
            if "europa league" in question and "win" in question:
                europa_winner_markets.append(market)
        
        logger.info(f"Found {len(europa_winner_markets)} Europa League Winner markets")
        return europa_winner_markets
    
    except Exception as e:
        logger.error(f"Error fetching Europa League markets: {e}")
        return []

def fetch_champions_league_markets() -> List[Dict[str, Any]]:
    """Fetch Champions League markets from Polymarket"""
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    params = {"limit": 30, "q": "Champions League", "cat": "soccer"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()
        logger.info(f"Fetched {len(markets)} Champions League markets")
        
        # Look for markets specifically about Champions League with Barcelona
        barcelona_markets = []
        for market in markets:
            question = market.get("question", "").lower()
            if "champions league" in question and "barcelona" in question:
                barcelona_markets.append(market)
        
        if not barcelona_markets:
            # If no explicit Barcelona markets, get all Champions League markets
            for market in markets:
                question = market.get("question", "").lower()
                if "champions league" in question and "win" in question:
                    barcelona_markets.append(market)
        
        logger.info(f"Found {len(barcelona_markets)} Champions League markets with Barcelona or Winner")
        return barcelona_markets
    
    except Exception as e:
        logger.error(f"Error fetching Champions League markets: {e}")
        return []

def print_detailed_market_info(market: Dict[str, Any], title: str):
    """Print detailed information about a market for analysis"""
    logger.info(f"\n{'=' * 80}")
    logger.info(f"ANALYSIS OF {title}")
    logger.info(f"{'=' * 80}")
    
    # Basic market info
    logger.info(f"Market ID: {market.get('id')}")
    logger.info(f"Question: {market.get('question')}")
    
    # Check if multi-option
    is_multi = market.get("is_multiple_option", False)
    logger.info(f"Is multi-option: {is_multi}")
    
    if is_multi:
        # Get options
        outcomes = json.loads(market.get("outcomes", "[]"))
        logger.info(f"Options ({len(outcomes)}): {outcomes}")
        
        # Get option images
        option_images = json.loads(market.get("option_images", "{}"))
        
        # Check event image
        event_image = market.get("event_image")
        logger.info(f"Event image: {event_image}")
        
        # Check each option's image
        for i, option in enumerate(outcomes):
            image_url = option_images.get(option)
            using_event_image = (image_url == event_image) if image_url and event_image else False
            
            logger.info(f"\nOption {i+1}: {option}")
            logger.info(f"  Image: {image_url}")
            if using_event_image:
                logger.info(f"  WARNING: Using event image!")
            else:
                logger.info(f"  OK: Has unique image")
    
    logger.info(f"{'=' * 80}\n")

def post_market_to_slack(market: Dict[str, Any], title: str):
    """Post a market to Slack for visual inspection"""
    # Skip Slack posting in this test script - just log the analysis
    logger.info(f"Would post {title} to Slack for visual inspection (skipped)")
    
    # Get options
    if market.get("is_multiple_option"):
        outcomes = json.loads(market.get("outcomes", "[]"))
        option_images = json.loads(market.get("option_images", "{}"))
        event_image = market.get("event_image")
        
        # Log option images
        logger.info(f"Checking images for {len(outcomes)} options")
        for option in outcomes:
            image_url = option_images.get(option)
            if image_url:
                using_event_image = (image_url == event_image)
                status = "USING EVENT IMAGE" if using_event_image else "Has unique image"
                logger.info(f"Option '{option}': {status}")

def analyze_and_fix_europa_league(markets: List[Dict[str, Any]]):
    """Analyze and fix Europa League 'Another Team' option issue"""
    if not markets:
        logger.error("No Europa League markets found")
        return
    
    # Transform markets with current code
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(markets)
    
    # Find multi-option Europa League Winner market
    europa_winner = None
    for market in transformed:
        if (market.get("is_multiple_option") and 
            "europa league" in market.get("question", "").lower() and
            "winner" in market.get("question", "").lower()):
            europa_winner = market
            break
    
    if not europa_winner:
        logger.error("No multi-option Europa League Winner market found")
        return
    
    # Print detailed info about the market
    print_detailed_market_info(europa_winner, "EUROPA LEAGUE WINNER MARKET (BEFORE FIX)")
    
    # Check if "Another Team" uses event banner
    outcomes = json.loads(europa_winner.get("outcomes", "[]"))
    option_images = json.loads(europa_winner.get("option_images", "{}"))
    event_image = europa_winner.get("event_image")
    
    # Look for "Another Team" option
    another_team_option = None
    for option in outcomes:
        if "another" in option.lower() or "other" in option.lower():
            another_team_option = option
            break
    
    if not another_team_option:
        logger.warning("No 'Another Team' option found in Europa League Winner market")
        return
    
    # Check if "Another Team" uses event banner
    using_event_image = False
    if another_team_option in option_images:
        using_event_image = (option_images[another_team_option] == event_image)
    
    if not using_event_image:
        logger.info("'Another Team' option already has a unique image, no fix needed")
        return
    
    logger.info(f"Found 'Another Team' option '{another_team_option}' using event banner image")
    
    # Post market to Slack for visual inspection
    post_market_to_slack(europa_winner, "EUROPA LEAGUE WINNER (BEFORE FIX)")

def analyze_and_fix_champions_league(markets: List[Dict[str, Any]]):
    """Analyze and fix Champions League Barcelona option issue"""
    if not markets:
        logger.error("No Champions League markets found")
        return
    
    # Transform markets with current code
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(markets)
    
    # Find multi-option Champions League market
    champions_league = None
    for market in transformed:
        if (market.get("is_multiple_option") and 
            "champions league" in market.get("question", "").lower()):
            champions_league = market
            break
    
    if not champions_league:
        logger.error("No multi-option Champions League market found")
        return
    
    # Print detailed info about the market
    print_detailed_market_info(champions_league, "CHAMPIONS LEAGUE MARKET (BEFORE FIX)")
    
    # Check if Barcelona uses event banner
    outcomes = json.loads(champions_league.get("outcomes", "[]"))
    option_images = json.loads(champions_league.get("option_images", "{}"))
    event_image = champions_league.get("event_image")
    
    # Look for Barcelona option
    barcelona_option = None
    for option in outcomes:
        if "barcelona" in option.lower():
            barcelona_option = option
            break
    
    if not barcelona_option:
        logger.warning("No Barcelona option found in Champions League market")
        return
    
    # Check if Barcelona uses event banner
    using_event_image = False
    if barcelona_option in option_images:
        using_event_image = (option_images[barcelona_option] == event_image)
    
    if not using_event_image:
        logger.info("Barcelona option already has a unique image, no fix needed")
        return
    
    logger.info(f"Found Barcelona option '{barcelona_option}' using event banner image")
    
    # Post market to Slack for visual inspection
    post_market_to_slack(champions_league, "CHAMPIONS LEAGUE (BEFORE FIX)")

def fetch_la_liga_markets() -> List[Dict[str, Any]]:
    """Fetch La Liga markets from Polymarket"""
    url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
    params = {"limit": 30, "q": "La Liga", "cat": "soccer"}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        markets = response.json()
        logger.info(f"Fetched {len(markets)} La Liga markets")
        
        # Look for markets specifically about La Liga Winner
        la_liga_winner_markets = []
        for market in markets:
            question = market.get("question", "").lower()
            if "la liga" in question and "win" in question:
                la_liga_winner_markets.append(market)
        
        logger.info(f"Found {len(la_liga_winner_markets)} La Liga Winner markets")
        return la_liga_winner_markets
    
    except Exception as e:
        logger.error(f"Error fetching La Liga markets: {e}")
        return []

def analyze_and_fix_la_liga(markets: List[Dict[str, Any]]):
    """Analyze and fix La Liga 'Another Team' option issue"""
    if not markets:
        logger.error("No La Liga markets found")
        return
    
    # Transform markets with current code
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(markets)
    
    # Find multi-option La Liga Winner market
    la_liga_winner = None
    for market in transformed:
        if (market.get("is_multiple_option") and 
            "la liga" in market.get("question", "").lower() and
            "winner" in market.get("question", "").lower()):
            la_liga_winner = market
            break
    
    if not la_liga_winner:
        logger.error("No multi-option La Liga Winner market found")
        return
    
    # Print detailed info about the market
    print_detailed_market_info(la_liga_winner, "LA LIGA WINNER MARKET (BEFORE FIX)")
    
    # Check if "Another Team" uses event banner
    outcomes = json.loads(la_liga_winner.get("outcomes", "[]"))
    option_images = json.loads(la_liga_winner.get("option_images", "{}"))
    event_image = la_liga_winner.get("event_image")
    
    # Look for "Another Team" option
    another_team_option = None
    for option in outcomes:
        if "another" in option.lower() or "other" in option.lower():
            another_team_option = option
            break
    
    if not another_team_option:
        logger.warning("No 'Another Team' option found in La Liga Winner market")
        return
    
    # Check if "Another Team" uses event banner
    using_event_image = False
    if another_team_option in option_images:
        using_event_image = (option_images[another_team_option] == event_image)
    
    if not using_event_image:
        logger.info("'Another Team' option already has a unique image, no fix needed")
        return
    
    logger.info(f"Found 'Another Team' option '{another_team_option}' using event banner image")
    
    # Log analysis data
    post_market_to_slack(la_liga_winner, "LA LIGA WINNER (BEFORE FIX)")

def main():
    """Main function to run option image tests"""
    logger.info("Starting option image tests for problematic markets")
    
    # Analyze Europa League Winner 'Another Team' issue
    europa_markets = fetch_europa_league_markets()
    analyze_and_fix_europa_league(europa_markets)
    
    # Analyze Champions League Barcelona issue
    champions_markets = fetch_champions_league_markets()
    analyze_and_fix_champions_league(champions_markets)
    
    # Analyze La Liga Winner 'Another Team' issue
    la_liga_markets = fetch_la_liga_markets()
    analyze_and_fix_la_liga(la_liga_markets)
    
    logger.info("Tests completed")

if __name__ == "__main__":
    main()