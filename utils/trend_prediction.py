"""
AI-powered market trend prediction for Polymarket data.

This module uses historical market data and AI (OpenAI) to predict trends
and provide insights for upcoming markets.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import requests
from openai import OpenAI
import time

from config import DATA_DIR, TMP_DIR, OPENAI_API_KEY

logger = logging.getLogger("trend_prediction")

class MarketTrendPredictor:
    """
    Analyzes historical market data and predicts trends using AI.
    """
    
    def __init__(self):
        """Initialize the market trend predictor"""
        self.data_dir = DATA_DIR
        self.tmp_dir = TMP_DIR
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Create necessary directories
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.tmp_dir, exist_ok=True)
        
    def load_historical_data(self) -> List[Dict[str, Any]]:
        """
        Load historical market data from the data directory.
        
        Returns:
            List[Dict[str, Any]]: List of historical market data
        """
        historical_data = []
        
        try:
            # Check if we have historical data available
            historical_file = os.path.join(self.data_dir, "polymarket_historical_data.json")
            
            if os.path.exists(historical_file):
                with open(historical_file, 'r') as f:
                    historical_data = json.load(f)
                    
                logger.info(f"Loaded {len(historical_data)} historical markets from {historical_file}")
            else:
                logger.warning(f"No historical market data found at {historical_file}")
                
            # Also try to load the most recent raw data
            recent_file = os.path.join(self.data_dir, "polymarket_raw_data.json")
            
            if os.path.exists(recent_file):
                with open(recent_file, 'r') as f:
                    recent_data = json.load(f)
                    
                # Extract markets from the recent data
                recent_markets = []
                if "markets" in recent_data:
                    recent_markets = recent_data["markets"]
                elif "data" in recent_data and "markets" in recent_data["data"]:
                    recent_markets = recent_data["data"]["markets"]
                elif "data" in recent_data:
                    recent_markets = recent_data["data"]
                
                if recent_markets:
                    logger.info(f"Found {len(recent_markets)} recent markets to analyze")
                    # Merge with historical data (avoid duplicates by id)
                    existing_ids = {market.get("id") for market in historical_data}
                    for market in recent_markets:
                        if market.get("id") not in existing_ids:
                            historical_data.append(market)
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error loading historical data: {str(e)}")
            return []
            
    def analyze_markets(self, markets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze markets to identify trends and patterns.
        
        Args:
            markets (List[Dict[str, Any]]): List of markets to analyze
        
        Returns:
            Dict[str, Any]: Analysis results with identified trends
        """
        if not markets:
            logger.warning("No markets to analyze")
            return {"error": "No markets available for analysis"}
            
        try:
            # Extract categories
            categories = {}
            for market in markets:
                category = market.get("category", "Uncategorized")
                if isinstance(category, list) and category:
                    category = category[0]
                    
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
                
            # Sort categories by popularity
            sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
            top_categories = sorted_categories[:5]
            
            # Extract popularity trends (volume, if available)
            volume_trends = {}
            for market in markets:
                category = market.get("category", "Uncategorized")
                if isinstance(category, list) and category:
                    category = category[0]
                
                volume = float(market.get("volume", 0))
                if category not in volume_trends:
                    volume_trends[category] = 0
                volume_trends[category] += volume
            
            # Calculate average market duration
            durations = []
            for market in markets:
                created_at = market.get("createdAt")
                expires_at = market.get("expiresAt")
                
                if created_at and expires_at:
                    try:
                        created_time = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        expires_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        duration = (expires_time - created_time).days
                        durations.append(duration)
                    except (ValueError, TypeError):
                        pass
            
            avg_duration = sum(durations) / len(durations) if durations else None
            
            analysis = {
                "markets_analyzed": len(markets),
                "top_categories": top_categories,
                "volume_trends": volume_trends,
                "average_duration": avg_duration,
                "timestamp": datetime.now().isoformat()
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing markets: {str(e)}")
            return {"error": f"Analysis failed: {str(e)}"}
    
    def generate_trend_preview(self, market: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered trend prediction for a specific market.
        
        Args:
            market (Dict[str, Any]): Market data to generate prediction for
            
        Returns:
            Dict[str, Any]: Trend prediction and insights
        """
        if not OPENAI_API_KEY:
            logger.error("OpenAI API key not available, cannot generate trend prediction")
            return {"error": "OpenAI API key not available"}
            
        try:
            # Load historical data for context
            historical_data = self.load_historical_data()
            
            # Run basic analysis on historical data
            analysis = self.analyze_markets(historical_data)
            
            # Extract key details about the market
            market_question = market.get("question", "")
            market_category = market.get("category", "")
            
            if isinstance(market_category, list) and market_category:
                market_category = market_category[0]
            
            # Create OpenAI prompt
            prompt = f"""
            I need to predict trends and insights for this Polymarket market:
            
            MARKET QUESTION: {market_question}
            CATEGORY: {market_category}
            
            Based on analysis of {len(historical_data)} historical markets:
            - Top categories: {', '.join([f"{cat} ({count})" for cat, count in analysis.get('top_categories', [])])}
            - Average market duration: {analysis.get('average_duration')} days
            
            Please provide:
            1. Expected market interest level (high/medium/low) and why
            2. Estimated trading volume prediction (high/medium/low)
            3. Recommended strategic launch timing
            4. 2-3 related historical events that might influence this market
            5. Potential market volatility factors
            
            Format your response as JSON with these fields:
            {{
                "interest_level": "high/medium/low",
                "interest_reasoning": "explanation",
                "volume_prediction": "high/medium/low",
                "strategic_timing": "best timing recommendation",
                "historical_context": ["event1", "event2", "event3"],
                "volatility_factors": ["factor1", "factor2"]
            }}
            """
            
            # Call OpenAI API
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
                messages=[
                    {"role": "system", "content": "You are a market analysis expert specializing in prediction markets."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
                max_tokens=800
            )
            
            # Parse the response
            prediction_text = response.choices[0].message.content
            prediction = json.loads(prediction_text)
            
            # Add metadata
            prediction["market_id"] = market.get("id")
            prediction["market_question"] = market_question
            prediction["generated_at"] = datetime.now().isoformat()
            prediction["based_on_markets"] = len(historical_data)
            
            # Save prediction to tmp directory for reference
            prediction_file = os.path.join(self.tmp_dir, f"prediction_{market.get('id')}.json")
            with open(prediction_file, 'w') as f:
                json.dump(prediction, f, indent=2)
                
            logger.info(f"Generated trend prediction for market {market.get('id')}")
            return prediction
            
        except Exception as e:
            logger.error(f"Error generating trend prediction: {str(e)}")
            return {"error": f"Prediction failed: {str(e)}"}
    
    def batch_predict_trends(self, markets: List[Dict[str, Any]], limit: int = 5) -> Dict[str, Any]:
        """
        Generate trend predictions for multiple markets.
        
        Args:
            markets (List[Dict[str, Any]]): List of markets to predict trends for
            limit (int): Maximum number of markets to process
            
        Returns:
            Dict[str, Any]: Trend predictions for each market
        """
        if not markets:
            logger.warning("No markets to predict trends for")
            return {"error": "No markets available"}
            
        # Limit the number of markets to process
        markets_to_process = markets[:limit]
        logger.info(f"Generating trend predictions for {len(markets_to_process)} markets")
        
        results = {}
        for market in markets_to_process:
            market_id = market.get("id")
            if not market_id:
                continue
                
            # Generate prediction and add to results
            prediction = self.generate_trend_preview(market)
            results[market_id] = prediction
            
            # Add a small delay to avoid hitting rate limits
            time.sleep(1)
            
        # Add metadata
        results["meta"] = {
            "markets_processed": len(results),
            "total_markets": len(markets),
            "generated_at": datetime.now().isoformat()
        }
        
        # Save batch results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_file = os.path.join(self.data_dir, f"trend_predictions_{timestamp}.json")
        with open(batch_file, 'w') as f:
            json.dump(results, f, indent=2)
            
        logger.info(f"Completed batch trend prediction for {len(results)} markets")
        return results