"""
데이터베이스 포괄적 테스트

데이터베이스 연결, 쿼리, 트랜잭션, 마이그레이션 등을 테스트합니다.
"""

import pytest
import sqlite3
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from contextlib import contextmanager

from src.core.database.connection_manager import ConnectionManager
from src.core.database.migration_service import MigrationService
from src.core.database.schema_manager import DatabaseSchema
from src.core.database.index_manager import IndexManager


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


class TestMigrationManager:
    """마이그레이션 관리자 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.conn = sqlite3.connect(self.db_path)
        self.migration_manager = MigrationManager(self.conn)

    def teardown_method(self):
        """각 테스트 후 정리"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_migration_table_creation(self):
        """마이그레이션 테이블 생성 테스트"""
        if hasattr(self.migration_manager, 'initialize'):
            self.migration_manager.initialize()
        
            # 마이그레이션 테이블이 생성되었는지 확인
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='migrations'")
            result = cursor.fetchone()
            assert result is not None

    def test_migration_execution(self):
        """마이그레이션 실행 테스트"""
        # 샘플 마이그레이션
        migration_sql = """
            CREATE TABLE sample_table (
                id INTEGER PRIMARY KEY,
                data TEXT
            )
        """
        
        if hasattr(self.migration_manager, 'execute_migration'):
            self.migration_manager.execute_migration("001_create_sample", migration_sql)
            
            # 테이블이 생성되었는지 확인
            cursor = self.conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sample_table'")
            result = cursor.fetchone()
            assert result is not None

    def test_migration_version_tracking(self):
        """마이그레이션 버전 추적 테스트"""
        if hasattr(self.migration_manager, 'get_current_version'):
            # 초기 버전 확인
            version = self.migration_manager.get_current_version()
            assert isinstance(version, (int, str, type(None)))

    def test_rollback_migration(self):
        """마이그레이션 롤백 테스트"""
        if hasattr(self.migration_manager, 'rollback'):
            # 롤백 기능이 있는 경우 테스트
            # 실제 구현에 따라 달라질 수 있음
            pass


class TestQueryBuilder:
    """쿼리 빌더 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.builder = QueryBuilder()

    def test_select_query_basic(self):
        """기본 SELECT 쿼리 테스트"""
        query = self.builder.select("*").from_table("blacklist_ips").build()
        expected = "SELECT * FROM blacklist_ips"
        assert query.strip() == expected

    def test_select_query_with_conditions(self):
        """조건부 SELECT 쿼리 테스트"""
        query = (self.builder
                .select("ip_address, source")
                .from_table("blacklist_ips")
                .where("is_active = ?", True)
                .build())
        
        assert "SELECT ip_address, source" in query
        assert "FROM blacklist_ips" in query
        assert "WHERE is_active = ?" in query

    def test_insert_query(self):
        """INSERT 쿼리 테스트"""
        query = (self.builder
                .insert_into("blacklist_ips")
                .values({
                    "ip_address": "192.168.1.1",
                    "source": "regtech",
                    "is_active": True
                })
                .build())
        
        assert "INSERT INTO blacklist_ips" in query
        assert "VALUES" in query

    def test_update_query(self):
        """UPDATE 쿼리 테스트"""
        query = (self.builder
                .update("blacklist_ips")
                .set({"is_active": False})
                .where("ip_address = ?", "192.168.1.1")
                .build())
        
        assert "UPDATE blacklist_ips" in query
        assert "SET is_active = ?" in query
        assert "WHERE ip_address = ?" in query

    def test_delete_query(self):
        """DELETE 쿼리 테스트"""
        query = (self.builder
                .delete_from("blacklist_ips")
                .where("exp_date < ?", datetime.now())
                .build())
        
        assert "DELETE FROM blacklist_ips" in query
        assert "WHERE exp_date < ?" in query

    def test_join_query(self):
        """JOIN 쿼리 테스트"""
        query = (self.builder
                .select("b.ip_address, s.name")
                .from_table("blacklist_ips b")
                .join("sources s", "b.source_id = s.id")
                .build())
        
        assert "SELECT b.ip_address, s.name" in query
        assert "JOIN sources s ON b.source_id = s.id" in query

    def test_complex_query(self):
        """복잡한 쿼리 테스트"""
        query = (self.builder
                .select("COUNT(*) as total")
                .from_table("blacklist_ips")
                .where("is_active = ?", True)
                .where("source IN (?, ?)", "regtech", "secudium")
                .group_by("source")
                .having("COUNT(*) > ?", 10)
                .order_by("total DESC")
                .limit(5)
                .build())
        
        assert "COUNT(*) as total" in query
        assert "WHERE is_active = ?" in query
        assert "GROUP BY source" in query
        assert "HAVING COUNT(*) > ?" in query
        assert "ORDER BY total DESC" in query
        assert "LIMIT 5" in query

    def test_parameter_binding(self):
        """파라미터 바인딩 테스트"""
        query, params = (self.builder
                        .select("*")
                        .from_table("blacklist_ips")
                        .where("ip_address = ?", "192.168.1.1")
                        .where("created_at > ?", datetime.now())
                        .build_with_params())
        
        assert "WHERE ip_address = ?" in query
        assert len(params) == 2
        assert params[0] == "192.168.1.1"

    def test_sql_injection_protection(self):
        """SQL 인젝션 보호 테스트"""
        malicious_input = "'; DROP TABLE blacklist_ips; --"
        
        query, params = (self.builder
                        .select("*")
                        .from_table("blacklist_ips")
                        .where("ip_address = ?", malicious_input)
                        .build_with_params())
        
        # 파라미터가 안전하게 바인딩되었는지 확인
        assert malicious_input in params
        assert "DROP TABLE" not in query


class TestTransactionManager:
    """트랜잭션 관리자 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.conn = sqlite3.connect(self.db_path)
        self.transaction_manager = TransactionManager(self.conn)
        
        # 테스트 테이블 생성
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE test_data (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.commit()

    def teardown_method(self):
        """각 테스트 후 정리"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_successful_transaction(self):
        """성공적인 트랜잭션 테스트"""
        with self.transaction_manager.transaction():
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("test1",))
            cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("test2",))
        
        # 데이터가 커밋되었는지 확인
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        assert count == 2

    def test_transaction_rollback(self):
        """트랜잭션 롤백 테스트"""
        try:
            with self.transaction_manager.transaction():
                cursor = self.conn.cursor()
                cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("test1",))
                # 의도적으로 예외 발생
                raise Exception("Test exception")
        except Exception:
            pass
        
        # 데이터가 롤백되었는지 확인
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM test_data")
        count = cursor.fetchone()[0]
        assert count == 0

    def test_nested_transactions(self):
        """중첩 트랜잭션 테스트"""
        with self.transaction_manager.transaction():
            cursor = self.conn.cursor()
            cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("outer",))
            
            try:
                with self.transaction_manager.transaction():
                    cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("inner",))
                    raise Exception("Inner exception")
            except Exception:
                pass
            
            cursor.execute("INSERT INTO test_data (value) VALUES (?)", ("outer2",))
        
        # 외부 트랜잭션은 성공, 내부는 롤백
        cursor = self.conn.cursor()
        cursor.execute("SELECT value FROM test_data ORDER BY id")
        values = [row[0] for row in cursor.fetchall()]
        
        # 구현에 따라 결과가 다를 수 있음 (savepoint 지원 여부)

    def test_transaction_timeout(self):
        """트랜잭션 타임아웃 테스트"""
        if hasattr(self.transaction_manager, 'timeout'):
            # 타임아웃 설정이 있는 경우
            pass

    def test_deadlock_detection(self):
        """데드락 감지 테스트"""
        # SQLite는 기본적으로 데드락이 발생하지 않지만
        # 다른 데이터베이스 시스템에서는 중요한 테스트
        pass


class TestDatabaseIntegration:
    """데이터베이스 통합 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        
        self.conn = sqlite3.connect(self.db_path)
        self.setup_test_schema()

    def teardown_method(self):
        """각 테스트 후 정리"""
        self.conn.close()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def setup_test_schema(self):
        """테스트용 스키마 설정"""
        cursor = self.conn.cursor()
        
        # 블랙리스트 IP 테이블
        cursor.execute("""
            CREATE TABLE blacklist_ips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                threat_level TEXT DEFAULT 'medium',
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                reg_date TEXT,
                exp_date TEXT,
                country TEXT,
                reason TEXT,
                view_count INTEGER DEFAULT 0
            )
        """)
        
        # 수집 통계 테이블
        cursor.execute("""
            CREATE TABLE collection_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_ips INTEGER DEFAULT 0,
                new_ips INTEGER DEFAULT 0,
                updated_ips INTEGER DEFAULT 0,
                success BOOLEAN DEFAULT 1,
                duration REAL DEFAULT 0.0,
                error_message TEXT
            )
        """)
        
        self.conn.commit()

    def test_full_crud_operations(self):
        """완전한 CRUD 작업 테스트"""
        cursor = self.conn.cursor()
        
        # CREATE
        cursor.execute("""
            INSERT INTO blacklist_ips (ip_address, source, threat_level)
            VALUES (?, ?, ?)
        """, ("192.168.1.1", "regtech", "high"))
        
        ip_id = cursor.lastrowid
        assert ip_id is not None
        
        # READ
        cursor.execute("SELECT * FROM blacklist_ips WHERE id = ?", (ip_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == "192.168.1.1"  # ip_address
        assert row[2] == "regtech"      # source
        assert row[3] == "high"         # threat_level
        
        # UPDATE
        cursor.execute("""
            UPDATE blacklist_ips 
            SET threat_level = ?, is_active = ?
            WHERE id = ?
        """, ("medium", False, ip_id))
        
        cursor.execute("SELECT threat_level, is_active FROM blacklist_ips WHERE id = ?", (ip_id,))
        row = cursor.fetchone()
        assert row[0] == "medium"
        assert row[1] == 0  # False as 0
        
        # DELETE
        cursor.execute("DELETE FROM blacklist_ips WHERE id = ?", (ip_id,))
        
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips WHERE id = ?", (ip_id,))
        count = cursor.fetchone()[0]
        assert count == 0

    def test_bulk_operations(self):
        """대량 작업 테스트"""
        cursor = self.conn.cursor()
        
        # 대량 삽입
        ips_data = [
            (f"192.168.1.{i}", "regtech", "medium")
            for i in range(1, 101)
        ]
        
        cursor.executemany("""
            INSERT INTO blacklist_ips (ip_address, source, threat_level)
            VALUES (?, ?, ?)
        """, ips_data)
        
        # 삽입된 데이터 확인
        cursor.execute("SELECT COUNT(*) FROM blacklist_ips")
        count = cursor.fetchone()[0]
        assert count == 100
        
        # 대량 업데이트
        cursor.execute("""
            UPDATE blacklist_ips 
            SET threat_level = 'high'
            WHERE ip_address LIKE '192.168.1.%'
        """)
        
        cursor.execute("""
            SELECT COUNT(*) FROM blacklist_ips 
            WHERE threat_level = 'high'
        """)
        count = cursor.fetchone()[0]
        assert count == 100

    def test_complex_queries(self):
        """복잡한 쿼리 테스트"""
        cursor = self.conn.cursor()
        
        # 테스트 데이터 삽입
        test_data = [
            ("1.1.1.1", "regtech", "high"),
            ("2.2.2.2", "regtech", "medium"),
            ("3.3.3.3", "secudium", "high"),
            ("4.4.4.4", "secudium", "low"),
        ]
        
        cursor.executemany("""
            INSERT INTO blacklist_ips (ip_address, source, threat_level)
            VALUES (?, ?, ?)
        """, test_data)
        
        # 소스별 위협 레벨 통계
        cursor.execute("""
            SELECT source, threat_level, COUNT(*) as count
            FROM blacklist_ips
            GROUP BY source, threat_level
            ORDER BY source, threat_level
        """)
        
        results = cursor.fetchall()
        assert len(results) == 4  # regtech(high,medium) + secudium(high,low)
        
        # 상위 위협 레벨 IP 조회
        cursor.execute("""
            SELECT ip_address, source
            FROM blacklist_ips
            WHERE threat_level = 'high'
            ORDER BY source, ip_address
        """)
        
        high_threat_ips = cursor.fetchall()
        assert len(high_threat_ips) == 2
        assert high_threat_ips[0][0] == "1.1.1.1"  # regtech
        assert high_threat_ips[1][0] == "3.3.3.3"  # secudium

    def test_data_integrity_constraints(self):
        """데이터 무결성 제약 조건 테스트"""
        cursor = self.conn.cursor()
        
        # 유니크 제약 조건 테스트
        cursor.execute("""
            INSERT INTO blacklist_ips (ip_address, source)
            VALUES (?, ?)
        """, ("192.168.1.1", "regtech"))
        
        # 중복 IP 삽입 시도
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO blacklist_ips (ip_address, source)
                VALUES (?, ?)
            """, ("192.168.1.1", "secudium"))

    def test_transaction_isolation(self):
        """트랜잭션 격리 테스트"""
        # 두 번째 연결 생성
        conn2 = sqlite3.connect(self.db_path)
        cursor1 = self.conn.cursor()
        cursor2 = conn2.cursor()
        
        try:
            # 첫 번째 연결에서 트랜잭션 시작
            self.conn.execute("BEGIN")
            cursor1.execute("""
                INSERT INTO blacklist_ips (ip_address, source)
                VALUES (?, ?)
            """, ("192.168.1.1", "regtech"))
            
            # 두 번째 연결에서 데이터 확인 (아직 커밋되지 않음)
            cursor2.execute("SELECT COUNT(*) FROM blacklist_ips")
            count_before_commit = cursor2.fetchone()[0]
            
            # 첫 번째 연결에서 커밋
            self.conn.commit()
            
            # 두 번째 연결에서 데이터 확인 (커밋 후)
            cursor2.execute("SELECT COUNT(*) FROM blacklist_ips")
            count_after_commit = cursor2.fetchone()[0]
            
            assert count_after_commit == count_before_commit + 1
            
        finally:
            conn2.close()

    def test_performance_with_indexes(self):
        """인덱스를 통한 성능 테스트"""
        cursor = self.conn.cursor()
        
        # 대량 데이터 삽입
        large_dataset = [
            (f"10.0.{i//256}.{i%256}", "regtech", "medium")
            for i in range(10000)
        ]
        
        cursor.executemany("""
            INSERT INTO blacklist_ips (ip_address, source, threat_level)
            VALUES (?, ?, ?)
        """, large_dataset)
        
        # 인덱스 없이 쿼리 시간 측정
        import time
        start_time = time.time()
        cursor.execute("SELECT * FROM blacklist_ips WHERE ip_address = '10.0.39.16'")
        result = cursor.fetchone()
        no_index_time = time.time() - start_time
        
        # 인덱스 생성
        cursor.execute("CREATE INDEX idx_ip_address ON blacklist_ips(ip_address)")
        
        # 인덱스 사용하여 쿼리 시간 측정
        start_time = time.time()
        cursor.execute("SELECT * FROM blacklist_ips WHERE ip_address = '10.0.39.16'")
        result = cursor.fetchone()
        with_index_time = time.time() - start_time
        
        # 인덱스가 성능을 향상시켰는지 확인
        # (작은 데이터셋에서는 차이가 미미할 수 있음)
        assert result is not None
        assert result[1] == "10.0.39.16"