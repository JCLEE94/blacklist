"""
시스템 레벨 Prometheus 메트릭 관리 믹스인

핵심 시스템 메트릭과 애플리케이션 레벨 메트릭을 관리합니다.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """메트릭 정의 클래스"""

    name: str
    help_text: str
    metric_type: str  # counter, gauge, histogram, info
    labels: list = field(default_factory=list)
    buckets: Optional[list] = None  # histogram용


class SystemMetricsMixin:
    """시스템 메트릭 관리 믹스인"""

    def _define_core_metrics(self):
        """핵심 시스템 메트릭 정의"""
        core_metrics = [
            MetricDefinition(
                name="blacklist_up",
                help_text="시스템 가동 상태 (1=가동, 0=중단)",
                metric_type="gauge",
            ),
            MetricDefinition(
                name="blacklist_uptime_seconds",
                help_text="시스템 가동 시간 (초)",
                metric_type="gauge",
            ),
            MetricDefinition(
                name="blacklist_version_info",
                help_text="시스템 버전 정보",
                metric_type="info",
                labels=["version", "build_date", "git_commit"],
            ),
            MetricDefinition(
                name="blacklist_http_requests_total",
                help_text="HTTP 요청 총 수",
                metric_type="counter",
                labels=["method", "endpoint", "status_code"],
            ),
            MetricDefinition(
                name="blacklist_http_request_duration_seconds",
                help_text="HTTP 요청 처리 시간",
                metric_type="histogram",
                labels=["method", "endpoint"],
                buckets=[
                    0.001,
                    0.005,
                    0.01,
                    0.025,
                    0.05,
                    0.1,
                    0.25,
                    0.5,
                    1.0,
                    2.5,
                    5.0,
                    10.0,
                ],
            ),
            MetricDefinition(
                name="blacklist_active_connections",
                help_text="활성 연결 수",
                metric_type="gauge",
            ),
            MetricDefinition(
                name="blacklist_errors_total",
                help_text="오류 총 수",
                metric_type="counter",
                labels=["error_type", "component"],
            ),
        ]

        for metric in core_metrics:
            self.metrics[metric.name] = metric

    def _define_application_metrics(self):
        """애플리케이션 레벨 메트릭 정의"""
        app_metrics = [
            MetricDefinition(
                name="blacklist_database_connections",
                help_text="데이터베이스 연결 수",
                metric_type="gauge",
                labels=["state"],  # active, idle, total
            ),
            MetricDefinition(
                name="blacklist_cache_operations_total",
                help_text="캐시 작업 총 수",
                metric_type="counter",
                labels=["operation", "result"],  # get/set/delete, hit/miss/error
            ),
            MetricDefinition(
                name="blacklist_cache_size_bytes",
                help_text="캐시 크기 (바이트)",
                metric_type="gauge",
            ),
            MetricDefinition(
                name="blacklist_memory_usage_bytes",
                help_text="메모리 사용량 (바이트)",
                metric_type="gauge",
                labels=["type"],  # rss, vms, shared
            ),
            MetricDefinition(
                name="blacklist_cpu_usage_percent",
                help_text="CPU 사용률 (%)",
                metric_type="gauge",
            ),
            MetricDefinition(
                name="blacklist_disk_usage_bytes",
                help_text="디스크 사용량 (바이트)",
                metric_type="gauge",
                labels=["path", "type"],  # path=/app/instance, type=used/free/total
            ),
        ]

        for metric in app_metrics:
            self.metrics[metric.name] = metric

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """HTTP 요청 메트릭 기록"""
        try:
            # 요청 수 증가
            self.metrics["blacklist_http_requests_total"].labels(
                method=method, endpoint=endpoint, status_code=str(status_code)
            ).inc()

            # 요청 처리 시간 기록
            self.metrics["blacklist_http_request_duration_seconds"].labels(
                method=method, endpoint=endpoint
            ).observe(duration)

        except Exception as e:
            logger.error(f"HTTP 요청 메트릭 기록 실패: {e}")

    def record_error(self, error_type: str, component: str):
        """오류 메트릭 기록"""
        try:
            self.metrics["blacklist_errors_total"].labels(
                error_type=error_type, component=component
            ).inc()

        except Exception as e:
            logger.error(f"오류 메트릭 기록 실패: {e}")

    def update_system_metrics(self, system_info: Dict[str, Any]):
        """시스템 메트릭 업데이트"""
        try:
            # 가동 상태
            self.metrics["blacklist_up"].set(1)

            # 가동 시간
            uptime = time.time() - self.start_time
            self.metrics["blacklist_uptime_seconds"].set(uptime)

            # 활성 연결 수 (예시)
            active_connections = system_info.get("active_connections", 0)
            self.metrics["blacklist_active_connections"].set(active_connections)

            # 메모리 사용량
            memory_info = system_info.get("memory", {})
            for memory_type, value in memory_info.items():
                if isinstance(value, (int, float)):
                    self.metrics["blacklist_memory_usage_bytes"].labels(
                        type=memory_type
                    ).set(value)

            # CPU 사용률
            cpu_percent = system_info.get("cpu_percent", 0)
            self.metrics["blacklist_cpu_usage_percent"].set(cpu_percent)

            # 디스크 사용량
            disk_info = system_info.get("disk", {})
            for path, disk_data in disk_info.items():
                if isinstance(disk_data, dict):
                    for disk_type, value in disk_data.items():
                        if isinstance(value, (int, float)):
                            self.metrics["blacklist_disk_usage_bytes"].labels(
                                path=path, type=disk_type
                            ).set(value)

        except Exception as e:
            logger.error(f"시스템 메트릭 업데이트 실패: {e}")

    def set_version_info(
        self, version: str, build_date: str = None, git_commit: str = None
    ):
        """버전 정보 설정"""
        try:
            version_metric = self.metrics.get("blacklist_version_info")
            if hasattr(version_metric, "info"):
                version_metric.info(
                    {
                        "version": version or "unknown",
                        "build_date": build_date or "unknown",
                        "git_commit": git_commit or "unknown",
                    }
                )

        except Exception as e:
            logger.error(f"버전 정보 설정 실패: {e}")

    def record_cache_operation(self, operation: str, result: str):
        """캐시 작업 메트릭 기록"""
        try:
            self.metrics["blacklist_cache_operations_total"].labels(
                operation=operation, result=result
            ).inc()

        except Exception as e:
            logger.error(f"캐시 작업 메트릭 기록 실패: {e}")
