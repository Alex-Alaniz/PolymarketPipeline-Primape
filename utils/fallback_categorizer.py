#!/usr/bin/env python3

"""
Fallback categorizer for when OpenAI API times out.

This module provides a simple keyword-based categorization
as a fallback when the OpenAI API times out.
"""

import re
from typing import Dict, List, Any, Tuple

# Categories
CATEGORIES = ["politics", "crypto", "sports", "business", "culture", "news", "tech"]

# Keywords for each category
CATEGORY_KEYWORDS = {
    "politics": [
        "election", "president", "vote", "congress", "senate", "house", "democrat", 
        "republican", "political", "government", "trump", "biden", "prime minister",
        "parliament", "candidate", "campaign", "ballot"
    ],
    "crypto": [
        "bitcoin", "ethereum", "btc", "eth", "cryptocurrency", "crypto", "token",
        "blockchain", "coin", "mining", "wallet", "defi", "nft", "dao", "exchange",
        "satoshi", "altcoin", "binance", "coinbase"
    ],
    "sports": [
        "football", "soccer", "nfl", "basketball", "nba", "baseball", "mlb", "hockey",
        "nhl", "tennis", "golf", "match", "game", "tournament", "championship", "coach",
        "player", "team", "league", "olympic", "sport", "athletic", "world cup",
        "champion", "boxing", "racing", "formula", "f1", "ufc", "premier league"
    ],
    "business": [
        "company", "stock", "market", "investor", "investment", "business", "finance",
        "economic", "economy", "earnings", "revenue", "profit", "loss", "ceo", "industry",
        "sector", "shareholder", "share price", "ipo", "merger", "acquisition", "quarterly",
        "fiscal", "wall street", "nasdaq", "dow jones", "s&p 500"
    ],
    "culture": [
        "movie", "film", "music", "artist", "actor", "actress", "celebrity", "award",
        "oscar", "emmy", "grammy", "entertainment", "box office", "album", "tv show",
        "series", "book", "author", "director", "hollywood", "concert", "festival",
        "streaming", "netflix", "disney"
    ],
    "news": [
        "breaking", "headline", "report", "update", "announcement", "development",
        "breaking news", "current events", "scandal"
    ],
    "tech": [
        "technology", "software", "hardware", "app", "application", "ai", "artificial intelligence",
        "robot", "gadget", "device", "smartphone", "iphone", "android", "google", "apple",
        "microsoft", "tech company", "social media", "facebook", "instagram", "twitter",
        "amazon", "computing", "internet", "web3", "digital", "virtual reality", "vr",
        "augmented reality", "ar", "machine learning", "ml", "startup"
    ]
}

def fallback_categorize(question: str) -> str:
    """
    Categorize a market question using keyword matching.
    
    Args:
        question: The market question to categorize
        
    Returns:
        Category name from CATEGORIES list
    """
    question = question.lower()
    
    # Count category keyword matches
    scores = {category: 0 for category in CATEGORIES}
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            # Match whole words only
            if re.search(r'\b' + re.escape(keyword) + r'\b', question):
                scores[category] += 1
    
    # Get category with highest score
    best_category = max(scores.items(), key=lambda x: x[1])
    
    # If no matches, default to "news"
    if best_category[1] == 0:
        return "news"
    
    return best_category[0]

def detect_event(question: str) -> Tuple[str, str]:
    """
    Detect potential event from a market question.
    
    Args:
        question: The market question
        
    Returns:
        Tuple of (event_id, event_name) or (None, None) if no event detected
    """
    # Strip punctuation and convert to lowercase
    q_lower = question.lower()
    
    # Try to detect common events
    if "world cup" in q_lower and any(year in q_lower for year in ["2022", "2026", "2030"]):
        if "2022" in q_lower:
            return "event_worldcup_2022", "FIFA World Cup 2022"
        elif "2026" in q_lower:
            return "event_worldcup_2026", "FIFA World Cup 2026"
        elif "2030" in q_lower:
            return "event_worldcup_2030", "FIFA World Cup 2030"
        
    elif "champions league" in q_lower:
        if "2025" in q_lower or "2025-2026" in q_lower:
            return "event_sports_001", "Champions League 2025-2026"
        elif "2024" in q_lower or "2024-2025" in q_lower:
            return "event_champions_league_2024", "Champions League 2024-2025"
        else:
            return "event_champions_league", "Champions League"
        
    elif "election" in q_lower and "us" in q_lower:
        if "2024" in q_lower:
            return "event_uselection_2024", "US Presidential Election 2024"
        elif "2028" in q_lower:
            return "event_uselection_2028", "US Presidential Election 2028"
        else:
            return "event_us_election", "US Election"
    
    elif "bitcoin" in q_lower and any(term in q_lower for term in ["price", "value", "market"]):
        return "event_crypto_001", "Bitcoin Price Predictions"
    
    # No recognized event
    return "", ""