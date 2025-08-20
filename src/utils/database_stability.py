"""
Database Stability Manager

Handles database connection pooling and health monitoring for PostgreSQL and SQLite.

Third-party packages:
- psutil: https://psutil.readthedocs.io/
- psycopg2: https://www.psycopg.org/docs/

Sample input: Database connection string
Expected output: Health status and connection management
"""

import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Dict

import psycopg2

logger = logging.getLogger(__name__)


class DatabaseStabilityManager:
    """데이터베이스 안정성 관리 (PostgreSQL/SQLite 지원)"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_pool = []
        self.max_connections = 10
        self.lock = threading.Lock()
        # Detect database type
        self.is_postgresql = self.db_path.startswith("postgresql://")
        db_type = 'PostgreSQL' if self.is_postgresql else 'SQLite'
        logger.info(f"DatabaseStabilityManager initialized for {db_type}")

    @contextmanager
    def get_connection(self):
        """안전한 데이터베이스 연결 획득 (PostgreSQL/SQLite)"""
        conn = None
        try:
            with self.lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
                else:
                    if self.is_postgresql:
                        conn = psycopg2.connect(self.db_path)
                        conn.set_session(autocommit=False)
                    else:
                        conn = sqlite3.connect(
                            self.db_path, timeout=30.0, check_same_thread=False
                        )
                        # WAL 모드 활성화 (동시성 향상)
                        conn.execute("PRAGMA journal_mode=WAL")
                        conn.execute("PRAGMA synchronous=NORMAL")
                        conn.execute("PRAGMA cache_size=10000")
                        conn.execute("PRAGMA temp_store=MEMORY")
            yield conn
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            raise
        finally:
            if conn:
                try:
                    conn.commit()
                    with self.lock:
                        if len(self.connection_pool) < self.max_connections:
                            self.connection_pool.append(conn)
                        else:
                            conn.close()
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
                    try:
                        conn.close()
                    except Exception:
                        pass

    def check_database_health(self) -> Dict[str, Any]:
        """데이터베이스 건강 상태 확인 (PostgreSQL/SQLite)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if self.is_postgresql:
                    # PostgreSQL 건강 상태 확인
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    # 테이블 개수 확인
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema = 'public'
                        """
                    )
                    table_count = cursor.fetchone()[0]
                    # 데이터베이스 크기 확인
                    cursor.execute("SELECT pg_database_size(current_database())")
                    db_size_bytes = cursor.fetchone()[0]
                    db_size_mb = db_size_bytes / (1024 * 1024)
                    # 인덱스 상태 확인
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM pg_indexes
                        WHERE schemaname = 'public'
                        """
                    )
                    index_count = cursor.fetchone()[0]
                else:
                    # SQLite 건강 상태 확인
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    # 테이블 개수 확인
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM sqlite_master
                        WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    """
                    )
                    table_count = cursor.fetchone()[0]
                    # 데이터베이스 크기 확인
                    cursor.execute("PRAGMA page_count")
                    page_count = cursor.fetchone()[0]
                    cursor.execute("PRAGMA page_size")
                    page_size = cursor.fetchone()[0]
                    db_size_mb = (page_count * page_size) / (1024 * 1024)
                    # 인덱스 상태 확인
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM sqlite_master
                        WHERE type='index' AND name NOT LIKE 'sqlite_%'
                    """
                    )
                    index_count = cursor.fetchone()[0]
                return {
                    "status": "healthy",
                    "table_count": table_count,
                    "index_count": index_count,
                    "size_mb": round(db_size_mb, 2),
                    "connection_pool_size": len(self.connection_pool),
                    "database_type": "PostgreSQL" if self.is_postgresql else "SQLite",
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "connection_pool_size": len(self.connection_pool),
                "database_type": "PostgreSQL" if self.is_postgresql else "SQLite",
            }

    def optimize_database(self) -> bool:
        """데이터베이스 최적화 실행"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                logger.info("데이터베이스 최적화 시작...")

                if self.is_postgresql:
                    # PostgreSQL 최적화
                    cursor.execute("VACUUM ANALYZE")
                    # 오래된 로그 정리 (30일 이상)
                    cutoff_date = datetime.now() - timedelta(days=30)
                    cursor.execute(
                        """
                        DELETE FROM system_logs
                        WHERE timestamp < %s
                    """,
                        (cutoff_date.isoformat(),),
                    )
                    # 만료된 인증 시도 기록 정리 (7일 이상)
                    cutoff_date = datetime.now() - timedelta(days=7)
                    cursor.execute(
                        """
                        DELETE FROM auth_attempts
                        WHERE attempt_time < %s
                    """,
                        (cutoff_date.isoformat(),),
                    )
                else:
                    # SQLite 최적화
                    cursor.execute("VACUUM")
                    cursor.execute("ANALYZE")
                    # 오래된 로그 정리 (30일 이상)
                    cutoff_date = datetime.now() - timedelta(days=30)
                    cursor.execute(
                        """
                        DELETE FROM system_logs
                        WHERE timestamp < ?
                    """,
                        (cutoff_date.isoformat(),),
                    )
                    # 만료된 인증 시도 기록 정리 (7일 이상)
                    cutoff_date = datetime.now() - timedelta(days=7)
                    cursor.execute(
                        """
                        DELETE FROM auth_attempts
                        WHERE attempt_time < ?
                    """,
                        (cutoff_date.isoformat(),),
                    )

                conn.commit()
                cursor.close()
                logger.info("데이터베이스 최적화 완료")
                return True
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False


if __name__ == "__main__":
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: SQLite database stability manager
    total_tests += 1
    try:
        db_manager = DatabaseStabilityManager(":memory:")
        health = db_manager.check_database_health()
        if health["status"] != "healthy":
            all_validation_failures.append(
                f"SQLite health check: Expected healthy, got {health['status']}"
            )
        if health["database_type"] != "SQLite":
            all_validation_failures.append(
                f"SQLite type: Expected SQLite, got {health['database_type']}"
            )
    except Exception as e:
        all_validation_failures.append(f"SQLite test failed with error: {e}")

    # Test 2: PostgreSQL URL detection
    total_tests += 1
    try:
        pg_manager = DatabaseStabilityManager("postgresql://user:pass@localhost/db")
        if not pg_manager.is_postgresql:
            all_validation_failures.append(
                "PostgreSQL URL detection: Expected True for PostgreSQL URL"
            )
    except Exception as e:
        all_validation_failures.append(f"PostgreSQL URL test failed: {e}")

    # Test 3: Connection pool initialization
    total_tests += 1
    try:
        manager = DatabaseStabilityManager(":memory:")
        if len(manager.connection_pool) != 0:
            all_validation_failures.append(
                f"Connection pool: Expected empty pool, got size {len(manager.connection_pool)}"
            )
        if manager.max_connections != 10:
            all_validation_failures.append(
                f"Max connections: Expected 10, got {manager.max_connections}"
            )
    except Exception as e:
        all_validation_failures.append(f"Connection pool test failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Database stability manager is validated and ready for use")
        sys.exit(0)
