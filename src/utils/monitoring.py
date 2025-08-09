"""
모니터링 및 메트릭 수집 유틸리티
"""

import logging
import time
from collections import defaultdict, deque
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict

import psutil

logger = logging.getLogger(__name__)

try:
    from prometheus_client import (CollectorRegistry, Counter, Gauge,
                                   Histogram, generate_latest)

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("Prometheus client not available")


class MetricsCollector:
    """메트릭 수집기"""

    def __init__(self, app_name: str = "secudium"):
        self.app_name = app_name
        self.metrics = defaultdict(lambda: deque(maxlen=1000))
        self.counters = defaultdict(int)

        if PROMETHEUS_AVAILABLE:
            self.registry = CollectorRegistry()

            # Prometheus 메트릭 정의
            self.request_count = Counter(
                "api_requests_total",
                "Total API requests",
                ["method", "endpoint", "status"],
                registry=self.registry,
            )

            self.request_duration = Histogram(
                "api_request_duration_seconds",
                "API request duration",
                ["method", "endpoint"],
                registry=self.registry,
            )

            self.blacklist_ips = Gauge(
                "blacklist_total_ips", "Total IPs in blacklist", registry=self.registry
            )

            self.active_ips = Gauge(
                "blacklist_active_ips",
                "Active IPs in blacklist",
                registry=self.registry,
            )

            self.cache_hits = Counter(
                "cache_hits_total",
                "Total cache hits",
                ["cache_type"],
                registry=self.registry,
            )

            self.cache_misses = Counter(
                "cache_misses_total",
                "Total cache misses",
                ["cache_type"],
                registry=self.registry,
            )

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """API 요청 기록"""
        # 내부 메트릭
        key = f"request:{method}:{endpoint}:{status}"
        self.counters[key] += 1
        self.metrics[f"duration:{endpoint}"].append(duration)

        # Prometheus 메트릭
        if PROMETHEUS_AVAILABLE:
            self.request_count.labels(
                method=method, endpoint=endpoint, status=str(status)
            ).inc()

            self.request_duration.labels(method=method, endpoint=endpoint).observe(
                duration
            )

    def update_blacklist_stats(self, total_ips: int, active_ips: int):
        """블랙리스트 통계 업데이트"""
        self.metrics["blacklist:total"].append(total_ips)
        self.metrics["blacklist:active"].append(active_ips)

        if PROMETHEUS_AVAILABLE:
            self.blacklist_ips.set(total_ips)
            self.active_ips.set(active_ips)

    def record_cache_hit(self, cache_type: str = "redis"):
        """캐시 히트 기록"""
        self.counters[f"cache:hit:{cache_type}"] += 1

        if PROMETHEUS_AVAILABLE:
            self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str = "redis"):
        """캐시 미스 기록"""
        self.counters[f"cache:miss:{cache_type}"] += 1

        if PROMETHEUS_AVAILABLE:
            self.cache_misses.labels(cache_type=cache_type).inc()

    def get_system_metrics(self) -> Dict[str, Any]:
        """시스템 메트릭 수집"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        return {
            "cpu_percent": cpu_percent,
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent,
            },
            "timestamp": datetime.now().isoformat(),
        }

    def record_metrics(self, metrics: Dict[str, Any]):
        """메트릭 기록 (monitoring loop용)"""
        time.time()
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                self.metrics[f"monitoring:{key}"].append(value)

        # 시스템 메트릭도 기록
        system_metrics = self.get_system_metrics()
        for key, value in system_metrics.items():
            if isinstance(value, (int, float)):
                self.metrics[f"system:{key}"].append(value)

    def get_app_metrics(self) -> Dict[str, Any]:
        """애플리케이션 메트릭 반환"""
        metrics = {
            "requests": dict(self.counters),
            "system": self.get_system_metrics(),
            "cache": {
                "hits": self.counters.get("cache:hit:redis", 0)
                + self.counters.get("cache:hit:memory", 0),
                "misses": self.counters.get("cache:miss:redis", 0)
                + self.counters.get("cache:miss:memory", 0),
            },
        }

        # 평균 응답 시간 계산
        duration_metrics = {}
        for key, values in self.metrics.items():
            if key.startswith("duration:") and values:
                endpoint = key.replace("duration:", "")
                duration_metrics[endpoint] = {
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                    "count": len(values),
                }

        metrics["durations"] = duration_metrics

        return metrics

    def export_prometheus(self) -> bytes:
        """Prometheus 형식으로 메트릭 내보내기"""
        if not PROMETHEUS_AVAILABLE:
            return b""

        return generate_latest(self.registry)


class HealthChecker:
    """헬스체크 관리"""

    def __init__(self):
        self.checks = {}
        self.last_check = {}

    def register_check(self, name: str, check_func: Callable, critical: bool = False):
        """헬스체크 등록"""
        self.checks[name] = {"func": check_func, "critical": critical}

    def run_checks(self) -> Dict[str, Any]:
        """모든 헬스체크 실행"""
        results = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        for name, check in self.checks.items():
            try:
                start_time = time.time()
                result = check["func"]()
                duration = time.time() - start_time

                results["checks"][name] = {
                    "status": "pass" if result else "fail",
                    "duration": duration,
                    "critical": check["critical"],
                }

                if not result and check["critical"]:
                    results["status"] = "unhealthy"

                self.last_check[name] = {
                    "timestamp": datetime.now(),
                    "result": result,
                    "duration": duration,
                }

            except Exception as e:
                results["checks"][name] = {
                    "status": "error",
                    "error": str(e),
                    "critical": check["critical"],
                }

                if check["critical"]:
                    results["status"] = "unhealthy"

        return results


def track_performance(metrics_collector: MetricsCollector):
    """성능 추적 데코레이터"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # Flask 응답인 경우
                if hasattr(result, "status_code"):
                    from flask import request

                    metrics_collector.record_request(
                        method=request.method,
                        endpoint=request.endpoint or request.path,
                        status=result.status_code,
                        duration=duration,
                    )

                return result

            except Exception:
                duration = time.time() - start_time

                # 오류도 기록
                from flask import request

                metrics_collector.record_request(
                    method=request.method,
                    endpoint=request.endpoint or request.path,
                    status=500,
                    duration=duration,
                )

                raise

        return wrapper

    return decorator


# 글로벌 인스턴스
_metrics_collector = None
_health_checker = None


def get_metrics_collector() -> MetricsCollector:
    """글로벌 메트릭 수집기 반환"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_health_checker() -> HealthChecker:
    """글로벌 헬스체커 반환"""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
