#!/usr/bin/env python3
"""
PostgreSQL 직접 테스트 스크립트
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.database import DatabaseManager
from sqlalchemy import text

def test_postgresql():
    database_url = "postgresql://blacklist_user:blacklist_password_change_me@localhost:5432/blacklist"
    
    print("🔗 PostgreSQL 연결 테스트")
    
    try:
        db_manager = DatabaseManager(database_url)
        
        print("✅ DatabaseManager 생성 성공")
        
        # 연결 테스트
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"📊 PostgreSQL 버전: {version}")
            
            # 테이블 생성 직접 실행
            print("🔧 테이블 생성 중...")
            
            # metadata 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # blacklist 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    id SERIAL PRIMARY KEY,
                    ip_address INET NOT NULL,
                    source TEXT NOT NULL,
                    threat_level TEXT DEFAULT 'medium',
                    description TEXT,
                    country TEXT,
                    detection_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT true
                )
            """))
            
            # blacklist_entries 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS blacklist_entries (
                    id SERIAL PRIMARY KEY,
                    ip_address INET NOT NULL,
                    first_seen TEXT,
                    last_seen TEXT,
                    detection_months TEXT,
                    is_active BOOLEAN DEFAULT true,
                    days_until_expiry INTEGER DEFAULT 90,
                    threat_level TEXT DEFAULT 'medium',
                    source TEXT NOT NULL DEFAULT 'unknown',
                    source_details TEXT,
                    country TEXT,
                    reason TEXT,
                    reg_date TEXT,
                    exp_date TEXT,
                    view_count INTEGER DEFAULT 0,
                    uuid TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    severity_score REAL DEFAULT 0.0,
                    confidence_level REAL DEFAULT 1.0,
                    tags TEXT,
                    last_verified TIMESTAMP,
                    verification_status TEXT DEFAULT 'unverified',
                    UNIQUE(ip_address)
                )
            """))
            
            # collection_logs 테이블 생성
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS collection_logs (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    items_collected INTEGER DEFAULT 0,
                    details JSONB,
                    error_message TEXT,
                    duration_seconds REAL,
                    collection_type TEXT,
                    event TEXT NOT NULL
                )
            """))
            
            conn.commit()
            print("✅ 테이블 생성 완료")
            
            # 테이블 확인
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = result.fetchall()
            
            print("📊 생성된 테이블:")
            for (table_name,) in tables:
                print(f"  ✅ {table_name}")
            
            # 메타데이터 삽입
            conn.execute(text("""
                INSERT INTO metadata (key, value) VALUES 
                    ('db_version', '2.0'),
                    ('db_type', 'postgresql'),
                    ('initialized_at', CURRENT_TIMESTAMP::text),
                    ('schema_migrated', 'true')
                ON CONFLICT (key) DO UPDATE SET 
                    value = EXCLUDED.value,
                    updated_at = CURRENT_TIMESTAMP
            """))
            conn.commit()
            
            print("🎯 메타데이터 삽입 완료")
            
            # 데이터 확인
            result = conn.execute(text("SELECT key, value FROM metadata"))
            metadata = result.fetchall()
            
            print("📋 메타데이터:")
            for key, value in metadata:
                print(f"  📌 {key}: {value}")
            
            return True
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return False

if __name__ == "__main__":
    success = test_postgresql()
    if success:
        print("\n🎉 PostgreSQL 테스트 성공!")
    else:
        print("\n❌ PostgreSQL 테스트 실패!")
        sys.exit(1)