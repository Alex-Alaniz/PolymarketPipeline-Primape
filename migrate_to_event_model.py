#!/usr/bin/env python3
"""
Migrate database from the current schema to the event-based schema.

This script creates the events table and updates existing markets to
reference the appropriate events. It extracts event information from
existing market data where possible.

WARNING: This script should be run on a backup of the database first
to ensure it works as expected before running it on the production database.
"""

import os
import sys
import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('migration')

# Flask setup for database context
from flask import Flask
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import both old and new models
from models import db as old_db
from models import Market as OldMarket
from models import PendingMarket as OldPendingMarket
from models import ProcessedMarket as OldProcessedMarket

# Import SQLAlchemy utilities
from sqlalchemy import MetaData, Table, Column, String, Text, Boolean, Integer, BigInteger, DateTime, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

# Create engine for direct table operations
engine = create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
metadata = MetaData()

def generate_event_id(event_name: str) -> str:
    """
    Generate a deterministic ID for an event based on its name.
    
    Args:
        event_name: Name of the event
        
    Returns:
        Deterministic ID for the event
    """
    return hashlib.sha256(event_name.encode()).hexdigest()[:40]

def extract_event_name_from_market(market_data: Dict[str, Any]) -> str:
    """
    Extract the event name from market data.
    
    Args:
        market_data: Market data dictionary
        
    Returns:
        Extracted event name or a default
    """
    title = market_data.get('question', '')
    description = market_data.get('description', '')
    
    # Try to extract event name from title or description
    indicators = ["Champions League", "La Liga", "NBA Finals", "World Cup", 
                 "Super Bowl", "Stanley Cup", "Grand Slam", "Olympics",
                 "Presidential Election", "Democratic Primary", "Republican Primary"]
    
    for indicator in indicators:
        if indicator in title or (description and indicator in description):
            return indicator
    
    # Category-based fallback
    category = market_data.get('category', '').lower()
    if "sports" in category:
        return "Sports Event"
    elif "politics" in category:
        return "Political Event"
    elif "crypto" in category:
        return "Crypto Market"
    else:
        return "News Event"

def create_events_table():
    """
    Create the events table in the database.
    """
    # Define events table
    events = Table(
        'events',
        metadata,
        Column('id', String(255), primary_key=True),
        Column('name', Text, nullable=False),
        Column('description', Text),
        Column('category', String(50), nullable=False, default='news'),
        Column('sub_category', String(100)),
        Column('banner_url', Text),
        Column('icon_url', Text),
        Column('source_id', String(255)),
        Column('raw_data', JSON),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )
    
    # Create the table
    if not engine.dialect.has_table(engine, 'events'):
        events.create(engine)
        logger.info("Created events table")
    else:
        logger.info("Events table already exists")
    
    return events

def add_event_id_to_markets():
    """
    Add event_id column to markets table.
    """
    with engine.connect() as conn:
        # Check if the column already exists
        inspector = metadata.tables['markets']
        if 'event_id' not in [c.name for c in inspector.columns]:
            conn.execute('ALTER TABLE markets ADD COLUMN event_id VARCHAR(255)')
            conn.execute('ALTER TABLE markets ADD CONSTRAINT fk_market_event FOREIGN KEY (event_id) REFERENCES events (id)')
            logger.info("Added event_id column to markets table")
        else:
            logger.info("event_id column already exists in markets table")

def add_event_columns_to_pending_markets():
    """
    Add event-related columns to pending_markets table.
    """
    with engine.connect() as conn:
        # Check if columns already exist
        inspector = metadata.tables['pending_markets']
        columns = [c.name for c in inspector.columns]
        
        if 'event_name' not in columns:
            conn.execute('ALTER TABLE pending_markets ADD COLUMN event_name TEXT')
            logger.info("Added event_name column to pending_markets table")
        
        if 'event_id' not in columns:
            conn.execute('ALTER TABLE pending_markets ADD COLUMN event_id VARCHAR(255)')
            logger.info("Added event_id column to pending_markets table")
        
        if 'option_images' not in columns:
            conn.execute('ALTER TABLE pending_markets ADD COLUMN option_images JSON')
            logger.info("Added option_images column to pending_markets table")

def add_event_columns_to_processed_markets():
    """
    Add event-related columns to processed_markets table.
    """
    with engine.connect() as conn:
        # Check if columns already exist
        inspector = metadata.tables['processed_markets']
        columns = [c.name for c in inspector.columns]
        
        if 'event_name' not in columns:
            conn.execute('ALTER TABLE processed_markets ADD COLUMN event_name TEXT')
            logger.info("Added event_name column to processed_markets table")
        
        if 'event_id' not in columns:
            conn.execute('ALTER TABLE processed_markets ADD COLUMN event_id VARCHAR(255)')
            logger.info("Added event_id column to processed_markets table")

def extract_and_create_events():
    """
    Extract events from existing markets and create event records.
    """
    with app.app_context():
        # Get all markets
        markets = OldMarket.query.all()
        events = {}  # Dictionary to store unique events
        
        # Extract events from markets
        for market in markets:
            # Extract event name
            market_data = {
                'question': market.question,
                'description': '',
                'category': market.category
            }
            event_name = extract_event_name_from_market(market_data)
            event_id = generate_event_id(event_name)
            
            # Skip if we've already processed this event
            if event_id in events:
                continue
            
            # Create event data
            event_data = {
                'id': event_id,
                'name': event_name,
                'description': '',
                'category': market.category or 'news',
                'banner_url': market.banner_uri,
                'icon_url': market.icon_url,
                'source_id': market.id,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # Store event
            events[event_id] = event_data
        
        # Insert events into database
        with engine.connect() as conn:
            for event_id, event_data in events.items():
                # Check if event already exists
                result = conn.execute(f"SELECT id FROM events WHERE id = '{event_id}'")
                if not result.fetchone():
                    # Insert event
                    columns = ', '.join(event_data.keys())
                    placeholders = ', '.join([':' + k for k in event_data.keys()])
                    query = f"INSERT INTO events ({columns}) VALUES ({placeholders})"
                    conn.execute(query, **event_data)
                    logger.info(f"Created event {event_id}: {event_data['name']}")
        
        logger.info(f"Created {len(events)} events from {len(markets)} markets")
        
        return events

def update_markets_with_event_ids(events: Dict[str, Dict[str, Any]]):
    """
    Update existing markets with event IDs.
    
    Args:
        events: Dictionary of event_id -> event_data
    """
    with app.app_context():
        # Get all markets
        markets = OldMarket.query.all()
        
        # Update markets with event IDs
        for market in markets:
            # Extract event name
            market_data = {
                'question': market.question,
                'description': '',
                'category': market.category
            }
            event_name = extract_event_name_from_market(market_data)
            event_id = generate_event_id(event_name)
            
            # Update market
            with engine.connect() as conn:
                conn.execute(
                    f"UPDATE markets SET event_id = '{event_id}' WHERE id = '{market.id}'"
                )
        
        logger.info(f"Updated {len(markets)} markets with event IDs")

def update_pending_markets_with_event_info():
    """
    Update pending markets with event information.
    """
    with app.app_context():
        # Get all pending markets
        pending_markets = OldPendingMarket.query.all()
        
        # Update pending markets with event info
        for market in pending_markets:
            # Extract event name
            market_data = {
                'question': market.question,
                'description': '',
                'category': market.category
            }
            event_name = extract_event_name_from_market(market_data)
            event_id = generate_event_id(event_name)
            
            # Update pending market
            with engine.connect() as conn:
                conn.execute(
                    f"UPDATE pending_markets SET event_name = '{event_name}', event_id = '{event_id}' WHERE poly_id = '{market.poly_id}'"
                )
        
        logger.info(f"Updated {len(pending_markets)} pending markets with event info")

def update_processed_markets_with_event_info():
    """
    Update processed markets with event information.
    """
    with app.app_context():
        # Get all processed markets
        processed_markets = OldProcessedMarket.query.all()
        
        # Update processed markets with event info
        for market in processed_markets:
            # Extract event name
            market_data = {
                'question': market.question,
                'description': '',
                'category': 'news'  # Default category
            }
            event_name = extract_event_name_from_market(market_data)
            event_id = generate_event_id(event_name)
            
            # Update processed market
            with engine.connect() as conn:
                conn.execute(
                    f"UPDATE processed_markets SET event_name = '{event_name}', event_id = '{event_id}' WHERE condition_id = '{market.condition_id}'"
                )
        
        logger.info(f"Updated {len(processed_markets)} processed markets with event info")

def main():
    """
    Main function to run the database migration.
    """
    try:
        # Confirm before proceeding
        if not os.environ.get('SKIP_CONFIRMATION'):
            print("WARNING: This script will modify the database schema.")
            print("It is recommended to run this on a backup first.")
            response = input("Do you want to proceed? (y/n): ")
            if response.lower() != 'y':
                print("Migration cancelled.")
                return 1
        
        # Load database metadata
        metadata.reflect(bind=engine)
        
        # Create events table
        create_events_table()
        
        # Update tables with new columns
        add_event_id_to_markets()
        add_event_columns_to_pending_markets()
        add_event_columns_to_processed_markets()
        
        # Extract and create events
        events = extract_and_create_events()
        
        # Update markets with event IDs
        update_markets_with_event_ids(events)
        
        # Update pending markets
        update_pending_markets_with_event_info()
        
        # Update processed markets
        update_processed_markets_with_event_info()
        
        logger.info("Migration completed successfully!")
        return 0
    
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())