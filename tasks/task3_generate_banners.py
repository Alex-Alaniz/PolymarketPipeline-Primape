"""
Task 3: Generate Banners with OpenAI

This module is responsible for generating banner images for approved markets
using OpenAI's DALL-E API and posting them for final approval.
"""

import os
import sys
import json
import logging
import time
import base64
import requests
from io import BytesIO
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime, timezone

# Import utilities
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.messaging import MessagingClient
from config import DATA_DIR, TMP_DIR, OPENAI_API_KEY

logger = logging.getLogger("task3")

def run_task(messaging_client: MessagingClient, task2_results: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Run Task 3: Generate banner images and post for final approval
    
    Args:
        messaging_client: MessagingClient instance for interacting with Slack/Discord
        task2_results: Results from Task 2 containing approved markets
        
    Returns:
        Tuple[List[Dict[str, Any]], Dict[str, Any]]: Markets with banners and task statistics
    """
    logger.info("Starting Task 3: Generating banner images with OpenAI")
    
    # Start the clock for this task
    start_time = time.time()
    
    # Dictionary to store statistics
    stats = {
        "task": "task3_generate_banners",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "markets_processed": 0,
        "banners_generated": 0,
        "banners_posted": 0,
        "market_list": [],
        "errors": [],
        "status": "running"
    }
    
    try:
        # Validate OpenAI API key
        if not OPENAI_API_KEY:
            error_msg = "OPENAI_API_KEY is required for banner generation"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            stats["status"] = "failed"
            return [], stats
        
        # Extract market list from task2 results
        if not task2_results or "market_list" not in task2_results:
            logger.error("Invalid task2 results: missing market_list")
            stats["errors"].append("Invalid task2 results: missing market_list")
            stats["status"] = "failed"
            return [], stats
        
        # Get the market list
        markets = task2_results.get("market_list", [])
        
        # Filter only approved markets
        approved_markets = [m for m in markets if m.get("status") == "approved"]
        
        if not approved_markets:
            logger.warning("No approved markets to generate banners for")
            stats["status"] = "success"  # Still a success, just nothing to do
            return [], stats
        
        # Create output directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
        
        # Process each approved market
        markets_with_banners = []
        
        for market in approved_markets:
            market_id = market.get("id", "unknown")
            question = market.get("question", "Unknown question")
            
            # Update stats
            stats["markets_processed"] += 1
            
            # Create market entry for statistics
            market_stats = {
                "market_id": market_id,
                "question": question,
                "banner_path": None,
                "message_id": None,
                "status": "pending"
            }
            
            try:
                # Generate banner image
                logger.info(f"Generating banner for market {market_id}: {question}")
                banner_path = generate_banner_image(market_id, question)
                
                if banner_path:
                    logger.info(f"Banner generated successfully: {banner_path}")
                    market_stats["banner_path"] = banner_path
                    market_stats["status"] = "generated"
                    stats["banners_generated"] += 1
                    
                    # Post banner for final approval
                    final_message = format_final_approval_message(market, banner_path)
                    message_id = messaging_client.post_image(final_message, banner_path)
                    
                    if message_id:
                        # Add reactions for approval/rejection
                        messaging_client.add_reactions(message_id, ["white_check_mark", "x"])
                        
                        # Update market stats
                        market_stats["message_id"] = message_id
                        market_stats["status"] = "posted"
                        stats["banners_posted"] += 1
                        
                        # Add to markets with banners
                        markets_with_banners.append({
                            "id": market_id,
                            "question": question,
                            "banner_path": banner_path,
                            "message_id": message_id,
                            "status": "posted"
                        })
                        
                        logger.info(f"Banner posted for final approval (message ID: {message_id})")
                    else:
                        logger.error(f"Failed to post banner for market {market_id}")
                        market_stats["status"] = "post_failed"
                        stats["errors"].append(f"Failed to post banner for market {market_id}")
                else:
                    logger.error(f"Failed to generate banner for market {market_id}")
                    market_stats["status"] = "generation_failed"
                    stats["errors"].append(f"Failed to generate banner for market {market_id}")
            
            except Exception as e:
                logger.error(f"Error processing market {market_id}: {str(e)}")
                market_stats["status"] = "error"
                stats["errors"].append(f"Error processing market {market_id}: {str(e)}")
            
            # Add market stats to the stats list
            stats["market_list"].append(market_stats)
            
            # Sleep to avoid rate limiting
            time.sleep(1)
        
        # Save markets with banners to file for persistence
        banners_file = os.path.join(TMP_DIR, f"task3_banners_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(banners_file, 'w') as f:
            json.dump({"markets": markets_with_banners}, f, indent=2)
        
        # Calculate task duration
        stats["duration"] = time.time() - start_time
        
        # Final status
        if stats["banners_posted"] > 0:
            stats["status"] = "success"
        else:
            stats["status"] = "failed"
        
        logger.info(f"Task 3 completed: {stats['banners_generated']} banners generated, {stats['banners_posted']} posted for approval")
        return markets_with_banners, stats
        
    except Exception as e:
        # Handle any errors
        logger.error(f"Error in Task 3: {str(e)}")
        stats["errors"].append(f"Task error: {str(e)}")
        stats["status"] = "failed"
        stats["duration"] = time.time() - start_time
        return [], stats

def generate_banner_image(market_id: str, question: str) -> Optional[str]:
    """
    Generate a banner image using OpenAI's DALL-E
    
    Args:
        market_id: Market ID
        question: Market question
        
    Returns:
        Optional[str]: Path to the generated image, or None if generation failed
    """
    try:
        # Prepare for OpenAI API
        api_key = OPENAI_API_KEY
        api_url = "https://api.openai.com/v1/images/generations"
        
        # Create a prompt for the banner image
        prompt_text = f"Create a visually appealing banner image for a prediction market with the question: '{question}'. Use bold, clean text and relevant imagery. Suitable for web display. Make it look professional and engaging. Include the question text in the image."
        
        # Set up API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        data = {
            "model": "dall-e-3",
            "prompt": prompt_text,
            "n": 1,
            "size": "1024x1024"
        }
        
        # Make the request to OpenAI
        logger.info(f"Sending request to OpenAI for market {market_id}")
        response = requests.post(api_url, headers=headers, json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            image_url = response_data["data"][0]["url"]
            
            # Download the image
            image_response = requests.get(image_url)
            
            if image_response.status_code == 200:
                # Create a safe filename from the market ID
                safe_filename = market_id.replace("/", "_").replace(":", "_").replace("?", "_")
                image_path = os.path.join(TMP_DIR, f"{safe_filename}.png")
                
                # Save the image
                with open(image_path, 'wb') as f:
                    f.write(image_response.content)
                
                logger.info(f"Banner image saved to {image_path}")
                return image_path
            else:
                logger.error(f"Failed to download image: {image_response.status_code}")
                return None
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"Error generating banner image: {str(e)}")
        return None

def format_final_approval_message(market: Dict[str, Any], banner_path: str) -> str:
    """
    Format a message for final approval with banner
    
    Args:
        market: Market data
        banner_path: Path to the banner image
        
    Returns:
        str: Formatted message text
    """
    market_id = market.get("id", "unknown")
    question = market.get("question", "Unknown question")
    
    message = (
        f"*FINAL APPROVAL NEEDED*\n\n"
        f"*Question:* {question}\n"
        f"*Market ID:* {market_id}\n\n"
        f"Please review the banner image above and react with :white_check_mark: to approve or :x: to reject."
    )
    
    return message