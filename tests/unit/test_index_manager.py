"""
Index Manager 테스트
"""

import sqlite3
import tempfile
import os
import pytest
from unittest.mock import Mock, patch, call

from src.core.database.index_manager import IndexManager
from src.core.database.table_definitions import TableDefinitions


class TestIndexManager:
    """IndexManager 테스트"""

    @pytest.fixture
    def temp_db(self):
        """테이블이 있는 임시 데이터베이스 생성"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # 테이블 생성
        TableDefinitions.create_all_tables(conn)
        yield conn
        
        conn.close()
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def mock_conn(self):
        """Mock 연결 객체"""
        conn = Mock()
        return conn

    def test_create_indexes(self, mock_conn):
        """인덱스 생성 테스트"""
        IndexManager.create_indexes(mock_conn)
        
        # execute가 여러 번 호출되었는지 확인
        assert mock_conn.execute.call_count > 0
        
        # 일부 중요한 인덱스가 생성되었는지 확인
        executed_sqls = [call.args[0] for call in mock_conn.execute.call_args_list]
        
        # 블랙리스트 관련 인덱스
        assert any("idx_blacklist_ip" in sql for sql in executed_sqls)
        assert any("idx_blacklist_active" in sql for sql in executed_sqls)
        assert any("idx_blacklist_source" in sql for sql in executed_sqls)
        
        # 수집 로그 관련 인덱스
        assert any("idx_collection_timestamp" in sql for sql in executed_sqls)
        assert any("idx_collection_source" in sql for sql in executed_sqls)
        
        # 인증 시도 관련 인덱스
        assert any("idx_auth_timestamp" in sql for sql in executed_sqls)
        assert any("idx_auth_ip" in sql for sql in executed_sqls)

    def test_create_indexes_with_sql_content(self, mock_conn):
        """인덱스 생성 SQL 내용 테스트"""
        IndexManager.create_indexes(mock_conn)
        
        executed_sqls = [call.args[0] for call in mock_conn.execute.call_args_list]
        
        # SQL이 CREATE INDEX 문인지 확인
        for sql in executed_sqls:
            assert "CREATE INDEX IF NOT EXISTS" in sql
        
        # 특정 인덱스 SQL 검증
        ip_index_sql = next((sql for sql in executed_sqls if "idx_blacklist_ip" in sql), None)
        assert ip_index_sql is not None
        assert "blacklist_entries(ip_address)" in ip_index_sql

    def test_create_indexes_exception_handling(self, mock_conn):
        """인덱스 생성 중 예외 처리 테스트"""
        # 일부 execute 호출에서 예외 발생
        def side_effect(sql):
            if "idx_blacklist_ip" in sql:
                raise sqlite3.Error("Index creation failed")
            return Mock()
        
        mock_conn.execute.side_effect = side_effect
        
        # 예외가 발생해도 중단되지 않아야 함
        with patch('src.core.database.index_manager.logger') as mock_logger:
            IndexManager.create_indexes(mock_conn)
            
            # 경고 로그가 기록되었는지 확인
            mock_logger.warning.assert_called()

    def test_drop_index(self, mock_conn):
        """인덱스 삭제 테스트"""
        index_name = "idx_test_index"
        
        IndexManager.drop_index(mock_conn, index_name)
        
        mock_conn.execute.assert_called_once_with(f"DROP INDEX IF EXISTS {index_name}")

    def test_drop_index_with_exception(self, mock_conn):
        """인덱스 삭제 중 예외 처리 테스트"""
        mock_conn.execute.side_effect = sqlite3.Error("Drop failed")
        
        with patch('src.core.database.index_manager.logger') as mock_logger:
            IndexManager.drop_index(mock_conn, "test_index")
            
            # 경고 로그가 기록되었는지 확인
            mock_logger.warning.assert_called()

    def test_analyze_database(self, mock_conn):
        """데이터베이스 통계 업데이트 테스트"""
        IndexManager.analyze_database(mock_conn)
        
        mock_conn.execute.assert_called_once_with("ANALYZE")

    def test_analyze_database_with_exception(self, mock_conn):
        """데이터베이스 통계 업데이트 중 예외 처리 테스트"""
        mock_conn.execute.side_effect = sqlite3.Error("Analyze failed")
        
        with patch('src.core.database.index_manager.logger') as mock_logger:
            IndexManager.analyze_database(mock_conn)
            
            # 경고 로그가 기록되었는지 확인
            mock_logger.warning.assert_called()

    @pytest.mark.integration
    def test_real_create_indexes(self, temp_db):
        """실제 인덱스 생성 통합 테스트"""
        # 인덱스 생성
        IndexManager.create_indexes(temp_db)
        temp_db.commit()
        
        # 인덱스가 생성되었는지 확인
        cursor = temp_db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        indexes = [row["name"] for row in cursor.fetchall()]
        
        # 주요 인덱스가 생성되었는지 확인
        expected_indexes = [
            "idx_blacklist_ip",
            "idx_blacklist_active", 
            "idx_blacklist_source",
            "idx_collection_timestamp",
            "idx_collection_source",
            "idx_auth_timestamp",
            "idx_auth_ip"
        ]
        
        for expected_index in expected_indexes:
            assert expected_index in indexes

    @pytest.mark.integration
    def test_real_drop_index(self, temp_db):
        """실제 인덱스 삭제 통합 테스트"""
        # 인덱스 생성
        IndexManager.create_indexes(temp_db)
        temp_db.commit()
        
        # 특정 인덱스 삭제
        IndexManager.drop_index(temp_db, "idx_blacklist_ip")
        temp_db.commit()
        
        # 인덱스가 삭제되었는지 확인
        cursor = temp_db.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index' AND name='idx_blacklist_ip'
        """)
        result = cursor.fetchone()
        assert result is None

    @pytest.mark.integration
    def test_real_analyze_database(self, temp_db):
        """실제 데이터베이스 분석 통합 테스트"""
        # 테스트 데이터 삽입
        temp_db.execute("""
            INSERT INTO blacklist_entries (ip_address, source)
            VALUES ('192.168.1.1', 'test')
        """)
        temp_db.commit()
        
        # 분석 실행 (예외가 발생하지 않아야 함)
        IndexManager.analyze_database(temp_db)

    @pytest.mark.integration
    def test_index_performance_benefit(self, temp_db):
        """인덱스 성능 향상 테스트"""
        # 테스트 데이터 대량 삽입
        test_data = [(f"192.168.1.{i}", "test", 1) for i in range(1, 101)]
        temp_db.executemany("""
            INSERT INTO blacklist_entries (ip_address, source, is_active)
            VALUES (?, ?, ?)
        """, test_data)
        temp_db.commit()
        
        # 인덱스 생성 전 쿼리 실행 계획
        cursor = temp_db.execute("EXPLAIN QUERY PLAN SELECT * FROM blacklist_entries WHERE ip_address = '192.168.1.50'")
        plan_without_index = cursor.fetchall()
        
        # 인덱스 생성
        IndexManager.create_indexes(temp_db)
        temp_db.commit()
        
        # 인덱스 생성 후 쿼리 실행 계획
        cursor = temp_db.execute("EXPLAIN QUERY PLAN SELECT * FROM blacklist_entries WHERE ip_address = '192.168.1.50'")
        plan_with_index = cursor.fetchall()
        
        # 실행 계획이 다르면 인덱스가 사용되고 있음을 의미
        assert plan_without_index != plan_with_index

    @pytest.mark.integration
    def test_compound_indexes(self, temp_db):
        """복합 인덱스 테스트"""
        IndexManager.create_indexes(temp_db)
        temp_db.commit()
        
        # 복합 인덱스가 생성되었는지 확인
        cursor = temp_db.execute("""
            SELECT sql FROM sqlite_master 
            WHERE type='index' AND name='idx_blacklist_active_source'
        """)
        result = cursor.fetchone()
        assert result is not None
        
        # 복합 인덱스 SQL에 두 컬럼이 모두 포함되어 있는지 확인
        index_sql = result["sql"]
        assert "is_active" in index_sql
        assert "source" in index_sql

    def test_index_names_uniqueness(self, mock_conn):
        """인덱스 이름 중복 확인 테스트"""
        IndexManager.create_indexes(mock_conn)
        
        executed_sqls = [call.args[0] for call in mock_conn.execute.call_args_list]
        
        # 인덱스 이름 추출
        index_names = []
        for sql in executed_sqls:
            if "CREATE INDEX IF NOT EXISTS" in sql:
                # "CREATE INDEX IF NOT EXISTS idx_name" 에서 인덱스 이름 추출
                parts = sql.split()
                idx_index = parts.index("NOT") + 2  # "EXISTS" 다음이 인덱스 이름
                if idx_index < len(parts):
                    index_names.append(parts[idx_index])
        
        # 인덱스 이름이 중복되지 않는지 확인
        assert len(index_names) == len(set(index_names))

    def test_index_sql_syntax(self, temp_db):
        """인덱스 SQL 구문 검증 테스트"""
        # 각 인덱스 생성이 SQL 오류를 발생시키지 않는지 테스트
        try:
            IndexManager.create_indexes(temp_db)
            temp_db.commit()
        except sqlite3.Error as e:
            pytest.fail(f"Invalid SQL syntax in index creation: {e}")

    def test_idempotent_index_creation(self, temp_db):
        """멱등성 인덱스 생성 테스트 (여러 번 실행해도 안전)"""
        # 첫 번째 인덱스 생성
        IndexManager.create_indexes(temp_db)
        temp_db.commit()
        
        # 인덱스 개수 확인
        cursor = temp_db.execute("""
            SELECT COUNT(*) as count FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        first_count = cursor.fetchone()["count"]
        
        # 두 번째 인덱스 생성 (IF NOT EXISTS 때문에 안전해야 함)
        IndexManager.create_indexes(temp_db)
        temp_db.commit()
        
        # 인덱스 개수가 동일해야 함
        cursor = temp_db.execute("""
            SELECT COUNT(*) as count FROM sqlite_master 
            WHERE type='index' AND name LIKE 'idx_%'
        """)
        second_count = cursor.fetchone()["count"]
        
        assert first_count == second_count

    @patch('src.core.database.index_manager.logger')
    def test_logging_on_success(self, mock_logger, temp_db):
        """성공 시 로깅 테스트"""
        IndexManager.analyze_database(temp_db)
        
        mock_logger.info.assert_called_with("데이터베이스 통계 업데이트 완료")

    @patch('src.core.database.index_manager.logger')
    def test_logging_on_drop_success(self, mock_logger, temp_db):
        """인덱스 삭제 성공 시 로깅 테스트"""
        # 인덱스 생성 후 삭제
        IndexManager.create_indexes(temp_db)
        IndexManager.drop_index(temp_db, "idx_blacklist_ip")
        
        mock_logger.info.assert_called_with("인덱스 삭제: idx_blacklist_ip")

    def test_all_table_indexes_coverage(self, mock_conn):
        """모든 테이블에 대한 인덱스 커버리지 테스트"""
        IndexManager.create_indexes(mock_conn)
        
        executed_sqls = [call.args[0] for call in mock_conn.execute.call_args_list]
        
        # 모든 주요 테이블에 대한 인덱스가 있는지 확인
        expected_tables = [
            "blacklist_entries",
            "collection_logs", 
            "auth_attempts",
            "system_status",
            "cache_entries",
            "metadata",
            "system_logs"
        ]
        
        for table in expected_tables:
            # 각 테이블에 대한 인덱스가 최소 하나는 있는지 확인
            has_index = any(table in sql for sql in executed_sqls)
            assert has_index, f"No index found for table: {table}"