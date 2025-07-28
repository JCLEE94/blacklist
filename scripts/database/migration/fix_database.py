#!/usr/bin/env python3
"""
Fix database schema issues
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3

from src.core.database import DatabaseManager


def fix_database():
    """Fix database schema"""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'instance',
        'blacklist.db',
    )

    print(f"Checking database at: {db_path}")

    if not os.path.exists(db_path):
        print("Database file does not exist, creating new one...")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='blacklist_ip'"
    )
    table_exists = cursor.fetchone()

    if table_exists:
        # Check columns
        cursor.execute("PRAGMA table_info(blacklist_ip)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print(f"Existing columns: {column_names}")

        if 'ip' not in column_names:
            print("ERROR: 'ip' column missing from blacklist_ip table")
            print("Recreating table with correct schema...")

            # Backup existing data if any
            cursor.execute("ALTER TABLE blacklist_ip RENAME TO blacklist_ip_old")
            conn.commit()

    # Create table with correct schema
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS blacklist_ip (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip VARCHAR(45) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            attack_type VARCHAR(50),
            country VARCHAR(100),
            source VARCHAR(100),
            extra_data TEXT,
            as_name VARCHAR(200),
            city VARCHAR(100)
        )
    """
    )

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_ip(ip)")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_ip(source)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_blacklist_created ON blacklist_ip(created_at)"
    )

    conn.commit()

    # Verify
    cursor.execute("PRAGMA table_info(blacklist_ip)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"New columns: {column_names}")

    if 'ip' in column_names:
        print("✅ Database schema fixed successfully!")
    else:
        print("❌ Failed to fix database schema")

    conn.close()


if __name__ == "__main__":
    fix_database()
