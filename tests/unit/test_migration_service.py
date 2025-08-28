"""
Migration Service 테스트
"""

import os
import sqlite3
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.database.connection_manager import ConnectionManager
from src.core.database.migration_service import MigrationService
from src.core.database.table_definitions import TableDefinitions


class TestMigrationService:
    """MigrationService 테스트"""

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
    def migration_service(self):
        """Migration Service 인스턴스"""
        connection_manager = Mock()
        table_definitions = Mock()
        return MigrationService(connection_manager, table_definitions)

    @pytest.fixture
    def real_migration_service(self, temp_db):
        """실제 Migration Service 인스턴스"""
        # temp_db를 파일 경로로 변환
        db_path = temp_db.execute("PRAGMA database_list").fetchone()[2]
        connection_manager = ConnectionManager(db_path)
        table_definitions = TableDefinitions()
        return MigrationService(connection_manager, table_definitions)

    def test_init(self):
        """초기화 테스트"""
        connection_manager = Mock()
        table_definitions = Mock()

        service = MigrationService(connection_manager, table_definitions)

        assert service.connection_manager == connection_manager
        assert service.table_definitions == table_definitions
        assert service.schema_version == "2.0.0"

    def test_get_current_schema_version_exists(self, migration_service):
        """현재 스키마 버전 조회 - 존재하는 경우"""
        # Mock connection context manager
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_row = {"value": "1.5.0"}

        mock_cursor.fetchone.return_value = mock_row
        mock_conn.execute.return_value = mock_cursor
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        version = migration_service.get_current_schema_version()

        assert version == "1.5.0"
        mock_conn.execute.assert_called_once_with(
            "SELECT value FROM metadata WHERE key = ?", ("schema_version",)
        )

    def test_get_current_schema_version_not_exists(self, migration_service):
        """현재 스키마 버전 조회 - 존재하지 않는 경우"""
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None

        mock_conn.execute.return_value = mock_cursor
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        version = migration_service.get_current_schema_version()

        assert version is None

    def test_get_current_schema_version_exception(self, migration_service):
        """현재 스키마 버전 조회 - 예외 발생"""
        migration_service.connection_manager.get_connection.side_effect = Exception(
            "DB Error"
        )

        version = migration_service.get_current_schema_version()

        assert version is None

    def test_migrate_schema_already_current(self, migration_service):
        """스키마 마이그레이션 - 이미 최신 버전"""
        migration_service.get_current_schema_version = Mock(return_value="2.0.0")

        with patch("src.core.database.migration_service.logger") as mock_logger:
            result = migration_service.migrate_schema()

            assert result is True
            mock_logger.info.assert_called_with("스키마가 이미 최신 버전입니다.")

    @patch.object(MigrationService, "_migrate_to_v2")
    @patch.object(MigrationService, "_record_schema_version")
    def test_migrate_schema_from_v1(
        self, mock_record, mock_migrate_v2, migration_service
    ):
        """스키마 마이그레이션 - 1.x에서 2.0으로"""
        migration_service.get_current_schema_version = Mock(return_value="1.5.0")

        mock_conn = MagicMock()
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        with patch("src.core.database.migration_service.logger") as mock_logger:
            result = migration_service.migrate_schema()

            assert result is True
            mock_migrate_v2.assert_called_once_with(mock_conn)
            mock_record.assert_called_once_with(mock_conn)
            mock_conn.commit.assert_called_once()
            mock_logger.info.assert_called()

    @patch.object(MigrationService, "_migrate_to_v2")
    def test_migrate_schema_no_previous_version(
        self, mock_migrate_v2, migration_service
    ):
        """스키마 마이그레이션 - 이전 버전이 없는 경우"""
        migration_service.get_current_schema_version = Mock(return_value=None)

        mock_conn = MagicMock()
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        result = migration_service.migrate_schema()

        assert result is True
        # 메타데이터 테이블 생성 확인
        migration_service.table_definitions.create_metadata_table.assert_called_once_with(
            mock_conn
        )
        mock_migrate_v2.assert_called_once_with(mock_conn)

    def test_migrate_schema_exception(self, migration_service):
        """스키마 마이그레이션 - 예외 발생"""
        migration_service.get_current_schema_version = Mock(return_value="1.0.0")
        migration_service.connection_manager.get_connection.side_effect = Exception(
            "Migration failed"
        )

        with patch("src.core.database.migration_service.logger") as mock_logger:
            result = migration_service.migrate_schema()

            assert result is False
            mock_logger.error.assert_called()

    def test_migrate_to_v2(self, migration_service):
        """버전 2.0으로 마이그레이션 테스트"""
        mock_conn = Mock()

        migration_service._migrate_to_v2(mock_conn)

        # ALTER TABLE 실행 확인 (컬럼 추가)
        assert mock_conn.execute.call_count > 0

        # 새 테이블 생성 메서드 호출 확인
        migration_service.table_definitions.create_auth_attempts_table.assert_called_once_with(
            mock_conn
        )
        migration_service.table_definitions.create_system_status_table.assert_called_once_with(
            mock_conn
        )
        migration_service.table_definitions.create_cache_table.assert_called_once_with(
            mock_conn
        )
        migration_service.table_definitions.create_metadata_table.assert_called_once_with(
            mock_conn
        )
        migration_service.table_definitions.create_system_logs_table.assert_called_once_with(
            mock_conn
        )

    def test_migrate_to_v2_duplicate_column_error(self, migration_service):
        """버전 2.0 마이그레이션 - 중복 컬럼 에러 처리"""
        mock_conn = Mock()

        # 중복 컬럼 에러 시뮬레이션
        def side_effect(sql):
            if "ALTER TABLE" in sql and "source" in sql:
                raise sqlite3.OperationalError("duplicate column name: source")
            return Mock()

        mock_conn.execute.side_effect = side_effect

        with patch("src.core.database.migration_service.logger") as mock_logger:
            migration_service._migrate_to_v2(mock_conn)

            # 중복 컬럼에 대한 디버그 로그 확인
            mock_logger.debug.assert_called()

    def test_record_schema_version(self, migration_service):
        """스키마 버전 기록 테스트"""
        mock_conn = Mock()

        migration_service._record_schema_version(mock_conn)

        mock_conn.execute.assert_called_once_with(
            """
            INSERT OR REPLACE INTO metadata
            (key, value, value_type, description, category)
            VALUES (?, ?, ?, ?, ?)
        """,
            ("schema_version", "2.0.0", "string", "데이터베이스 스키마 버전", "system"),
        )

    def test_cleanup_old_data(self, migration_service):
        """오래된 데이터 정리 테스트"""
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 10
        mock_conn.execute.return_value = mock_cursor

        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        result = migration_service.cleanup_old_data(30)

        assert result >= 0  # 삭제된 레코드 수
        mock_conn.commit.assert_called_once()

        # 여러 테이블에서 삭제 쿼리가 실행되었는지 확인
        execute_calls = [call.args[0] for call in mock_conn.execute.call_args_list]
        assert any("DELETE FROM collection_logs" in sql for sql in execute_calls)
        assert any("DELETE FROM auth_attempts" in sql for sql in execute_calls)
        assert any("DELETE FROM system_status" in sql for sql in execute_calls)
        assert any("DELETE FROM cache_entries" in sql for sql in execute_calls)

    def test_cleanup_old_data_exception(self, migration_service):
        """오래된 데이터 정리 - 예외 발생"""
        migration_service.connection_manager.get_connection.side_effect = Exception(
            "Cleanup failed"
        )

        with patch("src.core.database.migration_service.logger") as mock_logger:
            result = migration_service.cleanup_old_data()

            assert result == 0
            mock_logger.error.assert_called()

    def test_vacuum_database(self, migration_service):
        """데이터베이스 압축 테스트"""
        mock_conn = MagicMock()
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        with patch("src.core.database.migration_service.logger") as mock_logger:
            result = migration_service.vacuum_database()

            assert result is True
            mock_conn.execute.assert_called_once_with("VACUUM")
            mock_logger.info.assert_called_with("데이터베이스 압축 완료")

    def test_vacuum_database_exception(self, migration_service):
        """데이터베이스 압축 - 예외 발생"""
        migration_service.connection_manager.get_connection.side_effect = Exception(
            "Vacuum failed"
        )

        with patch("src.core.database.migration_service.logger") as mock_logger:
            result = migration_service.vacuum_database()

            assert result is False
            mock_logger.error.assert_called()

    @pytest.mark.integration
    def test_real_migration_full_flow(self, temp_db, real_migration_service):
        """실제 전체 마이그레이션 플로우 통합 테스트"""
        # 메타데이터 테이블 생성
        TableDefinitions.create_metadata_table(temp_db)
        temp_db.commit()

        # 1.0 버전으로 시작
        temp_db.execute(
            """
            INSERT INTO metadata (key, value, value_type, description, category)
            VALUES ('schema_version', '1.0.0', 'string', 'Schema version', 'system')
        """
        )
        temp_db.commit()

        # 마이그레이션 실행
        result = real_migration_service.migrate_schema()
        assert result is True

        # 최종 버전 확인
        version = real_migration_service.get_current_schema_version()
        assert version == "2.0.0"

    @pytest.mark.integration
    def test_real_cleanup_old_data(self, temp_db, real_migration_service):
        """실제 오래된 데이터 정리 통합 테스트"""
        # 테이블 생성
        TableDefinitions.create_all_tables(temp_db)
        temp_db.commit()

        # 테스트 데이터 삽입
        temp_db.execute(
            """
            INSERT INTO collection_logs (source, status, timestamp)
            VALUES ('test', 'success', datetime('now', '-100 days'))
        """
        )
        temp_db.execute(
            """
            INSERT INTO auth_attempts (ip_address, success, timestamp)
            VALUES ('192.168.1.1', 1, datetime('now', '-100 days'))
        """
        )
        temp_db.commit()

        # 정리 실행
        deleted_count = real_migration_service.cleanup_old_data(30)
        assert deleted_count > 0

    @pytest.mark.integration
    def test_real_vacuum_database(self, temp_db, real_migration_service):
        """실제 데이터베이스 압축 통합 테스트"""
        # 테이블 생성
        TableDefinitions.create_all_tables(temp_db)
        temp_db.commit()

        # 압축 실행 (예외가 발생하지 않아야 함)
        result = real_migration_service.vacuum_database()
        assert result is True

    def test_schema_version_persistence(self, temp_db, real_migration_service):
        """스키마 버전 지속성 테스트"""
        # 초기 버전 없음
        version = real_migration_service.get_current_schema_version()
        assert version is None

        # 마이그레이션 실행
        result = real_migration_service.migrate_schema()
        assert result is True

        # 버전이 기록되었는지 확인
        version = real_migration_service.get_current_schema_version()
        assert version == "2.0.0"

        # 다시 마이그레이션 시도 (이미 최신 버전이므로 스킵되어야 함)
        result = real_migration_service.migrate_schema()
        assert result is True

    def test_cleanup_system_logs_table_missing(self, migration_service):
        """시스템 로그 테이블이 없을 때 정리 테스트"""
        mock_conn = MagicMock()

        def side_effect(sql):
            if "DELETE FROM system_logs" in sql:
                raise sqlite3.OperationalError("no such table: system_logs")
            mock_cursor = Mock()
            mock_cursor.rowcount = 5
            return mock_cursor

        mock_conn.execute.side_effect = side_effect
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        # 예외가 발생해도 계속 진행되어야 함
        result = migration_service.cleanup_old_data()
        assert result >= 0

    @patch("src.core.database.migration_service.logger")
    def test_logging_migration_success(self, mock_logger, migration_service):
        """마이그레이션 성공 시 로깅 테스트"""
        migration_service.get_current_schema_version = Mock(return_value="1.0.0")

        mock_conn = MagicMock()
        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        migration_service.migrate_schema()

        # 성공 로그 확인
        success_calls = [
            call for call in mock_logger.info.call_args_list if "마이그레이션 완료" in str(call)
        ]
        assert len(success_calls) > 0

    @patch("src.core.database.migration_service.logger")
    def test_logging_cleanup_success(self, mock_logger, migration_service):
        """데이터 정리 성공 시 로깅 테스트"""
        mock_conn = MagicMock()
        mock_cursor = Mock()
        mock_cursor.rowcount = 15
        mock_conn.execute.return_value = mock_cursor

        migration_service.connection_manager.get_connection.return_value.__enter__ = (
            Mock(return_value=mock_conn)
        )
        migration_service.connection_manager.get_connection.return_value.__exit__ = (
            Mock(return_value=None)
        )

        migration_service.cleanup_old_data()

        # 정리 완료 로그 확인
        mock_logger.info.assert_called()
        info_call = mock_logger.info.call_args[0][0]
        assert "데이터 정리 완료" in info_call
