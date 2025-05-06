"""
Script to post a specific market to Slack for verification.
"""
import json
import logging
import os
import sys
from typing import Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import required modules
from utils.messaging import post_slack_message, add_reaction_to_message

def get_market_data(condition_id: str) -> Dict[str, Any]:
    """
    Get market data from the database for a specific condition ID.
    """
    conn = None
    try:
        # Connect to the database
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        
        # Create a cursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Execute the query
            cur.execute(
                "SELECT raw_data FROM processed_markets WHERE condition_id = %s",
                (condition_id,)
            )
            
            # Fetch the result
            result = cur.fetchone()
            
            if not result:
                logger.error(f"No market found with condition_id: {condition_id}")
                return {}
            
            # Parse the raw data from JSON
            raw_data = result['raw_data']
            
            return raw_data
            
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def post_market_for_verification(condition_id: str) -> bool:
    """
    Post a specific market to Slack for verification.
    """
    # Get market data
    market_data = get_market_data(condition_id)
    
    if not market_data:
        logger.error("Failed to get market data")
        return False
    
    try:
        # Extract key information
        question = market_data.get('question', 'Unknown question')
        outcomes_str = market_data.get('outcomes', '[]')
        option_images_str = market_data.get('option_images', '{}')
        event_image = market_data.get('event_image')
        
        # Parse JSON strings
        try:
            outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
            option_images = json.loads(option_images_str) if isinstance(option_images_str, str) else option_images_str
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON: {e}")
            outcomes = []
            option_images = {}
        
        # Create message blocks
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🔎 Image Fix Verification",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Market:* {question}"
                }
            },
            {
                "type": "section", 
                "text": {
                    "type": "mrkdwn",
                    "text": f"*ID:* {condition_id}"
                }
            }
        ]
        
        # Add event image if available
        if event_image:
            blocks.append({
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Event Image",
                    "emoji": True
                },
                "image_url": event_image,
                "alt_text": "Event Image"
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Event Image:* {event_image}"
                }
            })
        
        # Add options section
        if outcomes:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Options:*"
                }
            })
            
            # Add details for each option
            for option in outcomes:
                image_url = option_images.get(option)
                
                # Determine if this is a generic option
                generic_keywords = ["another team", "other team", "field", "other", "barcelona"]
                is_generic = any(keyword in option.lower() for keyword in generic_keywords)
                
                # Format the option text
                option_text = f"*{option}*"
                if is_generic:
                    option_text += " _(Generic option)_"
                
                # Create section for this option
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{option_text}\nImage: {image_url}"
                    }
                })
                
                # Add the image if available
                if image_url:
                    blocks.append({
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": f"Image for {option}",
                            "emoji": True
                        },
                        "image_url": image_url,
                        "alt_text": f"Image for {option}"
                    })
                
                # Add verification check
                if is_generic and image_url and image_url != event_image:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "✅ *FIXED:* Generic option correctly using non-event image"
                        }
                    })
                elif is_generic and image_url and image_url == event_image:
                    blocks.append({
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "❌ *ISSUE:* Generic option still using event image"
                        }
                    })
            
        # Post the message to Slack
        message_text = f"Verifying image fix for market: {question}"
        result = post_slack_message(message_text, blocks)
        
        if result:
            logger.info(f"Successfully posted market {condition_id} to Slack")
            return True
        else:
            logger.error(f"Failed to post market {condition_id} to Slack")
            return False
        
    except Exception as e:
        logger.error(f"Error posting market for verification: {e}")
        return False

def main():
    """Main function"""
    # Get markets to verify
    markets_to_verify = ['group_12585', 'group_12672']  # Champions League & La Liga
    
    success_count = 0
    
    for market_id in markets_to_verify:
        logger.info(f"Posting market {market_id} for verification")
        success = post_market_for_verification(market_id)
        
        if success:
            success_count += 1
    
    logger.info(f"Posted {success_count}/{len(markets_to_verify)} markets for verification")

if __name__ == "__main__":
    main()