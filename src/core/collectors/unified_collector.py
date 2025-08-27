#!/usr/bin/env python3
"""
통합 수집기 시스템 (메인 모듈)

모든 IP 소스의 수집을 통합 관리하는 리팩토링된 시스템입니다.
분할된 모듈들을 통합하여 단일 진입점을 제공합니다.

관련 패키지 문서:
- .collection_types: 데이터 타입 정의
- .base_collector: 추상 기본 클래스
- .collection_manager: 관리자 구현

입력 예시:
- config_path: "instance/unified_collection_config.json"
- collector: BaseCollector 인스턴스

출력 예시:
- 수집 결과 딕셔너리
- 통합 상태 보고서
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .base_collector import BaseCollector
    from .collection_manager import UnifiedCollectionManager
    from .collection_types import (
        CollectionConfig,
        CollectionPriority,
        CollectionResult,
        CollectionStats,
        CollectionStatus,
    )
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_collector import BaseCollector
    from collection_manager import UnifiedCollectionManager
    from collection_types import (
        CollectionConfig,
        CollectionPriority,
        CollectionResult,
        CollectionStats,
        CollectionStatus,
    )

logger = logging.getLogger(__name__)

# 메인 모듈의 공개 인터페이스
__all__ = [
    "CollectionStatus",
    "CollectionPriority",
    "CollectionResult",
    "CollectionConfig",
    "CollectionStats",
    "BaseCollector",
    "UnifiedCollectionManager",
    "UnifiedCollector",  # 호환성을 위한 별칭
    "create_collection_manager",
    "create_default_config",
]


def create_collection_manager(
    config_path: str = "instance/unified_collection_config.json",
) -> UnifiedCollectionManager:
    """통합 수집 관리자 생성 팩토리 함수

    Args:
        config_path: 설정 파일 경로

    Returns:
        UnifiedCollectionManager 인스턴스
    """
    try:
        manager = UnifiedCollectionManager(config_path)
        logger.info(f"통합 수집 관리자 생성 완료: {config_path}")
        return manager
    except Exception as e:
        logger.error(f"통합 수집 관리자 생성 실패: {e}")
        raise


def create_default_config(
    priority: CollectionPriority = CollectionPriority.NORMAL, **kwargs
) -> CollectionConfig:
    """기본 수집 설정 생성 팩토리 함수

    Args:
        priority: 수집 우선순위
        **kwargs: 추가 설정 옵션

    Returns:
        CollectionConfig 인스턴스
    """
    default_settings = {
        "enabled": True,
        "interval": 3600,
        "max_retries": 3,
        "timeout": 300,
        "parallel_workers": 1,
        "priority": priority,
        "rate_limit": None,
        "retry_delay": 5,
        "circuit_breaker_threshold": 5,
    }

    # 사용자 정의 설정으로 기본값 덮어쓰기
    default_settings.update(kwargs)

    return CollectionConfig(**default_settings)


# 호환성을 위한 별칭
UnifiedCollector = UnifiedCollectionManager


class CollectionOrchestrator:
    """수집 오케스트레이터 - 고수준 수집 관리"""

    def __init__(self, config_path: Optional[str] = None):
        """오케스트레이터 초기화

        Args:
            config_path: 설정 파일 경로
        """
        self.manager = create_collection_manager(
            config_path or "instance/unified_collection_config.json"
        )
        self.logger = logging.getLogger(f"{__name__}.orchestrator")

    def register_collectors(self, collectors: List[BaseCollector]):
        """여러 수집기 일괄 등록

        Args:
            collectors: 등록할 수집기 목록
        """
        for collector in collectors:
            try:
                self.manager.register_collector(collector)
                self.logger.info(f"수집기 등록 성공: {collector.name}")
            except Exception as e:
                self.logger.error(f"수집기 등록 실패 ({collector.name}): {e}")

    async def run_collection_cycle(self) -> Dict[str, CollectionResult]:
        """수집 사이클 실행

        Returns:
            수집 결과 딕셔너리
        """
        try:
            self.logger.info("수집 사이클 시작")
            results = await self.manager.collect_all()

            # 결과 요약 로깅
            successful = sum(
                1 for r in results.values() if r.status == CollectionStatus.COMPLETED
            )
            failed = len(results) - successful

            self.logger.info(f"수집 사이클 완료: 성공 {successful}, 실패 {failed}")

            return results

        except Exception as e:
            self.logger.error(f"수집 사이클 실행 오류: {e}")
            raise

    def get_comprehensive_status(self) -> Dict[str, Any]:
        """종합 상태 정보 조회

        Returns:
            종합 상태 딕셔너리
        """
        status = self.manager.get_detailed_status()
        performance = self.manager.get_performance_report()

        # 새로운 모니터링 시스템 출력 형식에 맞게 조정
        global_status = status.get("global_status", {})

        return {
            "status": status,
            "performance": performance,
            "summary": {
                "total_collectors": global_status.get("total_collectors", 0),
                "running_collectors": global_status.get("running_collectors", 0),
                "healthy_collectors": global_status.get("healthy_collectors", 0),
                "global_enabled": global_status.get("enabled", True),
                "recent_success_rate": performance.get("average_success_rate", 0.0),
            },
        }

    def emergency_stop(self):
        """긴급 정지 - 모든 수집 중단"""
        self.logger.warning("긴급 정지 실행")
        self.manager.cancel_all_collections()
        self.manager.disable_global_collection()

    def health_check(self) -> bool:
        """전체 시스템 건강 상태 확인

        Returns:
            시스템이 정상이면 True
        """
        try:
            status = self.manager.get_detailed_status()
            global_status = status.get("global_status", {})

            # 기본 조건 확인
            if not global_status.get("enabled", True):
                return False

            # 건강한 수집기가 하나라도 있는지 확인
            healthy_count = global_status.get("healthy_collectors", 0)
            total_count = global_status.get("total_collectors", 0)

            if healthy_count == 0 and total_count > 0:
                return False

            return True

        except Exception as e:
            self.logger.error(f"건강 상태 확인 오류: {e}")
            return False


# 사용 예시 및 검증
if __name__ == "__main__":
    import sys
    import tempfile

    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0

    # 테스트용 수집기 구현
    class TestCollector(BaseCollector):
        @property
        def source_type(self) -> str:
            return "test"

        async def _collect_data(self) -> List[Any]:
            await asyncio.sleep(0.1)
            return ["test_item1", "test_item2"]

    # 임시 디렉터리 사용
    with tempfile.TemporaryDirectory() as temp_dir:
        config_path = f"{temp_dir}/test_unified_config.json"

        # 테스트 1: 팩토리 함수 검증
        total_tests += 1
        try:
            manager = create_collection_manager(config_path)

            if not isinstance(manager, UnifiedCollectionManager):
                all_validation_failures.append("팩토리 함수: 잘못된 타입 반환")

        except Exception as e:
            all_validation_failures.append(f"팩토리 함수 오류: {e}")

        # 테스트 2: 기본 설정 생성
        total_tests += 1
        try:
            config = create_default_config(priority=CollectionPriority.HIGH, timeout=60)

            if config.priority != CollectionPriority.HIGH:
                all_validation_failures.append("기본 설정: 우선순위 설정 실패")

            if config.timeout != 60:
                all_validation_failures.append("기본 설정: 타임아웃 설정 실패")

        except Exception as e:
            all_validation_failures.append(f"기본 설정 생성 오류: {e}")

        # 테스트 3: 오케스트레이터 기능
        total_tests += 1
        try:
            orchestrator = CollectionOrchestrator(config_path)

            test_collector = TestCollector("test_orchestrator", config)
            orchestrator.register_collectors([test_collector])

            collectors = orchestrator.manager.list_collectors()
            if "test_orchestrator" not in collectors:
                all_validation_failures.append("오케스트레이터: 수집기 등록 실패")

        except Exception as e:
            all_validation_failures.append(f"오케스트레이터 기능 오류: {e}")

        # 테스트 4: 종합 상태 정보
        total_tests += 1
        try:
            comprehensive_status = orchestrator.get_comprehensive_status()

            required_sections = ["status", "performance", "summary"]
            for section in required_sections:
                if section not in comprehensive_status:
                    all_validation_failures.append(f"종합 상태: {section} 섹션 누락")

        except Exception as e:
            all_validation_failures.append(f"종합 상태 정보 오류: {e}")

        # 테스트 5: 비동기 수집 사이클
        total_tests += 1
        try:

            async def test_collection_cycle():
                return await orchestrator.run_collection_cycle()

            cycle_results = asyncio.run(test_collection_cycle())

            if "test_orchestrator" not in cycle_results:
                all_validation_failures.append("수집 사이클: 결과에 등록된 수집기 누락")

        except Exception as e:
            all_validation_failures.append(f"비동기 수집 사이클 오류: {e}")

        # 테스트 6: 건강 상태 확인
        total_tests += 1
        try:
            health_status = orchestrator.health_check()

            if not isinstance(health_status, bool):
                all_validation_failures.append("건강 상태: 불린 값이 아닌 결과 반환")

        except Exception as e:
            all_validation_failures.append(f"건강 상태 확인 오류: {e}")

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
        print("Unified collector system is validated and ready for use")
        sys.exit(0)
