#!/usr/bin/env python3
"""
Collection Monitoring - Health Assessment Module

수집기 건강 상태 평가 및 성능 분석을 담당하는 모듈입니다.
시스템 전체 건강 점수, 리소스 사용량 모니터링, 성능 임계값 관리를 제공합니다.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

# psutil 조건부 임포트 (시스템 메트릭용)
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - using fallback system metrics")

# 조건부 임포트로 독립 실행 지원
try:
    from .base_collector import BaseCollector
    from .collection_types import CollectionResult, CollectionStatus
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_collector import BaseCollector
    from collection_types import CollectionResult, CollectionStatus


class CollectionHealthAssessor:
    """수집기 건강 상태 평가"""

    def __init__(self, performance_thresholds: Dict[str, float] = None):
        """건강 평가기 초기화

        Args:
            performance_thresholds: 성능 임계값 딕셔너리
        """
        self._performance_thresholds = performance_thresholds or {
            "max_duration": 300,  # 5분
            "min_success_rate": 80,  # 80%
            "max_error_rate": 20,  # 20%
            "max_consecutive_failures": 3,
        }

    def assess_system_health(
        self,
        collectors: Dict[str, BaseCollector],
        collection_history: List[CollectionResult],
    ) -> Dict[str, Any]:
        """시스템 전체 건강 상태 평가

        Args:
            collectors: 수집기 딕셔너리
            collection_history: 수집 히스토리

        Returns:
            시스템 건강 상태 딕셔너리
        """
        if not collectors:
            return {
                "overall_status": "warning",
                "score": 0,
                "issues": ["등록된 수집기가 없습니다."],
            }

        healthy_count = len(self._get_healthy_collectors(collectors))
        total_count = len(collectors)
        health_ratio = healthy_count / total_count if total_count > 0 else 0

        # 최근 성공률 계산
        recent_results = (
            collection_history[-20:]
            if len(collection_history) >= 20
            else collection_history
        )
        if recent_results:
            success_count = sum(
                1 for r in recent_results if r.status == CollectionStatus.COMPLETED
            )
            recent_success_rate = (success_count / len(recent_results)) * 100
        else:
            recent_success_rate = 0

        # 건강 점수 계산 (0-100)
        health_score = int((health_ratio * 70) + (recent_success_rate * 0.3))

        # 상태 결정
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "warning"
        else:
            status = "critical"

        # 이슈 수집
        issues = []
        if health_ratio < 0.5:
            issues.append(
                f"건강하지 않은 수집기가 많습니다 ({healthy_count}/{total_count})"
            )

        if recent_success_rate < self._performance_thresholds["min_success_rate"]:
            issues.append(f"최근 성공률이 낮습니다 ({recent_success_rate:.1f}%)")

        return {
            "overall_status": status,
            "score": health_score,
            "healthy_collectors": f"{healthy_count}/{total_count}",
            "recent_success_rate": f"{recent_success_rate:.1f}%",
            "issues": issues,
        }

    def get_resource_usage(
        self, collectors: Dict[str, BaseCollector]
    ) -> Dict[str, Any]:
        """리소스 사용량 조회

        Args:
            collectors: 수집기 딕셔너리

        Returns:
            리소스 사용량 딕셔너리
        """
        running_count = len(self._get_running_collectors(collectors))

        return {
            "active_collections": running_count,
            "total_collectors": len(collectors),
            "memory_usage_mb": self._get_memory_usage(),
            "cpu_usage_percent": self._get_cpu_usage(),
            "utilization_rate": (
                (running_count / len(collectors) * 100) if collectors else 0
            ),
        }

    def check_collector_health(
        self, collector: BaseCollector
    ) -> tuple[bool, List[str]]:
        """수집기 건강 상태 확인

        Args:
            collector: 확인할 수집기

        Returns:
            (건강 상태, 이슈 목록)
        """
        health_check = collector.health_check()
        issues = []

        # 연속 실패 확인
        consecutive_failures = health_check.get("consecutive_failures", 0)
        if (
            consecutive_failures
            >= self._performance_thresholds["max_consecutive_failures"]
        ):
            issues.append(f"연속 {consecutive_failures}회 실패")

        # 성공률 확인
        success_rate = health_check.get("success_rate", 100)
        if success_rate < self._performance_thresholds["min_success_rate"]:
            issues.append(f"성공률이 낮습니다 ({success_rate:.1f}%)")

        return len(issues) == 0, issues

    def generate_recommendations(
        self,
        collectors: Dict[str, BaseCollector],
        collection_history: List[CollectionResult],
    ) -> List[str]:
        """개선 권장사항 생성

        Args:
            collectors: 수집기 딕셔너리
            collection_history: 수집 히스토리

        Returns:
            권장사항 목록
        """
        recommendations = []

        # 비활성화된 수집기 확인
        disabled_collectors = [
            name
            for name, collector in collectors.items()
            if not collector.config.enabled
        ]
        if disabled_collectors:
            recommendations.append(
                f"비활성화된 수집기가 있습니다: {', '.join(disabled_collectors[:3])}"
            )

        # 건강하지 않은 수집기 확인
        unhealthy_collectors = [
            name for name, collector in collectors.items() if not collector.is_healthy
        ]
        if unhealthy_collectors:
            recommendations.append(
                f"건강 상태를 확인해야 할 수집기: {', '.join(unhealthy_collectors[:3])}"
            )

        # 최근 실패율 확인
        if collection_history:
            recent_failures = [
                r
                for r in collection_history[-10:]
                if r.status == CollectionStatus.FAILED
            ]
            if len(recent_failures) > 3:
                recommendations.append("최근 실패율이 높습니다. 설정을 점검하세요.")

        # 성능 개선 권장사항
        if collection_history:
            slow_collections = [
                r
                for r in collection_history[-10:]
                if r.duration
                and r.duration > self._performance_thresholds["max_duration"]
            ]
            if slow_collections:
                recommendations.append(
                    "일부 수집이 느립니다. 타임아웃 설정을 확인하세요."
                )

        if not recommendations:
            recommendations.append("현재 시스템이 정상적으로 운영되고 있습니다.")

        return recommendations

    def update_performance_thresholds(self, thresholds: Dict[str, float]):
        """성능 임계값 업데이트

        Args:
            thresholds: 새로운 임계값 딕셔너리
        """
        self._performance_thresholds.update(thresholds)

    def _get_running_collectors(
        self, collectors: Dict[str, BaseCollector]
    ) -> List[str]:
        """실행 중인 수집기 목록"""
        return [name for name, collector in collectors.items() if collector.is_running]

    def _get_healthy_collectors(
        self, collectors: Dict[str, BaseCollector]
    ) -> List[str]:
        """건강한 수집기 목록"""
        return [name for name, collector in collectors.items() if collector.is_healthy]

    def _get_memory_usage(self) -> float:
        """실제 메모리 사용량 측정 (MB 단위)"""
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            return round(memory_info.rss / (1024 * 1024), 2)  # MB로 변환
        except Exception as e:
            logging.warning(f"Memory usage measurement failed: {e}")
            return 0.0

    def _get_cpu_usage(self) -> float:
        """실제 CPU 사용량 측정 (% 단위)"""
        if not PSUTIL_AVAILABLE:
            return 0.0

        try:
            # 현재 프로세스 CPU 사용률
            process = psutil.Process()
            cpu_percent = process.cpu_percent(interval=0.1)
            return round(cpu_percent, 2)
        except Exception as e:
            logging.warning(f"CPU usage measurement failed: {e}")
            return 0.0
