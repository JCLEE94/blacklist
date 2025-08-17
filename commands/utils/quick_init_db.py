#!/usr/bin/env python3
import sqlite3
import os

db_path = "/app/instance/blacklist.db" if os.path.exists("/app") else "instance/blacklist.db"
os.makedirs(os.path.dirname(db_path), exist_ok=True)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Create essential tables
cursor.execute("""
CREATE TABLE IF NOT EXISTS blacklist_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip_address TEXT NOT NULL UNIQUE,
    source TEXT,
    country TEXT,
    attack_type TEXT,
    detection_date TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    expires_at TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS collection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT,
    message TEXT,
    ip_count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    message TEXT,
    source TEXT,
    module TEXT,
    function TEXT,
    details TEXT
)
""")

conn.commit()
conn.close()
print("✅ DB initialized successfully!")