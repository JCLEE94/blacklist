"""
Collection system integration tests

Tests REGTECH collection, error handling, and collection workflows.
"""
import pytest
from unittest.mock import patch
from datetime import datetime

from src.core.unified_service import UnifiedBlacklistService
from .fixtures import IntegrationTestFixtures


class TestCollectionIntegration(IntegrationTestFixtures):
    """Test collection system integration"""

    @pytest.fixture
    def service(self, mock_container):
        """Create service instance with mock container"""
        with patch(
            "src.core.services.unified_service_core.get_container", return_value=mock_container
        ):
            service = UnifiedBlacklistService()
            service.container = mock_container
            service.blacklist_manager = mock_container.get("blacklist_manager")
            service.cache = mock_container.get("cache_manager")
            service.collection_manager = mock_container.get("collection_manager")
            service.regtech_collector = mock_container.get("regtech_collector")
            return service

    def test_get_collection_status_integration(self, service):
        """Test collection status retrieves data from multiple sources"""
        status = service.get_collection_status()

        assert status["enabled"] is True
        assert "sources" in status
        assert status["sources"]["regtech"]["enabled"] is True

        # Verify manager was called
        service.collection_manager.get_status.assert_called_once()

    def test_trigger_regtech_collection_full_flow(self, service):
        """Test complete REGTECH collection flow"""
        # Mock successful collection
        service.regtech_collector.collect_from_web.return_value = [
            {
                "ip": "10.0.0.1",
                "source": "regtech",
                "detection_date": datetime.now(),
                "reason": "Threat detected",
            },
            {
                "ip": "10.0.0.2",
                "source": "regtech",
                "detection_date": datetime.now(),
                "reason": "Malicious",
            },
        ]

        # Trigger collection
        result = service.trigger_regtech_collection(
            start_date="20250601", end_date="20250630"
        )

        # Verify success
        assert result["success"] is True
        assert result["collected"] == 2
        assert "Collection completed" in result["message"]

        # Verify collector was called with dates
        service.regtech_collector.collect_from_web.assert_called_with(
            start_date="20250601", end_date="20250630"
        )

        # Verify IPs were added to blacklist
        assert service.blacklist_manager.add_ip.call_count == 2

        # Verify cache was cleared
        service.cache.delete.assert_called()

    def test_trigger_regtech_collection_with_errors(self, service):
        """Test REGTECH collection error handling"""
        # Mock collection failure
        service.regtech_collector.collect_from_web.side_effect = Exception(
            "Network error"
        )

        result = service.trigger_regtech_collection()

        assert result["success"] is False
        assert "error" in result
        assert "Network error" in result["error"]

    def test_trigger_regtech_collection_partial_success(self, service):
        """Test handling of partial collection success"""
        # Mock some IPs failing to add
        service.blacklist_manager.add_ip.side_effect = [True, False, True]
        service.regtech_collector.collect_from_web.return_value = [
            {"ip": "1.1.1.1", "source": "regtech", "detection_date": datetime.now()},
            {"ip": "2.2.2.2", "source": "regtech", "detection_date": datetime.now()},
            {"ip": "3.3.3.3", "source": "regtech", "detection_date": datetime.now()},
        ]

        result = service.trigger_regtech_collection()

        # Should still report success but with correct count
        assert result["success"] is True
        assert result["collected"] == 2  # Only 2 succeeded

    def test_collection_logging_integration(self, service):
        """Test collection events are properly logged"""
        # Track log entries
        service.collection_logs = []

        # Trigger collection
        service.trigger_regtech_collection()

        # Verify logs were created
        assert len(service.collection_logs) > 0

        # Check log structure
        log = service.collection_logs[0]
        assert "timestamp" in log
        assert "source" in log
        assert log["source"] == "regtech"
        assert "action" in log
        assert "details" in log

    def test_error_logging_integration(self, service):
        """Test errors are properly logged"""
        service.collection_logs = []

        # Cause an error
        service.regtech_collector.collect_from_web.side_effect = Exception("Test error")

        result = service.trigger_regtech_collection()

        # Should have error log
        assert len(service.collection_logs) > 0
        error_logs = [
            log for log in service.collection_logs if "error" in log.get("details", {})
        ]
        assert len(error_logs) > 0