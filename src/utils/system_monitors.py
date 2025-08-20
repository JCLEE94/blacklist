"""
시스템 모니터링 및 데이터베이스 안정성 관리 클래스
"""

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Callable, Dict

import psutil
import psycopg2

# Import SystemHealth from the new location
from .system_health import SystemHealth

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
        logger.info(
            f"DatabaseStabilityManager initialized for {'PostgreSQL' if self.is_postgresql else 'SQLite'}"
        )

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
                except Exception as e:
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
                    except Exception as e:
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


class SystemMonitor:
    """시스템 모니터링 및 자동 복구"""

    def __init__(self, db_manager: DatabaseStabilityManager):
        self.db_manager = db_manager
        self.start_time = time.time()
        self.error_counts = {}
        self.monitoring_enabled = True
        self._monitor_thread = None
        self._monitoring_event = threading.Event()  # 이벤트 기반 대기용

    def get_system_health(self) -> SystemHealth:
        """시스템 전체 건강 상태 조회"""
        try:
            # CPU/메모리/디스크 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            # 데이터베이스 상태
            db_health = self.db_manager.check_database_health()
            # 업타임 계산
            uptime_seconds = int(time.time() - self.start_time)
            # 최근 1시간 에러 수
            error_count = self._count_recent_errors()
            # 경고 메시지 생성
            warnings = []
            if cpu_percent > 80:
                warnings.append(f"높은 CPU 사용률: {cpu_percent:.1f}%")
            if memory.percent > 80:
                warnings.append(f"높은 메모리 사용률: {memory.percent:.1f}%")
            if disk.percent > 80:
                warnings.append(f"높은 디스크 사용률: {disk.percent:.1f}%")
            if db_health["status"] != "healthy":
                warnings.append(
                    f"데이터베이스 상태 이상: {db_health.get('error', 'Unknown')}"
                )
            # Get actual cache status
            cache_health = self._check_cache_status()
            if cache_health["status"] != "healthy":
                warnings.append(
                    f"캐시 상태 이상: {cache_health.get('error', 'Unknown')}"
                )
            return SystemHealth(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_percent=disk.percent,
                database_status=db_health["status"],
                cache_status=cache_health["status"],
                uptime_seconds=uptime_seconds,
                active_connections=db_health.get("connection_pool_size", 0),
                error_count_last_hour=error_count,
                warnings=warnings,
            )
        except Exception as e:
            logger.error(f"System health check failed: {e}")
            return SystemHealth(
                database_status="error", warnings=[f"모니터링 오류: {str(e)}"]
            )

    def _count_recent_errors(self) -> int:
        """최근 1시간 에러 수 계산"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                if self.db_manager.is_postgresql:
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM system_logs
                        WHERE level IN ('ERROR', 'CRITICAL')
                        AND timestamp > %s
                    """,
                        (cutoff_time.isoformat(),),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM system_logs
                        WHERE level IN ('ERROR', 'CRITICAL')
                        AND timestamp > ?
                    """,
                        (cutoff_time.isoformat(),),
                    )
                result = cursor.fetchone()[0]
                cursor.close()
                return result
        except Exception as e:
            return 0

    def _check_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 확인"""
        try:
            # Redis 캐시 상태 확인
            from src.core.containers.utils import get_cache_manager

            cache_manager = get_cache_manager()
            if hasattr(cache_manager, "redis_client") and cache_manager.redis_client:
                try:
                    # Redis ping 테스트
                    cache_manager.redis_client.ping()
                    info = cache_manager.redis_client.info()
                    return {
                        "status": "healthy",
                        "type": "redis",
                        "memory_used": info.get("used_memory_human", "unknown"),
                        "connected_clients": info.get("connected_clients", 0),
                    }
                except Exception as e:
                    logger.warning(f"Redis health check failed: {e}")
                    return {"status": "degraded", "type": "memory", "error": str(e)}
            else:
                # 메모리 캐시 폴백
                return {
                    "status": "healthy",
                    "type": "memory",
                    "note": "Using memory cache fallback",
                }
        except Exception as e:
            logger.error(f"Cache status check failed: {e}")
            return {"status": "error", "error": str(e)}

    def log_system_event(
        self, level: str, message: str, component: str = None, **kwargs
    ):
        """시스템 이벤트 로깅"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                if self.db_manager.is_postgresql:
                    cursor.execute(
                        """
                        INSERT INTO system_logs
                        (level, message, logger_name, extra_data)
                        VALUES (%s, %s, %s, %s)
                    """,
                        (
                            level,
                            message,
                            component or "system_monitor",
                            str(kwargs) if kwargs else None,
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO system_logs
                        (level, message, component, additional_data)
                        VALUES (?, ?, ?, ?)
                    """,
                        (
                            level,
                            message,
                            component or "system_monitor",
                            str(kwargs) if kwargs else None,
                        ),
                    )
                cursor.close()
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")

    def start_monitoring(self, interval: int = 300):
        """백그라운드 모니터링 시작 (기본 5분 간격)"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            logger.warning("Monitoring already running")
            return

        def monitor_loop():
            while self.monitoring_enabled:
                try:
                    health = self.get_system_health()
                    # 임계 상태 시 자동 대응
                    if health.overall_status == "critical":
                        self.log_system_event(
                            "CRITICAL",
                            "System in critical state",
                            additional_data={
                                "cpu": health.cpu_percent,
                                "memory": health.memory_percent,
                                "errors": health.error_count_last_hour,
                            },
                        )
                        # 자동 복구 시도
                        self._attempt_auto_recovery(health)
                    elif health.overall_status == "warning":
                        self.log_system_event(
                            "WARNING",
                            "System performance degraded",
                            additional_data={"warnings": health.warnings},
                        )
                    # 이벤트 기반 대기 (성능 최적화)
                    self._monitoring_event.wait(timeout=interval)
                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}")
                    # 에러 시 이벤트 기반 대기
                    self._monitoring_event.wait(timeout=60)

        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"System monitoring started (interval: {interval}s)")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_enabled = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)
        logger.info("System monitoring stopped")

    def _attempt_auto_recovery(self, health: SystemHealth):
        """자동 복구 시도"""
        logger.info("Attempting auto-recovery...")
        # 데이터베이스 최적화
        if health.database_status != "healthy":
            success = self.db_manager.optimize_database()
            self.log_system_event(
                "INFO", f"Database optimization: {'success' if success else 'failed'}"
            )
        # 메모리 정리 (가비지 컴렉션)
        if health.memory_percent > 90:
            import gc

            gc.collect()
            self.log_system_event("INFO", "Forced garbage collection")


def safe_execute(func: Callable, default_return=None, log_errors: bool = True) -> Any:
    """안전한 함수 실행 래퍼"""
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"Safe execution failed for {func.__name__}: {e}")
        return default_return


def create_system_monitor(db_path: str = None) -> SystemMonitor:
    """시스템 모니터 인스턴스 생성"""
    if not db_path:
        db_path = os.environ.get("DATABASE_URL", "instance/blacklist.db")
        if db_path.startswith("sqlite:///"):
            db_path = db_path[10:]
    db_manager = DatabaseStabilityManager(db_path)
    monitor = SystemMonitor(db_manager)
    return monitor


# 전역 모니터 인스턴스
_global_monitor = None


def get_system_monitor() -> SystemMonitor:
    """전역 시스템 모니터 인스턴스 반환"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = create_system_monitor()
    return _global_monitor


def initialize_system_stability():
    """시스템 안정성 초기화"""
    monitor = get_system_monitor()
    monitor.start_monitoring()
    logger.info("System stability monitoring initialized")
    return monitor


if __name__ == "__main__":
    # Validation tests for system monitors
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: DatabaseStabilityManager creation
    total_tests += 1
    try:
        db_manager = DatabaseStabilityManager("test.db")
        if not hasattr(db_manager, "db_path"):
            all_validation_failures.append(
                "DatabaseStabilityManager initialization failed"
            )
    except Exception as e:
        all_validation_failures.append(f"DatabaseStabilityManager creation failed: {e}")

    # Test 2: SystemMonitor creation
    total_tests += 1
    try:
        db_manager = DatabaseStabilityManager("test.db")
        monitor = SystemMonitor(db_manager)
        if not hasattr(monitor, "db_manager"):
            all_validation_failures.append("SystemMonitor initialization failed")
    except Exception as e:
        all_validation_failures.append(f"SystemMonitor creation failed: {e}")

    # Test 3: Safe execute function
    total_tests += 1
    try:

        def test_func():
            return "success"

        result = safe_execute(test_func)
        if result != "success":
            all_validation_failures.append(
                f"Safe execute failed, expected 'success', got {result}"
            )
    except Exception as e:
        all_validation_failures.append(f"Safe execute test failed: {e}")
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
        sys.exit(0)
