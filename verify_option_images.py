"""
Verify that option images are correctly mapped for all options in a market.
This script helps debug the issue with Barcelona in Champions League market.
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

def reset_processed_markets():
    """Reset the database and start fresh for testing."""
    conn = None
    try:
        # Connect to the database
        database_url = os.environ.get('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        
        # Create a cursor
        with conn.cursor() as cur:
            # Delete all processed markets
            cur.execute("TRUNCATE processed_markets")
            conn.commit()
            logger.info("Reset processed_markets table")
            
        return True
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        return False
    finally:
        if conn:
            conn.close()

def inspect_market(condition_id: str) -> Dict[str, Any]:
    """
    Inspect a market's options and images.
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
            
            # Parse the raw data
            raw_data = result['raw_data']
            
            # Parse outcomes and option_images
            outcomes_str = raw_data.get('outcomes', '[]')
            option_images_str = raw_data.get('option_images', '{}')
            event_image = raw_data.get('event_image')
            
            try:
                outcomes = json.loads(outcomes_str) if isinstance(outcomes_str, str) else outcomes_str
                option_images = json.loads(option_images_str) if isinstance(option_images_str, str) else option_images_str
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON: {e}")
                outcomes = []
                option_images = {}
            
            # Display market information
            logger.info(f"Market: {raw_data.get('question', 'Unknown')}")
            logger.info(f"Event image: {event_image}")
            logger.info(f"Total outcomes: {len(outcomes)}")
            logger.info(f"Total option images: {len(option_images)}")
            
            # Check for missing options
            missing_options = []
            for option in outcomes:
                if option not in option_images:
                    missing_options.append(option)
            
            if missing_options:
                logger.warning(f"Missing images for options: {missing_options}")
            else:
                logger.info("All options have images assigned")
            
            # Display all options and their images
            logger.info("\nOptions and their images:")
            for i, option in enumerate(outcomes, 1):
                image = option_images.get(option, "MISSING")
                is_event_image = image == event_image
                
                status = "✓" if image != "MISSING" else "✗"
                if is_event_image:
                    status += " (using event image)"
                
                logger.info(f"{i}. {option}: {status}")
                logger.info(f"   Image: {image}")
            
            return {
                "market": raw_data.get('question', 'Unknown'),
                "outcomes": outcomes,
                "option_images": option_images,
                "event_image": event_image,
                "missing_options": missing_options
            }
            
    except Exception as e:
        logger.error(f"Error inspecting market: {e}")
        return {}
    finally:
        if conn:
            conn.close()

def main():
    """Main function to test the fix."""
    # Check if we should reset the database
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        reset_processed_markets()
        logger.info("Database reset. Run the pipeline to fetch new markets.")
        return
    
    # Markets to check
    markets = [
        ("Champions League Winner", "group_12585"),
        ("La Liga Winner", "group_12672")
    ]
    
    for market_name, condition_id in markets:
        logger.info(f"\n{'=' * 60}")
        logger.info(f"Inspecting {market_name} ({condition_id})")
        logger.info(f"{'=' * 60}")
        
        result = inspect_market(condition_id)
        
        if not result:
            logger.error(f"Failed to inspect {market_name}")
            continue
        
        # Report success or failure
        if result.get("missing_options"):
            logger.error(f"❌ {market_name} has missing images for options: {result['missing_options']}")
        else:
            logger.info(f"✅ {market_name} has images for all options")
        
        logger.info(f"{'=' * 60}\n")

if __name__ == "__main__":
    main()