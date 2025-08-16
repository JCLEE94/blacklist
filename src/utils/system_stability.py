"""
시스템 안정성 모니터링 및 자동 복구 유틸리티
"""

import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List

import psutil

logger = logging.getLogger(__name__)


@dataclass
class SystemHealth:
    """시스템 건강 상태"""

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    database_status: str = "unknown"
    cache_status: str = "unknown"
    uptime_seconds: int = 0
    active_connections: int = 0
    error_count_last_hour: int = 0
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def overall_status(self) -> str:
        """전체적인 시스템 상태"""
        if self.error_count_last_hour > 50:
            return "critical"
        elif self.cpu_percent > 90 or self.memory_percent > 90:
            return "warning"
        elif self.database_status != "healthy":
            return "warning"
        else:
            return "healthy"


class DatabaseStabilityManager:
    """데이터베이스 안정성 관리"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.connection_pool = []
        self.max_connections = 10
        self.lock = threading.Lock()

    @contextmanager
    def get_connection(self):
        """안전한 데이터베이스 연결 획득"""
        conn = None
        try:
            with self.lock:
                if self.connection_pool:
                    conn = self.connection_pool.pop()
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
        """데이터베이스 건강 상태 확인"""
        try:
            with self.get_connection() as conn:
                # 기본 연결 테스트
                conn.execute("SELECT 1").fetchone()

                # 테이블 개수 확인
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM sqlite_master
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                """
                )
                table_count = cursor.fetchone()[0]

                # 데이터베이스 크기 확인
                cursor = conn.execute("PRAGMA page_count")
                page_count = cursor.fetchone()[0]
                cursor = conn.execute("PRAGMA page_size")
                page_size = cursor.fetchone()[0]
                db_size_mb = (page_count * page_size) / (1024 * 1024)

                # 인덱스 상태 확인
                cursor = conn.execute(
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
                }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "connection_pool_size": len(self.connection_pool),
            }

    def _check_cache_status(self) -> Dict[str, Any]:
        """Check cache (Redis) health status"""
        try:
            # Try to import and check Redis backend
            from src.utils.advanced_cache.redis_backend import RedisBackend

            # Create a Redis backend instance to check health
            redis_backend = RedisBackend()
            health = redis_backend.health_check()

            return health
        except ImportError:
            # If Redis backend is not available, try basic Redis check
            try:
                import redis

                r = redis.Redis.from_url(
                    os.environ.get("REDIS_URL", "redis://localhost:6379/0")
                )
                r.ping()
                return {"status": "healthy", "available": True}
            except Exception as e:
                logger.debug(f"Redis not available: {e}")
                return {
                    "status": "degraded",
                    "available": False,
                    "error": "Using memory cache",
                }
        except Exception as e:
            logger.debug(f"Cache health check failed: {e}")
            return {"status": "degraded", "available": False, "error": str(e)}

    def optimize_database(self) -> bool:
        """데이터베이스 최적화 실행"""
        try:
            with self.get_connection() as conn:
                logger.info("데이터베이스 최적화 시작...")

                # VACUUM으로 데이터베이스 정리
                conn.execute("VACUUM")

                # 통계 업데이트
                conn.execute("ANALYZE")

                # 오래된 로그 정리 (30일 이상)
                cutoff_date = datetime.now() - timedelta(days=30)
                conn.execute(
                    """
                    DELETE FROM system_logs
                    WHERE timestamp < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                # 만료된 인증 시도 기록 정리 (7일 이상)
                cutoff_date = datetime.now() - timedelta(days=7)
                conn.execute(
                    """
                    DELETE FROM auth_attempts
                    WHERE attempt_time < ?
                """,
                    (cutoff_date.isoformat(),),
                )

                conn.commit()
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
                warnings.append("높은 CPU 사용률: {cpu_percent:.1f}%")
            if memory.percent > 80:
                warnings.append("높은 메모리 사용률: {memory.percent:.1f}%")
            if disk.percent > 80:
                warnings.append("높은 디스크 사용률: {disk.percent:.1f}%")
            if db_health["status"] != "healthy":
                warnings.append(
                    "데이터베이스 상태 이상: {db_health.get('error', 'Unknown')}"
                )

            # Get actual cache status
            cache_health = self._check_cache_status()
            if cache_health["status"] != "healthy":
                warnings.append(
                    "캐시 상태 이상: {cache_health.get('error', 'Unknown')}"
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
                database_status="error", warnings=["모니터링 오류: {str(e)}"]
            )

    def _count_recent_errors(self) -> int:
        """최근 1시간 에러 수 계산"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=1)
            with self.db_manager.get_connection() as conn:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*) FROM system_logs
                    WHERE level IN ('ERROR', 'CRITICAL')
                    AND timestamp > ?
                """,
                    (cutoff_time.isoformat(),),
                )
                return cursor.fetchone()[0]
        except Exception as e:
            return 0


    def _check_cache_status(self) -> Dict[str, Any]:
        """캐시 상태 확인"""
        try:
            # Redis 캐시 상태 확인
            from src.core.cache_manager import get_cache_manager
            cache_manager = get_cache_manager()
            
            if hasattr(cache_manager, 'redis_client') and cache_manager.redis_client:
                try:
                    # Redis ping 테스트
                    cache_manager.redis_client.ping()
                    info = cache_manager.redis_client.info()
                    return {
                        "status": "healthy",
                        "type": "redis",
                        "memory_used": info.get('used_memory_human', 'unknown'),
                        "connected_clients": info.get('connected_clients', 0)
                    }
                except Exception as e:
                    logger.warning(f"Redis health check failed: {e}")
                    return {
                        "status": "degraded",
                        "type": "memory",
                        "error": str(e)
                    }
            else:
                # 메모리 캐시 폴백
                return {
                    "status": "healthy",
                    "type": "memory",
                    "note": "Using memory cache fallback"
                }
        except Exception as e:
            logger.error(f"Cache status check failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    def log_system_event(self, level: str, message: str, module: str = None, **kwargs):
        """시스템 이벤트 로깅"""
        try:
            with self.db_manager.get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO system_logs
                    (level, message, module, additional_data)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        level,
                        message,
                        module or "system_monitor",
                        str(kwargs) if kwargs else None,
                    ),
                )
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

                    time.sleep(interval)

                except Exception as e:
                    logger.error(f"Monitoring loop error: {e}")
                    time.sleep(60)  # 에러 시 1분 대기

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
                "INFO", "Database optimization: {'success' if success else 'failed'}"
            )

        # 메모리 정리 (가비지 컬렉션)
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
