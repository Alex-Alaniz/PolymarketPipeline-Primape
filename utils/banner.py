"""
Banner generation utilities for the Polymarket pipeline.
"""
import os
import json
import logging
import tempfile
import requests
from typing import Dict, Any, Optional
from datetime import datetime

from config import OPENAI_API_KEY, TMP_DIR

logger = logging.getLogger("banner_generator")

class BannerGenerator:
    """Generates banner images for markets using OpenAI DALL-E."""
    
    def __init__(self):
        """Initialize the banner generator."""
        if OPENAI_API_KEY:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("OpenAI SDK not installed")
                self.client = None
            except Exception as e:
                logger.error(f"Error initializing OpenAI client: {str(e)}")
                self.client = None
        else:
            logger.warning("OPENAI_API_KEY not set, banner generation will be mocked")
            self.client = None
        
        # Ensure tmp directory exists
        os.makedirs(TMP_DIR, exist_ok=True)
    
    def generate_banner(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Generate a banner image for a market using OpenAI.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Path to generated banner image, or None if failed
        """
        # Get market info
        market_id = market.get("id")
        question = market.get("question", "Unknown market")
        category = market.get("category", "General")
        sub_category = market.get("sub_category", "Other")
        
        # Create output path
        output_path = os.path.join(TMP_DIR, f"{market_id}.png")
        
        # If OpenAI client is available, use it to generate an image
        if self.client:
            try:
                # Create prompt for DALL-E
                prompt = self._create_banner_prompt(question, category, sub_category)
                logger.info(f"Generating banner for market {market_id} with prompt: {prompt}")
                
                # Generate image with DALL-E
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                )
                
                # Get image URL
                image_url = response.data[0].url
                
                # Download image
                if self._download_image(image_url, output_path):
                    logger.info(f"Banner generated for market {market_id} at {output_path}")
                    return output_path
                else:
                    logger.error(f"Failed to download banner image for market {market_id}")
                    return self._generate_placeholder_banner(market)
                
            except Exception as e:
                logger.error(f"Error generating banner for market {market_id}: {str(e)}")
                return self._generate_placeholder_banner(market)
        else:
            # If no OpenAI client, generate a placeholder banner
            logger.warning(f"OpenAI client not available, generating placeholder banner for market {market_id}")
            return self._generate_placeholder_banner(market)
    
    def _create_banner_prompt(self, question: str, category: str, sub_category: str) -> str:
        """
        Create a prompt for DALL-E based on market information.
        
        Args:
            question (str): Market question
            category (str): Market category
            sub_category (str): Market sub-category
            
        Returns:
            str: Prompt for DALL-E
        """
        # Extract key elements from the question
        # Remove "Will" and question mark
        topic = question.replace("Will ", "").rstrip("?")
        
        # Create base prompt
        base_prompt = f"Create a professional, high-quality banner image for a prediction market about '{topic}'. The image should be visually appealing, suitable for a financial prediction platform, with subtle visual elements relevant to {category}/{sub_category}."
        
        # Add category-specific guidance
        if category.lower() == "sports":
            prompt = f"{base_prompt} Include subtle sports imagery related to {sub_category}, but keep it clean and professional without any team logos or specific player likenesses. Use a color scheme that evokes the sport."
        elif category.lower() == "crypto":
            prompt = f"{base_prompt} Include abstract visual elements suggesting cryptocurrency or blockchain technology, with a modern, tech-oriented aesthetic. Avoid specific crypto logos or symbols."
        elif category.lower() == "politics":
            prompt = f"{base_prompt} Create a dignified image suggesting politics or governance without partisan symbols or specific political figures. Use a balanced, neutral color scheme."
        elif category.lower() == "entertainment":
            prompt = f"{base_prompt} Design an eye-catching banner related to {sub_category} entertainment, using visual elements suggesting the subject without specific copyrighted images or celebrities."
        else:
            prompt = f"{base_prompt} Use a clean, professional style with abstract elements suggesting the subject matter. The image should be suitable for a financial predictions platform."
        
        # Add general styling guidelines
        prompt += " The image should be high contrast with good legibility when text is overlaid, avoiding cluttered backgrounds or overly busy designs. Render in a photorealistic style with professional lighting and composition."
        
        return prompt
    
    def _download_image(self, url: str, output_path: str) -> bool:
        """
        Download an image from a URL.
        
        Args:
            url (str): URL of the image
            output_path (str): Path to save the image
            
        Returns:
            bool: Success status
        """
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
            else:
                logger.error(f"Failed to download image: HTTP {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            return False
    
    def _generate_placeholder_banner(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Generate a placeholder banner when OpenAI is not available.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Path to placeholder banner, or None if failed
        """
        try:
            # Get market info
            market_id = market.get("id")
            question = market.get("question", "Unknown market")
            category = market.get("category", "General")
            
            # Create output path
            output_path = os.path.join(TMP_DIR, f"{market_id}.png")
            
            # For now, we'll create a very simple placeholder file (empty PNG)
            with open(output_path, 'wb') as f:
                # A minimal valid PNG file (1x1 transparent pixel)
                f.write(bytes.fromhex('89504e470d0a1a0a0000000d494844520000000100000001010300000025db56ca00000003504c5445000000a77a3dda0000000174524e530040e6d8660000000a4944415408d76360000000020001e221bc330000000049454e44ae426082'))
            
            logger.info(f"Created placeholder banner for market {market_id} at {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error creating placeholder banner: {str(e)}")
            return None