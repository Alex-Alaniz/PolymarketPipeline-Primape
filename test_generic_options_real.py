"""
Test script to find and process real market data with generic options
to verify the fix for generic option image handling.
"""
import json
import logging
import os
from typing import Dict, List, Any, Set

# Import Slack client from the existing utils
from utils.messaging import post_slack_message, add_reaction_to_message

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

# Generic options keywords to look for
GENERIC_OPTIONS = [
    "another team", 
    "other team", 
    "another club", 
    "other club", 
    "barcelona", 
    "field", 
    "other"
]

def fetch_markets_with_generic_options() -> List[Dict[str, Any]]:
    """
    Fetch markets from Polymarket API and filter to find ones with generic options
    in Champions League or other competitions.
    """
    # Base URL for Polymarket API
    base_url = "https://gamma-api.polymarket.com"
    
    # Fetch Sports markets first, as they're most likely to have generic options
    sports_url = f"{base_url}/markets?category=sports&limit=100"
    
    logger.info(f"Fetching sports markets from Polymarket API: {sports_url}")
    try:
        response = requests.get(sports_url)
        response.raise_for_status()
        markets = response.json()["markets"]
        logger.info(f"Successfully fetched {len(markets)} sports markets")
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []
    
    # Find markets mentioning Champions League, World Cup, or other competitions
    # that might have generic options like "Another Team" or "Barcelona"
    target_keywords = [
        "champions league", 
        "world cup", 
        "euro", 
        "europa league",
        "uefa",
        "league winner",
        "cup winner"
    ]
    
    filtered_markets = []
    event_ids_seen = set()
    
    for market in markets:
        # Check if market title or question contains any target keyword
        market_question = market.get("question", "").lower()
        if any(keyword in market_question for keyword in target_keywords):
            # Add to filtered list
            filtered_markets.append(market)
            
            # Track event IDs to find related markets
            if "events" in market and len(market["events"]) > 0:
                for event in market["events"]:
                    event_ids_seen.add(event.get("id"))
    
    logger.info(f"Found {len(filtered_markets)} markets matching target keywords")
    logger.info(f"Found {len(event_ids_seen)} unique event IDs")
    
    # Second pass: find all markets that share the same event IDs
    # These are likely to be part of the same multi-option market
    if event_ids_seen:
        logger.info("Fetching additional markets that share events with our target markets")
        all_event_markets = []
        
        # Fetch additional markets for each event ID
        for event_id in event_ids_seen:
            try:
                event_url = f"{base_url}/markets?eventId={event_id}&limit=50"
                response = requests.get(event_url)
                response.raise_for_status()
                event_markets = response.json()["markets"]
                all_event_markets.extend(event_markets)
                logger.info(f"Fetched {len(event_markets)} markets for event ID {event_id}")
            except Exception as e:
                logger.error(f"Error fetching markets for event ID {event_id}: {e}")
        
        # Add unique markets not already in our filtered list
        existing_ids = {m.get("id") for m in filtered_markets}
        for market in all_event_markets:
            if market.get("id") not in existing_ids:
                filtered_markets.append(market)
                existing_ids.add(market.get("id"))
        
        logger.info(f"Total markets after including related markets: {len(filtered_markets)}")
    
    # Look for markets that might contain generic options
    markets_with_generic_options = []
    
    for market in filtered_markets:
        market_question = market.get("question", "").lower()
        # Check if the market question contains any generic option keywords
        if any(generic_option in market_question for generic_option in GENERIC_OPTIONS):
            markets_with_generic_options.append(market)
    
    logger.info(f"Found {len(markets_with_generic_options)} markets that explicitly mention generic options")
    
    # Return the combined list - markets with target keywords + generic options
    return filtered_markets

def post_to_slack(markets: List[Dict[str, Any]]) -> bool:
    """Post markets to Slack for verification"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.error("Slack credentials not available - cannot post to Slack")
        return False
    
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Create a summary message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔎 Generic Option Image Fix Test",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Found {len(markets)} markets that might include generic options. Posting each market to allow verification of proper image assignment."
                }
            },
            {
                "type": "divider"
            }
        ]
        
        # Post the summary message
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text="Generic Option Image Fix Test",
            blocks=blocks
        )
        
        logger.info(f"Posted summary to Slack, message timestamp: {response['ts']}")
        
        # Post each market individually for inspection
        for i, market in enumerate(markets, 1):
            question = market.get("question", "Unknown question")
            market_id = market.get("id", "Unknown ID")
            has_events = "events" in market and len(market["events"]) > 0
            
            events_info = ""
            event_image = None
            
            if has_events:
                events_count = len(market["events"])
                events_info = f"{events_count} events"
                if events_count > 0 and "image" in market["events"][0]:
                    event_image = market["events"][0]["image"]
            
            # Create blocks for this market
            market_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Market {i}/{len(markets)}*: {question}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*ID:* {market_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Events:* {events_info}"
                        }
                    ]
                }
            ]
            
            # Add market image if available
            if "image" in market and market["image"]:
                market_blocks.append({
                    "type": "image",
                    "title": {
                        "type": "plain_text",
                        "text": "Market Image",
                        "emoji": True
                    },
                    "image_url": market["image"],
                    "alt_text": "Market Image"
                })
            
            # Add event image if available and different from market image
            if event_image and event_image != market.get("image"):
                market_blocks.append({
                    "type": "image",
                    "title": {
                        "type": "plain_text",
                        "text": "Event Image",
                        "emoji": True
                    },
                    "image_url": event_image,
                    "alt_text": "Event Image"
                })
            
            # Add a divider
            market_blocks.append({"type": "divider"})
            
            # Post this market
            client.chat_postMessage(
                channel=SLACK_CHANNEL_ID,
                text=f"Market {i}/{len(markets)}: {question}",
                blocks=market_blocks
            )
            
            logger.info(f"Posted market {i}/{len(markets)}: {question}")
        
        # Post a final verification message
        verification_blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "After all these markets are transformed, generic options like 'Another Team' and 'Barcelona' should use team-specific images instead of event banner images. Please run the following command to verify:"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "```\npython verify_option_images.py\n```"
                }
            }
        ]
        
        client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text="Verification Instructions",
            blocks=verification_blocks
        )
        
        return True
        
    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e}")
        return False

def main():
    """Main function"""
    logger.info("Starting test to find markets with generic options")
    
    # Fetch markets that might have generic options
    markets = fetch_markets_with_generic_options()
    
    if not markets:
        logger.warning("No suitable markets found for testing")
        return
    
    logger.info(f"Found {len(markets)} potential markets for testing")
    
    # Post markets to Slack for verification
    success = post_to_slack(markets)
    
    if success:
        logger.info("Successfully posted markets to Slack for verification")
    else:
        logger.error("Failed to post markets to Slack")

if __name__ == "__main__":
    main()