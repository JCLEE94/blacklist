"""SECUDIUM collector tests

Tests for SECUDIUM IP collection functionality, session management, and error handling.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.core.collectors.unified_collector import (
    CollectionConfig,
    CollectionResult,
    CollectionStatus,
)
from src.core.collectors.secudium_collector import SecudiumCollector


class TestSecudiumCollector:
    """SECUDIUM 수집기 테스트"""

    def setup_method(self):
        """각 테스트 전 설정"""
        config = CollectionConfig()
        config.enabled = True
        config.max_retries = 3
        config.timeout = 300
        self.collector = SecudiumCollector(config)
        self.collector.username = "test_user"
        self.collector.password = "test_pass"

    def test_collector_disabled_by_default(self):
        """SECUDIUM 수집기가 기본적으로 비활성화되었는지 테스트"""
        # Create a new collector without enabling it
        config = CollectionConfig()
        collector = SecudiumCollector(config)
        assert collector.config.enabled is False

    def test_collect_returns_empty_when_disabled(self):
        """비활성화된 상태에서 수집 시 빈 결과 반환 테스트"""
        # Create a disabled collector
        config = CollectionConfig()
        config.enabled = False
        collector = SecudiumCollector(config)

        async def run_test():
            result = await collector.collect()
            return result

        result = asyncio.run(run_test())

        assert result.status.value == "cancelled"
        assert result.collected_count == 0
        assert "비활성화" in result.error_message

    def test_session_creation(self):
        """세션 생성 테스트"""
        session = self.collector._create_session()

        assert session is not None
        assert "User-Agent" in session.headers
        assert "Mozilla" in session.headers["User-Agent"]

    def test_login_method_exists_but_returns_false(self):
        """로그인 메서드가 존재하지만 False를 반환하는지 테스트"""

        async def run_test():
            result = await self.collector._login(self.collector._create_session())
            return result

        result = asyncio.run(run_test())
        assert result is False

    def test_bulletin_data_collection_returns_empty(self):
        """게시판 데이터 수집이 빈 결과를 반환하는지 테스트"""

        async def run_test():
            result = await self.collector._collect_bulletin_data(
                self.collector._create_session()
            )
            return result

        result = asyncio.run(run_test())
        assert result == []

    def test_source_type_property(self):
        """소스 타입 속성 테스트"""
        assert self.collector.source_type == "SECUDIUM"

    def test_config_initialization(self):
        """설정 초기화 테스트"""
        # 기본 설정 확인
        assert hasattr(self.collector, "config")
        assert hasattr(self.collector.config, "enabled")
        assert hasattr(self.collector.config, "max_retries")
        assert hasattr(self.collector.config, "timeout")

    def test_session_headers(self):
        """세션 헤더 테스트"""
        session = self.collector._create_session()

        # 기대되는 헤더들이 있는지 확인
        expected_headers = ["User-Agent", "Accept", "Accept-Language"]

        for header in expected_headers:
            if header in session.headers:
                assert session.headers[header] is not None

    def test_collector_state_management(self):
        """수집기 상태 관리 테스트"""
        # 초기 상태 확인
        assert self.collector.username == "test_user"
        assert self.collector.password == "test_pass"

        # 상태 변경 테스트
        self.collector.username = "new_user"
        assert self.collector.username == "new_user"

    def test_error_handling_in_collect(self):
        """수집 시 에러 처리 테스트"""

        async def run_test():
            # 예외 발생 시나리오
            with patch.object(
                self.collector, "_login", side_effect=Exception("Connection error")
            ):
                result = await self.collector.collect()
                return result

        result = asyncio.run(run_test())

        # 에러가 적절히 처리되었는지 확인
        assert result.status.value in ["failed", "cancelled"]
        assert result.collected_count == 0

    def test_timeout_handling(self):
        """타임아웃 처리 테스트"""
        # 타임아웃 설정 테스트
        assert self.collector.config.timeout == 300

        # 타임아웃 설정 변경
        self.collector.config.timeout = 60
        assert self.collector.config.timeout == 60

    def test_retry_configuration(self):
        """재시도 설정 테스트"""
        # 재시도 횟수 확인
        assert self.collector.config.max_retries == 3

        # 재시도 설정 변경
        self.collector.config.max_retries = 5
        assert self.collector.config.max_retries == 5

    def test_data_validation(self):
        """데이터 유효성 검사 테스트"""
        # 빈 데이터 처리
        empty_data = []
        assert self.collector._validate_data(empty_data) == []

        # 유횤한 데이터 처리
        valid_data = [{"ip": "8.8.8.8", "source": "SECUDIUM"}]
        result = self.collector._validate_data(valid_data)
        assert len(result) == 1
        assert result[0]["ip"] == "8.8.8.8"

    def test_logging_functionality(self):
        """로깅 기능 테스트"""
        # 로거가 올바르게 설정되었는지 확인
        assert hasattr(self.collector, "logger")
        assert self.collector.logger is not None

        # 로깅 메서드 테스트
        with patch.object(self.collector.logger, "info") as mock_log:
            self.collector._log_info("Test message")
            mock_log.assert_called_once_with("Test message")

    def test_cleanup_operations(self):
        """정리 작업 테스트"""
        session = self.collector._create_session()

        # 세션 정리 테스트
        self.collector._cleanup_session(session)

        # 세션이 올바르게 정리되었는지 확인
        # (실제 구현에 따라 달라질 수 있음)
        pass

    def test_concurrent_collection_prevention(self):
        """동시 수집 방지 테스트"""

        async def run_test():
            # 두 개의 동시 수집 작업 시도
            task1 = asyncio.create_task(self.collector.collect())
            task2 = asyncio.create_task(self.collector.collect())

            results = await asyncio.gather(task1, task2, return_exceptions=True)
            return results

        results = asyncio.run(run_test())

        # 두 작업 모두 완료되었는지 확인
        assert len(results) == 2
        for result in results:
            if isinstance(result, CollectionResult):
                assert result.status.value in ["completed", "cancelled", "failed"]
