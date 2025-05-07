"""
End-to-end test to verify our fix for the image handling issue.
This script:
1. Fetches real market data from Polymarket API
2. Processes it through the transformer
3. Posts a sample to Slack for review
4. Shows detailed image assignment for any generic options
"""
import json
import os
import logging
import requests
from typing import Dict, Any, List
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from utils.market_transformer import MarketTransformer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

def fetch_real_markets():
    """Fetch real market data from Polymarket API"""
    logger.info("Fetching real market data from Polymarket API")
    
    # Use two categories to increase chance of finding multi-option markets
    categories = ["soccer", "sports"]
    all_markets = []
    
    for category in categories:
        url = "https://gamma-api.polymarket.com/markets?closed=false&archived=false&active=true&limit=100"
        params = {
            "cat": category,
            "limit": 50
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            markets = response.json()
            logger.info(f"Fetched {len(markets)} markets from category '{category}'")
            all_markets.extend(markets)
        except Exception as e:
            logger.error(f"Error fetching markets from category '{category}': {e}")
    
    logger.info(f"Fetched total of {len(all_markets)} markets from all categories")
    return all_markets

def transform_markets(markets):
    """Transform markets using our MarketTransformer"""
    logger.info(f"Transforming {len(markets)} markets")
    transformer = MarketTransformer()
    transformed = transformer.transform_markets(markets)
    logger.info(f"Transformed into {len(transformed)} markets")
    return transformed

def find_multi_option_markets(transformed_markets):
    """Find multi-option markets in the transformed data"""
    multi_option_markets = []
    
    for market in transformed_markets:
        if market.get("is_multiple_option", False):
            multi_option_markets.append(market)
            continue
            
        # Also check if outcomes contains more than 2 options (for legacy format)
        if market.get("outcomes"):
            outcomes = market.get("outcomes")
            if isinstance(outcomes, str):
                try:
                    decoded = json.loads(outcomes)
                    if len(decoded) > 2:
                        # Add is_multiple_option flag
                        market["is_multiple_option"] = True
                        multi_option_markets.append(market)
                except:
                    pass
            elif isinstance(outcomes, list) and len(outcomes) > 2:
                # Add is_multiple_option flag
                market["is_multiple_option"] = True
                multi_option_markets.append(market)
    
    logger.info(f"Found {len(multi_option_markets)} multi-option markets")
    return multi_option_markets

def check_generic_options(multi_option_markets):
    """Check for generic options in multi-option markets"""
    # Generic options we're looking for
    generic_options = [
        "another team", "other team", "another club", 
        "other club", "barcelona", "field", "other"
    ]
    
    markets_with_generic_options = []
    
    for market in multi_option_markets:
        # Get the outcomes
        outcomes = market.get("outcomes", "[]")
        if isinstance(outcomes, str):
            try:
                decoded_outcomes = json.loads(outcomes)
            except:
                continue
        else:
            decoded_outcomes = outcomes
        
        # Check if any outcome is a generic option
        has_generic = False
        for outcome in decoded_outcomes:
            is_generic = any(generic_term.lower() in outcome.lower() for generic_term in generic_options)
            if is_generic:
                has_generic = True
                break
                
        if has_generic:
            markets_with_generic_options.append(market)
    
    logger.info(f"Found {len(markets_with_generic_options)} markets with generic options")
    return markets_with_generic_options

def analyze_generic_option_images(markets_with_generic_options):
    """Analyze image assignments for generic options"""
    # Generic options we're looking for
    generic_options = [
        "another team", "other team", "another club", 
        "other club", "barcelona", "field", "other"
    ]
    
    results = []
    
    for market in markets_with_generic_options:
        # Get the outcomes and images
        outcomes = market.get("outcomes", "[]")
        if isinstance(outcomes, str):
            try:
                decoded_outcomes = json.loads(outcomes)
            except:
                continue
        else:
            decoded_outcomes = outcomes
        
        option_images = market.get("option_images", "{}")
        if isinstance(option_images, str):
            try:
                decoded_images = json.loads(option_images)
            except:
                continue
        else:
            decoded_images = option_images
        
        event_image = market.get("event_image")
        
        # Check each option
        market_analysis = {
            "market_id": market.get("id"),
            "question": market.get("question"),
            "options": [],
            "has_issues": False
        }
        
        for option in decoded_outcomes:
            is_generic = any(generic_term.lower() in option.lower() for generic_term in generic_options)
            image = decoded_images.get(option)
            is_event_image = (image == event_image)
            
            option_data = {
                "option": option,
                "is_generic": is_generic,
                "image": image,
                "is_event_image": is_event_image,
                "issue": (is_generic and is_event_image)
            }
            
            market_analysis["options"].append(option_data)
            
            if option_data["issue"]:
                market_analysis["has_issues"] = True
        
        results.append(market_analysis)
    
    # Count issues
    markets_with_issues = [m for m in results if m["has_issues"]]
    logger.info(f"Found {len(markets_with_issues)} markets with generic option image issues")
    
    return results

def post_to_slack(results):
    """Post analysis results to Slack for review"""
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.error("Slack credentials not available - skipping Slack posting")
        return False
    
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Create a message
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "Generic Option Image Fix Verification",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Analyzed {len(results)} markets with generic options"
                }
            }
        ]
        
        # Add issue count
        markets_with_issues = [m for m in results if m["has_issues"]]
        if markets_with_issues:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ Found {len(markets_with_issues)} markets with generic option image issues"
                }
            })
        else:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ No generic option image issues found! The fix is working properly!"
                }
            })
        
        # Add a divider
        blocks.append({"type": "divider"})
        
        # Add market details (up to 3 markets for brevity)
        for market in results[:3]:
            # Add market header
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Market:* {market['question']}"
                }
            })
            
            # Add options
            options_text = ""
            for option in market["options"]:
                status = "✅" if not option["issue"] else "❌"
                generic_tag = "GENERIC" if option["is_generic"] else "Standard"
                event_image_tag = "USING EVENT IMAGE" if option["is_event_image"] else "using unique image"
                
                options_text += f"{status} {generic_tag} option '{option['option']}': {event_image_tag}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": options_text
                }
            })
            
            # Add a divider
            blocks.append({"type": "divider"})
        
        # Post the message
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text="Generic Option Image Fix Verification",
            blocks=blocks
        )
        
        logger.info(f"Posted analysis to Slack, message timestamp: {response['ts']}")
        return True
        
    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e}")
        return False

def main():
    """Main verification function"""
    logger.info("=== VERIFYING IMAGE FIX END-TO-END ===")
    
    # Fetch real market data
    markets = fetch_real_markets()
    
    if not markets:
        logger.error("No markets fetched, cannot proceed with verification")
        return
    
    # Transform markets
    transformed_markets = transform_markets(markets)
    
    # Find multi-option markets
    multi_option_markets = find_multi_option_markets(transformed_markets)
    
    if not multi_option_markets:
        logger.warning("No multi-option markets found, cannot verify fix")
        return
    
    # Check for markets with generic options
    markets_with_generic_options = check_generic_options(multi_option_markets)
    
    if not markets_with_generic_options:
        logger.warning("No markets with generic options found, cannot verify fix")
        return
    
    # Analyze image assignments
    results = analyze_generic_option_images(markets_with_generic_options)
    
    # Post to Slack
    slack_posted = post_to_slack(results)
    
    # Print a summary
    markets_with_issues = [m for m in results if m["has_issues"]]
    if markets_with_issues:
        logger.error(f"❌ Found {len(markets_with_issues)} markets with generic option image issues")
        for market in markets_with_issues:
            logger.error(f"  Market: {market['question']}")
            for option in market["options"]:
                if option["issue"]:
                    logger.error(f"    ❌ {option['option']} is using event image")
    else:
        logger.info("✅ No generic option image issues found! The fix is working properly!")
    
    logger.info("=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    main()