#!/usr/bin/env python3
"""
Validate the batch categorization implementation.

This script performs a validation of the batch categorization system
without requiring access to the Polymarket API, focusing specifically
on testing the efficiency and effectiveness of the categorization approach.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('validate_batch')

# Local imports - run within Flask app context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

from models import db, Market, PendingMarket, ProcessedMarket
db.init_app(app)

# Import batch categorizer
from utils.batch_categorizer import batch_categorize_markets, keyword_based_categorization

def load_test_questions() -> List[Dict[str, Any]]:
    """
    Load a diverse set of test questions for categorization.
    
    Returns:
        List of sample question objects
    """
    questions = [
        {
            "id": 1,
            "question": "Will Donald Trump win the 2024 US Presidential election?",
            "description": "This market will resolve to YES if Donald Trump wins the 2024 US Presidential election."
        },
        {
            "id": 2,
            "question": "Will Bitcoin exceed $100,000 before the end of 2024?",
            "description": "This market will resolve to YES if the price of Bitcoin exceeds $100,000 USD on any major exchange before the end of 2024."
        },
        {
            "id": 3,
            "question": "Will the New York Yankees win the 2024 World Series?",
            "description": "This market will resolve to YES if the New York Yankees win the 2024 MLB World Series."
        },
        {
            "id": 4,
            "question": "Will Apple release a foldable iPhone in 2024?",
            "description": "This market will resolve to YES if Apple officially announces and releases a foldable iPhone device in 2024."
        },
        {
            "id": 5,
            "question": "Will Nvidia stock (NVDA) exceed $1,000 before December 31, 2024?",
            "description": "This market will resolve to YES if the stock price of Nvidia (NVDA) exceeds $1,000 USD on any trading day before December 31, 2024."
        },
        {
            "id": 6,
            "question": "Will Avatar 3 gross over $2 billion at the global box office?",
            "description": "This market will resolve to YES if Avatar 3 grosses over $2 billion USD at the global box office according to Box Office Mojo."
        },
        {
            "id": 7,
            "question": "Will NASA successfully land astronauts on the Moon in the Artemis program before 2026?",
            "description": "This market will resolve to YES if NASA successfully lands astronauts on the Moon as part of the Artemis program before January 1, 2026."
        }
    ]
    
    return questions

def test_batch_vs_individual() -> None:
    """Test batch categorization vs. individual categorization."""
    logger.info("Running comparative test: batch vs. individual categorization")
    
    # Load test questions
    test_questions = load_test_questions()
    
    # Method 1: Individual categorization with keyword fallback
    logger.info("Testing individual categorization with keyword fallback...")
    individual_start_time = datetime.now()
    
    individual_results = []
    for question_obj in test_questions:
        question = question_obj["question"]
        category = keyword_based_categorization(question)
        individual_results.append({
            "id": question_obj["id"],
            "question": question,
            "category": category
        })
    
    individual_end_time = datetime.now()
    individual_duration = (individual_end_time - individual_start_time).total_seconds()
    
    # Method 2: Batch categorization
    logger.info("Testing batch categorization...")
    batch_start_time = datetime.now()
    
    batch_results = batch_categorize_markets(test_questions)
    
    batch_end_time = datetime.now()
    batch_duration = (batch_end_time - batch_start_time).total_seconds()
    
    # Compare results
    logger.info("\n=== Categorization Results Comparison ===")
    logger.info(f"Individual approach time: {individual_duration:.3f} seconds")
    logger.info(f"Batch approach time: {batch_duration:.3f} seconds")
    logger.info(f"Improvement: {(individual_duration/batch_duration if batch_duration > 0 else 0):.1f}x faster\n")
    
    # Compare categories
    logger.info("Category comparison:")
    for i, question_obj in enumerate(test_questions):
        q_id = question_obj["id"]
        question = question_obj["question"]
        
        # Find in both result sets
        individual_result = next((item for item in individual_results if item["id"] == q_id), None)
        batch_result = next((item for item in batch_results if item["id"] == q_id), None)
        
        individual_category = individual_result["category"] if individual_result else "n/a"
        batch_category = batch_result.get("ai_category", "n/a") if batch_result else "n/a"
        
        logger.info(f"Question {i+1}: '{question[:50]}...'")
        logger.info(f"  - Individual: {individual_category}")
        logger.info(f"  - Batch:      {batch_category}")
        logger.info("")
    
    # Distribution of categories
    batch_categories = {}
    for result in batch_results:
        category = result.get("ai_category", "news")
        if category in batch_categories:
            batch_categories[category] += 1
        else:
            batch_categories[category] = 1
    
    logger.info("Batch categorization distribution:")
    for category, count in batch_categories.items():
        percentage = count / len(batch_results) * 100
        logger.info(f"  - {category}: {count} questions ({percentage:.1f}%)")
    
    logger.info("\nBatch categorization validation complete")

def main() -> int:
    """
    Main function for batch categorization validation.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("Starting batch categorization validation")
    
    with app.app_context():
        try:
            # Run the tests
            test_batch_vs_individual()
            
            logger.info("Validation completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            return 1

if __name__ == "__main__":
    sys.exit(main())