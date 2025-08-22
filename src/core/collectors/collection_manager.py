#!/usr/bin/env python3
"""
통합 수집 관리자 시스템 (메인 코디네이터)

수집기 등록 관리, 설정 관리, 서비스 코디네이션을 담당합니다.
실행 엔진과 모니터링 시스템을 조합하여 통합 인터페이스를 제공합니다.

관련 패키지 문서:
- json: https://docs.python.org/3/library/json.html
- pathlib: https://docs.python.org/3/library/pathlib.html

입력 예시:
- config_path: "instance/unified_collection_config.json"
- collector: BaseCollector 객체

출력 예시:
- 통합 수집 결과
- 종합 상태 보고서
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .base_collector import BaseCollector
    from .collection_types import CollectionResult, CollectionStatus
    from .collection_execution import CollectionExecutor
    from .collection_monitoring import CollectionMonitor
except ImportError:
    import sys
    import os

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_collector import BaseCollector
    from collection_types import CollectionResult, CollectionStatus
    from collection_execution import CollectionExecutor
    from collection_monitoring import CollectionMonitor

logger = logging.getLogger(__name__)


class UnifiedCollectionManager:
    """통합 수집 관리자 - 메인 코디네이터"""

    def __init__(self, config_path: str = "instance/unified_collection_config.json"):
        """통합 수집 관리자 초기화

        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = Path(config_path)
        self.collectors: Dict[str, BaseCollector] = {}
        self.global_config = self._load_config()

        # 핵심 구성 요소 초기화
        self.executor = CollectionExecutor(
            concurrent_limit=self.global_config.get("concurrent_collections", 3)
        )
        self.monitor = CollectionMonitor()

        # 테스트 호환성을 위한 속성
        self._status = CollectionStatus.IDLE

        self.logger = logging.getLogger(__name__)

    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            else:
                # 기본 설정
                default_config = {
                    "global_enabled": True,
                    "concurrent_collections": 3,
                    "retry_delay": 5,
                    "collectors": {},
                    "resource_limits": {"max_memory_mb": 512, "max_cpu_percent": 80},
                    "monitoring": {
                        "health_check_interval": 30,
                        "stats_retention_days": 7,
                    },
                }
                self._save_config(default_config)
                return default_config
        except Exception as e:
            self.logger.error(f"설정 파일 로드 실패: {e}")
            return {"global_enabled": True, "collectors": {}}

    def _save_config(self, config: Dict[str, Any]):
        """설정 파일 저장"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"설정 파일 저장 실패: {e}")

    def register_collector(self, collector: BaseCollector):
        """수집기 등록"""
        if not isinstance(collector, BaseCollector):
            raise TypeError("수집기는 BaseCollector 인스턴스여야 합니다.")

        self.collectors[collector.name] = collector
        self.logger.info(f"수집기 등록: {collector.name} ({collector.source_type})")

    def unregister_collector(self, name: str) -> bool:
        """수집기 등록 해제"""
        if name in self.collectors:
            collector = self.collectors[name]
            if collector.is_running:
                collector.cancel()
                self.logger.warning(f"실행 중인 수집기 등록 해제: {name}")

            del self.collectors[name]
            self.logger.info(f"수집기 등록 해제: {name}")
            return True
        return False

    def get_collector(self, name: str) -> Optional[BaseCollector]:
        """수집기 조회"""
        return self.collectors.get(name)

    def list_collectors(self) -> List[str]:
        """수집기 목록 조회"""
        return list(self.collectors.keys())

    def get_running_collectors(self) -> List[str]:
        """실행 중인 수집기 목록"""
        return [
            name for name, collector in self.collectors.items() if collector.is_running
        ]

    def get_healthy_collectors(self) -> List[str]:
        """정상 상태 수집기 목록"""
        return [
            name for name, collector in self.collectors.items() if collector.is_healthy
        ]

    async def collect_all(self) -> Dict[str, CollectionResult]:
        """모든 수집기 실행 (실행 엔진 위임)"""
        self._set_status(CollectionStatus.RUNNING)

        try:
            results = await self.executor.execute_all_collections(
                self.collectors, self.global_config.get("global_enabled", True)
            )

            # 상태 업데이트
            if not results:
                self._set_status(CollectionStatus.COMPLETED)
            else:
                failed_count = sum(
                    1 for r in results.values() if r.status == CollectionStatus.FAILED
                )

                if failed_count == 0:
                    self._set_status(CollectionStatus.COMPLETED)
                elif failed_count == len(results):
                    self._set_status(CollectionStatus.FAILED)
                else:
                    self._set_status(CollectionStatus.COMPLETED)

            return results

        except Exception as e:
            self.logger.error(f"전체 수집 실행 오류: {e}")
            self._set_status(CollectionStatus.FAILED)
            return {}

    async def collect_single(self, collector_name: str) -> Optional[CollectionResult]:
        """단일 수집기 실행 (실행 엔진 위임)"""
        collector = self.collectors.get(collector_name)
        if not collector:
            self.logger.error(f"수집기를 찾을 수 없습니다: {collector_name}")
            return None

        return await self.executor.execute_single_collection(collector)

    def cancel_collection(self, collector_name: str) -> bool:
        """수집 취소"""
        collector = self.collectors.get(collector_name)
        if collector:
            collector.cancel()
            self.logger.info(f"수집 취소 요청: {collector_name}")
            return True
        return False

    def cancel_all_collections(self):
        """모든 수집 취소"""
        cancelled_count = 0
        for collector in self.collectors.values():
            if collector.is_running:
                collector.cancel()
                cancelled_count += 1

        self.logger.info(f"모든 수집 취소 요청: {cancelled_count}개 수집기")

    def pause_collection(self, collector_name: str) -> bool:
        """수집 일시 정지"""
        collector = self.collectors.get(collector_name)
        if collector:
            collector.pause()
            self.logger.info(f"수집 일시 정지 요청: {collector_name}")
            return True
        return False

    def resume_collection(self, collector_name: str) -> bool:
        """수집 재개"""
        collector = self.collectors.get(collector_name)
        if collector:
            collector.resume()
            self.logger.info(f"수집 재개 요청: {collector_name}")
            return True
        return False

    def get_detailed_status(self) -> Dict[str, Any]:
        """전체 상태 조회 (모니터링 시스템 위임)"""
        return self.monitor.generate_status_report(
            self.collectors,
            self.global_config,
            self.executor.collection_history,
            self.executor.stats,
        )

    def _get_resource_usage(self) -> Dict[str, Any]:
        """리소스 사용량 조회"""
        # 기본적인 리소스 정보 반환
        # 실제 구현에서는 psutil 등을 사용할 수 있음
        return {
            "active_collections": len(self.get_running_collectors()),
            "total_collections_today": self.stats.total_collections,
            "memory_usage_mb": 0,  # TODO: psutil로 실제 메모리 사용량 측정
            "cpu_usage_percent": 0,  # TODO: psutil로 실제 CPU 사용량 측정
        }

    def enable_global_collection(self):
        """전역 수집 활성화"""
        self.global_config["global_enabled"] = True
        self._save_config(self.global_config)
        self.logger.info("전역 수집 활성화")

    def disable_global_collection(self):
        """전역 수집 비활성화"""
        self.global_config["global_enabled"] = False
        self._save_config(self.global_config)

        # 실행 중인 수집 취소
        self.cancel_all_collections()

        self.logger.info("전역 수집 비활성화")

    def enable_collector(self, name: str) -> bool:
        """수집기 활성화"""
        collector = self.collectors.get(name)
        if collector:
            collector.config.enabled = True
            self.logger.info(f"수집기 활성화: {name}")
            return True
        return False

    def disable_collector(self, name: str) -> bool:
        """수집기 비활성화"""
        collector = self.collectors.get(name)
        if collector:
            # 실행 중이라면 취소
            if collector.is_running:
                collector.cancel()

            collector.config.enabled = False
            self.logger.info(f"수집기 비활성화: {name}")
            return True
        return False

    def reset_collector_statistics(self, name: str) -> bool:
        """수집기 통계 리셋"""
        collector = self.collectors.get(name)
        if collector:
            collector.reset_statistics()
            return True
        return False

    def reset_all_statistics(self):
        """모든 통계 리셋"""
        for collector in self.collectors.values():
            collector.reset_statistics()

        self.executor.reset_statistics()
        self.monitor.clear_alerts()

        self.logger.info("모든 통계 리셋 완료")

    def get_performance_report(self) -> Dict[str, Any]:
        """성능 보고서 생성 (실행 엔진 위임)"""
        base_report = self.executor.get_execution_statistics()

        # 수집기별 상세 정보 추가
        base_report["collectors"] = {
            name: {
                "health": collector.health_check(),
                "performance": self.executor.get_collector_performance(name),
            }
            for name, collector in self.collectors.items()
        }

        return base_report

    # Test compatibility methods
    def _set_status(self, status: CollectionStatus):
        """Set global status for test compatibility"""
        self._status = status

    def get_status(self) -> CollectionStatus:
        """Get simple status for test compatibility"""
        return getattr(self, "_status", CollectionStatus.IDLE)

    def add_collector(self, collector):
        """Add collector for test compatibility"""
        self.register_collector(collector)

    def get_results(self) -> List[CollectionResult]:
        """Get results for test compatibility"""
        return self.executor.collection_history

    @property
    def _collectors(self):
        """Get collectors dict for test compatibility"""
        return self.collectors

    @property
    def _results(self):
        """Get results list for test compatibility"""
        return self.executor.collection_history

    @property
    def collection_history(self):
        """Access to collection history for compatibility"""
        return self.executor.collection_history

    @property
    def stats(self):
        """Access to statistics for compatibility"""
        return self.executor.stats


# Backward compatibility alias for tests
UnifiedCollector = UnifiedCollectionManager


if __name__ == "__main__":
    import asyncio
    import sys
    import tempfile

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
            await asyncio.sleep(0.1)
            return ["item1", "item2"]

    # 임시 디렉터리 사용
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = f"{temp_dir}/test_config.json"

        # 테스트 1: 관리자 초기화 (구성 요소 포함)
        total_tests += 1
        try:
            manager = UnifiedCollectionManager(config_path)

            required_components = ["collectors", "executor", "monitor"]
            for component in required_components:
                if not hasattr(manager, component):
                    all_validation_failures.append(
                        f"관리자 초기화: {component} 구성 요소 누락"
                    )

        except Exception as e:
            all_validation_failures.append(f"관리자 초기화 오류: {e}")

        # 테스트 2: 수집기 등록 및 위임 확인
        total_tests += 1
        try:
            config = CollectionConfig(enabled=True)
            test_collector = TestCollector("test_unified", config)

            manager.register_collector(test_collector)

            if "test_unified" not in manager.list_collectors():
                all_validation_failures.append("수집기 등록: 등록 실패")

        except Exception as e:
            all_validation_failures.append(f"수집기 등록 오류: {e}")

        # 테스트 3: 실행 엔진 위임 확인
        total_tests += 1
        try:

            async def test_execution_delegation():
                results = await manager.collect_all()
                return results

            results = asyncio.run(test_execution_delegation())

            if "test_unified" not in results:
                all_validation_failures.append("실행 위임: 결과에 수집기 누락")

        except Exception as e:
            all_validation_failures.append(f"실행 위임 오류: {e}")

        # 테스트 4: 모니터링 위임 확인
        total_tests += 1
        try:
            status = manager.get_detailed_status()

            required_sections = ["global_status", "system_health", "alerts"]
            for section in required_sections:
                if section not in status:
                    all_validation_failures.append(
                        f"모니터링 위임: {section} 섹션 누락"
                    )

        except Exception as e:
            all_validation_failures.append(f"모니터링 위임 오류: {e}")

        # 테스트 5: 성능 보고서 위임
        total_tests += 1
        try:
            report = manager.get_performance_report()

            if "total_executions" not in report:
                all_validation_failures.append("성능 보고서: 실행 통계 누락")

            if "collectors" not in report:
                all_validation_failures.append("성능 보고서: 수집기 정보 누락")

        except Exception as e:
            all_validation_failures.append(f"성능 보고서 오류: {e}")

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
        print(
            "UnifiedCollectionManager (coordinated) module is validated and ready for use"
        )
        sys.exit(0)
