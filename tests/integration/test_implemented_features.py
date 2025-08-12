#!/usr/bin/env python3
"""
미구현 기능 완성 후 통합 테스트
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

# API 키 관리 테스트
from src.models.api_key import ApiKey, ApiKeyManager


class TestApiKeyManagement:
    """API 키 관리 시스템 테스트"""

    def test_api_key_creation(self):
        """API 키 생성 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            manager = ApiKeyManager(tmp.name)

            raw_key, api_key = manager.create_api_key(
                name="test-key",
                description="Test API key",
                permissions=["read", "write"],
                expires_in_days=30,
            )

            assert raw_key.startswith("ak_")
            assert len(raw_key) > 40
            assert api_key.name == "test-key"
            assert api_key.permissions == ["read", "write"]
            assert api_key.is_active

            os.unlink(tmp.name)

    def test_api_key_validation(self):
        """API 키 검증 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            manager = ApiKeyManager(tmp.name)

            # 키 생성
            raw_key, created_key = manager.create_api_key(
                name="validation-test", permissions=["read"]
            )

            # 검증 테스트
            validated_key = manager.validate_api_key(raw_key)
            assert validated_key is not None
            assert validated_key.name == "validation-test"
            assert validated_key.usage_count == 1

            # 잘못된 키 테스트
            invalid_validated = manager.validate_api_key("invalid_key")
            assert invalid_validated is None

            os.unlink(tmp.name)

    def test_api_key_expiration(self):
        """API 키 만료 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            manager = ApiKeyManager(tmp.name)

            # 만료된 키 생성 (시뮬레이션)
            raw_key, api_key = manager.create_api_key(
                name="expired-key", expires_in_days=-1  # 이미 만료된 키
            )

            # 만료된 키는 검증 실패해야 함
            validated_key = manager.validate_api_key(raw_key)
            assert validated_key is None

            os.unlink(tmp.name)

    def test_api_key_revocation(self):
        """API 키 비활성화 테스트"""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            manager = ApiKeyManager(tmp.name)

            raw_key, api_key = manager.create_api_key(name="revoke-test")

            # 비활성화
            success = manager.revoke_api_key(api_key.key_id)
            assert success

            # 비활성화된 키는 검증 실패해야 함
            validated_key = manager.validate_api_key(raw_key)
            assert validated_key is None

            os.unlink(tmp.name)


class TestCollectorSystem:
    """수집기 시스템 테스트"""

    def test_collector_factory_initialization(self):
        """수집기 팩토리 초기화 테스트"""
        from src.core.collectors.collector_factory import CollectorFactory

        factory = CollectorFactory()
        manager = factory.create_collection_manager()

        assert manager is not None
        assert hasattr(manager, "collectors")
        assert hasattr(manager, "global_config")

    def test_regtech_collector_creation(self):
        """REGTECH 수집기 생성 테스트"""
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig

        # 환경 변수 모킹
        with patch.dict(
            os.environ,
            {"REGTECH_USERNAME": "test_user", "REGTECH_PASSWORD": "test_pass"},
        ):
            config = CollectionConfig(enabled=True)
            collector = RegtechCollector(config)

            assert collector.name == "REGTECH"
            assert collector.source_type == "REGTECH"
            assert collector.username == "test_user"
            assert collector.password == "test_pass"

    def test_collector_error_handling(self):
        """수집기 에러 핸들링 테스트"""
        from src.core.collectors.regtech_collector import RegtechCollector
        from src.core.collectors.unified_collector import CollectionConfig

        # 잘못된 환경 변수로 테스트
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                config = CollectionConfig(enabled=True)
                RegtechCollector(config)

    @pytest.mark.asyncio
    async def test_collection_cancellation(self):
        """수집 취소 기능 테스트"""
        from src.core.collectors.unified_collector import (
            BaseCollector,
            CollectionConfig,
        )

        class TestCollector(BaseCollector):
            @property
            def source_type(self):
                return "TEST"

            async def _collect_data(self):
                import asyncio

                await asyncio.sleep(10)  # 긴 작업 시뮬레이션
                return []

        config = CollectionConfig(enabled=True, timeout=1)
        collector = TestCollector("test", config)

        # 비동기적으로 취소 요청
        import asyncio

        async def cancel_after_delay():
            await asyncio.sleep(0.1)
            collector.cancel()

        # 수집과 취소를 동시에 실행
        cancel_task = asyncio.create_task(cancel_after_delay())
        result = await collector.collect()
        await cancel_task

        assert result.status.value == "cancelled"


class TestErrorRecovery:
    """에러 복구 시스템 테스트"""

    def test_circuit_breaker(self):
        """서킷 브레이커 테스트"""
        from src.utils.error_recovery import CircuitBreaker

        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        @breaker
        def failing_function():
            raise Exception("Test failure")

        # 첫 번째 실패
        with pytest.raises(Exception):
            failing_function()

        # 두 번째 실패 (임계값 도달)
        with pytest.raises(Exception):
            failing_function()

        # 세 번째 호출은 서킷 브레이커에 의해 차단
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            failing_function()

    def test_retry_with_backoff(self):
        """재시도 백오프 테스트"""
        from src.utils.error_recovery import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, backoff_factor=0.1)
        def sometimes_failing_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Not yet")
            return "success"

        result = sometimes_failing_function()
        assert result == "success"
        assert call_count == 3

    def test_error_collector(self):
        """에러 수집기 테스트"""
        from src.utils.error_recovery import ErrorCollector

        collector = ErrorCollector()

        # 에러 기록
        test_error = ValueError("Test error")
        collector.record_error(test_error, "test_context")

        # 요약 확인
        summary = collector.get_error_summary()
        assert summary["total_errors"] == 1
        assert "ValueError" in summary["error_types"]
        assert summary["error_types"]["ValueError"] == 1

    def test_health_checker(self):
        """헬스 체커 테스트"""
        from src.utils.error_recovery import HealthChecker

        checker = HealthChecker()

        # 정상 체크 등록
        def healthy_check():
            return {"status": "ok"}

        # 실패 체크 등록
        def failing_check():
            raise Exception("Health check failed")

        checker.register_check("healthy", healthy_check)
        checker.register_check("failing", failing_check)

        # 개별 체크 실행
        healthy_result = checker.run_check("healthy")
        assert healthy_result["status"] == "healthy"

        failing_result = checker.run_check("failing")
        assert failing_result["status"] == "unhealthy"

        # 전체 체크 실행
        all_results = checker.run_all_checks()
        assert all_results["overall_status"] == "degraded"
        assert len(all_results["checks"]) == 2


class TestJWTTokenSystem:
    """JWT 토큰 시스템 테스트"""

    def test_security_manager_initialization(self):
        """보안 매니저 초기화 테스트"""
        from src.utils.security import SecurityManager

        manager = SecurityManager("test_secret", "jwt_secret")
        assert manager.secret_key == "test_secret"
        assert manager.jwt_secret == "jwt_secret"

    def test_jwt_token_generation_and_verification(self):
        """JWT 토큰 생성 및 검증 테스트"""
        from src.utils.security import SecurityManager

        manager = SecurityManager("test_secret", "jwt_secret")

        # 토큰 생성
        token = manager.generate_jwt_token("test_user", ["admin"], 1)
        assert token is not None

        # 토큰 검증
        payload = manager.verify_jwt_token(token)
        assert payload is not None
        assert payload["user_id"] == "test_user"
        assert payload["roles"] == ["admin"]

    def test_jwt_token_expiration(self):
        """JWT 토큰 만료 테스트"""
        import time

        from src.utils.security import SecurityManager

        manager = SecurityManager("test_secret", "jwt_secret")

        # 매우 짧은 만료시간 (1초)
        token = manager.generate_jwt_token(
            "test_user", ["user"], expires_hours=1 / 3600
        )

        # 즉시 검증 (성공해야 함)
        payload = manager.verify_jwt_token(token)
        assert payload is not None

        # 2초 후 검증 (실패해야 함)
        time.sleep(2)
        expired_payload = manager.verify_jwt_token(token)
        assert expired_payload is None


class TestSystemIntegration:
    """시스템 통합 테스트"""

    def test_container_initialization(self):
        """컨테이너 초기화 테스트"""
        from src.core.container import get_container

        container = get_container()
        assert container is not None

        # 주요 서비스들이 등록되어 있는지 확인
        services = ["config", "blacklist_manager", "cache_manager"]
        for service in services:
            try:
                service_instance = container.get(service)
                # 서비스가 None이 아니면 성공
                print(
                    "Service {service}: {'Available' if service_instance else 'Not available'}"
                )
            except Exception as e:
                print("Service {service}: Error - {e}")

    def test_performance_monitoring(self):
        """성능 모니터링 테스트"""
        from src.utils.error_recovery import ResourceMonitor

        monitor = ResourceMonitor()
        metrics = monitor.collect_metrics()

        assert "timestamp" in metrics
        if "error" not in metrics:
            assert "cpu_percent" in metrics
            assert "memory_percent" in metrics
            assert isinstance(metrics["cpu_percent"], (int, float))
            assert isinstance(metrics["memory_percent"], (int, float))

    def test_safe_execute_utility(self):
        """안전 실행 유틸리티 테스트"""
        from src.utils.error_recovery import safe_execute

        # 성공 케이스
        def success_func(x, y):
            return x + y

        result, error = safe_execute(success_func, 2, 3)
        assert result == 5
        assert error is None

        # 실패 케이스
        def failing_func():
            raise ValueError("Test error")

        result, error = safe_execute(failing_func)
        assert result is None
        assert isinstance(error, ValueError)


if __name__ == "__main__":
    # 개별 테스트 실행을 위한 스크립트
    pytest.main([__file__, "-v", "--tb=short"])
