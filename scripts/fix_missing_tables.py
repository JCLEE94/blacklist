#!/usr/bin/env python3
"""
누락된 데이터베이스 테이블을 생성하는 스크립트
주로 auth_attempts 테이블과 관련 인덱스 생성
"""

import sqlite3
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def create_missing_tables(db_path):
    """누락된 테이블 생성"""
    print(f"데이터베이스 경로: {db_path}")

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        # auth_attempts 테이블 생성
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL,
                user_agent TEXT,
                attempt_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT FALSE,
                failure_reason TEXT,
                username TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 인덱스 생성
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_ip 
            ON auth_attempts(ip_address)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_time 
            ON auth_attempts(attempt_time)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_attempts_success 
            ON auth_attempts(success)
        """
        )

        # API 키 테이블이 없으면 생성 (이미 있을 수 있음)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT UNIQUE NOT NULL,
                key_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                permissions TEXT DEFAULT 'read',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                last_used_at TIMESTAMP,
                usage_count INTEGER DEFAULT 0
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash 
            ON api_keys(key_hash)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_api_keys_active 
            ON api_keys(is_active)
        """
        )

        # 시스템 설정 테이블
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                description TEXT,
                category TEXT DEFAULT 'general',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # 시스템 로그 테이블
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                line_number INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                additional_data TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_system_logs_level 
            ON system_logs(level)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp 
            ON system_logs(timestamp)
        """
        )

        conn.commit()
        print("모든 테이블이 성공적으로 생성되었습니다.")

        # 테이블 목록 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"생성된 테이블 수: {len(tables)}")
        for table in tables:
            print(f"  - {table[0]}")


def main():
    """메인 함수"""
    # 기본 데이터베이스 경로들
    db_paths = ["instance/blacklist.db", "blacklist.db", "/app/instance/blacklist.db"]

    # 명령행 인수로 경로 지정 가능
    if len(sys.argv) > 1:
        db_paths = [sys.argv[1]]

    for db_path in db_paths:
        if os.path.exists(db_path) or db_path.startswith("/app/"):
            try:
                create_missing_tables(db_path)
                print(f"✅ {db_path} 처리 완료")
                break
            except Exception as e:
                print(f"❌ {db_path} 처리 실패: {e}")
        else:
            print(f"⚠️  {db_path} 파일이 존재하지 않음")
    else:
        print("⚠️  데이터베이스 파일을 찾을 수 없습니다.")
        print("사용법: python3 scripts/fix_missing_tables.py [db_path]")


if __name__ == "__main__":
    main()
