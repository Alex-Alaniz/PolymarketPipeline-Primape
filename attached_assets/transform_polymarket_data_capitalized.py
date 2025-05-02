#!/usr/bin/env python3
"""
Enhanced transformation script for Polymarket data with proper capitalization preservation.

This script transforms Polymarket data into the format required by the smart contract,
handling both binary and multiple-option markets correctly while preserving proper capitalization.
"""

import json
import os
import logging
import re
from datetime import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("transform_data.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("transform_data")

# Constants
DATA_DIR = "data"
POLYMARKET_FILE = os.path.join(DATA_DIR, "polymarket_markets.json")
TRANSFORMED_FILE = os.path.join(DATA_DIR, "transformed_markets.json")
PROCESSED_MARKETS_FILE = os.path.join(DATA_DIR, "processed_markets.json")

class PolymarketTransformer:
    """Class to transform Polymarket data to the required format"""
    
    def __init__(self):
        """Initialize the transformer"""
        self.polymarket_data = None
        self.transformed_data = {"markets": []}
        self.processed_markets = self._load_processed_markets()
        
        # Create data directory if it doesn't exist
        os.makedirs(DATA_DIR, exist_ok=True)
    
    def _load_processed_markets(self):
        """Load the list of already processed markets"""
        if os.path.exists(PROCESSED_MARKETS_FILE):
            try:
                with open(PROCESSED_MARKETS_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Error reading processed markets file, starting fresh")
                return {"markets": []}
        return {"markets": []}
    
    def _save_processed_markets(self):
        """Save the list of processed markets"""
        with open(PROCESSED_MARKETS_FILE, 'w') as f:
            json.dump(self.processed_markets, f, indent=2)
    
    def load_polymarket_data(self):
        """Load the Polymarket data from JSON file"""
        if not os.path.exists(POLYMARKET_FILE):
            logger.error(f"Polymarket data file {POLYMARKET_FILE} not found")
            return False
        
        try:
            with open(POLYMARKET_FILE, 'r') as f:
                self.polymarket_data = json.load(f)
                logger.info(f"Loaded {len(self.polymarket_data.get('markets', []))} markets from {POLYMARKET_FILE}")
                return True
        except json.JSONDecodeError:
            logger.error(f"Error parsing Polymarket data file {POLYMARKET_FILE}")
            return False
    
    def is_market_processed(self, market_id):
        """Check if a market has already been processed"""
        processed_ids = [m.get("original_market_id") for m in self.processed_markets.get("markets", [])]
        return market_id in processed_ids
    
    def extract_entity_from_question(self, question, pattern):
        """Extract the entity from a question based on a pattern"""
        match = re.search(pattern, question, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None
    
    def extract_base_question(self, question, entity=None):
        """Extract the base question without the specific entity"""
        if entity:
            # Replace the entity with a placeholder
            base_question = question.replace(entity, "ENTITY")
            # Convert to lowercase for comparison purposes only
            return base_question.lower()
        return question.lower()
    
    def group_related_markets(self, markets):
        """Group related markets based on patterns in their questions"""
        # Define patterns for different types of related markets
        patterns = {
            "top_goalscorer": r"Will (.*) be the top goalscorer in the EPL\?",
            "league_winner": r"Will (.*) win (La Liga|the Premier League|Serie A|Bundesliga|Ligue 1)\?",
            "president": r"Will (.*) be (elected|the next) president of (.*)\?",
            "company_market_cap": r"Will (.*) be the largest company in the world by market cap",
            "oscar_winner": r"Will (.*) win the Oscar for (Best Picture|Best Director|Best Actor|Best Actress)",
            "election_winner": r"Will (.*) win the (.*) election\?",
        }
        
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
                    break
            
            # If no pattern matched, treat as individual market
            if not matched:
                base_question = question.lower()  # For grouping purposes only
                grouped_markets[base_question].append((market, question, None))
        
        # Second pass: determine which groups are actually multiple-option markets
        result = []
        for base_question, market_group in grouped_markets.items():
            # If only one market in the group, it's a regular market
            if len(market_group) == 1:
                market, original_question, _ = market_group[0]
                result.append((market, "binary", original_question))
            # If multiple markets with the same pattern, it's a multiple-option market
            elif len(market_group) > 1:
                # Check if all markets have the same options (Yes/No)
                all_yes_no = all(
                    len(m[0].get("outcomes", [])) == 2 and 
                    "Yes" in [o.get("name") for o in m[0].get("outcomes", [])] and
                    "No" in [o.get("name") for o in m[0].get("outcomes", [])]
                    for m in market_group
                )
                
                if all_yes_no:
                    # Extract the common part of the question for the group title
                    # Use the original capitalization from the first market
                    _, original_question, _ = market_group[0]
                    
                    # For specific patterns, create a better title
                    if "goalscorer" in base_question:
                        group_title = "Top goalscorer in the EPL"
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
                    
                    # Use the first market as a template
                    template_market = market_group[0][0]
                    
                    result.append((
                        {
                            "id": f"group_{base_question}",
                            "question": group_title,
                            "outcomes": [{"name": entity} for entity in entities],
                            "end_timestamp": template_market.get("end_timestamp"),
                            "category": template_market.get("category"),
                            "sub_category": template_market.get("sub_category"),
                            "original_market_ids": market_ids
                        },
                        "multiple",
                        group_title  # Preserve the properly capitalized title
                    ))
                else:
                    # If not all Yes/No, treat as individual markets
                    for market, original_question, _ in market_group:
                        result.append((market, "binary", original_question))
        
        return result
    
    def transform_markets(self):
        """Transform the Polymarket markets to the required format"""
        if not self.polymarket_data:
            logger.error("No Polymarket data loaded")
            return False
        
        markets = self.polymarket_data.get("markets", [])
        
        # Filter active markets
        active_markets = []
        for market in markets:
            # Skip markets that have already ended
            end_timestamp = market.get("end_timestamp")
            if end_timestamp:
                end_date = datetime.fromtimestamp(end_timestamp / 1000)
                if end_date < datetime.now():
                    continue
            
            # Skip markets that have already been processed
            market_id = market.get("id")
            if self.is_market_processed(market_id):
                continue
            
            # Skip markets with insufficient data
            if not market.get("question") or not market.get("outcomes"):
                continue
            
            active_markets.append(market)
        
        logger.info(f"Found {len(active_markets)} active markets to transform")
        
        # Group related markets
        grouped_markets = self.group_related_markets(active_markets)
        logger.info(f"Grouped into {len(grouped_markets)} markets")
        
        # Transform each market or group
        transformed_count = 0
        for market, market_type, original_question in grouped_markets:
            try:
                if market_type == "binary":
                    # Binary market
                    market_id = market.get("id")
                    
                    # Skip if already processed
                    if self.is_market_processed(market_id):
                        continue
                    
                    # Get question and options
                    question = original_question  # Use original capitalization
                    
                    # Get options (Yes/No)
                    options = []
                    for outcome in market.get("outcomes", []):
                        options.append(outcome.get("name"))
                    
                    # Skip if not enough options
                    if len(options) < 2:
                        continue
                    
                    # Get duration in seconds
                    duration = 0
                    end_timestamp = market.get("end_timestamp")
                    if end_timestamp:
                        end_date = datetime.fromtimestamp(end_timestamp / 1000)
                        duration = int((end_date - datetime.now()).total_seconds())
                        if duration <= 0:
                            continue
                    
                    # Create transformed market
                    transformed_market = {
                        "_question": question,
                        "_options": options,
                        "_duration": duration,
                        "market_type": "binary",
                        "original_market_id": market_id,
                        "category": market.get("category"),
                        "sub_category": market.get("sub_category")
                    }
                    
                    self.transformed_data["markets"].append(transformed_market)
                    transformed_count += 1
                    
                    # Add to processed markets
                    self.processed_markets["markets"].append({
                        "original_market_id": market_id,
                        "question": question,
                        "processed_at": datetime.now().isoformat()
                    })
                    
                else:
                    # Multiple-option market
                    market_ids = market.get("original_market_ids", [])
                    
                    # Skip if any of the markets have already been processed
                    if any(self.is_market_processed(market_id) for market_id in market_ids):
                        continue
                    
                    # Get question and options
                    question = original_question  # Use original capitalization
                    
                    # Get options (entity names)
                    options = []
                    for outcome in market.get("outcomes", []):
                        options.append(outcome.get("name"))
                    
                    # Skip if not enough options
                    if len(options) < 2:
                        continue
                    
                    # Get duration in seconds
                    duration = 0
                    end_timestamp = market.get("end_timestamp")
                    if end_timestamp:
                        end_date = datetime.fromtimestamp(end_timestamp / 1000)
                        duration = int((end_date - datetime.now()).total_seconds())
                        if duration <= 0:
                            continue
                    
                    # Create transformed market
                    transformed_market = {
                        "_question": question,
                        "_options": options,
                        "_duration": duration,
                        "market_type": "multiple",
                        "original_market_ids": market_ids,
                        "category": market.get("category"),
                        "sub_category": market.get("sub_category")
                    }
                    
                    self.transformed_data["markets"].append(transformed_market)
                    transformed_count += 1
                    
                    # Add to processed markets
                    for market_id in market_ids:
                        self.processed_markets["markets"].append({
                            "original_market_id": market_id,
                            "question": question,
                            "processed_at": datetime.now().isoformat()
                        })
            
            except Exception as e:
                logger.error(f"Error transforming market: {e}")
                continue
        
        logger.info(f"Transformed {transformed_count} markets successfully")
        
        # Save transformed data
        with open(TRANSFORMED_FILE, 'w') as f:
            json.dump(self.transformed_data, f, indent=2)
        
        # Save processed markets
        self._save_processed_markets()
        
        return True

def main():
    """Main function"""
    transformer = PolymarketTransformer()
    
    # Load Polymarket data
    if not transformer.load_polymarket_data():
        logger.error("Failed to load Polymarket data")
        return False
    
    # Transform markets
    if not transformer.transform_markets():
        logger.error("Failed to transform markets")
        return False
    
    logger.info("Market transformation completed successfully")
    return True

if __name__ == "__main__":
    main()
