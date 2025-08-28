#!/usr/bin/env python3
"""
수집 실행 엔진 시스템

비동기 수집 실행, 세마포어 제어, 결과 관리를 담당합니다.
동시 수집 제한, 에러 처리, 결과 수집 기능을 제공합니다.

관련 패키지 문서:
- asyncio: https://docs.python.org/3/library/asyncio.html
- typing: https://docs.python.org/3/library/typing.html

입력 예시:
- collectors: BaseCollector 객체들의 딕셔너리
- semaphore_limit: 동시 실행 제한 수

출력 예시:
- 수집 결과 딕셔너리 (CollectionResult 객체들)
- 실행 통계 및 상태 정보
"""

import asyncio
import logging
from typing import Any, Dict, List

# 조건부 임포트로 독립 실행 지원
try:
    from .base_collector import BaseCollector
    from .collection_types import CollectionResult, CollectionStats, CollectionStatus
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from base_collector import BaseCollector
    from collection_types import CollectionResult, CollectionStats, CollectionStatus

logger = logging.getLogger(__name__)


class CollectionExecutor:
    """수집 실행 엔진"""

    def __init__(self, concurrent_limit: int = 3):
        """수집 실행 엔진 초기화

        Args:
            concurrent_limit: 동시 실행 제한 수
        """
        self.concurrent_limit = concurrent_limit
        self.collection_history: List[CollectionResult] = []
        self.max_history_size = 100
        self.stats = CollectionStats()
        self.logger = logging.getLogger(f"{__name__}.executor")

    async def execute_all_collections(
        self, collectors: Dict[str, BaseCollector], global_enabled: bool = True
    ) -> Dict[str, CollectionResult]:
        """모든 수집기 실행

        Args:
            collectors: 수집기 딕셔너리
            global_enabled: 전역 활성화 상태

        Returns:
            수집 결과 딕셔너리
        """
        if not global_enabled:
            self.logger.info("전역 수집이 비활성화되어 있습니다.")
            return {}

        if not collectors:
            self.logger.warning("등록된 수집기가 없습니다.")
            return {}

        self.logger.info(f"전체 수집 시작: {len(collectors)}개 수집기")

        # 세마포어를 사용한 동시 수집 제한
        semaphore = asyncio.Semaphore(self.concurrent_limit)

        async def collect_with_semaphore(collector: BaseCollector):
            """세마포어 적용된 수집 실행"""
            async with semaphore:
                try:
                    return await collector.collect()
                except Exception as e:
                    self.logger.error(f"수집기 {collector.name} 실행 오류: {e}")
                    return CollectionResult(
                        source_name=collector.name,
                        status=CollectionStatus.FAILED,
                        error_message=str(e),
                    )

        # 모든 수집기 병렬 실행
        tasks = [
            collect_with_semaphore(collector)
            for collector in collectors.values()
            if collector.config.enabled
        ]

        if not tasks:
            self.logger.warning("활성화된 수집기가 없습니다.")
            return {}

        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            self.logger.error(f"전체 수집 오류: {e}")
            return {}

        # 결과 정리
        collection_results = {}
        active_collectors = [c for c in collectors.values() if c.config.enabled]

        for i, result in enumerate(results):
            collector_name = active_collectors[i].name

            if isinstance(result, Exception):
                collection_results[collector_name] = CollectionResult(
                    source_name=collector_name,
                    status=CollectionStatus.FAILED,
                    error_message=str(result),
                )
            else:
                collection_results[collector_name] = result

        # 히스토리 저장 및 통계 업데이트
        self._update_statistics(collection_results)

        # 전체 수집 상태 로깅
        failed_count = sum(
            1
            for r in collection_results.values()
            if r.status == CollectionStatus.FAILED
        )

        self.logger.info(
            f"전체 수집 완료: 성공 {len(collection_results) - failed_count}, 실패 {failed_count}"
        )
        return collection_results

    async def execute_single_collection(
        self, collector: BaseCollector
    ) -> CollectionResult:
        """단일 수집기 실행

        Args:
            collector: 실행할 수집기

        Returns:
            수집 결과
        """
        try:
            result = await collector.collect()
            self.collection_history.append(result)
            self.stats.update_from_result(result)
            self._trim_history()
            return result
        except Exception as e:
            self.logger.error(f"단일 수집 오류 ({collector.name}): {e}")
            error_result = CollectionResult(
                source_name=collector.name,
                status=CollectionStatus.FAILED,
                error_message=str(e),
            )
            self.collection_history.append(error_result)
            self._trim_history()
            return error_result

    def _update_statistics(self, collection_results: Dict[str, CollectionResult]):
        """통계 정보 업데이트

        Args:
            collection_results: 수집 결과 딕셔너리
        """
        for result in collection_results.values():
            self.collection_history.append(result)
            self.stats.update_from_result(result)

        self._trim_history()

    def _trim_history(self):
        """히스토리 크기 제한"""
        if len(self.collection_history) > self.max_history_size:
            self.collection_history = self.collection_history[-self.max_history_size :]

    def get_execution_statistics(self) -> Dict[str, Any]:
        """실행 통계 조회

        Returns:
            실행 통계 딕셔너리
        """
        total_items = sum(r.collected_count for r in self.collection_history)
        total_errors = sum(r.error_count for r in self.collection_history)

        return {
            "total_executions": len(self.collection_history),
            "total_items_collected": total_items,
            "total_errors": total_errors,
            "average_success_rate": self.stats.average_success_rate,
            "average_duration": self.stats.average_duration,
            "recent_results": [
                result.to_dict() for result in self.collection_history[-5:]
            ],
            "success_rate_trend": self._calculate_success_rate_trend(),
            "performance_trend": self._calculate_performance_trend(),
        }

    def _calculate_success_rate_trend(self) -> List[float]:
        """성공률 동향 계산

        Returns:
            최근 10개 수집의 성공률 목록
        """
        recent_results = self.collection_history[-10:]
        return [r.success_rate for r in recent_results]

    def _calculate_performance_trend(self) -> List[float]:
        """성능 동향 계산 (초당 아이템 수)

        Returns:
            최근 10개 수집의 성능 지표 목록
        """
        recent_results = self.collection_history[-10:]
        return [
            r.items_per_second or 0.0
            for r in recent_results
            if r.items_per_second is not None
        ]

    def reset_statistics(self):
        """통계 정보 리셋"""
        self.stats = CollectionStats()
        self.collection_history.clear()
        self.logger.info("실행 통계 리셋 완료")

    def get_recent_results(self, limit: int = 10) -> List[CollectionResult]:
        """최근 수집 결과 조회

        Args:
            limit: 조회할 결과 수

        Returns:
            최근 수집 결과 목록
        """
        return self.collection_history[-limit:]

    def get_failed_results(self, limit: int = 10) -> List[CollectionResult]:
        """실패한 수집 결과 조회

        Args:
            limit: 조회할 결과 수

        Returns:
            실패한 수집 결과 목록
        """
        failed_results = [
            r for r in self.collection_history if r.status == CollectionStatus.FAILED
        ]
        return failed_results[-limit:]

    def get_collector_performance(self, collector_name: str) -> Dict[str, Any]:
        """특정 수집기 성능 조회

        Args:
            collector_name: 수집기 이름

        Returns:
            수집기별 성능 통계
        """
        collector_results = [
            r for r in self.collection_history if r.source_name == collector_name
        ]

        if not collector_results:
            return {"error": "수집 기록이 없습니다."}

        successful = [
            r for r in collector_results if r.status == CollectionStatus.COMPLETED
        ]

        return {
            "total_executions": len(collector_results),
            "successful_executions": len(successful),
            "success_rate": (len(successful) / len(collector_results)) * 100,
            "average_items": (
                sum(r.collected_count for r in successful) / len(successful)
                if successful
                else 0
            ),
            "recent_results": [r.to_dict() for r in collector_results[-5:]],
        }


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
            await asyncio.sleep(0.1)
            return ["item1", "item2", "item3"]

    # 테스트 1: 실행 엔진 초기화
    total_tests += 1
    try:
        executor = CollectionExecutor(concurrent_limit=2)

        if executor.concurrent_limit != 2:
            all_validation_failures.append(
                f"실행 엔진 초기화: 예상 limit 2, 실제 {executor.concurrent_limit}"
            )

    except Exception as e:
        all_validation_failures.append(f"실행 엔진 초기화 오류: {e}")

    # 테스트 2: 단일 수집 실행
    total_tests += 1
    try:
        config = CollectionConfig(enabled=True, timeout=5)
        test_collector = TestCollector("test_single", config)

        async def test_single_execution():
            return await executor.execute_single_collection(test_collector)

        result = asyncio.run(test_single_execution())

        if result.status != CollectionStatus.COMPLETED:
            all_validation_failures.append(f"단일 수집: 예상 COMPLETED, 실제 {result.status}")

        if result.collected_count != 3:
            all_validation_failures.append(
                f"단일 수집: 예상 수집 3개, 실제 {result.collected_count}개"
            )

    except Exception as e:
        all_validation_failures.append(f"단일 수집 실행 오류: {e}")

    # 테스트 3: 다중 수집 실행
    total_tests += 1
    try:
        collectors = {
            "test1": TestCollector("test1", config),
            "test2": TestCollector("test2", config),
        }

        async def test_multiple_execution():
            return await executor.execute_all_collections(
                collectors, global_enabled=True
            )

        results = asyncio.run(test_multiple_execution())

        if len(results) != 2:
            all_validation_failures.append(f"다중 수집: 예상 결과 2개, 실제 {len(results)}개")

        if "test1" not in results or "test2" not in results:
            all_validation_failures.append("다중 수집: 예상 수집기 결과 누락")

    except Exception as e:
        all_validation_failures.append(f"다중 수집 실행 오류: {e}")

    # 테스트 4: 통계 조회
    total_tests += 1
    try:
        stats = executor.get_execution_statistics()

        required_fields = [
            "total_executions",
            "total_items_collected",
            "average_success_rate",
        ]
        for field in required_fields:
            if field not in stats:
                all_validation_failures.append(f"통계 조회: {field} 필드 누락")

        if stats["total_executions"] == 0:
            all_validation_failures.append("통계 조회: 실행 기록이 없음")

    except Exception as e:
        all_validation_failures.append(f"통계 조회 오류: {e}")

    # 테스트 5: 수집기별 성능 조회
    total_tests += 1
    try:
        performance = executor.get_collector_performance("test1")

        if "total_executions" not in performance:
            all_validation_failures.append("수집기 성능: total_executions 필드 누락")

        if performance.get("total_executions", 0) == 0:
            all_validation_failures.append("수집기 성능: 실행 기록이 없음")

    except Exception as e:
        all_validation_failures.append(f"수집기 성능 조회 오류: {e}")

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
        print("CollectionExecutor module is validated and ready for use")
        sys.exit(0)
