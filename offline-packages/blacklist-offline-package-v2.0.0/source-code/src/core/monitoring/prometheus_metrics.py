"""
Prometheus 메트릭 수집 및 노출

시스템의 주요 지표를 Prometheus 형식으로 수집하고 노출합니다.
"""

import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from prometheus_client import (
    Counter as PrometheusCounter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    multiprocess,
    REGISTRY
)
from flask import Response

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """메트릭 정의 클래스"""
    name: str
    help_text: str
    metric_type: str  # counter, gauge, histogram, info
    labels: list = field(default_factory=list)
    buckets: Optional[list] = None  # histogram용


class PrometheusMetrics:
    """Prometheus 메트릭 관리 클래스"""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """메트릭 초기화"""
        self.registry = registry or REGISTRY
        self.metrics = {}
        self.start_time = time.time()
        
        # 기본 메트릭 정의
        self._define_core_metrics()
        self._define_application_metrics()
        self._define_business_metrics()
        
        # 메트릭 생성
        self._create_metrics()
    
    def _define_core_metrics(self):
        """핵심 시스템 메트릭 정의"""
        core_metrics = [
            MetricDefinition(
                name="blacklist_up",
                help_text="시스템 가동 상태 (1=가동, 0=중단)",
                metric_type="gauge"
            ),
            MetricDefinition(
                name="blacklist_uptime_seconds",
                help_text="시스템 가동 시간 (초)",
                metric_type="gauge"
            ),
            MetricDefinition(
                name="blacklist_version_info",
                help_text="시스템 버전 정보",
                metric_type="info",
                labels=["version", "build_date", "git_commit"]
            ),
            MetricDefinition(
                name="blacklist_http_requests_total",
                help_text="HTTP 요청 총 수",
                metric_type="counter",
                labels=["method", "endpoint", "status_code"]
            ),
            MetricDefinition(
                name="blacklist_http_request_duration_seconds",
                help_text="HTTP 요청 처리 시간",
                metric_type="histogram",
                labels=["method", "endpoint"],
                buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
            ),
            MetricDefinition(
                name="blacklist_active_connections",
                help_text="활성 연결 수",
                metric_type="gauge"
            ),
            MetricDefinition(
                name="blacklist_errors_total",
                help_text="오류 총 수",
                metric_type="counter",
                labels=["error_type", "component"]
            )
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
                labels=["state"]  # active, idle, total
            ),
            MetricDefinition(
                name="blacklist_cache_operations_total",
                help_text="캐시 작업 총 수",
                metric_type="counter",
                labels=["operation", "result"]  # get/set/delete, hit/miss/error
            ),
            MetricDefinition(
                name="blacklist_cache_size_bytes",
                help_text="캐시 크기 (바이트)",
                metric_type="gauge"
            ),
            MetricDefinition(
                name="blacklist_memory_usage_bytes",
                help_text="메모리 사용량 (바이트)",
                metric_type="gauge",
                labels=["type"]  # rss, vms, shared
            ),
            MetricDefinition(
                name="blacklist_cpu_usage_percent",
                help_text="CPU 사용률 (%)",
                metric_type="gauge"
            ),
            MetricDefinition(
                name="blacklist_disk_usage_bytes",
                help_text="디스크 사용량 (바이트)",
                metric_type="gauge",
                labels=["path", "type"]  # path=/app/instance, type=used/free/total
            )
        ]
        
        for metric in app_metrics:
            self.metrics[metric.name] = metric
    
    def _define_business_metrics(self):
        """비즈니스 로직 메트릭 정의"""
        business_metrics = [
            MetricDefinition(
                name="blacklist_ips_total",
                help_text="블랙리스트 IP 총 수",
                metric_type="gauge",
                labels=["source", "status"]  # regtech/secudium, active/inactive
            ),
            MetricDefinition(
                name="blacklist_collections_total",
                help_text="데이터 수집 작업 총 수",
                metric_type="counter",
                labels=["source", "status"]  # regtech/secudium, success/failure
            ),
            MetricDefinition(
                name="blacklist_collection_duration_seconds",
                help_text="데이터 수집 소요 시간",
                metric_type="histogram",
                labels=["source"],
                buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0]
            ),
            MetricDefinition(
                name="blacklist_collection_items_total",
                help_text="수집된 아이템 수",
                metric_type="counter",
                labels=["source", "type"]  # source=regtech/secudium, type=new/updated/duplicate
            ),
            MetricDefinition(
                name="blacklist_api_queries_total",
                help_text="API 쿼리 총 수",
                metric_type="counter",
                labels=["endpoint", "result"]  # /api/blacklist/active, success/error
            ),
            MetricDefinition(
                name="blacklist_threats_detected_total",
                help_text="탐지된 위협 총 수",
                metric_type="counter",
                labels=["threat_level", "source"]  # high/medium/low, regtech/secudium
            ),
            MetricDefinition(
                name="blacklist_authentication_attempts_total",
                help_text="인증 시도 총 수",
                metric_type="counter",
                labels=["service", "result"]  # regtech/secudium/api, success/failure
            ),
            MetricDefinition(
                name="blacklist_data_freshness_seconds",
                help_text="데이터 신선도 (마지막 업데이트 이후 시간)",
                metric_type="gauge",
                labels=["source"]
            )
        ]
        
        for metric in business_metrics:
            self.metrics[metric.name] = metric
    
    def _create_metrics(self):
        """실제 Prometheus 메트릭 객체 생성"""
        for name, definition in self.metrics.items():
            try:
                if definition.metric_type == "counter":
                    self.metrics[name] = PrometheusCounter(
                        name, definition.help_text,
                        labelnames=definition.labels,
                        registry=self.registry
                    )
                elif definition.metric_type == "gauge":
                    self.metrics[name] = Gauge(
                        name, definition.help_text,
                        labelnames=definition.labels,
                        registry=self.registry
                    )
                elif definition.metric_type == "histogram":
                    self.metrics[name] = Histogram(
                        name, definition.help_text,
                        labelnames=definition.labels,
                        buckets=definition.buckets,
                        registry=self.registry
                    )
                elif definition.metric_type == "info":
                    self.metrics[name] = Info(
                        name, definition.help_text,
                        labelnames=definition.labels,
                        registry=self.registry
                    )
                    
            except Exception as e:
                logger.error(f"메트릭 생성 실패 ({name}): {e}")
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """HTTP 요청 메트릭 기록"""
        try:
            # 요청 수 증가
            self.metrics["blacklist_http_requests_total"].labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()
            
            # 요청 처리 시간 기록
            self.metrics["blacklist_http_request_duration_seconds"].labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            
        except Exception as e:
            logger.error(f"HTTP 요청 메트릭 기록 실패: {e}")
    
    def record_collection_event(self, source: str, success: bool, duration: float, items_count: Dict[str, int]):
        """데이터 수집 이벤트 메트릭 기록"""
        try:
            # 수집 작업 수 증가
            status = "success" if success else "failure"
            self.metrics["blacklist_collections_total"].labels(
                source=source,
                status=status
            ).inc()
            
            # 수집 소요 시간 기록
            if success:
                self.metrics["blacklist_collection_duration_seconds"].labels(
                    source=source
                ).observe(duration)
                
                # 수집된 아이템 수 기록
                for item_type, count in items_count.items():
                    self.metrics["blacklist_collection_items_total"].labels(
                        source=source,
                        type=item_type
                    ).inc(count)
        
        except Exception as e:
            logger.error(f"수집 이벤트 메트릭 기록 실패: {e}")
    
    def record_authentication_attempt(self, service: str, success: bool):
        """인증 시도 메트릭 기록"""
        try:
            result = "success" if success else "failure"
            self.metrics["blacklist_authentication_attempts_total"].labels(
                service=service,
                result=result
            ).inc()
            
        except Exception as e:
            logger.error(f"인증 시도 메트릭 기록 실패: {e}")
    
    def record_threat_detection(self, threat_level: str, source: str):
        """위협 탐지 메트릭 기록"""
        try:
            self.metrics["blacklist_threats_detected_total"].labels(
                threat_level=threat_level,
                source=source
            ).inc()
            
        except Exception as e:
            logger.error(f"위협 탐지 메트릭 기록 실패: {e}")
    
    def record_error(self, error_type: str, component: str):
        """오류 메트릭 기록"""
        try:
            self.metrics["blacklist_errors_total"].labels(
                error_type=error_type,
                component=component
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
                                path=path,
                                type=disk_type
                            ).set(value)
            
        except Exception as e:
            logger.error(f"시스템 메트릭 업데이트 실패: {e}")
    
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
                                source=source,
                                status=status
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
    
    def set_version_info(self, version: str, build_date: str = None, git_commit: str = None):
        """버전 정보 설정"""
        try:
            self.metrics["blacklist_version_info"].info({
                "version": version or "unknown",
                "build_date": build_date or "unknown",
                "git_commit": git_commit or "unknown"
            })
            
        except Exception as e:
            logger.error(f"버전 정보 설정 실패: {e}")
    
    def record_cache_operation(self, operation: str, result: str):
        """캐시 작업 메트릭 기록"""
        try:
            self.metrics["blacklist_cache_operations_total"].labels(
                operation=operation,
                result=result
            ).inc()
            
        except Exception as e:
            logger.error(f"캐시 작업 메트릭 기록 실패: {e}")
    
    def record_api_query(self, endpoint: str, success: bool):
        """API 쿼리 메트릭 기록"""
        try:
            result = "success" if success else "error"
            self.metrics["blacklist_api_queries_total"].labels(
                endpoint=endpoint,
                result=result
            ).inc()
            
        except Exception as e:
            logger.error(f"API 쿼리 메트릭 기록 실패: {e}")
    
    def get_metrics_output(self) -> str:
        """Prometheus 형식 메트릭 출력"""
        try:
            return generate_latest(self.registry).decode('utf-8')
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
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
            )
        except Exception as e:
            logger.error(f"메트릭 응답 생성 실패: {e}")
            return Response(
                "# 메트릭 생성 실패\n",
                status=500,
                content_type=CONTENT_TYPE_LATEST
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


# 전역 메트릭 인스턴스
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


# 데코레이터들
def track_http_requests(func):
    """HTTP 요청 추적 데코레이터"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            # Flask request context에서 정보 추출
            from flask import request
            method = request.method
            endpoint = request.endpoint or 'unknown'
            
            result = func(*args, **kwargs)
            
            # 성공적인 응답
            status_code = getattr(result, 'status_code', 200)
            duration = time.time() - start_time
            
            metrics = get_metrics()
            metrics.record_http_request(method, endpoint, status_code, duration)
            
            return result
            
        except Exception as e:
            # 오류 발생
            duration = time.time() - start_time
            
            try:
                from flask import request
                method = request.method
                endpoint = request.endpoint or 'unknown'
                
                metrics = get_metrics()
                metrics.record_http_request(method, endpoint, 500, duration)
                metrics.record_error('http_request_error', 'web')
            except:
                pass
            
            raise e
    
    return wrapper

def track_collection_operation(source: str):
    """데이터 수집 작업 추적 데코레이터"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # 결과에서 수집 정보 추출
                items_count = {
                    'new': result.get('new_items', 0),
                    'updated': result.get('updated_items', 0),
                    'duplicate': result.get('duplicate_items', 0)
                } if isinstance(result, dict) else {'total': 1}
                
                metrics = get_metrics()
                metrics.record_collection_event(source, True, duration, items_count)
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                metrics = get_metrics()
                metrics.record_collection_event(source, False, duration, {})
                metrics.record_error('collection_error', source)
                
                raise e
        
        return wrapper
    return decorator