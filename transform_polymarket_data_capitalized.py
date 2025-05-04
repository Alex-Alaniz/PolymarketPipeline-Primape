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
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Any, Optional, Tuple

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
        # For testing purposes, always start with an empty processed markets list
        # This ensures we process all markets in each test run
        logger.info("Starting with a clean slate of processed markets for testing")
        return {"markets": []}
        
        # The code below is commented out but would be uncommented in production
        # to avoid reprocessing markets that have already been handled
        """
        if os.path.exists(PROCESSED_MARKETS_FILE):
            try:
                with open(PROCESSED_MARKETS_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning("Error reading processed markets file, starting fresh")
                return {"markets": []}
        return {"markets": []}
        """
    
    def _save_processed_markets(self):
        """Save the list of processed markets"""
        # For testing purposes, just log but don't actually save
        logger.info(f"Would save {len(self.processed_markets.get('markets', []))} processed markets (skipped for testing)")
        
        # The code below is commented out for testing but would be uncommented in production
        """
        with open(PROCESSED_MARKETS_FILE, 'w') as f:
            json.dump(self.processed_markets, f, indent=2)
        """
    
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
    
    def transform_markets_from_api(self, api_markets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform markets fetched directly from the Polymarket CLOB API.
        
        Args:
            api_markets (List[Dict[str, Any]]): Markets from Polymarket CLOB API
            
        Returns:
            List[Dict[str, Any]]: Transformed markets in ApeChain format
        """
        if not api_markets:
            logger.error("No Polymarket CLOB API markets provided")
            return []
        
        logger.info(f"Transforming {len(api_markets)} markets from Polymarket CLOB API")
        
        # The transformed markets list
        transformed_markets = []
        transformed_count = 0
        
        # Process each market from the API
        for market in api_markets:
            try:
                # Extract required fields from CLOB API format
                market_id = market.get("condition_id")
                question = market.get("question")
                
                # Convert end_date_iso to timestamp if available
                end_timestamp = None
                end_date_iso = market.get("end_date_iso")
                if end_date_iso:
                    try:
                        end_datetime = datetime.fromisoformat(end_date_iso.replace("Z", "+00:00"))
                        end_timestamp = int(end_datetime.timestamp() * 1000)  # Convert to milliseconds
                    except Exception as date_error:
                        logger.warning(f"Error parsing end date {end_date_iso}: {str(date_error)}")
                
                # Skip markets that have already been processed
                if self.is_market_processed(market_id):
                    logger.info(f"Skipping market {market_id} - already processed")
                    continue
                
                # Strict filtering for market status
                is_archived = market.get("archived", False)
                is_closed = market.get("closed", False)
                
                # Skip archived markets
                if is_archived:
                    logger.info(f"Skipping market {market_id} - archived")
                    continue
                
                # Skip closed markets
                if is_closed:
                    logger.info(f"Skipping market {market_id} - closed")
                    continue
                
                # Skip markets that have already ended
                if end_timestamp:
                    current_time = datetime.now().timestamp() * 1000
                    if end_timestamp < current_time:
                        logger.info(f"Skipping market {market_id} - already ended (expiry: {datetime.fromtimestamp(end_timestamp/1000)})")
                        continue
                else:
                    # If no end_timestamp is provided, try to extract it from other fields
                    end_date_str = market.get("end_date") or market.get("end_time")
                    if end_date_str:
                        try:
                            # Try to parse various date formats
                            for date_format in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"]:
                                try:
                                    end_date = datetime.strptime(end_date_str, date_format)
                                    if end_date < datetime.now():
                                        logger.info(f"Skipping market {market_id} - already ended (parsed date: {end_date})")
                                        continue
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            logger.warning(f"Could not parse end date '{end_date_str}' for market {market_id}: {e}")
                    
                    # If we can't determine expiry and the question has a date in it, check if it's in the past
                    if question:
                        # Look for date patterns in the question (like "by March 31" or "by end of 2023")
                        date_patterns = [
                            r"by\s+([a-zA-Z]+\s+\d{1,2})",  # by March 31
                            r"by\s+the\s+end\s+of\s+(\d{4})",  # by the end of 2023
                            r"by\s+(\d{4})",  # by 2023
                            r"by\s+Q\d+\s+(\d{4})",  # by Q1 2023
                            r"before\s+([a-zA-Z]+\s+\d{1,2})"  # before March 31
                        ]
                        
                        for pattern in date_patterns:
                            match = re.search(pattern, question, re.IGNORECASE)
                            if match:
                                date_text = match.group(1)
                                try:
                                    # For "March 31" type dates, add the current year if not specified
                                    if re.match(r"[a-zA-Z]+\s+\d{1,2}", date_text):
                                        current_year = datetime.now().year
                                        date_text = f"{date_text}, {current_year}"
                                        # Try to parse the date
                                        import dateutil.parser
                                        parsed_date = dateutil.parser.parse(date_text)
                                        if parsed_date < datetime.now():
                                            logger.info(f"Skipping market {market_id} - contains past date in question: {date_text}")
                                            continue
                                except Exception as e:
                                    logger.warning(f"Could not parse date from question for market {market_id}: {e}")
                
                # Skip markets with insufficient data
                if not question or "tokens" not in market:
                    logger.info(f"Skipping market {market_id} - insufficient data")
                    continue
                
                # Determine market type (binary or multiple)
                market_type = "binary"
                api_tokens = market.get("tokens", [])
                
                # For CLOB API, we have tokens instead of outcomes
                # If exactly 2 tokens, it's likely a binary market
                if len(api_tokens) == 2:
                    market_type = "binary"
                elif len(api_tokens) > 2:
                    market_type = "multiple"
                
                # Map category from tags or default to General
                tags = market.get("tags", ["General"])
                category = tags[0] if tags else "General"
                sub_category = tags[1] if len(tags) > 1 else "Other"
                
                # Extract tokens as options with their prices
                options = []
                for token in api_tokens:
                    options.append({
                        "name": token.get("outcome", "Unknown"),
                        "probability": token.get("price", 0.5),
                        # No direct volume in CLOB API, use minimum_order_size as proxy
                        "volume": market.get("minimum_order_size", 0)
                    })
                
                # Create the transformed market object
                transformed_market = {
                    "id": market_id,
                    "type": market_type,
                    "question": question,
                    "options": options,
                    "category": category,
                    "sub_category": sub_category,
                    "expiry": end_timestamp,
                    "original_market_id": market_id,
                    # Additional CLOB-specific fields
                    "description": market.get("description", ""),
                    "market_slug": market.get("market_slug", ""),
                    "image": market.get("image", "")
                }
                
                # Add to results
                transformed_markets.append(transformed_market)
                transformed_count += 1
                
                # Add to processed markets
                self.processed_markets["markets"].append({
                    "original_market_id": market_id,
                    "transformed_market_id": market_id,
                    "processed_date": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error transforming CLOB API market {market.get('condition_id', 'unknown')}: {str(e)}")
                continue
        
        # Save processed markets list
        self._save_processed_markets()
        
        logger.info(f"Transformed {transformed_count} markets from Polymarket CLOB API")
        return transformed_markets
        
    def transform_markets(self):
        """Transform the Polymarket markets to the required format"""
        if not self.polymarket_data:
            logger.error("No Polymarket data loaded")
            return False
        
        markets = self.polymarket_data.get("markets", [])
        
        # Filter active markets
        active_markets = []
        for market in markets:
            market_id = market.get("id")
            
            # Debug information for filtering process
            logger.info(f"Processing market: {market_id} - {market.get('question')}")
            
            # Check market status
            is_closed = market.get("closed", False)
            
            if is_closed:
                logger.info(f"Skipping market {market_id} - closed")
                continue
                
            # Check end timestamp
            end_timestamp = market.get("end_timestamp")
            if end_timestamp:
                end_date = datetime.fromtimestamp(end_timestamp / 1000)
                logger.info(f"Market {market_id} ends on {end_date}, current time is {datetime.now()}")
                
                # Skip markets that have already ended
                if end_date < datetime.now():
                    logger.info(f"Skipping market {market_id} - already ended")
                    continue
                
            # Even if no end_timestamp or if it's in the future, check question text for past dates
            question_text = market.get("question", "")
            if question_text:
                # Check for date patterns in the question (like "by March 31" or "by end of 2023")
                date_patterns = [
                    r"by\s+([a-zA-Z]+\s+\d{1,2})",  # by March 31
                    r"by\s+the\s+end\s+of\s+(\d{4})",  # by the end of 2023
                    r"by\s+(\d{4})",  # by 2023
                    r"by\s+Q\d+\s+(\d{4})",  # by Q1 2023
                    r"before\s+([a-zA-Z]+\s+\d{1,2})"  # before March 31
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, question_text, re.IGNORECASE)
                    if match:
                        date_text = match.group(1)
                        try:
                            # For "March 31" type dates, add the current year if not specified
                            if re.match(r"[a-zA-Z]+\s+\d{1,2}", date_text):
                                current_year = datetime.now().year
                                date_text = f"{date_text}, {current_year}"
                                # Try to parse the date
                                import dateutil.parser
                                parsed_date = dateutil.parser.parse(date_text)
                                if parsed_date < datetime.now():
                                    logger.info(f"Skipping market {market_id} - contains past date in question: {date_text}")
                                    continue
                        except Exception as e:
                            logger.warning(f"Could not parse date from question for market {market_id}: {e}")
            
            # Check if already processed
            if self.is_market_processed(market_id):
                logger.info(f"Skipping market {market_id} - already processed")
                continue
            
            # Check for insufficient data
            if not market.get("question") or not market.get("outcomes"):
                logger.info(f"Skipping market {market_id} - insufficient data")
                continue
            
            logger.info(f"Adding market {market_id} to active markets")
            active_markets.append(market)
            
        # If no active markets found, return
        if not active_markets:
            logger.warning("No active markets found after filtering. Continuing with empty market list.")
            # This will ensure we only use active markets and don't fall back to including expired ones
        
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
                        options.append({
                            "name": outcome.get("name"),
                            "probability": outcome.get("probability", 0.5),
                            "volume": outcome.get("volume", 0)
                        })
                    
                    # Create transformed market
                    transformed_market = {
                        "id": market_id,
                        "type": "binary",
                        "question": question,
                        "options": options,
                        "category": market.get("category"),
                        "sub_category": market.get("sub_category"),
                        "expiry": market.get("end_timestamp"),
                        "original_market_id": market_id
                    }
                    
                    # Add to transformed data
                    self.transformed_data["markets"].append(transformed_market)
                    
                    # Add to processed markets
                    self.processed_markets["markets"].append({
                        "original_market_id": market_id,
                        "transformed_market_id": market_id,
                        "processed_date": datetime.now().isoformat()
                    })
                    
                    transformed_count += 1
                    
                elif market_type == "multiple":
                    # Multiple-option market
                    group_id = market.get("id")
                    
                    # Get question and options
                    question = original_question  # Use capitalized group title
                    
                    # Get options (entities)
                    options = []
                    for outcome in market.get("outcomes", []):
                        options.append({
                            "name": outcome.get("name"),
                            "probability": 1.0 / len(market.get("outcomes", [])),  # Equal probability
                            "volume": 0  # No volume data available
                        })
                    
                    # Create transformed market
                    transformed_market = {
                        "id": group_id,
                        "type": "multiple",
                        "question": question,
                        "options": options,
                        "category": market.get("category"),
                        "sub_category": market.get("sub_category"),
                        "expiry": market.get("end_timestamp"),
                        "original_market_ids": market.get("original_market_ids", [])
                    }
                    
                    # Add to transformed data
                    self.transformed_data["markets"].append(transformed_market)
                    
                    # Add original markets to processed markets
                    for original_id in market.get("original_market_ids", []):
                        self.processed_markets["markets"].append({
                            "original_market_id": original_id,
                            "transformed_market_id": group_id,
                            "processed_date": datetime.now().isoformat()
                        })
                    
                    transformed_count += 1
                    
            except Exception as e:
                logger.error(f"Error transforming market {market.get('id')}: {str(e)}")
        
        logger.info(f"Transformed {transformed_count} markets")
        
        # Save transformed data
        with open(TRANSFORMED_FILE, 'w') as f:
            json.dump(self.transformed_data, f, indent=2)
            
        # Save processed markets
        self._save_processed_markets()
        
        return True


def main():
    """Main function"""
    # Create transformer
    transformer = PolymarketTransformer()
    
    # For testing purposes, always create a fresh sample Polymarket data file
    logger.info(f"Creating sample Polymarket data file {POLYMARKET_FILE}")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(POLYMARKET_FILE), exist_ok=True)
    
    # Clear processed markets file to ensure markets are processed again
    if os.path.exists(PROCESSED_MARKETS_FILE):
        os.remove(PROCESSED_MARKETS_FILE)
        logger.info(f"Removed previous {PROCESSED_MARKETS_FILE} to process all markets")
    
    # Create sample data
    sample_data = {
        "markets": [
            {
                "id": "market1",
                "question": "Will Manchester City win the Premier League?",
                "outcomes": [
                    {"name": "Yes", "probability": 0.75, "volume": 1000000},
                    {"name": "No", "probability": 0.25, "volume": 500000}
                ],
                "end_timestamp": int((datetime.now() + timedelta(days=30)).timestamp() * 1000),
                "category": "Sports",
                "sub_category": "Football"
            },
            {
                "id": "market2",
                "question": "Will Arsenal win the Premier League?",
                "outcomes": [
                    {"name": "Yes", "probability": 0.20, "volume": 800000},
                    {"name": "No", "probability": 0.80, "volume": 1200000}
                ],
                "end_timestamp": int((datetime.now() + timedelta(days=30)).timestamp() * 1000),
                "category": "Sports",
                "sub_category": "Football"
            },
            {
                "id": "market3",
                "question": "Will Liverpool win the Premier League?",
                "outcomes": [
                    {"name": "Yes", "probability": 0.15, "volume": 700000},
                    {"name": "No", "probability": 0.85, "volume": 900000}
                ],
                "end_timestamp": int((datetime.now() + timedelta(days=30)).timestamp() * 1000),
                "category": "Sports",
                "sub_category": "Football"
            },
            {
                "id": "market4",
                "question": "Will Bitcoin reach $100,000 by the end of 2025?",
                "outcomes": [
                    {"name": "Yes", "probability": 0.35, "volume": 2000000},
                    {"name": "No", "probability": 0.65, "volume": 3000000}
                ],
                "end_timestamp": int((datetime.now() + timedelta(days=365)).timestamp() * 1000),
                "category": "Crypto",
                "sub_category": "Bitcoin"
            }
        ]
    }
    
    with open(POLYMARKET_FILE, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    # Load Polymarket data
    if not transformer.load_polymarket_data():
        logger.error("Failed to load Polymarket data")
        return 1
    
    # Transform markets
    if not transformer.transform_markets():
        logger.error("Failed to transform markets")
        return 1
    
    logger.info(f"Successfully transformed markets, output written to {TRANSFORMED_FILE}")
    return 0


if __name__ == "__main__":
    exit(main())