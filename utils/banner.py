"""
Banner generation utilities for the Polymarket pipeline.
"""
import os
import json
import time
import requests
from typing import Dict, Any, Optional

from config import OPENAI_API_KEY, TMP_DIR

# Try to import OpenAI
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = bool(OPENAI_API_KEY)
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai package not installed, image generation disabled")

class BannerGenerator:
    """Generates banner images for markets using OpenAI DALL-E."""
    
    def __init__(self):
        """Initialize the banner generator."""
        # Create tmp directory if it doesn't exist
        os.makedirs(TMP_DIR, exist_ok=True)
        
        # Initialize OpenAI client if available
        self.openai_client = None
        if OPENAI_AVAILABLE:
            try:
                self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
                print("OpenAI client initialized")
            except Exception as e:
                print(f"Error initializing OpenAI client: {str(e)}")
    
    def generate_banner(self, market: Dict[str, Any]) -> Optional[str]:
        """
        Generate a banner image for a market using OpenAI.
        
        Args:
            market (Dict[str, Any]): Market data
            
        Returns:
            Optional[str]: Path to generated banner image, or None if failed
        """
        if not self.openai_client:
            print("OpenAI client not available for banner generation")
            return self._generate_placeholder_banner(market)
        
        try:
            # Extract market information
            market_id = market.get("id")
            question = market.get("question")
            category = market.get("category", "Other")
            sub_category = market.get("sub_category", "Other")
            
            # Create a prompt for DALL-E
            prompt = self._create_banner_prompt(question, category, sub_category)
            print(f"Generated prompt for market {market_id}: {prompt}")
            
            # Generate image using DALL-E
            response = self.openai_client.images.generate(
                model="dall-e-3",  # Using the latest DALL-E model available
                prompt=prompt,
                n=1,
                size="1024x1024",  # Standard banner size
                quality="standard",
                response_format="url"
            )
            
            # Get image URL
            image_url = response.data[0].url
            
            # Download image
            output_path = os.path.join(TMP_DIR, f"{market_id}.png")
            self._download_image(image_url, output_path)
            
            return output_path
            
        except Exception as e:
            print(f"Error generating banner: {str(e)}")
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
        # Basic template for the prompt
        base_prompt = """Create a professional, visually appealing banner image for a prediction market about: "{question}". 
The style should be sleek, modern and suitable for a financial/betting platform.
The image should be symbolic or metaphorical rather than literal, with high-quality graphics.
Avoid using any text in the image. Use a cohesive color scheme that fits the subject matter.
The image should be appropriate for a professional audience and have a clean, polished look."""
        
        # Customize based on category
        category_specifics = ""
        if category.lower() == "politics":
            category_specifics = """Use subtle political imagery that is neutral and not partisan.
Consider motifs like capitol buildings, flags, vote ballots, or other neutral political symbols."""
        elif category.lower() == "sports":
            category_specifics = """Use dynamic sports imagery related to {sub_category}.
Include relevant equipment, venues, or abstract representations of the sport."""
        elif category.lower() == "crypto":
            category_specifics = """Use imagery reflecting blockchain, digital technology, and finance.
Consider abstract representations of cryptocurrencies with a high-tech aesthetic."""
        elif category.lower() == "entertainment":
            category_specifics = """Use imagery related to {sub_category} entertainment.
For movies or TV, consider film-related motifs; for music, use musical elements."""
        elif category.lower() == "finance":
            category_specifics = """Use clean, professional financial imagery.
Consider graphs, markets, stock symbols, or abstract representations of economic concepts."""
        
        # Combine prompts
        full_prompt = base_prompt + "\n" + category_specifics
        
        # Format with actual values
        return full_prompt.format(
            question=question,
            category=category,
            sub_category=sub_category
        )
    
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
                print(f"Failed to download image: HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"Error downloading image: {str(e)}")
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
            market_id = market.get("id")
            
            # For demo/testing purposes, we'll just create a simple placeholder
            # In a real implementation, this would generate a basic image using PIL or similar
            
            # Create a placeholder file path
            output_path = os.path.join(TMP_DIR, f"{market_id}.png")
            
            # Since we can't generate an actual image here,
            # we'll make note of it in the logs
            print(f"Would generate placeholder banner for market {market_id}")
            
            # For testing, we'll use a placeholder URL if available
            # or return None to indicate failure
            return output_path
            
        except Exception as e:
            print(f"Error generating placeholder banner: {str(e)}")
            return None