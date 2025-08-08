"""
Error recovery and resilience tests

Tests service behavior under various failure conditions.
"""
from unittest.mock import Mock, patch

import pytest

from src.core.unified_service import UnifiedBlacklistService

from .fixtures import IntegrationTestFixtures


class TestServiceErrorRecovery(IntegrationTestFixtures):
    """Test service error recovery and resilience"""

    @pytest.fixture
    def failing_service(self, mock_container):
        """Create service with components that fail intermittently"""
        # Make components fail on first call, succeed on retry
        call_counts = {"blacklist": 0, "cache": 0}

        def blacklist_get_all(*args, **kwargs):
            call_counts["blacklist"] += 1
            if call_counts["blacklist"] == 1:
                raise Exception("Temporary DB error")
            return []

        def cache_get(*args, **kwargs):
            call_counts["cache"] += 1
            if call_counts["cache"] == 1:
                raise Exception("Temporary cache error")
            return None

        mock_container.get(
            "blacklist_manager"
        ).get_all_ips.side_effect = blacklist_get_all
        mock_container.get("cache_manager").get.side_effect = cache_get

        with patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            return UnifiedBlacklistService()

    def test_service_recovers_from_transient_errors(self, failing_service):
        """Test service recovers from transient errors"""
        # First call might fail
        health1 = failing_service.get_system_health()

        # Second call should succeed
        health2 = failing_service.get_system_health()

        # At least one should be successful
        assert health1["status"] == "healthy" or health2["status"] == "healthy"

    def test_service_degrades_gracefully(self, mock_container):
        """Test service degrades gracefully when components fail"""
        # Make all components fail
        mock_container.get("blacklist_manager").get_all_ips.side_effect = Exception(
            "DB down"
        )
        mock_container.get("cache_manager").get.side_effect = Exception("Cache down")
        mock_container.get("collection_manager").get_status.side_effect = Exception(
            "Collection down"
        )

        with patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            service = UnifiedBlacklistService()

            # Service should still respond
            health = service.get_system_health()

            assert health["status"] == "degraded"
            assert health["total_ips"] == 0
            assert len(health.get("issues", [])) > 0
