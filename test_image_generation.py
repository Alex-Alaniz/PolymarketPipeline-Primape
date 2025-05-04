#!/usr/bin/env python
"""
Test script for the image generation pipeline with OpenAI DALL-E.

This script tests the generation of banner images for Polymarket markets
using OpenAI's DALL-E API and updates the database accordingly.
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Add logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"image_generation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger('image_generation_test')

# Import utilities
from utils.image_generation import generate_market_banner

# Import app and models
from main import app
from models import db, ProcessedMarket, Market

def load_sample_market(file_path):
    """
    Load a sample market from a JSON file.
    
    Args:
        file_path: Path to JSON file containing market data
        
    Returns:
        dict: Market data dictionary
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            
        # If the file contains an array of markets, use the first one
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        elif isinstance(data, dict) and 'markets' in data and len(data['markets']) > 0:
            return data['markets'][0]
        elif isinstance(data, dict):
            return data
        else:
            raise ValueError("No valid market data found in file")
    except Exception as e:
        logger.error(f"Error loading sample market: {str(e)}")
        return None

def test_image_generation(market, output_dir=None):
    """
    Test image generation for a market.
    
    Args:
        market: Market data dictionary
        output_dir: Directory to save images, defaults to 'tmp/test_images'
        
    Returns:
        tuple: (success, image_path, error_message)
    """
    if output_dir is None:
        output_dir = 'tmp/test_images'
        os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Testing image generation for market: {market.get('question', 'Unknown')}")
    
    return generate_market_banner(market, output_dir)

def update_database(market_id, image_path, image_uri=None):
    """
    Update the database with image generation results.
    
    Args:
        market_id: Market ID
        image_path: Path to generated image
        image_uri: Optional URI for the image
        
    Returns:
        bool: Success status
    """
    try:
        with app.app_context():
            # Check if market exists in ProcessedMarket table
            processed_market = ProcessedMarket.query.filter_by(condition_id=market_id).first()
            
            if processed_market:
                # Update existing ProcessedMarket
                processed_market.image_generated = True
                processed_market.image_path = image_path
                processed_market.image_generation_attempts += 1
                processed_market.last_processed = datetime.utcnow()
                
                if image_uri:
                    processed_market.image_uri = image_uri
                    
                db.session.commit()
                logger.info(f"Updated ProcessedMarket record for {market_id}")
            else:
                # Create new ProcessedMarket record
                new_market = ProcessedMarket(
                    condition_id=market_id,
                    question="Test Market",
                    first_seen=datetime.utcnow(),
                    last_processed=datetime.utcnow(),
                    process_count=1,
                    posted=False,
                    approved=True,  # Assume approved for testing
                    approval_date=datetime.utcnow(),
                    image_generated=True,
                    image_path=image_path,
                    image_generation_attempts=1
                )
                
                if image_uri:
                    new_market.image_uri = image_uri
                    
                db.session.add(new_market)
                db.session.commit()
                logger.info(f"Created new ProcessedMarket record for {market_id}")
            
            # Check if market exists in main Market table
            market = Market.query.filter_by(id=market_id).first()
            
            if market:
                # Update existing Market
                market.banner_path = image_path
                
                if image_uri:
                    market.banner_uri = image_uri
                    
                market.updated_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"Updated Market record for {market_id}")
                
            return True
    except Exception as e:
        logger.error(f"Error updating database: {str(e)}")
        return False

def main():
    """
    Main function for testing image generation.
    """
    parser = argparse.ArgumentParser(description='Test image generation for Polymarket markets')
    parser.add_argument('--file', '-f', help='Path to JSON file containing market data', default='data/polymarket_sample.json')
    parser.add_argument('--output-dir', '-o', help='Directory to save generated images', default='tmp/test_images')
    args = parser.parse_args()
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Load sample market
    market = load_sample_market(args.file)
    
    if not market:
        logger.error("Failed to load sample market")
        return 1
    
    logger.info(f"Loaded sample market: {market.get('question', 'Unknown')}")
    
    # Test image generation
    success, image_path, error = test_image_generation(market, args.output_dir)
    
    if not success:
        logger.error(f"Image generation failed: {error}")
        return 1
    
    logger.info(f"Image generation successful: {image_path}")
    
    # Generate a test URI
    image_name = os.path.basename(image_path)
    image_uri = f"/images/{image_name}"
    
    # Update database
    market_id = market.get('id') or market.get('condition_id')
    if not market_id:
        logger.error("Market ID not found in data")
        return 1
    
    db_success = update_database(market_id, image_path, image_uri)
    
    if not db_success:
        logger.error("Failed to update database")
        return 1
    
    logger.info(f"Database updated successfully for market {market_id}")
    logger.info(f"Image generation test completed successfully")
    
    # Print image path for manual verification
    print(f"\nImage generated at: {image_path}")
    print(f"Image URI: {image_uri}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())