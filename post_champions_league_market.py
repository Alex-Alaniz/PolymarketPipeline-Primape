"""
Script to post Champions League market to Slack for verification.
"""
import json
import logging
import os
import sys
from typing import Dict, Any, List

import psycopg2
from psycopg2.extras import RealDictCursor
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Slack configuration
SLACK_BOT_TOKEN = os.environ.get('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.environ.get('SLACK_CHANNEL_ID')

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

def post_market_to_slack(market_data: Dict[str, Any]) -> bool:
    """
    Post a market to Slack for approval.
    """
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logger.error("Slack credentials not available")
        return False
    
    try:
        # Initialize Slack client
        client = WebClient(token=SLACK_BOT_TOKEN)
        
        # Extract key information
        question = market_data.get('question', 'Unknown market')
        condition_id = market_data.get('id', 'Unknown ID')
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
                    "text": "Multiple-Choice Market for Approval",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{question}*"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*ID:* {condition_id}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Type:* Multiple-Choice"
                    }
                ]
            }
        ]
        
        # Add event banner image if available
        if event_image:
            blocks.append({
                "type": "image",
                "title": {
                    "type": "plain_text",
                    "text": "Event Banner",
                    "emoji": True
                },
                "image_url": event_image,
                "alt_text": "Event Banner"
            })
        
        # Add options section
        if outcomes:
            options_text = "*Options:*\n"
            for i, option in enumerate(outcomes, 1):
                options_text += f"{i}. {option}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": options_text
                }
            })
            
            # Add images for each option
            for option in outcomes:
                image_url = option_images.get(option)
                if image_url:
                    # Check if this is a generic option
                    generic_keywords = ["another team", "other team", "field", "other", "barcelona"]
                    is_generic = any(keyword in option.lower() for keyword in generic_keywords)
                    
                    # Add appropriate label
                    option_label = f"Image for {option}"
                    if is_generic:
                        option_label += " (Generic Option)"
                    
                    blocks.append({
                        "type": "image",
                        "title": {
                            "type": "plain_text",
                            "text": option_label,
                            "emoji": True
                        },
                        "image_url": image_url,
                        "alt_text": option_label
                    })
                    
                    # Add verification info for generic options
                    if is_generic:
                        status = "✅ FIXED" if image_url != event_image else "❌ ISSUE"
                        message = "Generic option correctly using team image" if image_url != event_image else "Generic option still using event banner image"
                        
                        blocks.append({
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{status}:* {message}"
                            }
                        })
        
        # Add divider and approval instructions
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please react with :white_check_mark: to approve or :x: to reject this market."
            }
        })
        
        # Post the message to Slack
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=f"Multiple-Choice Market for Approval: {question}",
            blocks=blocks
        )
        
        message_ts = response['ts']
        logger.info(f"Posted message to Slack, timestamp: {message_ts}")
        
        # Add approval/rejection reactions
        client.reactions_add(
            channel=SLACK_CHANNEL_ID,
            name="white_check_mark",
            timestamp=message_ts
        )
        client.reactions_add(
            channel=SLACK_CHANNEL_ID,
            name="x",
            timestamp=message_ts
        )
        
        logger.info("Added approval/rejection reactions")
        
        # Update the database to mark this market as posted
        conn = None
        try:
            database_url = os.environ.get('DATABASE_URL')
            conn = psycopg2.connect(database_url)
            
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE processed_markets SET posted = TRUE, message_id = %s WHERE condition_id = %s",
                    (message_ts, condition_id)
                )
                conn.commit()
                logger.info(f"Updated database to mark market {condition_id} as posted")
        except Exception as e:
            logger.error(f"Error updating database: {e}")
        finally:
            if conn:
                conn.close()
        
        return True
        
    except SlackApiError as e:
        logger.error(f"Error posting to Slack: {e}")
        return False

def main():
    """Main function to post Champions League market"""
    # Champions League market ID
    market_id = 'group_12585'
    
    logger.info(f"Fetching Champions League market with ID: {market_id}")
    market_data = get_market_data(market_id)
    
    if not market_data:
        logger.error(f"Failed to fetch market data for {market_id}")
        return False
    
    logger.info(f"Found market: {market_data.get('question', 'Unknown market')}")
    
    # Post to Slack
    success = post_market_to_slack(market_data)
    
    if success:
        logger.info(f"Successfully posted Champions League market to Slack")
        return True
    else:
        logger.error(f"Failed to post Champions League market to Slack")
        return False

if __name__ == "__main__":
    main()