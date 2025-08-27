#!/usr/bin/env python3
"""
수집 모니터링 및 상태 관리 시스템 (리팩토링된 버전)

수집기 상태 추적, 성능 모니터링, 리소스 사용량 관리를 담당합니다.
상태 보고서 생성, 건강 상태 확인, 경고 시스템을 제공합니다.

이 모듈은 다음 컴포넌트들을 통합합니다:
- CollectionHealthAssessor: 건강 상태 평가
- CollectionAlertManager: 경고 시스템 관리
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .base_collector import BaseCollector
    from .collection_monitor_alerts import CollectionAlertManager
    from .collection_monitor_health import CollectionHealthAssessor
    from .collection_types import CollectionResult, CollectionStats, CollectionStatus
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_collector import BaseCollector
    from collection_monitor_alerts import CollectionAlertManager
    from collection_monitor_health import CollectionHealthAssessor
    from collection_types import CollectionResult, CollectionStats, CollectionStatus

logger = logging.getLogger(__name__)


class CollectionMonitor:
    """수집 모니터링 시스템 (리팩토링된 버전)"""

    def __init__(self):
        """모니터링 시스템 초기화"""
        self.logger = logging.getLogger(f"{__name__}.monitor")

        # 컴포넌트 초기화
        self.health_assessor = CollectionHealthAssessor()
        self.alert_manager = CollectionAlertManager()

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
            "system_health": self.health_assessor.assess_system_health(
                collectors, collection_history
            ),
            "resource_usage": self.health_assessor.get_resource_usage(collectors),
            "alerts": self.alert_manager.get_active_alerts(),
            "recommendations": self.health_assessor.generate_recommendations(
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
        """실행 중인 수집기 목록"""
        return [name for name, collector in collectors.items() if collector.is_running]

    def _get_healthy_collectors(
        self, collectors: Dict[str, BaseCollector]
    ) -> List[str]:
        """건강한 수집기 목록"""
        return [name for name, collector in collectors.items() if collector.is_healthy]

    def add_alert(self, level: str, message: str, collector_name: Optional[str] = None):
        """경고 추가 (alert_manager에 위임)"""
        self.alert_manager.add_alert(level, message, collector_name)

    def check_collector_health(self, collector: BaseCollector) -> bool:
        """수집기 건강 상태 확인 및 경고 생성

        Args:
            collector: 확인할 수집기

        Returns:
            건강 상태 (True: 건강, False: 문제)
        """
        is_healthy, issues = self.health_assessor.check_collector_health(collector)

        # 문제가 발견되면 경고 생성
        if not is_healthy:
            for issue in issues:
                self.alert_manager.add_alert(
                    "warning", f"수집기 '{collector.name}': {issue}", collector.name
                )

        return is_healthy

    def update_performance_thresholds(self, thresholds: Dict[str, float]):
        """성능 임계값 업데이트 (health_assessor에 위임)"""
        self.health_assessor.update_performance_thresholds(thresholds)
        self.logger.info(f"성능 임계값 업데이트: {thresholds}")

    def clear_alerts(self, collector_name: Optional[str] = None):
        """모든 경고 삭제 (alert_manager에 위임)"""
        self.alert_manager.clear_alerts(collector_name)

    def get_alert_summary(self) -> Dict[str, Any]:
        """경고 요약 정보 조회 (alert_manager에 위임)"""
        return self.alert_manager.get_alert_summary()


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

        if not hasattr(monitor, "health_assessor"):
            all_validation_failures.append("모니터 초기화: health_assessor 속성 누락")

        if not hasattr(monitor, "alert_manager"):
            all_validation_failures.append("모니터 초기화: alert_manager 속성 누락")

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

        alerts = monitor.alert_manager.get_active_alerts()
        if len(alerts) != 1:
            all_validation_failures.append(
                f"경고 시스템: 예상 경고 1개, 실제 {len(alerts)}개"
            )

        if alerts and alerts[0]["message"] != "테스트 경고":
            all_validation_failures.append("경고 시스템: 경고 메시지 불일치")

    except Exception as e:
        all_validation_failures.append(f"경고 시스템 오류: {e}")

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
        print("Refactored CollectionMonitor module is validated and ready for use")
        sys.exit(0)
