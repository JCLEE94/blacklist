"""
Core service integration tests

Tests basic service initialization, health checks, and core functionality.
"""

from unittest.mock import Mock, patch

import pytest

from src.core.unified_service import UnifiedBlacklistService

from .fixtures import IntegrationTestFixtures


class TestServiceCore(IntegrationTestFixtures):
    """Test core service functionality"""

    @pytest.fixture
    def service(self, mock_container):
        """Create service instance with mock container"""
        with patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            service = UnifiedBlacklistService()
            service.container = mock_container
            service.blacklist_manager = mock_container.get("blacklist_manager")
            service.cache = mock_container.get("cache_manager")
            service.collection_manager = mock_container.get("collection_manager")
            service.regtech_collector = mock_container.get("regtech_collector")
            return service

    def test_service_initialization(self, mock_container):
        """Test service initializes with all dependencies"""
        with patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            service = UnifiedBlacklistService()

            # Verify all components initialized
            assert service.container is not None
            assert service.blacklist_manager is not None
            assert service.cache is not None
            assert service.collection_manager is not None

    def test_service_handles_missing_dependencies(self):
        """Test service handles missing dependencies gracefully"""
        mock_container = Mock()
        mock_container.get.return_value = None

        with patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            service = UnifiedBlacklistService()

            # Should still initialize but with None values
            assert service.container is not None

    def test_system_health_aggregates_all_components(self, service):
        """Test system health check aggregates data from all components"""
        # Mock various component states
        service.blacklist_manager.get_all_ips.return_value = [
            {"ip": "1.2.0.1", "is_active": True},
            {"ip": "2.2.2.2", "is_active": True},
            {"ip": "3.3.3.3", "is_active": False},
        ]

        health = service.get_system_health()

        assert health["total_ips"] == 3
        assert health["active_ips"] == 2
        assert health["status"] == "healthy"
        assert "database" in health
        assert "cache" in health
        assert "collection" in health

    def test_system_health_reports_unhealthy_state(self, service):
        """Test system health reports issues correctly"""
        # Make database fail
        service.blacklist_manager.get_all_ips.side_effect = Exception("DB Error")

        health = service.get_system_health()

        assert health["status"] == "degraded"
        assert health["total_ips"] == 0
        assert "issues" in health
        assert any("database" in issue for issue in health["issues"])
