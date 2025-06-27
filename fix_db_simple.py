#!/usr/bin/env python3
import sqlite3
import os

# 프로덕션 컨테이너에서 실행할 스크립트
db_path = '/app/instance/blacklist.db'
if not os.path.exists(db_path):
    db_path = 'instance/blacklist.db'
    os.makedirs('instance', exist_ok=True)

print(f"Fixing database at: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 테이블 삭제 및 재생성
cursor.execute("DROP TABLE IF EXISTS blacklist_ip")
cursor.execute("""
CREATE TABLE blacklist_ip (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip VARCHAR(45) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    attack_type VARCHAR(50),
    country VARCHAR(100),
    source VARCHAR(100),
    extra_data TEXT
)
""")

cursor.execute("DROP TABLE IF EXISTS ip_detection")
cursor.execute("""
CREATE TABLE ip_detection (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ip VARCHAR(45) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50),
    attack_type VARCHAR(50),
    confidence_score REAL DEFAULT 1.0,
    blacklist_ip_id INTEGER,
    FOREIGN KEY (blacklist_ip_id) REFERENCES blacklist_ip(id)
)
""")

cursor.execute("DROP TABLE IF EXISTS daily_stats")
cursor.execute("""
CREATE TABLE daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE NOT NULL,
    total_ips INTEGER DEFAULT 0,
    regtech_count INTEGER DEFAULT 0,
    secudium_count INTEGER DEFAULT 0,
    public_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")

conn.commit()
conn.close()

print("✅ Database schema fixed successfully!")