"""
실시간 성능 모니터링 대시보드

이 모듈은 Blacklist 시스템의 성능을 실시간으로 모니터링하고
시각화하는 대시보드 기능을 제공합니다.
"""

import threading
import time
from collections import deque
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List

import psutil
from loguru import logger

from .alerts import AlertManager
from .metrics import PerformanceMetric

try:
    from src.utils.async_processor import get_global_async_processor
    from src.utils.memory_optimizer import get_global_memory_optimizer
    from src.utils.performance_cache import get_global_performance_cache
except ImportError:
    # 폴백 임포트
    get_global_performance_cache = lambda: None
    get_global_async_processor = lambda: None
    get_global_memory_optimizer = lambda: None


class PerformanceDashboard:
    """실시간 성능 대시보드"""

    def __init__(self, max_metrics: int = 1000):
        self.max_metrics = max_metrics
        self.metrics_history = deque(maxlen=max_metrics)

        # 알림 관리자
        self.alert_manager = AlertManager()

        # 실시간 데이터
        self.current_connections = 0
        self.request_count = 0
        self.error_count = 0
        self.total_response_time = 0.0

        # 스레드 안전성
        self._lock = threading.RLock()

        # 모니터링 스레드
        self.monitoring_active = False
        self.monitoring_thread = None

        logger.info("Performance dashboard initialized")

    def record_request(self, response_time_ms: float, status_code: int = 200):
        """요청 기록"""
        with self._lock:
            self.request_count += 1
            self.total_response_time += response_time_ms

            if status_code >= 400:
                self.error_count += 1

    def record_connection(self, delta: int):
        """연결 수 변경 기록"""
        with self._lock:
            self.current_connections = max(0, self.current_connections + delta)

    def collect_metrics(self) -> PerformanceMetric:
        """현재 성능 메트릭 수집"""
        with self._lock:
            # 시스템 메트릭
            psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)

            # 프로세스 메트릭
            process = psutil.Process()
            process_memory_mb = process.memory_info().rss / 1024 / 1024

            # 응답 시간 계산
            avg_response_time = (
                self.total_response_time / self.request_count
                if self.request_count > 0
                else 0.0
            )

            # 캐시 메트릭
            cache_hit_rate = 0.0
            try:
                cache = get_global_performance_cache()
                if cache:
                    stats = cache.get_stats()
                    cache_hit_rate = stats.get("hit_rate_percent", 0.0)
            except Exception:
                pass

            # 데이터베이스 쿼리 수 (추정)
            db_queries = self.request_count * 1.5  # 평균적으로 요청당 1.5개 쿼리

            metric = PerformanceMetric(
                timestamp=datetime.now(),
                response_time_ms=avg_response_time,
                memory_usage_mb=process_memory_mb,
                cpu_usage_percent=cpu_percent,
                active_connections=self.current_connections,
                cache_hit_rate=cache_hit_rate,
                database_queries=int(db_queries),
                errors_count=self.error_count,
            )

            # 메트릭 히스토리 저장
            self.metrics_history.append(metric)

            # 알림 검사
            self.alert_manager.check_alerts(metric)

            return metric

    def get_dashboard_data(self) -> Dict[str, Any]:
        """대시보드 데이터 반환"""
        with self._lock:
            current_metric = self.collect_metrics()

            # 히스토리 데이터 (최근 100개)
            recent_metrics = list(self.metrics_history)[-100:]

            # 시계열 데이터 준비
            timestamps = [m.timestamp.isoformat() for m in recent_metrics]
            response_times = [m.response_time_ms for m in recent_metrics]
            memory_usage = [m.memory_usage_mb for m in recent_metrics]
            cpu_usage = [m.cpu_usage_percent for m in recent_metrics]
            cache_hit_rates = [m.cache_hit_rate for m in recent_metrics]

            # 통계 계산
            if recent_metrics:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                avg_memory_usage = sum(memory_usage) / len(memory_usage)
                avg_cpu_usage = sum(cpu_usage) / len(cpu_usage)
                avg_cache_hit_rate = sum(cache_hit_rates) / len(cache_hit_rates)
            else:
                avg_response_time = max_response_time = min_response_time = 0
                avg_memory_usage = avg_cpu_usage = avg_cache_hit_rate = 0

            # 성능 등급 계산
            performance_grade = self._calculate_performance_grade(current_metric)

            # 활성 알림 (최근 10개)
            recent_alerts = self.alert_manager.get_active_alerts()[-10:]

            return {
                "current_metrics": asdict(current_metric),
                "statistics": {
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "max_response_time_ms": round(max_response_time, 2),
                    "min_response_time_ms": round(min_response_time, 2),
                    "avg_memory_usage_mb": round(avg_memory_usage, 2),
                    "avg_cpu_usage_percent": round(avg_cpu_usage, 2),
                    "avg_cache_hit_rate": round(avg_cache_hit_rate, 2),
                    "total_requests": self.request_count,
                    "total_errors": self.error_count,
                    "error_rate_percent": round(
                        (
                            (self.error_count / self.request_count * 100)
                            if self.request_count > 0
                            else 0
                        ),
                        2,
                    ),
                },
                "time_series": {
                    "timestamps": timestamps,
                    "response_times": response_times,
                    "memory_usage": memory_usage,
                    "cpu_usage": cpu_usage,
                    "cache_hit_rates": cache_hit_rates,
                },
                "performance_grade": performance_grade,
                "active_alerts": recent_alerts,
                "system_info": self._get_system_info(),
                "optimization_suggestions": self._get_optimization_suggestions(
                    current_metric
                ),
            }

    def _calculate_performance_grade(self, metric: PerformanceMetric) -> Dict[str, Any]:
        """성능 등급 계산"""
        # 응답 시간 점수 (40점)
        if metric.response_time_ms <= 50:
            response_score = 40
        elif metric.response_time_ms <= 200:
            response_score = 35
        elif metric.response_time_ms <= 1000:
            response_score = 25
        elif metric.response_time_ms <= 5000:
            response_score = 10
        else:
            response_score = 0

        # 메모리 사용 점수 (25점)
        if metric.memory_usage_mb <= 100:
            memory_score = 25
        elif metric.memory_usage_mb <= 300:
            memory_score = 20
        elif metric.memory_usage_mb <= 500:
            memory_score = 15
        elif metric.memory_usage_mb <= 1000:
            memory_score = 10
        else:
            memory_score = 0

        # CPU 사용 점수 (20점)
        if metric.cpu_usage_percent <= 20:
            cpu_score = 20
        elif metric.cpu_usage_percent <= 50:
            cpu_score = 15
        elif metric.cpu_usage_percent <= 80:
            cpu_score = 10
        elif metric.cpu_usage_percent <= 95:
            cpu_score = 5
        else:
            cpu_score = 0

        # 캐시 효율성 점수 (15점)
        if metric.cache_hit_rate >= 90:
            cache_score = 15
        elif metric.cache_hit_rate >= 75:
            cache_score = 12
        elif metric.cache_hit_rate >= 50:
            cache_score = 8
        elif metric.cache_hit_rate >= 25:
            cache_score = 4
        else:
            cache_score = 0

        total_score = response_score + memory_score + cpu_score + cache_score

        # 등급 계산
        if total_score >= 95:
            grade = "A+"
        elif total_score >= 90:
            grade = "A"
        elif total_score >= 85:
            grade = "A-"
        elif total_score >= 80:
            grade = "B+"
        elif total_score >= 75:
            grade = "B"
        elif total_score >= 70:
            grade = "B-"
        elif total_score >= 65:
            grade = "C+"
        elif total_score >= 60:
            grade = "C"
        elif total_score >= 50:
            grade = "D"
        else:
            grade = "F"

        return {
            "total_score": total_score,
            "grade": grade,
            "breakdown": {
                "response_time": response_score,
                "memory_usage": memory_score,
                "cpu_usage": cpu_score,
                "cache_efficiency": cache_score,
            },
        }

    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(memory.total / 1024 / 1024 / 1024, 2),
                "memory_available_gb": round(memory.available / 1024 / 1024 / 1024, 2),
                "disk_total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
            }
        except Exception as e:
            logger.error(f"System info collection failed: {e}")
            return {}

    def _get_optimization_suggestions(self, metric: PerformanceMetric) -> List[str]:
        """최적화 제안 사항"""
        suggestions = []

        if metric.response_time_ms > 1000:
            suggestions.append("응답 시간이 높습니다. 캐시 활용을 고려하세요.")

        if metric.memory_usage_mb > 500:
            suggestions.append("메모리 사용량이 높습니다. 객체 풀링을 고려하세요.")

        if metric.cpu_usage_percent > 80:
            suggestions.append("CPU 사용률이 높습니다. 비동기 처리를 고려하세요.")

        if metric.cache_hit_rate < 50:
            suggestions.append("캐시 효율이 낮습니다. 캐시 전략을 검토하세요.")

        if metric.errors_count > 10:
            suggestions.append("에러 발생빈도가 높습니다. 로그를 확인하세요.")

        if not suggestions:
            suggestions.append("시스템 성능이 양호합니다.")

        return suggestions

    def start_monitoring(self, interval: int = 30):
        """모니터링 시작"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(
            target=self._monitoring_loop, args=(interval,), daemon=True
        )
        self.monitoring_thread.start()
        logger.info(f"Performance monitoring started (interval: {interval}s)")

    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Performance monitoring stopped")

    def _monitoring_loop(self, interval: int):
        """모니터링 루프"""
        while self.monitoring_active:
            try:
                self.collect_metrics()
                time.sleep(interval)
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                time.sleep(1)

    def reset_counters(self):
        """카운터 리셋"""
        with self._lock:
            self.request_count = 0
            self.error_count = 0
            self.total_response_time = 0.0
            self.alert_manager.clear_alerts()
            logger.info("Performance counters reset")
