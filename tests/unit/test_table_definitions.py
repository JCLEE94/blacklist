"""
Table Definitions 테스트
"""

import os
import sqlite3
import tempfile
from unittest.mock import Mock, call, patch

import pytest

from src.core.database.table_definitions import TableDefinitions


class TestTableDefinitions:
    """TableDefinitions 테스트"""

    @pytest.fixture
    def temp_db(self):
        """임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        yield conn

        conn.close()
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def mock_conn(self):
        """Mock 연결 객체"""
        conn = Mock()
        conn.execute.return_value = Mock()
        return conn

    def test_create_blacklist_entries_table(self, mock_conn):
        """블랙리스트 엔트리 테이블 생성 테스트"""
        TableDefinitions.create_blacklist_entries_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        # 테이블 생성 SQL 검증
        assert "CREATE TABLE IF NOT EXISTS blacklist_entries" in sql_call
        assert "ip_address TEXT NOT NULL UNIQUE" in sql_call
        assert "source TEXT NOT NULL DEFAULT 'unknown'" in sql_call
        assert "severity_score REAL DEFAULT 0.0" in sql_call
        assert "confidence_level REAL DEFAULT 1.0" in sql_call

    def test_create_collection_logs_table(self, mock_conn):
        """수집 로그 테이블 생성 테스트"""
        TableDefinitions.create_collection_logs_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        assert "CREATE TABLE IF NOT EXISTS collection_logs" in sql_call
        assert "source TEXT NOT NULL" in sql_call
        assert "status TEXT NOT NULL" in sql_call
        assert "execution_time_ms REAL DEFAULT 0.0" in sql_call

    def test_create_auth_attempts_table(self, mock_conn):
        """인증 시도 테이블 생성 테스트"""
        TableDefinitions.create_auth_attempts_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        assert "CREATE TABLE IF NOT EXISTS auth_attempts" in sql_call
        assert "ip_address TEXT NOT NULL" in sql_call
        assert "success BOOLEAN NOT NULL" in sql_call
        assert "risk_score REAL DEFAULT 0.0" in sql_call

    def test_create_system_status_table(self, mock_conn):
        """시스템 상태 테이블 생성 테스트"""
        TableDefinitions.create_system_status_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        assert "CREATE TABLE IF NOT EXISTS system_status" in sql_call
        assert "component TEXT NOT NULL" in sql_call
        assert "status TEXT NOT NULL" in sql_call
        assert "response_time_ms REAL DEFAULT 0.0" in sql_call

    def test_create_cache_table(self, mock_conn):
        """캐시 테이블 생성 테스트"""
        TableDefinitions.create_cache_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        assert "CREATE TABLE IF NOT EXISTS cache_entries" in sql_call
        assert "key TEXT PRIMARY KEY" in sql_call
        assert "value TEXT NOT NULL" in sql_call
        assert "ttl INTEGER NOT NULL" in sql_call

    def test_create_metadata_table(self, mock_conn):
        """메타데이터 테이블 생성 테스트"""
        TableDefinitions.create_metadata_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        assert "CREATE TABLE IF NOT EXISTS metadata" in sql_call
        assert "key TEXT PRIMARY KEY" in sql_call
        assert "value TEXT NOT NULL" in sql_call
        assert "value_type TEXT DEFAULT 'string'" in sql_call

    def test_create_system_logs_table(self, mock_conn):
        """시스템 로그 테이블 생성 테스트"""
        TableDefinitions.create_system_logs_table(mock_conn)

        mock_conn.execute.assert_called_once()
        sql_call = mock_conn.execute.call_args[0][0]

        assert "CREATE TABLE IF NOT EXISTS system_logs" in sql_call
        assert "level TEXT NOT NULL" in sql_call
        assert "message TEXT NOT NULL" in sql_call

    @patch.object(TableDefinitions, "create_metadata_table")
    @patch.object(TableDefinitions, "create_blacklist_entries_table")
    @patch.object(TableDefinitions, "create_collection_logs_table")
    @patch.object(TableDefinitions, "create_auth_attempts_table")
    @patch.object(TableDefinitions, "create_system_status_table")
    @patch.object(TableDefinitions, "create_cache_table")
    @patch.object(TableDefinitions, "create_system_logs_table")
    def test_create_all_tables_success(
        self,
        mock_system_logs,
        mock_cache,
        mock_system_status,
        mock_auth_attempts,
        mock_collection_logs,
        mock_blacklist_entries,
        mock_metadata,
        mock_conn,
    ):
        """모든 테이블 생성 성공 테스트"""
        result = TableDefinitions.create_all_tables(mock_conn)

        assert result is True
        mock_metadata.assert_called_once_with(mock_conn)
        mock_blacklist_entries.assert_called_once_with(mock_conn)
        mock_collection_logs.assert_called_once_with(mock_conn)
        mock_auth_attempts.assert_called_once_with(mock_conn)
        mock_system_status.assert_called_once_with(mock_conn)
        mock_cache.assert_called_once_with(mock_conn)
        mock_system_logs.assert_called_once_with(mock_conn)
        mock_conn.commit.assert_called_once()

    @patch.object(TableDefinitions, "create_metadata_table")
    def test_create_all_tables_failure(self, mock_metadata, mock_conn):
        """테이블 생성 실패 테스트"""
        mock_metadata.side_effect = Exception("Table creation failed")

        result = TableDefinitions.create_all_tables(mock_conn)

        assert result is False
        mock_metadata.assert_called_once_with(mock_conn)

    def test_real_blacklist_entries_table_creation(self, temp_db):
        """실제 블랙리스트 엔트리 테이블 생성 테스트"""
        TableDefinitions.create_blacklist_entries_table(temp_db)

        # 테이블이 생성되었는지 확인
        cursor = temp_db.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='blacklist_entries'
        """
        )
        result = cursor.fetchone()
        assert result is not None
        assert result["name"] == "blacklist_entries"

        # 테이블 스키마 확인
        cursor = temp_db.execute("PRAGMA table_info(blacklist_entries)")
        columns = {row["name"]: row for row in cursor.fetchall()}

        assert "ip_address" in columns
        assert "source" in columns
        assert "severity_score" in columns
        assert columns["ip_address"]["notnull"] == 1  # NOT NULL

    def test_real_collection_logs_table_creation(self, temp_db):
        """실제 수집 로그 테이블 생성 테스트"""
        TableDefinitions.create_collection_logs_table(temp_db)

        # 테이블이 생성되었는지 확인
        cursor = temp_db.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='collection_logs'
        """
        )
        result = cursor.fetchone()
        assert result is not None

        # 테이블에 데이터 삽입 테스트
        temp_db.execute(
            """
            INSERT INTO collection_logs (source, status, items_collected)
            VALUES ('test', 'success', 10)
        """
        )
        temp_db.commit()

        cursor = temp_db.execute("SELECT * FROM collection_logs")
        row = cursor.fetchone()
        assert row["source"] == "test"
        assert row["status"] == "success"
        assert row["items_collected"] == 10

    def test_real_auth_attempts_table_creation(self, temp_db):
        """실제 인증 시도 테이블 생성 테스트"""
        TableDefinitions.create_auth_attempts_table(temp_db)

        # 테이블 데이터 삽입 테스트
        temp_db.execute(
            """
            INSERT INTO auth_attempts (ip_address, success, risk_score)
            VALUES ('192.168.1.1', 1, 0.5)
        """
        )
        temp_db.commit()

        cursor = temp_db.execute("SELECT * FROM auth_attempts")
        row = cursor.fetchone()
        assert row["ip_address"] == "192.168.1.1"
        assert row["success"] == 1
        assert row["risk_score"] == 0.5

    @pytest.mark.integration
    def test_real_create_all_tables_integration(self, temp_db):
        """실제 모든 테이블 생성 통합 테스트"""
        result = TableDefinitions.create_all_tables(temp_db)
        assert result is True

        # 모든 테이블이 생성되었는지 확인
        expected_tables = [
            "blacklist_entries",
            "collection_logs",
            "auth_attempts",
            "system_status",
            "cache_entries",
            "metadata",
            "system_logs",
        ]

        cursor = temp_db.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """
        )
        created_tables = [row["name"] for row in cursor.fetchall()]

        for table in expected_tables:
            assert table in created_tables
