#!/usr/bin/env python3
"""
시스템 에러 복구 및 안정성 유틸리티
"""

import logging
import time
import traceback
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """서킷 브레이커 패턴 구현"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN for {func.__name__}")

            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """복구 시도 여부 확인"""
        return (
            self.last_failure_time
            and time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """성공 시 상태 리셋"""
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        """실패 시 상태 업데이트"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


def retry_with_backoff(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,),
    jitter: bool = True,
):
    """지수적 백오프를 사용한 재시도 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(f"Final retry failed for {func.__name__}: {e}")
                        raise e

                    # 지수적 백오프 계산
                    delay = backoff_factor**attempt
                    if jitter:
                        import random

                        delay *= 0.5 + random.random() * 0.5  # 50-100% 지터

                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


class ErrorCollector:
    """에러 수집 및 분석"""

    def __init__(self, max_errors: int = 1000):
        self.max_errors = max_errors
        self.errors: List[Dict[str, Any]] = []
        self.error_counts: Dict[str, int] = {}

    def record_error(
        self,
        error: Exception,
        context: str = "",
        additional_info: Dict[str, Any] = None,
    ):
        """에러 기록"""
        try:
            error_info = {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
                "traceback": traceback.format_exc(),
                "additional_info": additional_info or {},
            }

            self.errors.append(error_info)

            # 에러 타입별 카운트
            error_type = error_info["error_type"]
            self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

            # 최대 크기 제한
            if len(self.errors) > self.max_errors:
                self.errors = self.errors[-self.max_errors :]

            logger.error(f"Error recorded: {error_type} in {context}: {error}")

        except Exception as e:
            logger.error(f"Failed to record error: {e}")

    def get_error_summary(self) -> Dict[str, Any]:
        """에러 요약 통계"""
        if not self.errors:
            return {"total_errors": 0, "error_types": {}, "recent_errors": []}

        # 최근 1시간 에러
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_errors = [
            error
            for error in self.errors
            if datetime.fromisoformat(error["timestamp"]) > one_hour_ago
        ]

        return {
            "total_errors": len(self.errors),
            "recent_errors_count": len(recent_errors),
            "error_types": dict(self.error_counts),
            "recent_errors": recent_errors[-10:],  # 최근 10개
            "most_common_error": (
                max(self.error_counts.items(), key=lambda x: x[1])[0]
                if self.error_counts
                else None
            ),
        }

    def clear_old_errors(self, hours: int = 24):
        """오래된 에러 정리"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        original_count = len(self.errors)
        self.errors = [
            error
            for error in self.errors
            if datetime.fromisoformat(error["timestamp"]) > cutoff_time
        ]

        cleared_count = original_count - len(self.errors)
        if cleared_count > 0:
            logger.info(f"Cleared {cleared_count} old errors")


class HealthChecker:
    """시스템 헬스 체크"""

    def __init__(self):
        self.checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}

    def register_check(self, name: str, check_func: Callable):
        """헬스 체크 함수 등록"""
        self.checks[name] = check_func
        logger.info(f"Health check registered: {name}")

    def run_check(self, name: str) -> Dict[str, Any]:
        """개별 헬스 체크 실행"""
        if name not in self.checks:
            return {
                "status": "error",
                "message": "Unknown health check: {name}",
                "timestamp": datetime.now().isoformat(),
            }

        try:
            start_time = time.time()
            result = self.checks[name]()
            duration = time.time() - start_time

            check_result = {
                "status": "healthy",
                "result": result,
                "duration_ms": round(duration * 1000, 2),
                "timestamp": datetime.now().isoformat(),
            }

            self.last_check_results[name] = check_result
            return check_result

        except Exception as e:
            error_result = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

            self.last_check_results[name] = error_result
            logger.error(f"Health check failed for {name}: {e}")
            return error_result

    def run_all_checks(self) -> Dict[str, Any]:
        """모든 헬스 체크 실행"""
        results = {}
        overall_status = "healthy"

        for name in self.checks:
            result = self.run_check(name)
            results[name] = result

            if result["status"] != "healthy":
                overall_status = "degraded"

        return {
            "overall_status": overall_status,
            "checks": results,
            "timestamp": datetime.now().isoformat(),
        }

    def get_last_results(self) -> Dict[str, Any]:
        """마지막 체크 결과 반환"""
        return dict(self.last_check_results)


class ResourceMonitor:
    """리소스 사용량 모니터링"""

    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history = 1000

    def collect_metrics(self) -> Dict[str, Any]:
        """현재 리소스 메트릭 수집"""
        import os

        import psutil

        try:
            process = psutil.Process(os.getpid())

            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage("/").percent,
                "process_memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
                "process_cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "threads": process.num_threads(),
            }

            self.metrics_history.append(metrics)

            # 히스토리 크기 제한
            if len(self.metrics_history) > self.max_history:
                self.metrics_history = self.metrics_history[-self.max_history :]

            return metrics

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            return {"error": str(e), "timestamp": datetime.now().isoformat()}

    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """메트릭 요약 통계"""
        if not self.metrics_history:
            return {"error": "No metrics available"}

        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [
            metric
            for metric in self.metrics_history
            if datetime.fromisoformat(metric["timestamp"]) > cutoff_time
        ]

        if not recent_metrics:
            return {"error": "No metrics in last {hours} hours"}

        # 평균 계산
        cpu_values = [
            m.get("cpu_percent", 0) for m in recent_metrics if "cpu_percent" in m
        ]
        memory_values = [
            m.get("memory_percent", 0) for m in recent_metrics if "memory_percent" in m
        ]

        return {
            "period_hours": hours,
            "sample_count": len(recent_metrics),
            "avg_cpu_percent": (
                round(sum(cpu_values) / len(cpu_values), 2) if cpu_values else 0
            ),
            "avg_memory_percent": (
                round(sum(memory_values) / len(memory_values), 2)
                if memory_values
                else 0
            ),
            "max_cpu_percent": max(cpu_values) if cpu_values else 0,
            "max_memory_percent": max(memory_values) if memory_values else 0,
            "latest_metrics": recent_metrics[-1] if recent_metrics else None,
        }


# 전역 인스턴스들
_error_collector = ErrorCollector()
_health_checker = HealthChecker()
_resource_monitor = ResourceMonitor()


def get_error_collector() -> ErrorCollector:
    """전역 에러 수집기 반환"""
    return _error_collector


def get_health_checker() -> HealthChecker:
    """전역 헬스 체커 반환"""
    return _health_checker


def get_resource_monitor() -> ResourceMonitor:
    """전역 리소스 모니터 반환"""
    return _resource_monitor


def safe_execute(func: Callable, *args, **kwargs) -> tuple[Any, Optional[Exception]]:
    """안전한 함수 실행 (에러를 반환값으로 처리)"""
    try:
        result = func(*args, **kwargs)
        return result, None
    except Exception as e:
        _error_collector.record_error(e, context=func.__name__)
        return None, e


def log_performance(threshold_ms: float = 1000):
    """성능 로깅 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    logger.warning(
                        "Slow execution: {func.__name__} took {duration_ms:.2f}ms "
                        "(threshold: {threshold_ms}ms)"
                    )
                else:
                    logger.debug(
                        "Performance: {func.__name__} took {duration_ms:.2f}ms"
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(
                    "Function {func.__name__} failed after {duration_ms:.2f}ms: {e}"
                )
                raise

        return wrapper

    return decorator
