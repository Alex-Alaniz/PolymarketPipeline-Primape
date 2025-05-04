"""
Utility module for generating banner images for markets using OpenAI's DALL-E.
"""
import os
import logging
import time
import base64
from typing import Optional, Dict, Any, Tuple
import requests
from datetime import datetime
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

# Set up logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in environment variables. Image generation will fail.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_prompt_for_market(market: Dict[str, Any]) -> str:
    """
    Generate a detailed prompt for DALL-E based on market data.
    
    Args:
        market: Market data dictionary
        
    Returns:
        str: Detailed prompt for image generation
    """
    # Extract key information
    question = market.get('question', '')
    market_type = market.get('type', 'binary')
    category = market.get('category', 'general')
    
    # Base prompt template
    base_prompt = (
        f"Create a clean, visually striking banner image representing "
        f"a prediction market about: '{question}'. "
    )
    
    # Add category-specific elements
    category_elements = {
        'politics': "Include subtle political imagery like government buildings, flags, or voting symbols. Use a formal, news-like style.",
        'sports': "Use dynamic sports imagery with action elements. Include relevant equipment or stadium visuals.",
        'entertainment': "Create a glamorous, eye-catching design with entertainment industry symbols like film reels, cameras, or spotlights.",
        'finance': "Use clean, professional financial imagery with graphs, charts, or currency symbols. Employ a blue and green color scheme.",
        'technology': "Create a futuristic, tech-oriented image with circuit patterns, digital elements, or modern device silhouettes.",
        'science': "Include scientific symbols, lab equipment, or data visualizations. Use a clean, precise visual style.",
        'crypto': "Incorporate blockchain imagery, cryptocurrency symbols, or abstract digital patterns. Use a modern tech aesthetic."
    }
    
    category_prompt = category_elements.get(category.lower(), "Use a clean, professional design with neutral colors and abstract elements representing uncertainty and prediction.")
    
    # Add market type elements
    type_elements = {
        'binary': "The image should clearly represent a yes/no or true/false dichotomy, perhaps with contrasting elements.",
        'multiple-choice': "The design should subtly hint at multiple possible outcomes or choices.",
        'scalar': "Include elements that suggest a range or spectrum of possible values."
    }
    
    type_prompt = type_elements.get(market_type.lower(), "")
    
    # Final formatting instructions
    format_instructions = (
        "The image should be high quality, suitable for a professional trading platform. "
        "Use a 16:9 aspect ratio with clean typography and minimal text. "
        "Avoid including any text that directly quotes the market question. "
        "The style should be modern, digital, and somewhat abstract - avoid photorealistic human faces or controversial imagery."
    )
    
    # Combine all elements
    full_prompt = f"{base_prompt} {category_prompt} {type_prompt} {format_instructions}"
    
    return full_prompt

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_image(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Generate an image using OpenAI's DALL-E model.
    
    Args:
        prompt: Text prompt for image generation
        
    Returns:
        Optional[Dict[str, Any]]: Response from OpenAI API or None if failed
    """
    try:
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        
        # Generate image using DALL-E 3
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024",
            quality="standard",
            response_format="url"
        )
        
        return {
            "url": response.data[0].url,
            "revised_prompt": response.data[0].revised_prompt
        }
    except Exception as e:
        logger.error(f"Error generating image: {str(e)}")
        return None

def download_image(url: str, save_path: str) -> bool:
    """
    Download image from URL and save to path.
    
    Args:
        url: Image URL
        save_path: Path to save the image
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # Download the image
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save to file
        with open(save_path, 'wb') as f:
            f.write(response.content)
            
        return True
    except Exception as e:
        logger.error(f"Error downloading image: {str(e)}")
        return False

def generate_market_banner(market: Dict[str, Any], output_dir: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Generate a banner image for a market and save it.
    
    Args:
        market: Market data dictionary
        output_dir: Directory to save the image
        
    Returns:
        Tuple[bool, Optional[str], Optional[str]]: Success status, path to saved image, and error message
    """
    try:
        # Generate a unique filename based on market ID and timestamp
        market_id = market.get('id') or market.get('condition_id')
        if not market_id:
            return False, None, "Market ID not found in market data"
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{market_id}_{timestamp}.png"
        save_path = os.path.join(output_dir, filename)
        
        # Generate prompt
        prompt = generate_prompt_for_market(market)
        logger.info(f"Generated prompt for market {market_id}: {prompt[:100]}...")
        
        # Generate image
        image_result = generate_image(prompt)
        if not image_result or 'url' not in image_result:
            return False, None, "Failed to generate image"
        
        # Download and save the image
        download_success = download_image(image_result['url'], save_path)
        if not download_success:
            return False, None, "Failed to download and save image"
        
        logger.info(f"Successfully generated and saved banner image for market {market_id} to {save_path}")
        return True, save_path, None
        
    except Exception as e:
        error_msg = f"Error generating banner for market: {str(e)}"
        logger.error(error_msg)
        return False, None, error_msg