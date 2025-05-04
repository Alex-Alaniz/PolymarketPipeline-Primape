"""
Banner generator utility for Polymarket markets.

This module generates banner images for Polymarket markets using OpenAI's DALL-E API.
"""
import os
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Import image generation module
from utils.image_generation import generate_market_banner

# Set up logging
logger = logging.getLogger(__name__)

class BannerGenerator:
    """
    Banner generator for Polymarket markets.
    
    This class handles the generation of banner images for Polymarket markets
    using OpenAI's DALL-E API, and optionally updates the database to track generation status.
    """
    
    def __init__(self):
        """Initialize the banner generator."""
        self.tmp_dir = os.environ.get("TMP_DIR", "tmp")
        self.output_dir = os.path.join(self.tmp_dir, "banners")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Check if OpenAI API key is available
        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not found in environment variables. Banner generation will fail.")
    
    def generate_banner(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Generate a banner image for a market.
        
        Args:
            market: Market data dictionary
            
        Returns:
            Optional[str]: Path to the generated image, or None if generation failed
        """
        try:
            market_id = market.get("id") or market.get("condition_id")
            if not market_id:
                logger.error("Market ID not found in market data")
                return None
            
            # Generate banner
            success, image_path, error = generate_market_banner(market, self.output_dir)
            
            if not success or not image_path:
                logger.error(f"Failed to generate banner for market {market_id}: {error}")
                return None
            
            logger.info(f"Successfully generated banner for market {market_id} at {image_path}")
            
            # Update database if available
            try:
                self.update_database(market_id, image_path)
            except Exception as e:
                logger.warning(f"Failed to update database for market {market_id}: {str(e)}")
            
            return image_path
        
        except Exception as e:
            logger.error(f"Error generating banner: {str(e)}")
            return None
    
    def update_database(self, market_id: str, image_path: str) -> bool:
        """
        Update the database with banner generation status.
        
        Args:
            market_id: Market ID
            image_path: Path to the generated image
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if we have database access
            from models import db, ProcessedMarket
            from main import app
            
            with app.app_context():
                # Find the market in the database
                market = ProcessedMarket.query.get(market_id)
                if not market:
                    logger.warning(f"Market {market_id} not found in database")
                    return False
                
                # Update image generation status
                market.image_generated = True
                market.image_path = image_path
                market.image_generation_attempts += 1
                market.last_processed = datetime.utcnow()
                
                # Save to database
                db.session.commit()
                
                logger.info(f"Updated database for market {market_id} with image path {image_path}")
                return True
        
        except ImportError:
            logger.warning("Database models not available, skipping database update")
            return False
        
        except Exception as e:
            logger.error(f"Error updating database: {str(e)}")
            return False