#!/usr/bin/env python3
"""
수집 모니터링 및 상태 관리 시스템

수집기 상태 추적, 성능 모니터링, 리소스 사용량 관리를 담당합니다.
상태 보고서 생성, 건강 상태 확인, 경고 시스템을 제공합니다.

관련 패키지 문서:
- typing: https://docs.python.org/3/library/typing.html
- datetime: https://docs.python.org/3/library/datetime.html

입력 예시:
- collectors: BaseCollector 객체들의 딕셔너리
- collection_results: 수집 결과 목록

출력 예시:
- 상태 보고서 딕셔너리
- 성능 메트릭 및 경고 정보
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .base_collector import BaseCollector
    from .collection_types import CollectionResult, CollectionStatus, CollectionStats
except ImportError:
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_collector import BaseCollector
    from collection_types import CollectionResult, CollectionStatus, CollectionStats

logger = logging.getLogger(__name__)


class CollectionMonitor:
    """수집 모니터링 시스템"""

    def __init__(self):
        """모니터링 시스템 초기화"""
        self.logger = logging.getLogger(f"{__name__}.monitor")
        self._alerts: List[Dict[str, Any]] = []
        self._performance_thresholds = {
            "max_duration": 300,  # 5분
            "min_success_rate": 80,  # 80%
            "max_error_rate": 20,  # 20%
            "max_consecutive_failures": 3,
        }

    def generate_status_report(
        self,
        collectors: Dict[str, BaseCollector],
        global_config: Dict[str, Any],
        collection_history: List[CollectionResult],
        stats: CollectionStats,
    ) -> Dict[str, Any]:
        """전체 상태 보고서 생성

        Args:
            collectors: 수집기 딕셔너리
            global_config: 전역 설정
            collection_history: 수집 히스토리
            stats: 수집 통계

        Returns:
            상세 상태 보고서
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "global_status": {
                "enabled": global_config.get("global_enabled", True),
                "total_collectors": len(collectors),
                "running_collectors": len(self._get_running_collectors(collectors)),
                "healthy_collectors": len(self._get_healthy_collectors(collectors)),
                "enabled_collectors": len(
                    [c for c in collectors.values() if c.config.enabled]
                ),
            },
            "collectors": {
                name: self._get_collector_status(collector)
                for name, collector in collectors.items()
            },
            "recent_activity": {
                "recent_results": [
                    result.to_dict() for result in collection_history[-10:]
                ],
                "total_collections": len(collection_history),
                "statistics": stats.to_dict(),
            },
            "system_health": self._assess_system_health(collectors, collection_history),
            "resource_usage": self._get_resource_usage(collectors),
            "alerts": self._get_active_alerts(),
            "recommendations": self._generate_recommendations(
                collectors, collection_history
            ),
        }

    def _get_collector_status(self, collector: BaseCollector) -> Dict[str, Any]:
        """개별 수집기 상태 조회

        Args:
            collector: 수집기 객체

        Returns:
            수집기 상태 딕셔너리
        """
        health_check = collector.health_check()

        return {
            "name": collector.name,
            "type": collector.source_type,
            "enabled": collector.config.enabled,
            "is_running": collector.is_running,
            "is_healthy": collector.is_healthy,
            "health_details": health_check,
            "configuration": {
                "timeout": collector.config.timeout,
                "max_retries": collector.config.max_retries,
                "retry_delay": collector.config.retry_delay,
                "priority": collector.config.priority.value,
            },
            "last_result": (
                collector.current_result.to_dict() if collector.current_result else None
            ),
        }

    def _get_running_collectors(
        self, collectors: Dict[str, BaseCollector]
    ) -> List[str]:
        """실행 중인 수집기 목록

        Args:
            collectors: 수집기 딕셔너리

        Returns:
            실행 중인 수집기 이름 목록
        """
        return [name for name, collector in collectors.items() if collector.is_running]

    def _get_healthy_collectors(
        self, collectors: Dict[str, BaseCollector]
    ) -> List[str]:
        """건강한 수집기 목록

        Args:
            collectors: 수집기 딕셔너리

        Returns:
            건강한 수집기 이름 목록
        """
        return [name for name, collector in collectors.items() if collector.is_healthy]

    def _assess_system_health(
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

    def _get_resource_usage(
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
            "memory_usage_mb": 0,  # TODO: psutil로 실제 메모리 사용량 측정
            "cpu_usage_percent": 0,  # TODO: psutil로 실제 CPU 사용량 측정
            "utilization_rate": (
                (running_count / len(collectors) * 100) if collectors else 0
            ),
        }

    def _get_active_alerts(self) -> List[Dict[str, Any]]:
        """활성 경고 목록 조회

        Returns:
            활성 경고 목록
        """
        # 최근 경고만 반환 (예: 최근 1시간)
        current_time = datetime.now()
        active_alerts = []

        for alert in self._alerts:
            alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
            time_diff = (current_time - alert_time).total_seconds()

            # 1시간 이내의 경고만 활성으로 간주
            if time_diff <= 3600:
                active_alerts.append(alert)

        return active_alerts

    def _generate_recommendations(
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

    def add_alert(self, level: str, message: str, collector_name: Optional[str] = None):
        """경고 추가

        Args:
            level: 경고 수준 (info, warning, error, critical)
            message: 경고 메시지
            collector_name: 관련 수집기 이름 (선택사항)
        """
        alert = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "collector": collector_name,
        }

        self._alerts.append(alert)

        # 경고 목록 크기 제한 (최대 100개)
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

        self.logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"Alert: {message}"
            + (f" (collector: {collector_name})" if collector_name else ""),
        )

    def check_collector_health(self, collector: BaseCollector) -> bool:
        """수집기 건강 상태 확인 및 경고 생성

        Args:
            collector: 확인할 수집기

        Returns:
            건강 상태 (True: 건강, False: 문제)
        """
        health_check = collector.health_check()

        # 연속 실패 확인
        consecutive_failures = health_check.get("consecutive_failures", 0)
        if (
            consecutive_failures
            >= self._performance_thresholds["max_consecutive_failures"]
        ):
            self.add_alert(
                "warning",
                f"수집기 '{collector.name}'에서 연속 {consecutive_failures}회 실패",
                collector.name,
            )
            return False

        # 성공률 확인
        success_rate = health_check.get("success_rate", 100)
        if success_rate < self._performance_thresholds["min_success_rate"]:
            self.add_alert(
                "warning",
                f"수집기 '{collector.name}'의 성공률이 낮습니다 ({success_rate:.1f}%)",
                collector.name,
            )
            return False

        return True

    def update_performance_thresholds(self, thresholds: Dict[str, float]):
        """성능 임계값 업데이트

        Args:
            thresholds: 새로운 임계값 딕셔너리
        """
        self._performance_thresholds.update(thresholds)
        self.logger.info(f"성능 임계값 업데이트: {thresholds}")

    def clear_alerts(self):
        """모든 경고 삭제"""
        self._alerts.clear()
        self.logger.info("모든 경고가 삭제되었습니다.")


if __name__ == "__main__":
    import sys

    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0

    # 테스트용 수집기 구현
    try:
        from .collection_types import CollectionConfig
    except ImportError:
        from collection_types import CollectionConfig

    class TestCollector(BaseCollector):
        @property
        def source_type(self) -> str:
            return "test"

        async def _collect_data(self) -> List[Any]:
            return ["item1", "item2"]

    # 테스트 1: 모니터 초기화
    total_tests += 1
    try:
        monitor = CollectionMonitor()

        if not hasattr(monitor, "_alerts"):
            all_validation_failures.append("모니터 초기화: _alerts 속성 누락")

    except Exception as e:
        all_validation_failures.append(f"모니터 초기화 오류: {e}")

    # 테스트 2: 상태 보고서 생성
    total_tests += 1
    try:
        config = CollectionConfig(enabled=True)
        test_collector = TestCollector("test_monitor", config)
        collectors = {"test_monitor": test_collector}
        global_config = {"global_enabled": True}
        collection_history = []
        stats = CollectionStats()

        report = monitor.generate_status_report(
            collectors, global_config, collection_history, stats
        )

        required_sections = ["global_status", "collectors", "system_health"]
        for section in required_sections:
            if section not in report:
                all_validation_failures.append(f"상태 보고서: {section} 섹션 누락")

    except Exception as e:
        all_validation_failures.append(f"상태 보고서 생성 오류: {e}")

    # 테스트 3: 경고 시스템
    total_tests += 1
    try:
        monitor.add_alert("warning", "테스트 경고", "test_collector")

        alerts = monitor._get_active_alerts()
        if len(alerts) != 1:
            all_validation_failures.append(
                f"경고 시스템: 예상 경고 1개, 실제 {len(alerts)}개"
            )

        if alerts and alerts[0]["message"] != "테스트 경고":
            all_validation_failures.append("경고 시스템: 경고 메시지 불일치")

    except Exception as e:
        all_validation_failures.append(f"경고 시스템 오류: {e}")

    # 테스트 4: 건강 상태 평가
    total_tests += 1
    try:
        health = monitor._assess_system_health(collectors, [])

        required_fields = ["overall_status", "score", "healthy_collectors"]
        for field in required_fields:
            if field not in health:
                all_validation_failures.append(f"건강 상태: {field} 필드 누락")

    except Exception as e:
        all_validation_failures.append(f"건강 상태 평가 오류: {e}")

    # 테스트 5: 수집기 건강 확인
    total_tests += 1
    try:
        is_healthy = monitor.check_collector_health(test_collector)

        if not isinstance(is_healthy, bool):
            all_validation_failures.append("수집기 건강 확인: 불린 값이 아닌 결과")

    except Exception as e:
        all_validation_failures.append(f"수집기 건강 확인 오류: {e}")

    # 최종 검증 결과
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("CollectionMonitor module is validated and ready for use")
        sys.exit(0)
