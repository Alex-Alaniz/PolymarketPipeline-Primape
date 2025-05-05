#!/usr/bin/env python3
"""
Market Transformer for Polymarket data.

This module transforms Polymarket data into the format required for Apechain,
handling both binary and multiple-option markets correctly.
"""

import re
import json
import logging
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Any, Tuple, Optional

# Configure logging
logger = logging.getLogger("market_transformer")

class MarketTransformer:
    """Class to transform Polymarket data to the required format"""
    
    def __init__(self):
        """Initialize the transformer"""
        self.processed_market_ids = set()
    
    def extract_entity_from_question(self, question: str, pattern: str) -> Optional[str]:
        """Extract the entity from a question based on a pattern"""
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            entity = match.group(1).strip()
            logger.debug(f"Extracted entity '{entity}' from question: '{question}'")
            return entity
        logger.debug(f"No entity extracted from question: '{question}' using pattern: {pattern}")
        return None
    
    def extract_base_question(self, question: str, entity: Optional[str] = None) -> str:
        """Extract the base question without the specific entity"""
        if entity:
            # Use regex to replace the entity with a placeholder
            # This handles case-insensitive matching and special characters
            base_question = re.sub(re.escape(entity), "ENTITY", question, flags=re.IGNORECASE)
            logger.debug(f"Extracted base question: '{base_question}' from '{question}' with entity '{entity}'")
            # Convert to lowercase for comparison purposes only
            return base_question.lower()
        logger.debug(f"No entity provided, using question as is: '{question}'")
        return question.lower()
    
    def get_patterns(self) -> Dict[str, str]:
        """Define patterns for different types of related markets"""
        return {
            "top_goalscorer": r"(?i)will\s+(.*?)\s+be\s+the\s+top\s+goalscorer\s+in\s+the\s+epl\s*\?",
            "league_winner": r"(?i)will\s+(.*?)\s+win\s+(la\s+liga|the\s+premier\s+league|serie\s+a|bundesliga|ligue\s+1)\s*\?",
            "president": r"(?i)will\s+(.*?)\s+be\s+(elected|the\s+next)\s+president\s+of\s+(.*?)\s*\?",
            "company_market_cap": r"(?i)will\s+(.*?)\s+be\s+the\s+largest\s+company\s+in\s+the\s+world\s+by\s+market\s+cap",
            "oscar_winner": r"(?i)will\s+(.*?)\s+win\s+the\s+oscar\s+for\s+(best\s+picture|best\s+director|best\s+actor|best\s+actress)",
            "election_winner": r"(?i)will\s+(.*?)\s+win\s+the\s+(.*?)\s+election\s*\?",
            "premier_league_top_scorer": r"(?i)will\s+(.*?)\s+be\s+the\s+(english\s+premier\s+league|epl)\s+top\s+scorer\s*\?",
        }
    
    def group_related_markets(self, markets: List[Dict[str, Any]]) -> List[Tuple[Dict[str, Any], str, str]]:
        """
        Group related markets based on patterns in their questions.
        
        Args:
            markets: List of market data dictionaries
            
        Returns:
            List of tuples (market_data, market_type, original_question)
        """
        # Define patterns for different types of related markets
        patterns = self.get_patterns()
        
        # Group markets by base question
        grouped_markets = defaultdict(list)
        
        # First pass: identify and group related markets
        for market in markets:
            question = market.get("question", "")
            
            # Check if market matches any pattern
            matched = False
            for pattern_name, pattern in patterns.items():
                entity = self.extract_entity_from_question(question, pattern)
                if entity:
                    base_question = self.extract_base_question(question, entity)
                    # Store original question for capitalization preservation
                    grouped_markets[base_question].append((market, question, entity))
                    matched = True
                    logger.info(f"Matched pattern '{pattern_name}': {question} -> entity: {entity}")
                    break
            
            # If no pattern matched, treat as individual market
            if not matched:
                base_question = question.lower()  # For grouping purposes only
                grouped_markets[base_question].append((market, question, None))
        
        # Second pass: determine which groups are actually multiple-option markets
        result = []
        for base_question, market_group in grouped_markets.items():
            # Log the groups we've found
            if len(market_group) > 1:
                logger.info(f"Found potential market group with {len(market_group)} markets: {base_question}")
                for i, (m, q, e) in enumerate(market_group):
                    logger.info(f"  Market {i+1}: {q} -> entity: {e}")
                    
            # If only one market in the group, it's a regular market
            if len(market_group) == 1:
                market, original_question, _ = market_group[0]
                result.append((market, "binary", original_question))
            # If multiple markets with the same pattern, it's a multiple-option market
            elif len(market_group) > 1:
                # Check if all markets have the same Yes/No options
                all_yes_no = True
                for m, _, _ in market_group:
                    try:
                        # Parse outcomes which come as a JSON string
                        outcomes_raw = m.get("outcomes", "[]")
                        outcomes = json.loads(outcomes_raw) if isinstance(outcomes_raw, str) else outcomes_raw
                        if len(outcomes) != 2 or "Yes" not in outcomes or "No" not in outcomes:
                            all_yes_no = False
                            break
                    except Exception:
                        all_yes_no = False
                        break
                
                if all_yes_no:
                    # Extract the common part of the question for the group title
                    # Use the original capitalization from the first market
                    _, original_question, _ = market_group[0]
                    
                    # For specific patterns, create a better title
                    if "goalscorer" in base_question or "english premier league top scorer" in base_question.lower():
                        group_title = "English Premier League Top Scorer"
                    elif "win la liga" in base_question:
                        group_title = "La Liga Winner"
                    elif "win the premier league" in base_question:
                        group_title = "Premier League Winner"
                    elif "win serie a" in base_question:
                        group_title = "Serie A Winner"
                    elif "win bundesliga" in base_question:
                        group_title = "Bundesliga Winner"
                    elif "win ligue 1" in base_question:
                        group_title = "Ligue 1 Winner"
                    elif "president of" in base_question:
                        country = re.search(r"president of (.*)\?", original_question, re.IGNORECASE)
                        if country:
                            group_title = f"The next President of {country.group(1)}"
                        else:
                            group_title = "The next President"
                    elif "largest company" in base_question:
                        group_title = "The largest company in the world by market cap on December 31"
                    elif "oscar for" in base_question:
                        category = re.search(r"oscar for (.*)", original_question, re.IGNORECASE)
                        if category:
                            group_title = f"Oscar Winner for {category.group(1)}"
                        else:
                            group_title = "Oscar Winner"
                    elif "election" in base_question:
                        election = re.search(r"win the (.*) election", original_question, re.IGNORECASE)
                        if election:
                            group_title = f"{election.group(1)} Election Winner"
                        else:
                            group_title = "Election Winner"
                    else:
                        # Use a generic title based on the first market's question
                        # Remove "Will X be" or "Will X win" from the beginning
                        group_title = re.sub(r"^Will .* (be|win) ", "", original_question)
                        # Remove question mark
                        group_title = group_title.rstrip("?")
                        # Capitalize first letter
                        group_title = group_title[0].upper() + group_title[1:]
                    
                    # Create a multiple-option market
                    entities = [entity for _, _, entity in market_group if entity]
                    market_ids = [m[0].get("id") for m in market_group]
                    condition_ids = [m[0].get("conditionId") for m in market_group if m[0].get("conditionId")]
                    
                    # Use the first market as a template
                    template_market = market_group[0][0]
                    
                    # Create a new market data dictionary
                    multiple_market = {
                        "id": f"group_{base_question.replace(' ', '_')}",
                        "question": group_title,
                        "conditionId": condition_ids[0] if condition_ids else "",
                        "slug": template_market.get("slug", ""),
                        "endDate": template_market.get("endDate"),
                        "image": template_market.get("image"),
                        "icon": template_market.get("icon"),
                        "fetched_category": template_market.get("fetched_category", "general"),
                        "original_market_ids": market_ids,
                        "outcomes": json.dumps(entities), # Store as JSON string
                        "is_multiple_option": True
                    }
                    
                    result.append((multiple_market, "multiple", group_title))
                else:
                    # If not all Yes/No, treat as individual markets
                    for market, original_question, _ in market_group:
                        result.append((market, "binary", original_question))
        
        return result
    
    def transform_markets(self, markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform markets into the format required for our pipeline.
        
        Args:
            markets: List of market data dictionaries from Polymarket API
            
        Returns:
            List of transformed market dictionaries
        """
        if not markets:
            logger.error("No markets provided for transformation")
            return []
        
        logger.info(f"Transforming {len(markets)} markets")
        
        # Group related markets
        grouped_markets = self.group_related_markets(markets)
        logger.info(f"Grouped into {len(grouped_markets)} markets")
        
        # Transform each market or group
        transformed_markets = []
        for market, market_type, original_question in grouped_markets:
            try:
                # Skip if already processed (by conditionId)
                condition_id = market.get("conditionId")
                if condition_id and condition_id in self.processed_market_ids:
                    continue
                
                # Process based on market type
                if market_type == "binary":
                    # For binary markets, keep most of the original data
                    transformed_market = market.copy()
                    transformed_markets.append(transformed_market)
                    
                    # Mark as processed
                    if condition_id:
                        self.processed_market_ids.add(condition_id)
                
                elif market_type == "multiple":
                    # For multiple-option markets, use the modified data
                    transformed_market = market.copy()
                    transformed_markets.append(transformed_market)
                    
                    # Mark original market IDs as processed
                    for orig_id in market.get("original_market_ids", []):
                        self.processed_market_ids.add(orig_id)
            
            except Exception as e:
                logger.error(f"Error transforming market: {str(e)}")
        
        logger.info(f"Transformed {len(transformed_markets)} markets")
        return transformed_markets