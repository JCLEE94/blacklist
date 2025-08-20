"""
Prometheus 메트릭 수집 및 노출

시스템의 주요 지표를 Prometheus 형식으로 수집하고 노출합니다.
믹스인 패턴을 사용하여 모듈화된 메트릭 관리를 제공합니다.
"""

import logging
import time
from typing import Optional

from flask import Response
from prometheus_client import CONTENT_TYPE_LATEST
from prometheus_client import REGISTRY
from prometheus_client import CollectorRegistry
from prometheus_client import Counter as PrometheusCounter
from prometheus_client import Gauge
from prometheus_client import Histogram
from prometheus_client import Info
from prometheus_client import generate_latest

from .mixins.collection_metrics import CollectionMetricsMixin

# 믹스인 모듈 import
from .mixins.system_metrics import SystemMetricsMixin

logger = logging.getLogger(__name__)


class PrometheusMetrics(SystemMetricsMixin, CollectionMetricsMixin):
    """
    Prometheus 메트릭 관리 클래스

    시스템 메트릭과 컬렉션 메트릭을 믹스인으로 조합하여
    완전한 메트릭 관리 기능을 제공합니다.
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """메트릭 초기화"""
        self.registry = registry or REGISTRY
        self.metrics = {}
        self.start_time = time.time()

        # 믹스인에서 메트릭 정의 로드
        self._define_core_metrics()
        self._define_application_metrics()
        self._define_business_metrics()

        # 메트릭 객체 생성
        self._create_metrics()

    def _create_metrics(self):
        """실제 Prometheus 메트릭 객체 생성"""
        for name, definition in self.metrics.items():
            try:
                if definition.metric_type == "counter":
                    self.metrics[name] = PrometheusCounter(
                        name,
                        definition.help_text,
                        labelnames=definition.labels,
                        registry=self.registry,
                    )
                elif definition.metric_type == "gauge":
                    self.metrics[name] = Gauge(
                        name,
                        definition.help_text,
                        labelnames=definition.labels,
                        registry=self.registry,
                    )
                elif definition.metric_type == "histogram":
                    self.metrics[name] = Histogram(
                        name,
                        definition.help_text,
                        labelnames=definition.labels,
                        buckets=definition.buckets,
                        registry=self.registry,
                    )
                elif definition.metric_type == "info":
                    self.metrics[name] = Info(
                        name,
                        definition.help_text,
                        labelnames=definition.labels,
                        registry=self.registry,
                    )

            except Exception as e:
                logger.error(f"메트릭 생성 실패 ({name}): {e}")

    def get_metrics_output(self) -> str:
        """Prometheus 형식 메트릭 출력"""
        try:
            return generate_latest(self.registry).decode("utf-8")
        except Exception as e:
            logger.error(f"메트릭 출력 생성 실패: {e}")
            return ""

    def get_metrics_response(self) -> Response:
        """Flask Response 객체로 메트릭 반환"""
        try:
            metrics_output = self.get_metrics_output()
            return Response(
                metrics_output,
                content_type=CONTENT_TYPE_LATEST,
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        except Exception as e:
            logger.error(f"메트릭 응답 생성 실패: {e}")
            return Response(
                "# 메트릭 생성 실패\n", status=500, content_type=CONTENT_TYPE_LATEST
            )

    def reset_metrics(self):
        """메트릭 리셋 (테스트용)"""
        try:
            self.registry._collector_to_names.clear()
            self.registry._names_to_collectors.clear()
            self._create_metrics()
            logger.info("메트릭이 리셋되었습니다.")

        except Exception as e:
            logger.error(f"메트릭 리셋 실패: {e}")


# 전역 메트릭 인스턴스 관리
_metrics_instance = None


def get_metrics() -> PrometheusMetrics:
    """전역 메트릭 인스턴스 반환"""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = PrometheusMetrics()
    return _metrics_instance


def init_metrics(version: str = None, build_date: str = None, git_commit: str = None):
    """메트릭 시스템 초기화"""
    metrics = get_metrics()

    # 버전 정보 설정
    if version or build_date or git_commit:
        metrics.set_version_info(version, build_date, git_commit)

    logger.info("Prometheus 메트릭 시스템이 초기화되었습니다.")
    return metrics


# 데코레이터들을 함수로 export (기존 코드와의 호환성 유지)
def track_http_requests(func):
    """HTTP 요청 추적 데코레이터"""
    from .mixins.decorators import track_http_requests as _track_http_requests

    return _track_http_requests(func)


def track_collection_operation(source: str):
    """데이터 수집 작업 추적 데코레이터"""
    from .mixins.decorators import (
        track_collection_operation as _track_collection_operation,
    )

    return _track_collection_operation(source)
