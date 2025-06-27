#!/usr/bin/env python3
"""
Fix production database schema
"""
import requests
import json

def fix_database_via_api():
    """Fix database schema via API call"""
    
    # SQL to recreate table with correct schema
    fix_sql = """
    DROP TABLE IF EXISTS blacklist_ip;
    CREATE TABLE blacklist_ip (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip VARCHAR(45) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        attack_type VARCHAR(50),
        country VARCHAR(100),
        source VARCHAR(100),
        extra_data TEXT
    );
    
    DROP TABLE IF EXISTS ip_detection;
    CREATE TABLE ip_detection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ip VARCHAR(45) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        source VARCHAR(50),
        attack_type VARCHAR(50),
        confidence_score REAL DEFAULT 1.0,
        blacklist_ip_id INTEGER,
        FOREIGN KEY (blacklist_ip_id) REFERENCES blacklist_ip(id)
    );
    
    DROP TABLE IF EXISTS daily_stats;
    CREATE TABLE daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date DATE UNIQUE NOT NULL,
        total_ips INTEGER DEFAULT 0,
        regtech_count INTEGER DEFAULT 0,
        secudium_count INTEGER DEFAULT 0,
        public_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    print("🔧 Fixing database schema...")
    print("SQL Commands:")
    for line in fix_sql.strip().split('\n'):
        if line.strip():
            print(f"  {line.strip()}")
    
    # This would need a database endpoint, but we'll create a script for the container
    print("\n📋 Copy this script to container and run:")
    print("docker exec blacklist python3 -c \"")
    print("import sqlite3")
    print("conn = sqlite3.connect('/app/instance/blacklist.db')")
    print("cursor = conn.cursor()")
    
    for stmt in fix_sql.strip().split(';'):
        if stmt.strip():
            print(f"cursor.execute('''{stmt.strip()};''')")
            print("conn.commit()")
    
    print("print('Database schema fixed!')")
    print("conn.close()\"")

if __name__ == "__main__":
    fix_database_via_api()