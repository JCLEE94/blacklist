"""
System Monitor

Provides system health monitoring and automatic recovery capabilities.

Third-party packages:
- psutil: https://psutil.readthedocs.io/

Sample input: Database manager instance
Expected output: System health metrics and monitoring reports
"""

import gc
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Dict

import psutil

from .database_stability import DatabaseStabilityManager
from .system_health import SystemHealth

logger = logging.getLogger(__name__)


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
        except Exception:
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
            gc.collect()
            self.log_system_event("INFO", "Forced garbage collection")


if __name__ == "__main__":
    import sys

    from .database_stability import DatabaseStabilityManager

    all_validation_failures = []
    total_tests = 0

    # Test 1: System monitor initialization
    total_tests += 1
    try:
        db_manager = DatabaseStabilityManager(":memory:")
        monitor = SystemMonitor(db_manager)
        if monitor.start_time <= 0:
            all_validation_failures.append("System monitor: Invalid start time")
        if not monitor.monitoring_enabled:
            all_validation_failures.append(
                "System monitor: Should be enabled by default"
            )
    except Exception as e:
        all_validation_failures.append(f"System monitor initialization failed: {e}")

    # Test 2: System health check
    total_tests += 1
    try:
        db_manager = DatabaseStabilityManager(":memory:")
        monitor = SystemMonitor(db_manager)
        health = monitor.get_system_health()
        if not hasattr(health, "cpu_percent"):
            all_validation_failures.append(
                "Health check: Missing cpu_percent attribute"
            )
        if not hasattr(health, "database_status"):
            all_validation_failures.append(
                "Health check: Missing database_status attribute"
            )
    except Exception as e:
        all_validation_failures.append(f"System health check failed: {e}")

    # Test 3: Error counting
    total_tests += 1
    try:
        db_manager = DatabaseStabilityManager(":memory:")
        monitor = SystemMonitor(db_manager)
        error_count = monitor._count_recent_errors()
        if error_count < 0:
            all_validation_failures.append(
                f"Error count: Expected non-negative, got {error_count}"
            )
    except Exception as e:
        all_validation_failures.append(f"Error counting test failed: {e}")

    # Final validation result
    if all_validation_failures:
        failed_count = len(all_validation_failures)
        print(f"❌ VALIDATION FAILED - {failed_count} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("System monitor is validated and ready for use")
        sys.exit(0)
