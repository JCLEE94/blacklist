"""
데이터베이스 관련 테스트 픽스처
"""

import os
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_database():
    """테스트용 메모리 데이터베이스 - 실제 스키마 사용"""
    import os
    import sys
    from pathlib import Path

    # 프로젝트 루트를 Python 경로에 추가
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    try:
        from src.core.database_schema import DatabaseSchema

        # 메모리 데이터베이스 사용
        db_schema = DatabaseSchema(":memory:")

        # 실제 스키마로 테이블 생성
        success = db_schema.create_all_tables()

        if success:
            yield db_schema.db_path
        else:
            # 스키마 생성 실패시 fallback
            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()

            # 최소한의 테이블만 생성
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS blacklist_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT NOT NULL UNIQUE,
                source TEXT NOT NULL DEFAULT 'test',
                first_seen TEXT,
                last_seen TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS collection_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                collection_date TEXT,
                ip_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # 추가 필요한 테이블들
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS auth_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT,
                username TEXT,
                attempt_time TEXT,
                success BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS system_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS cache_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            )

            # 스키마 버전 설정
            cursor.execute(
                "INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', '2.0.0')"
            )

            conn.commit()
            conn.close()

            yield ":memory:"

    except ImportError:
        # DatabaseSchema import 실패시 fallback
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        # 기본 테이블들 생성
        cursor.execute(
            """
        CREATE TABLE IF NOT EXISTS blacklist_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL UNIQUE,
            source TEXT NOT NULL DEFAULT 'test',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        )

        conn.commit()
        conn.close()

        yield ":memory:"


@pytest.fixture
def mock_database_connection(test_database):
    """모킹된 데이터베이스 연결"""
    from unittest.mock import MagicMock

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    # 기본 쿼리 응답 설정
    mock_cursor.fetchall.return_value = [
        ("192.168.1.1", "TEST_SOURCE", "2024-01-01", 0.9, 1),
        ("10.0.0.1", "REGTECH", "2024-01-02", 0.8, 1),
    ]
    mock_cursor.fetchone.return_value = ("192.168.1.1", "TEST_SOURCE")
    mock_cursor.rowcount = 2

    return mock_conn
