#!/usr/bin/env python3

"""
Test script for finding truly active, non-expired markets from Polymarket API.

This script tests multiple API parameter combinations and performs additional
date filtering to find the best approach for fetching only current, active markets.
"""

import requests
import json
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("current_active_markets_test")

def test_api_parameters():
    """
    Test different API parameter combinations to find which ones work best.
    """
    # Get current timestamp
    now_ts = int(datetime.now(timezone.utc).timestamp())
    
    api_params = [
        ("accepting_orders=true", "Markets accepting orders"),
        ("accepting_orders=true&active=true", "Markets accepting orders and active"),
        ("active=true&sort_by=end_time&sort_direction=desc", "Active markets sorted by newest end time"),
        (f"end_time_from={now_ts}", "Markets with end time in the future"),
        (f"accepting_orders=true&end_time_from={now_ts}", "Markets accepting orders with end time in the future"),
        (f"accepting_orders=true&active=true&end_time_from={now_ts}", "Active markets accepting orders with end time in future")
    ]
    
    results = {}
    current_year = datetime.now().year
    now = datetime.now(timezone.utc)
    
    for params, desc in api_params:
        url = f"https://clob.polymarket.com/markets?{params}"
        
        logger.info(f"Testing API parameters: {params}")
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "application/json"
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if "data" in data and isinstance(data["data"], list):
                    markets = data["data"]
                    
                    # Count different types of markets
                    total_count = len(markets)
                    expired_count = 0
                    future_count = 0
                    
                    # Track markets for different years
                    year_counts = {}
                    
                    for market in markets:
                        # Check expiry date
                        expired = False
                        future = False
                        year = None
                        
                        end_date = market.get("end_date_iso")
                        if end_date:
                            try:
                                end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
                                
                                # Get the year
                                year = end_dt.year
                                year_counts[year] = year_counts.get(year, 0) + 1
                                
                                # Check if expired
                                if end_dt < now:
                                    expired_count += 1
                                    expired = True
                                elif end_dt > now + timedelta(days=30):
                                    future_count += 1
                                    future = True
                            except Exception as e:
                                logger.debug(f"Error parsing end_date_iso: {e}")
                        
                        # Add to sample market examples by year
                        if year and year >= current_year and not expired:
                            year_key = f"sample_{year}"
                            if year_key not in results:
                                results[year_key] = []
                            
                            if len(results[year_key]) < 3:  # Limit to 3 examples per year
                                results[year_key].append({
                                    "question": market.get("question"),
                                    "condition_id": market.get("condition_id"),
                                    "end_date": end_date,
                                    "accepting_orders": market.get("accepting_orders", False)
                                })
                    
                    results[params] = {
                        "total": total_count,
                        "expired": expired_count,
                        "future": future_count,
                        "year_counts": year_counts
                    }
                    
                    logger.info(f"  Found {total_count} markets ({expired_count} expired, {future_count} future)")
                    if year_counts:
                        years_str = ", ".join([f"{year}: {count}" for year, count in sorted(year_counts.items())])
                        logger.info(f"  Markets by year: {years_str}")
                else:
                    logger.error(f"  No 'data' field in response for {params}")
            else:
                logger.error(f"  HTTP error {response.status_code} for {params}")
        
        except Exception as e:
            logger.error(f"  Error testing {params}: {str(e)}")
    
    return results

def generate_curl_commands(results):
    """
    Generate curl commands based on test results.
    """
    logger.info("\n\nOPTIMAL CURL COMMANDS FOR ACTIVE MARKETS:")
    logger.info("===========================================\n")
    
    # Find best parameters based on results
    best_params = None
    best_score = -1
    
    for params in results:
        if isinstance(results[params], dict) and "total" in results[params]:
            data = results[params]
            current_year = datetime.now().year
            
            # Calculate a score based on total markets and recency
            score = data["total"] * 0.2  # Some weight for total available markets
            
            # Add score for current and future year markets
            for year, count in data.get("year_counts", {}).items():
                if year >= current_year:
                    year_weight = 1.0 if year == current_year else 0.5  # Current year is most important
                    score += count * year_weight
            
            # Subtract penalty for expired markets
            score -= data["expired"] * 0.5
            
            logger.info(f"Score for {params}: {score:.2f}")
            
            if score > best_score:
                best_score = score
                best_params = params
    
    # Generate the best curl command
    if best_params:
        # Base command for the best parameters
        base_cmd = f'''curl -X GET \
  "https://clob.polymarket.com/markets?{best_params}" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" \
  -H "Accept: application/json"'''
        
        logger.info("\nBest parameters: " + best_params)
        logger.info("\nCurl command for best parameters:")
        logger.info("-" * 80)
        logger.info(base_cmd)
        
        # Additional recommended curl command with more filtering
        enhanced_params = best_params
        current_year = datetime.now().year
        
        # Add additional filtering based on test results
        if "active=true" not in enhanced_params:
            enhanced_params += "&active=true"
        
        logger.info("\nEnhanced curl command with additional filtering:")
        logger.info("-" * 80)
        logger.info(f'''curl -X GET \
  "https://clob.polymarket.com/markets?{enhanced_params}" \
  -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36" \
  -H "Accept: application/json"''')
    else:
        logger.warning("Couldn't determine best parameters from test results.")

def print_sample_markets(results):
    """
    Print sample markets for current and future years.
    """
    current_year = datetime.now().year
    
    logger.info("\n\nSAMPLE CURRENT AND FUTURE MARKETS:")
    logger.info("=====================================\n")
    
    for year in range(current_year, current_year + 2):  # Current year and next year
        sample_key = f"sample_{year}"
        
        if sample_key in results and results[sample_key]:
            logger.info(f"Sample markets for {year}:")
            
            for i, market in enumerate(results[sample_key]):
                logger.info(f"Market #{i+1}:")
                logger.info(f"  Question: {market['question']}")
                logger.info(f"  Condition ID: {market['condition_id']}")
                logger.info(f"  End Date: {market['end_date']}")
                logger.info(f"  Accepting Orders: {market['accepting_orders']}")
                logger.info("")
        else:
            logger.info(f"No sample markets found for {year}")

def main():
    """
    Main function to run the test.
    """
    logger.info("Starting test for finding current active markets")
    
    # Test different API parameters
    results = test_api_parameters()
    
    # Generate curl commands based on test results
    generate_curl_commands(results)
    
    # Print sample markets
    print_sample_markets(results)
    
    # Recommendations
    logger.info("\n\nRECOMMENDATIONS:")
    logger.info("===============\n")
    logger.info("1. Use 'accepting_orders=true&active=true' as base parameters")
    logger.info("2. Add additional post-processing filters in code:")
    logger.info("   - Filter out markets with end_date_iso in the past")
    logger.info("   - Verify question text doesn't refer to past events (e.g., past years)")
    logger.info("   - Look for dates in the question text to confirm it's a future event")
    logger.info("3. Use pagination (limit=50&next_cursor=<value>) for handling large result sets")
    logger.info("\nCompleted test for current active markets")

if __name__ == "__main__":
    main()
