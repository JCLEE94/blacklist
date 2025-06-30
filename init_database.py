#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
운영/개발 환경 모두에서 사용 가능
"""
import sqlite3
import os
import sys

def init_database(force_recreate=False):
    # Docker 환경과 로컬 환경 모두 지원
    if os.path.exists('/app'):
        db_path = '/app/instance/blacklist.db'
        # Docker 환경에서 디렉토리 생성 및 권한 설정
        try:
            os.makedirs('/app/instance', exist_ok=True)
            os.makedirs('/app/data', exist_ok=True)
            os.makedirs('/app/logs', exist_ok=True)
            os.makedirs('/app/data/by_detection_month', exist_ok=True)
            # 권한 설정 시도
            os.chmod('/app/instance', 0o777)
            os.chmod('/app/data', 0o777)
            os.chmod('/app/logs', 0o777)
            os.chmod('/app/data/by_detection_month', 0o777)
        except Exception as e:
            print(f"Warning: Failed to set permissions: {e}")
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
            
            if 'ip' not in columns or force_recreate:
                if force_recreate:
                    print("🔄 Force recreating table...")
                else:
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
                detection_date TIMESTAMP,
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
    # 명령줄 인자로 --force-recreate 옵션 지원
    force_recreate = '--force-recreate' in sys.argv
    success = init_database(force_recreate=force_recreate)
    sys.exit(0 if success else 1)