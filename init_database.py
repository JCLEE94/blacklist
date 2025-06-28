#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
운영/개발 환경 모두에서 사용 가능
"""
import sqlite3
import os
import sys

def init_database():
    # Docker 환경과 로컬 환경 모두 지원
    if os.path.exists('/app'):
        db_path = '/app/instance/blacklist.db'
    else:
        db_path = 'instance/blacklist.db'
        os.makedirs('instance', exist_ok=True)
    
    print(f"Initializing database at: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 기존 테이블 체크
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='blacklist_ip'
        """)
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            # 테이블이 있으면 컬럼 체크
            cursor.execute("PRAGMA table_info(blacklist_ip)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'ip' not in columns:
                print("❌ 'ip' column missing in blacklist_ip table. Recreating table...")
                cursor.execute("DROP TABLE IF EXISTS blacklist_ip")
                table_exists = False
        
        if not table_exists:
            print("Creating blacklist_ip table...")
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
            cursor.execute("CREATE INDEX idx_blacklist_ip ON blacklist_ip(ip)")
            cursor.execute("CREATE INDEX idx_blacklist_source ON blacklist_ip(source)")
        
        # ip_detection 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ip_detection (
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
        
        # daily_stats 테이블
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
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
        
        print("✅ Database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)