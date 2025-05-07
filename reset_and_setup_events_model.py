#!/usr/bin/env python3
"""
Reset and set up the database schema for the event-based model.

This script drops all existing tables and creates new ones with the proper
event-based schema. It should only be run when setting up the pipeline for
the first time or when doing a complete schema reset.

WARNING: THIS WILL DELETE ALL DATA IN THE DATABASE.
"""

import os
import sys
from flask import Flask

# Initialize Flask app for database context
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Import database models
from models_updated import db, Event, Market, PendingMarket, ProcessedMarket
db.init_app(app)

def reset_database():
    """Drop all tables and recreate them with the event-based schema."""
    print("WARNING: This will delete ALL data in the database.")
    print("Type 'yes' to continue or anything else to abort.")
    
    confirmation = input("> ")
    
    if confirmation.lower() != "yes":
        print("Aborted.")
        return 1
    
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        
        print("Creating tables with event-based schema...")
        db.create_all()
        
        print("Database schema reset successfully.")
        print("The following tables have been created:")
        
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        for table in tables:
            print(f"  - {table}")
            columns = inspector.get_columns(table)
            for column in columns:
                column_type = str(column['type'])
                print(f"      {column['name']}: {column_type}")
        
        print("\nEvent-based schema setup complete.")
    
    return 0

def main():
    """Main function."""
    return reset_database()

if __name__ == "__main__":
    sys.exit(main())