#!/usr/bin/env python3
"""
Fetch specific team images for Champions League and La Liga markets
"""
import json
import requests
import sys
from typing import Dict, List, Any, Optional, Tuple

def fetch_specific_team_images() -> None:
    """
    Fetch images for specific teams in Champions League and La Liga
    """
    # Teams to search for
    teams = [
        ("Barcelona Champions League", "Barcelona", "Will Barcelona win the UEFA Champions League"),
        ("Another Team La Liga", "another team", "Will another team win La Liga"),
    ]
    
    # URL setup
    base_url = "https://gamma-api.polymarket.com/markets"
    
    for search_term, team_name, expected_question in teams:
        print(f"\nSearching for {team_name} in {search_term}...")
        
        # Make API request
        params = {
            "limit": 10,
            "query": search_term,
            "skip": 0
        }
        
        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            markets = response.json()
            
            # Look for the specific market
            found = False
            for market in markets:
                question = market.get("question", "")
                image = market.get("image", "")
                
                # Check if this is our target market
                if expected_question.lower() in question.lower():
                    print(f"Found market: {question}")
                    print(f"Image URL: {image}")
                    print(f"Market ID: {market.get('id')}")
                    found = True
                    break
            
            if not found:
                print(f"Could not find exact match for {expected_question}")
                # Print first few results for debugging
                for i, market in enumerate(markets[:5]):
                    print(f"  Result {i+1}: {market.get('question')} - {market.get('image')}")
        
        except Exception as e:
            print(f"Error fetching data: {str(e)}")

if __name__ == "__main__":
    fetch_specific_team_images()