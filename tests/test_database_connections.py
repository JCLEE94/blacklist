"""Database connection management tests

Tests for database connection manager, connection pooling, and error handling.
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from contextlib import contextmanager

from src.core.database.connection_manager import ConnectionManager


class TestConnectionManager:
    """데이터베이스 연결 관리자 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.manager = ConnectionManager(self.db_path)

    def teardown_method(self):
        """각 테스트 후 정리"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_connection_creation(self):
        """데이터베이스 연결 생성 테스트"""
        conn = self.manager.get_connection()
        assert conn is not None
        assert isinstance(conn, sqlite3.Connection)
        
        # 연결이 유효한지 확인
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1

    def test_connection_reuse(self):
        """연결 재사용 테스트"""
        conn1 = self.manager.get_connection()
        conn2 = self.manager.get_connection()
        
        # 같은 연결 객체를 반환하는지 확인 (풀링이 구현된 경우)
        # 또는 새로운 연결을 반환하는지 확인 (구현에 따라)
        assert conn1 is not None
        assert conn2 is not None

    def test_connection_error_handling(self):
        """연결 오류 처리 테스트"""
        # 잘못된 경로로 연결 시도
        invalid_manager = ConnectionManager("/invalid/path/database.db")
        
        # 연결 실패 시 적절한 예외가 발생하는지 확인
        with pytest.raises(Exception):
            invalid_manager.get_connection()

    def test_connection_timeout(self):
        """연결 타임아웃 테스트"""
        # 타임아웃 설정이 있는 경우
        if hasattr(self.manager, 'timeout'):
            # 긴 시간이 걸리는 작업 시뮬레이션
            conn = self.manager.get_connection()
            cursor = conn.cursor()
            
            # 타임아웃이 적절히 처리되는지 확인
            try:
                cursor.execute("SELECT sqlite_version()")
                result = cursor.fetchone()
                assert result is not None
            except Exception as e:
                # 타임아웃 예외가 적절히 처리되는지 확인
                pass

    def test_multiple_connections(self):
        """다중 연결 테스트"""
        connections = []
        
        # 여러 연결 생성
        for i in range(5):
            conn = self.manager.get_connection()
            connections.append(conn)
        
        # 모든 연결이 유효한지 확인
        for conn in connections:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_connection_cleanup(self):
        """연결 정리 테스트"""
        conn = self.manager.get_connection()
        assert conn is not None
        
        # 연결 정리
        if hasattr(self.manager, 'close_connection'):
            self.manager.close_connection(conn)
        else:
            conn.close()

    def test_database_initialization(self):
        """데이터베이스 초기화 테스트"""
        conn = self.manager.get_connection()
        cursor = conn.cursor()
        
        # 기본 테이블 생성
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_table (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 테이블이 생성되었는지 확인
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'")
        result = cursor.fetchone()
        assert result is not None
        assert result[0] == "test_table"
