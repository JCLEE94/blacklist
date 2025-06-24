#!/usr/bin/env python3
"""
데이터베이스 스키마 수정
"""
import sqlite3
import json
from datetime import datetime

def fix_schema():
    """데이터베이스 스키마 수정"""
    conn = sqlite3.connect('instance/blacklist.db')
    cursor = conn.cursor()
    
    try:
        # 현재 테이블 스키마 확인
        cursor.execute("PRAGMA table_info(blacklist_ip)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        print("Current columns:", column_names)
        
        # 새로운 테이블 생성 (올바른 스키마)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blacklist_ip_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL,
                detection_date DATE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                threat_type TEXT,
                attack_type TEXT,
                country TEXT,
                city TEXT,
                as_name TEXT,
                metadata TEXT
            )
        ''')
        
        # 기존 데이터 마이그레이션
        cursor.execute('''
            INSERT INTO blacklist_ip_new (ip, source, detection_date, is_active, threat_type, metadata)
            SELECT ip, source, detection_date, is_active, threat_type, metadata
            FROM blacklist_ip
        ''')
        
        # 기존 테이블 삭제하고 새 테이블로 교체
        cursor.execute('DROP TABLE blacklist_ip')
        cursor.execute('ALTER TABLE blacklist_ip_new RENAME TO blacklist_ip')
        
        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist_ip(ip)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist_ip(source)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_created_at ON blacklist_ip(created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_is_active ON blacklist_ip(is_active)')
        
        conn.commit()
        print("Schema fixed successfully!")
        
        # 데이터 확인
        cursor.execute('SELECT COUNT(*) FROM blacklist_ip')
        count = cursor.fetchone()[0]
        print(f"Total records: {count}")
        
        # 샘플 데이터 출력
        cursor.execute('SELECT ip, source, detection_date FROM blacklist_ip LIMIT 5')
        for row in cursor.fetchall():
            print(f"  {row[0]} from {row[1]} ({row[2]})")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    fix_schema()