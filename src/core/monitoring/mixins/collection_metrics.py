"""
데이터 수집 관련 Prometheus 메트릭 믹스인

데이터 수집 작업, 인증, 위협 탐지 등의 비즈니스 로직 메트릭을 관리합니다.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class CollectionMetricsMixin:
    """데이터 수집 메트릭 관리 믹스인"""

    def _define_business_metrics(self):
        """비즈니스 로직 메트릭 정의"""
        from .system_metrics import MetricDefinition

        business_metrics = [
            MetricDefinition(
                name="blacklist_ips_total",
                help_text="블랙리스트 IP 총 수",
                metric_type="gauge",
                labels=["source", "status"],  # regtech/secudium, active/inactive
            ),
            MetricDefinition(
                name="blacklist_collections_total",
                help_text="데이터 수집 작업 총 수",
                metric_type="counter",
                labels=["source", "status"],  # regtech/secudium, success/failure
            ),
            MetricDefinition(
                name="blacklist_collection_duration_seconds",
                help_text="데이터 수집 소요 시간",
                metric_type="histogram",
                labels=["source"],
                buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0],
            ),
            MetricDefinition(
                name="blacklist_collection_items_total",
                help_text="수집된 아이템 수",
                metric_type="counter",
                labels=["source", "type"],  # regtech/secudium, new/updated/dup
            ),
            MetricDefinition(
                name="blacklist_api_queries_total",
                help_text="API 쿼리 총 수",
                metric_type="counter",
                labels=["endpoint", "result"],  # /api/blacklist/active, success/error
            ),
            MetricDefinition(
                name="blacklist_threats_detected_total",
                help_text="탐지된 위협 총 수",
                metric_type="counter",
                labels=["threat_level", "source"],  # high/medium/low, regtech/secudium
            ),
            MetricDefinition(
                name="blacklist_authentication_attempts_total",
                help_text="인증 시도 총 수",
                metric_type="counter",
                labels=["service", "result"],  # regtech/secudium/api, success/failure
            ),
            MetricDefinition(
                name="blacklist_data_freshness_seconds",
                help_text="데이터 신선도 (마지막 업데이트 이후 시간)",
                metric_type="gauge",
                labels=["source"],
            ),
        ]

        for metric in business_metrics:
            self.metrics[metric.name] = metric

    def record_collection_event(
        self, source: str, success: bool, duration: float, items_count: Dict[str, int]
    ):
        """데이터 수집 이벤트 메트릭 기록"""
        try:
            # 수집 작업 수 증가
            status = "success" if success else "failure"
            self.metrics["blacklist_collections_total"].labels(
                source=source, status=status
            ).inc()

            # 수집 소요 시간 기록
            if success:
                self.metrics["blacklist_collection_duration_seconds"].labels(
                    source=source
                ).observe(duration)

                # 수집된 아이템 수 기록
                for item_type, count in items_count.items():
                    self.metrics["blacklist_collection_items_total"].labels(
                        source=source, type=item_type
                    ).inc(count)

        except Exception as e:
            logger.error(f"수집 이벤트 메트릭 기록 실패: {e}")

    def record_authentication_attempt(self, service: str, success: bool):
        """인증 시도 메트릭 기록"""
        try:
            result = "success" if success else "failure"
            self.metrics["blacklist_authentication_attempts_total"].labels(
                service=service, result=result
            ).inc()

        except Exception as e:
            logger.error(f"인증 시도 메트릭 기록 실패: {e}")

    def record_threat_detection(self, threat_level: str, source: str):
        """위협 탐지 메트릭 기록"""
        try:
            self.metrics["blacklist_threats_detected_total"].labels(
                threat_level=threat_level, source=source
            ).inc()

        except Exception as e:
            logger.error(f"위협 탐지 메트릭 기록 실패: {e}")

    def record_api_query(self, endpoint: str, success: bool):
        """API 쿼리 메트릭 기록"""
        try:
            result = "success" if success else "error"
            self.metrics["blacklist_api_queries_total"].labels(
                endpoint=endpoint, result=result
            ).inc()

        except Exception as e:
            logger.error(f"API 쿼리 메트릭 기록 실패: {e}")

    def update_business_metrics(self, business_data: Dict[str, Any]):
        """비즈니스 메트릭 업데이트"""
        try:
            # IP 통계
            ip_stats = business_data.get("ip_stats", {})
            for source, source_data in ip_stats.items():
                if isinstance(source_data, dict):
                    for status, count in source_data.items():
                        if isinstance(count, (int, float)):
                            self.metrics["blacklist_ips_total"].labels(
                                source=source, status=status
                            ).set(count)

            # 데이터 신선도
            freshness_data = business_data.get("data_freshness", {})
            for source, seconds in freshness_data.items():
                if isinstance(seconds, (int, float)):
                    self.metrics["blacklist_data_freshness_seconds"].labels(
                        source=source
                    ).set(seconds)

            # 캐시 정보
            cache_info = business_data.get("cache", {})
            cache_size = cache_info.get("size_bytes", 0)
            self.metrics["blacklist_cache_size_bytes"].set(cache_size)

            # 데이터베이스 연결 정보
            db_info = business_data.get("database", {})
            for state, count in db_info.items():
                if isinstance(count, (int, float)):
                    self.metrics["blacklist_database_connections"].labels(
                        state=state
                    ).set(count)

        except Exception as e:
            logger.error(f"비즈니스 메트릭 업데이트 실패: {e}")
