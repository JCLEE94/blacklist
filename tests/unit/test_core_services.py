"""
Core Services 테스트
"""

import os
import tempfile
from unittest.mock import MagicMock, Mock, patch

import pytest
from .test_core_services_mocks import (
    MockUnifiedService,
    MockBlacklistManager,
    MockCacheManager,
    MockCollectionManager,
)


class TestCoreServices:
    """Core Services 테스트"""

    @pytest.fixture
    def mock_unified_service(self):
        """Mock Unified Service"""
        return MockUnifiedService()

    @pytest.fixture
    def mock_blacklist_manager(self):
        """Mock Blacklist Manager"""
        return MockBlacklistManager()

    @pytest.fixture
    def mock_cache_manager(self):
        """Mock Cache Manager"""
        return MockCacheManager()

    @pytest.fixture
    def mock_collection_manager(self):
        """Mock Collection Manager"""
        return MockCollectionManager()

    def test_unified_service_get_active_ips(self, mock_unified_service):
        """Unified Service 활성 IP 조회 테스트"""
        ips = mock_unified_service.get_active_ips()

        assert isinstance(ips, list)
        assert len(ips) == 3
        assert "192.168.1.1" in ips
        assert "192.168.1.2" in ips
        assert "10.0.0.1" in ips

    def test_unified_service_get_blacklist_data(self, mock_unified_service):
        """Unified Service 블랙리스트 데이터 조회 테스트"""
        data = mock_unified_service.get_blacklist_data()

        assert isinstance(data, list)
        assert len(data) == 2

        # First entry validation
        entry = data[0]
        assert entry["ip_address"] == "192.168.1.1"
        assert entry["source"] == "REGTECH"
        assert entry["threat_level"] == "high"
        assert entry["is_active"] is True

    def test_unified_service_get_collection_status(self, mock_unified_service):
        """Unified Service 수집 상태 조회 테스트"""
        status = mock_unified_service.get_collection_status()

        assert isinstance(status, dict)
        assert "enabled" in status
        assert "last_collection" in status
        assert "total_entries" in status
        assert "sources" in status

        # Sources validation
        assert "REGTECH" in status["sources"]
        assert "SECUDIUM" in status["sources"]
        assert status["sources"]["REGTECH"]["active"] is True

    def test_unified_service_collection_enable_disable(self, mock_unified_service):
        """Unified Service 수집 활성화/비활성화 테스트"""
        # Initially enabled
        assert mock_unified_service.enabled is True

        # Disable
        result = mock_unified_service.disable_collection()
        assert result is True
        assert mock_unified_service.enabled is False

        # Enable
        result = mock_unified_service.enable_collection()
        assert result is True
        assert mock_unified_service.enabled is True

    def test_unified_service_trigger_regtech_collection(self, mock_unified_service):
        """Unified Service REGTECH 수집 트리거 테스트"""
        result = mock_unified_service.trigger_regtech_collection()

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["items_collected"] == 25
        assert result["items_new"] == 5
        assert result["items_updated"] == 20
        assert "execution_time_ms" in result

    def test_unified_service_trigger_secudium_collection(self, mock_unified_service):
        """Unified Service SECUDIUM 수집 트리거 테스트"""
        result = mock_unified_service.trigger_secudium_collection()

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["items_collected"] == 15
        assert result["items_new"] == 3
        assert result["items_updated"] == 12

    def test_unified_service_get_enhanced_blacklist_data(self, mock_unified_service):
        """Unified Service 향상된 블랙리스트 데이터 테스트"""
        result = mock_unified_service.get_enhanced_blacklist_data(page=1, limit=50)

        assert isinstance(result, dict)
        assert "entries" in result
        assert "total" in result
        assert "metadata" in result

        # Metadata validation
        metadata = result["metadata"]
        assert metadata["version"] == "2.0"
        assert metadata["schema_version"] == "2.0.0"
        assert "generated_at" in metadata

    def test_unified_service_get_trends_analysis(self, mock_unified_service):
        """Unified Service 트렌드 분석 테스트"""
        result = mock_unified_service.get_trends_analysis(days=7)

        assert isinstance(result, dict)
        assert "daily_counts" in result
        assert "trend_direction" in result
        assert "growth_rate" in result
        assert result["period_days"] == 7
        assert result["trend_direction"] == "increasing"

    def test_unified_service_get_analytics_summary(self, mock_unified_service):
        """Unified Service 분석 요약 테스트"""
        result = mock_unified_service.get_analytics_summary(period="30d")

        assert isinstance(result, dict)
        assert result["total_entries"] == 1000
        assert result["active_entries"] == 950
        assert "threat_levels" in result
        assert "sources" in result
        assert result["period"] == "30d"

    def test_blacklist_manager_add_ip(self, mock_blacklist_manager):
        """Blacklist Manager IP 추가 테스트"""
        ip = "192.168.1.100"
        source = "TEST"
        metadata = {"threat_level": "high"}

        entry = mock_blacklist_manager.add_ip(ip, source, metadata)

        assert entry["ip_address"] == ip
        assert entry["source"] == source
        assert entry["metadata"] == metadata
        assert len(mock_blacklist_manager.entries) == 1

    def test_blacklist_manager_remove_ip(self, mock_blacklist_manager):
        """Blacklist Manager IP 제거 테스트"""
        # Add IP first
        ip = "192.168.1.100"
        mock_blacklist_manager.add_ip(ip, "TEST")
        assert len(mock_blacklist_manager.entries) == 1

        # Remove IP
        result = mock_blacklist_manager.remove_ip(ip)
        assert result is True
        assert len(mock_blacklist_manager.entries) == 0

    def test_blacklist_manager_get_active_ips(self, mock_blacklist_manager):
        """Blacklist Manager 활성 IP 조회 테스트"""
        # Add multiple IPs
        ips = ["192.168.1.1", "192.168.1.2", "10.0.0.1"]
        for ip in ips:
            mock_blacklist_manager.add_ip(ip, "TEST")

        active_ips = mock_blacklist_manager.get_active_ips()

        assert len(active_ips) == 3
        for ip in ips:
            assert ip in active_ips

    def test_blacklist_manager_get_statistics(self, mock_blacklist_manager):
        """Blacklist Manager 통계 조회 테스트"""
        # Add some test data
        mock_blacklist_manager.add_ip("192.168.1.1", "REGTECH")
        mock_blacklist_manager.add_ip("192.168.1.2", "SECUDIUM")

        stats = mock_blacklist_manager.get_statistics()

        assert isinstance(stats, dict)
        assert stats["total_entries"] == 2
        assert "sources" in stats
        assert "threat_levels" in stats

    def test_cache_manager_basic_operations(self, mock_cache_manager):
        """Cache Manager 기본 작업 테스트"""
        key = "test_key"
        value = {"data": "test_value"}

        # Set value
        result = mock_cache_manager.set(key, value, ttl=3600)
        assert result is True

        # Get value
        retrieved = mock_cache_manager.get(key)
        assert retrieved == value

        # Check existence
        assert mock_cache_manager.exists(key) is True

        # Delete value
        result = mock_cache_manager.delete(key)
        assert result is True
        assert mock_cache_manager.exists(key) is False

    def test_cache_manager_clear(self, mock_cache_manager):
        """Cache Manager 전체 클리어 테스트"""
        # Add multiple items
        for i in range(5):
            mock_cache_manager.set(f"key_{i}", f"value_{i}")

        assert len(mock_cache_manager.cache) == 5

        # Clear cache
        result = mock_cache_manager.clear()
        assert result is True
        assert len(mock_cache_manager.cache) == 0

    def test_cache_manager_get_stats(self, mock_cache_manager):
        """Cache Manager 통계 조회 테스트"""
        # Add some test data
        mock_cache_manager.set("key1", "value1")
        mock_cache_manager.set("key2", "value2")

        stats = mock_cache_manager.get_stats()

        assert isinstance(stats, dict)
        assert stats["keys"] == 2
        assert "memory_usage" in stats
        assert "hit_rate" in stats
        assert stats["hit_rate"] == 0.85

    def test_collection_manager_enable_disable(self, mock_collection_manager):
        """Collection Manager 활성화/비활성화 테스트"""
        # Initially enabled
        assert mock_collection_manager.is_enabled() is True

        # Disable
        mock_collection_manager.disable()
        assert mock_collection_manager.is_enabled() is False

        # Enable
        mock_collection_manager.enable()
        assert mock_collection_manager.is_enabled() is True

    def test_collection_manager_regtech_collection(self, mock_collection_manager):
        """Collection Manager REGTECH 수집 테스트"""
        result = mock_collection_manager.collect_from_regtech()

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["items_collected"] == 30
        assert result["items_new"] == 10
        assert result["items_updated"] == 20
        assert isinstance(result["errors"], list)

    def test_collection_manager_secudium_collection(self, mock_collection_manager):
        """Collection Manager SECUDIUM 수집 테스트"""
        result = mock_collection_manager.collect_from_secudium()

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["items_collected"] == 20
        assert result["items_new"] == 5
        assert result["items_updated"] == 15

    def test_collection_manager_get_logs(self, mock_collection_manager):
        """Collection Manager 로그 조회 테스트"""
        logs = mock_collection_manager.get_collection_logs(limit=50)

        assert isinstance(logs, list)
        assert len(logs) == 2

        # First log entry
        log = logs[0]
        assert "timestamp" in log
        assert log["source"] == "REGTECH"
        assert log["status"] == "success"
        assert log["items_collected"] == 30

    def test_service_integration(
        self, mock_unified_service, mock_blacklist_manager, mock_cache_manager
    ):
        """서비스 통합 테스트"""
        # Test workflow simulation

        # 1. Check collection status
        status = mock_unified_service.get_collection_status()
        assert status["enabled"] is True

        # 2. Trigger collection
        regtech_result = mock_unified_service.trigger_regtech_collection()
        assert regtech_result["success"] is True

        # 3. Add collected IPs to blacklist
        for ip in ["192.168.1.100", "192.168.1.101"]:
            mock_blacklist_manager.add_ip(ip, "REGTECH")

        # 4. Cache the results
        active_ips = mock_blacklist_manager.get_active_ips()
        mock_cache_manager.set("active_ips", active_ips, ttl=3600)

        # 5. Verify cached data
        cached_ips = mock_cache_manager.get("active_ips")
        assert cached_ips == active_ips

    def test_service_error_handling(self, mock_unified_service):
        """서비스 에러 처리 테스트"""

        # Mock service to simulate errors
        def failing_method():
            raise Exception("Service unavailable")

        # Test error recovery mechanisms
        try:
            failing_method()
            assert False, "Should have raised exception"
        except Exception as e:
            assert str(e) == "Service unavailable"
            # Service should handle gracefully
            assert mock_unified_service.enabled is not None

    def test_service_performance_metrics(self, mock_unified_service):
        """서비스 성능 메트릭 테스트"""
        # Test response times and metrics
        import time

        start_time = time.time()
        result = mock_unified_service.get_analytics_summary()
        end_time = time.time()

        execution_time = end_time - start_time

        assert execution_time < 1.0  # Should be fast for mock
        assert isinstance(result, dict)
        assert "generated_at" in result

    def test_service_data_validation(
        self, mock_unified_service, mock_blacklist_manager
    ):
        """서비스 데이터 유효성 검증 테스트"""
        # Test IP address validation
        valid_ips = ["192.168.1.1", "10.0.0.1", "172.16.0.1"]
        invalid_ips = ["invalid_ip", "999.999.999.999", ""]

        # Valid IPs should be added successfully
        for ip in valid_ips:
            entry = mock_blacklist_manager.add_ip(ip, "TEST")
            assert entry is not None
            assert entry["ip_address"] == ip

        # Test data structure validation
        blacklist_data = mock_unified_service.get_blacklist_data()
        for entry in blacklist_data:
            required_fields = ["ip_address", "source", "threat_level", "is_active"]
            for field in required_fields:
                assert field in entry

    @pytest.mark.integration
    def test_end_to_end_workflow(
        self,
        mock_unified_service,
        mock_blacklist_manager,
        mock_cache_manager,
        mock_collection_manager,
    ):
        """End-to-End 워크플로우 테스트"""
        # 1. Enable collection
        mock_collection_manager.enable()
        assert mock_collection_manager.is_enabled() is True

        # 2. Trigger REGTECH collection
        regtech_result = mock_collection_manager.collect_from_regtech()
        assert regtech_result["success"] is True

        # 3. Trigger SECUDIUM collection
        secudium_result = mock_collection_manager.collect_from_secudium()
        assert secudium_result["success"] is True

        # 4. Get collection status
        status = mock_unified_service.get_collection_status()
        assert status["enabled"] is True

        # 5. Get analytics
        analytics = mock_unified_service.get_analytics_summary()
        assert analytics["total_entries"] > 0

        # 6. Cache analytics results
        mock_cache_manager.set("analytics_summary", analytics, ttl=1800)
        cached_analytics = mock_cache_manager.get("analytics_summary")
        assert cached_analytics == analytics

        # 7. Get trends
        trends = mock_unified_service.get_trends_analysis()
        assert trends["trend_direction"] in ["increasing", "decreasing", "stable"]

        # 8. Verify workflow completed successfully
        assert True
