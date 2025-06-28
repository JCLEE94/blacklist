#!/usr/bin/env python3
"""
Initialize database tables
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from src.core.database import DatabaseManager

def init_database():
    print("Initializing database...")
    
    # Create database manager
    db_manager = DatabaseManager()
    
    # Initialize database
    db_manager.init_db()
    
    print("Database initialized successfully!")
    
    # Check tables
    with db_manager.engine.connect() as conn:
        from sqlalchemy import text
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
        print(f"\nCreated tables: {tables}")
        
        # Check blacklist_ip columns
        result = conn.execute(text("PRAGMA table_info(blacklist_ip)"))
        columns = [(row[1], row[2]) for row in result]
        print(f"\nblacklist_ip columns: {columns}")

if __name__ == "__main__":
    init_database()