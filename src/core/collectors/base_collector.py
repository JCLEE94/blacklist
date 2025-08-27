#!/usr/bin/env python3
"""
기본 수집기 추상 클래스

모든 수집기의 공통 인터페이스와 기본 기능을 제공합니다.
비동기 수집, 재시도, 타임아웃, 취소 기능을 지원합니다.

관련 패키지 문서:
- asyncio: https://docs.python.org/3/library/asyncio.html
- abc: https://docs.python.org/3/library/abc.html

입력 예시:
- name: "수집기 이름"
- config: CollectionConfig 객체

출력 예시:
- CollectionResult 객체 (수집 결과 포함)
- 상태 정보 디덕셔너리
"""

import asyncio
import logging
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

# 조건부 임포트로 독립 실행 지원
try:
    from .collection_types import CollectionConfig, CollectionResult, CollectionStatus
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from collection_types import CollectionConfig, CollectionResult, CollectionStatus

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    모든 수집기의 기본 클래스
    통일된 인터페이스 제공
    """

    def __init__(self, name: str, config: CollectionConfig):
        """기본 수집기 초기화

        Args:
            name: 수집기 이름
            config: 수집 설정
        """
        self.name = name
        self.config = config
        self.logger = logging.getLogger(f"{__name__}.{name}")

        # 상태 관리
        self._current_result = None
        self._is_running = False
        self._cancel_requested = False
        self._pause_requested = False

        # 성능 추적
        self._last_execution_time = None
        self._consecutive_failures = 0
        self._circuit_breaker_open = False
        self._rate_limiter_last_call = 0.0

        # 통계
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0

    @property
    @abstractmethod
    def source_type(self) -> str:
        """소스 타입 반환"""

    @property
    def is_running(self) -> bool:
        """수집 중 여부"""
        return self._is_running

    @property
    def current_result(self) -> Optional[CollectionResult]:
        """현재 수집 결과"""
        return self._current_result

    @property
    def is_healthy(self) -> bool:
        """수집기 상태 양호 여부"""
        return (
            not self._circuit_breaker_open
            and self._consecutive_failures < self.config.circuit_breaker_threshold
        )

    def cancel(self):
        """수집 취소 요청"""
        self._cancel_requested = True
        self.logger.info(f"수집 취소 요청: {self.name}")

    def pause(self):
        """수집 일시 정지 요청"""
        self._pause_requested = True
        self.logger.info(f"수집 일시 정지 요청: {self.name}")

    def resume(self):
        """수집 재개 요청"""
        self._pause_requested = False
        self.logger.info(f"수집 재개 요청: {self.name}")

    def reset_circuit_breaker(self):
        """서킷 브레이커 리셋"""
        self._circuit_breaker_open = False
        self._consecutive_failures = 0
        self.logger.info(f"서킷 브레이커 리셋: {self.name}")

    @abstractmethod
    async def _collect_data(self) -> List[Any]:
        """
        실제 데이터 수집 구현
        각 수집기에서 구현해야 함
        """

    def _should_cancel(self) -> bool:
        """취소 요청 확인"""
        return self._cancel_requested

    def _should_pause(self) -> bool:
        """일시 정지 요청 확인"""
        return self._pause_requested

    def _check_circuit_breaker(self) -> bool:
        """서킷 브레이커 상태 확인"""
        if self._consecutive_failures >= self.config.circuit_breaker_threshold:
            self._circuit_breaker_open = True
            return False
        return True

    async def _apply_rate_limit(self):
        """비율 제한 적용"""
        if self.config.is_rate_limited():
            current_time = time.time()
            time_since_last_call = current_time - self._rate_limiter_last_call
            min_interval = 1.0 / self.config.rate_limit

            if time_since_last_call < min_interval:
                sleep_time = min_interval - time_since_last_call
                await asyncio.sleep(sleep_time)

            self._rate_limiter_last_call = time.time()

    async def _wait_for_resume(self):
        """일시 정지 상태에서 대기"""
        while self._should_pause() and not self._should_cancel():
            self.logger.debug(f"수집기 일시 정지 중: {self.name}")
            await asyncio.sleep(1)

    async def collect(self) -> CollectionResult:
        """
        수집 실행 (공통 로직)
        """
        # 사전 검사
        if not self.config.enabled:
            self.logger.info(f"수집기 비활성화됨: {self.name}")
            return CollectionResult(
                source_name=self.name,
                status=CollectionStatus.CANCELLED,
                error_message="수집기가 비활성화되어 있습니다.",
            )

        if self._is_running:
            self.logger.warning(f"수집기 이미 실행 중: {self.name}")
            return CollectionResult(
                source_name=self.name,
                status=CollectionStatus.FAILED,
                error_message="수집기가 이미 실행 중입니다.",
            )

        if not self._check_circuit_breaker():
            self.logger.warning(f"서킷 브레이커 열림: {self.name}")
            return CollectionResult(
                source_name=self.name,
                status=CollectionStatus.FAILED,
                error_message="서킷 브레이커가 열렸습니다.",
            )

        self._is_running = True
        self._cancel_requested = False
        self._total_executions += 1

        # 수집 결과 초기화
        self._current_result = CollectionResult(
            source_name=self.name,
            status=CollectionStatus.RUNNING,
            start_time=datetime.now(),
        )

        retries = 0
        collected_data = []

        while retries <= self.config.max_retries:
            try:
                self.logger.info(
                    f"수집 시작: {self.name} (시도 {retries + 1}/{self.config.max_retries + 1})"
                )

                # 레이트 리미팅 적용
                await self._apply_rate_limit()

                # 일시 정지 상태 확인
                await self._wait_for_resume()

                # 취소 요청 확인
                if self._should_cancel():
                    self._current_result.status = CollectionStatus.CANCELLED
                    self._current_result.error_message = "사용자에 의해 취소됨"
                    break

                # 타임아웃 설정
                collected_data = await asyncio.wait_for(
                    self._collect_data(), timeout=self.config.timeout
                )

                # 수집 성공
                self._current_result.status = CollectionStatus.COMPLETED
                self._current_result.collected_count = len(collected_data)
                self._current_result.data = collected_data
                self._current_result.end_time = datetime.now()

                # 성공 통계 업데이트
                self._successful_executions += 1
                self._consecutive_failures = 0
                self._last_execution_time = datetime.now()

                self.logger.info(
                    f"수집 완료: {self.name} - {len(collected_data)}개 수집"
                )
                break

            except asyncio.TimeoutError:
                # 취소 요청 확인을 타임아웃보다 우선
                if self._should_cancel():
                    self._current_result.status = CollectionStatus.CANCELLED
                    self._current_result.error_message = "사용자에 의해 취소됨"
                    break

                error_msg = f"수집 타임아웃: {self.name} ({self.config.timeout}초)"
                self.logger.error(error_msg)
                self._current_result.add_error(error_msg)

                retries += 1
                if retries <= self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay)

            except Exception as e:
                error_msg = f"수집 오류: {self.name} - {str(e)}"
                self.logger.error(error_msg)
                self.logger.error(traceback.format_exc())

                self._current_result.add_error(error_msg)

                retries += 1
                if retries <= self.config.max_retries:
                    await asyncio.sleep(
                        self.config.retry_delay * (2 ** (retries - 1))
                    )  # 지수 백오프

        # 실패 처리
        if self._current_result.status not in [
            CollectionStatus.COMPLETED,
            CollectionStatus.CANCELLED,
        ]:
            self._current_result.status = CollectionStatus.FAILED
            self._failed_executions += 1
            self._consecutive_failures += 1

        self._is_running = False
        self._current_result.end_time = datetime.now()

        return self._current_result

    def health_check(self) -> Dict[str, Any]:
        """수집기 상태 점검"""
        return {
            "name": self.name,
            "type": self.source_type,
            "enabled": self.config.enabled,
            "is_running": self.is_running,
            "is_healthy": self.is_healthy,
            "circuit_breaker_open": self._circuit_breaker_open,
            "consecutive_failures": self._consecutive_failures,
            "total_executions": self._total_executions,
            "successful_executions": self._successful_executions,
            "failed_executions": self._failed_executions,
            "success_rate": (
                (self._successful_executions / self._total_executions * 100)
                if self._total_executions > 0
                else 0.0
            ),
            "last_execution_time": (
                self._last_execution_time.isoformat()
                if self._last_execution_time
                else None
            ),
            "last_result": (
                self._current_result.to_dict() if self._current_result else None
            ),
        }

    def reset_statistics(self):
        """통계 정보 리셋"""
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._consecutive_failures = 0
        self._last_execution_time = None
        self.logger.info(f"통계 정보 리셋: {self.name}")

    def update_config(self, config: CollectionConfig):
        """수집 설정 업데이트"""
        self.config = config
        self.logger.info(f"수집 설정 업데이트: {self.name}")


if __name__ == "__main__":
    import sys

    # 실제 데이터로 검증
    all_validation_failures = []
    total_tests = 0

    # 테스트용 구체 수집기 구현
    class TestCollector(BaseCollector):
        @property
        def source_type(self) -> str:
            return "test"

        async def _collect_data(self) -> List[Any]:
            # 간단한 테스트 데이터 반환
            await asyncio.sleep(0.1)
            return ["item1", "item2", "item3"]

    # 테스트 1: 기본 수집기 초기화
    total_tests += 1
    try:
        config = CollectionConfig(enabled=True, timeout=5)
        collector = TestCollector("test_collector", config)

        if collector.name != "test_collector":
            all_validation_failures.append(
                f"수집기 이름: 예상 'test_collector', 실제 '{collector.name}'"
            )

        if collector.source_type != "test":
            all_validation_failures.append(
                f"소스 타입: 예상 'test', 실제 '{collector.source_type}'"
            )

    except Exception as e:
        all_validation_failures.append(f"기본 수집기 초기화 오류: {e}")

    # 테스트 2: 비동기 수집 실행
    total_tests += 1
    try:

        async def test_collection():
            result = await collector.collect()
            return result

        # 비동기 함수 실행
        result = asyncio.run(test_collection())

        if result.status != CollectionStatus.COMPLETED:
            all_validation_failures.append(
                f"수집 상태: 예상 COMPLETED, 실제 {result.status}"
            )

        if result.collected_count != 3:
            all_validation_failures.append(
                f"수집 개수: 예상 3, 실제 {result.collected_count}"
            )

    except Exception as e:
        all_validation_failures.append(f"비동기 수집 오류: {e}")

    # 테스트 3: 상태 검사
    total_tests += 1
    try:
        if collector.is_running:
            all_validation_failures.append(
                "상태 검사: 수집 완료 후에도 is_running=True"
            )

        if not collector.is_healthy:
            all_validation_failures.append(
                "상태 검사: 정상 수집 후에도 is_healthy=False"
            )

    except Exception as e:
        all_validation_failures.append(f"상태 검사 오류: {e}")

    # 테스트 4: 헬스 체크
    total_tests += 1
    try:
        health = collector.health_check()

        required_fields = ["name", "type", "enabled", "is_running", "is_healthy"]
        for field in required_fields:
            if field not in health:
                all_validation_failures.append(f"헬스 체크: {field} 필드 누락")

    except Exception as e:
        all_validation_failures.append(f"헬스 체크 오류: {e}")

    # 테스트 5: 취소 기능
    total_tests += 1
    try:
        collector.cancel()

        if not collector._should_cancel():
            all_validation_failures.append(
                "취소 기능: cancel() 호출 후에도 _should_cancel()=False"
            )

    except Exception as e:
        all_validation_failures.append(f"취소 기능 오류: {e}")

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
        print("BaseCollector module is validated and ready for use")
        sys.exit(0)
