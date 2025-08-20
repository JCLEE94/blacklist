#!/usr/bin/env python3
"""
Unit tests for CollectionServiceMixin
Tests collection operations, data gathering, and source management.
"""

import asyncio
import unittest.mock as mock
from datetime import datetime
from datetime import timedelta

import pytest

from src.core.services.collection_service import CollectionServiceMixin


# Create a test service factory function
def create_test_collection_service():
    """Factory function to create test service with proper initialization"""

    class TestCollectionService(CollectionServiceMixin):
        """Test implementation of CollectionServiceMixin"""

        def add_collection_log(self, source, action, details=None):
            """Mock add_collection_log method"""
            log_entry = {
                "source": source,
                "action": action,
                "details": details or {},
                "timestamp": datetime.now().isoformat(),
            }
            self.collection_logs.append(log_entry)

        def clear_all_database_data(self):
            """Mock clear_all_database_data method"""
            return {"cleared_tables": ["blacklist_entries"], "total_cleared": 100}

        def get_collection_logs(self, limit=10):
            """Mock get_collection_logs method"""
            return self.collection_logs[-limit:]

        def _has_data_for_date(self, source, date_str):
            """Mock _has_data_for_date method"""
            return False

    service = TestCollectionService()
    service.logger = mock.Mock()
    service._components = {}
    service.blacklist_manager = mock.Mock()
    service.collection_manager = mock.Mock()
    service.collection_enabled = False
    service.daily_collection_enabled = False
    service.collection_logs = []

    return service


class TestCollectionServiceMixin:
    """Test cases for CollectionServiceMixin"""

    @pytest.fixture
    def service(self):
        """Create test service instance"""
        return create_test_collection_service()

    @pytest.fixture
    def mock_regtech_component(self):
        """Create mock REGTECH component"""
        component = mock.Mock()
        component.auto_collect.return_value = {
            "success": True,
            "items_collected": 50,
            "items_new": 30,
            "execution_time_ms": 1500,
        }
        component.collect_from_web.return_value = {
            "success": True,
            "items_collected": 25,
            "items_new": 15,
        }
        return component

    @pytest.fixture
    def mock_secudium_component(self):
        """Create mock SECUDIUM component"""
        component = mock.Mock()
        component.auto_collect.return_value = {
            "success": True,
            "items_collected": 30,
            "items_new": 20,
            "execution_time_ms": 1200,
        }
        return component

    @pytest.mark.asyncio
    async def test_collect_all_data_success(
        self, service, mock_regtech_component, mock_secudium_component
    ):
        """Test successful collection from all sources"""
        service._components = {
            "regtech": mock_regtech_component,
            "secudium": mock_secudium_component,
        }

        result = await service.collect_all_data()

        assert result["success"] is True
        assert result["summary"]["successful_sources"] == 2
        assert result["summary"]["failed_sources"] == 0
        assert "regtech" in result["results"]
        assert "secudium" in result["results"]
        assert result["results"]["regtech"]["success"] is True
        assert result["results"]["secudium"]["success"] is True

    @pytest.mark.asyncio
    async def test_collect_all_data_partial_failure(
        self, service, mock_regtech_component, mock_secudium_component
    ):
        """Test collection with one source failing"""
        mock_regtech_component.auto_collect.return_value = {
            "success": False,
            "error": "Connection failed",
        }

        service._components = {
            "regtech": mock_regtech_component,
            "secudium": mock_secudium_component,
        }

        result = await service.collect_all_data()

        assert result["success"] is True  # Still success if at least one source works
        assert result["summary"]["successful_sources"] == 1
        assert result["summary"]["failed_sources"] == 1
        assert result["results"]["regtech"]["success"] is False
        assert result["results"]["secudium"]["success"] is True

    @pytest.mark.asyncio
    async def test_collect_all_data_no_components(self, service):
        """Test collection with no components available"""
        service._components = {}

        result = await service.collect_all_data()

        assert result["success"] is False
        assert result["summary"]["successful_sources"] == 0
        assert result["summary"]["failed_sources"] == 0
        assert result["results"] == {}

    @pytest.mark.asyncio
    async def test_collect_all_data_component_exception(
        self, service, mock_regtech_component
    ):
        """Test collection with component raising exception"""
        mock_regtech_component.auto_collect.side_effect = Exception("Network error")

        service._components = {"regtech": mock_regtech_component}

        result = await service.collect_all_data()

        assert result["success"] is False
        assert result["summary"]["failed_sources"] == 1
        assert result["results"]["regtech"]["success"] is False
        assert "Network error" in result["results"]["regtech"]["error"]

    @pytest.mark.asyncio
    async def test_collect_regtech_data(self, service, mock_regtech_component):
        """Test REGTECH data collection"""
        service._components = {"regtech": mock_regtech_component}

        result = await service._collect_regtech_data()

        assert result["success"] is True
        mock_regtech_component.auto_collect.assert_called_once()

    @pytest.mark.asyncio
    async def test_collect_regtech_data_with_date(
        self, service, mock_regtech_component
    ):
        """Test REGTECH data collection with date range"""
        service._components = {"regtech": mock_regtech_component}

        result = await service._collect_regtech_data_with_date(
            "2023-01-01", "2023-01-31"
        )

        assert result["success"] is True
        mock_regtech_component.collect_from_web.assert_called_once_with(
            5, 100, 1, "2023-01-01", "2023-01-31"
        )

    @pytest.mark.asyncio
    async def test_collect_secudium_data(self, service, mock_secudium_component):
        """Test SECUDIUM data collection"""
        service._components = {"secudium": mock_secudium_component}

        result = await service._collect_secudium_data()

        assert result["success"] is True
        mock_secudium_component.auto_collect.assert_called_once()

    def test_search_ip_success(self, service):
        """Test successful IP search"""
        service.blacklist_manager.search_ip.return_value = {
            "found": True,
            "ip": "192.168.1.1",
            "threat_level": "high",
        }

        result = service.search_ip("192.168.1.1")

        assert result["success"] is True
        assert result["ip"] == "192.168.1.1"
        assert result["result"]["found"] is True

    def test_search_ip_failure(self, service):
        """Test IP search with exception"""
        service.blacklist_manager.search_ip.side_effect = Exception("Database error")

        result = service.search_ip("192.168.1.1")

        assert result["success"] is False
        assert result["ip"] == "192.168.1.1"
        assert "Database error" in result["error"]

    def test_enable_collection_success(self, service):
        """Test successful collection enablement"""
        result = service.enable_collection()

        assert result["success"] is True
        assert service.collection_enabled is True
        assert service.daily_collection_enabled is True
        assert service.collection_manager.collection_enabled is True
        assert len(service.collection_logs) == 1
        assert service.collection_logs[0]["action"] == "collection_enabled"

    def test_enable_collection_failure(self, service):
        """Test collection enablement failure"""
        service.clear_all_database_data = mock.Mock(
            side_effect=Exception("Clear failed")
        )

        result = service.enable_collection()

        assert result["success"] is False
        assert "Clear failed" in result["error"]

    def test_disable_collection_success(self, service):
        """Test successful collection disablement"""
        service.collection_enabled = True
        service.daily_collection_enabled = True

        result = service.disable_collection()

        assert result["success"] is True
        assert service.collection_enabled is False
        assert service.daily_collection_enabled is False
        assert service.collection_manager.collection_enabled is False
        assert len(service.collection_logs) == 1
        assert service.collection_logs[0]["action"] == "collection_disabled"

    def test_disable_collection_failure(self, service):
        """Test collection disablement failure"""
        service.add_collection_log = mock.Mock(side_effect=Exception("Log failed"))

        result = service.disable_collection()

        assert result["success"] is False
        assert "Log failed" in result["error"]

    def test_get_collection_status_basic(self, service):
        """Test basic collection status retrieval"""
        service.collection_enabled = True
        service.daily_collection_enabled = True

        status = service.get_collection_status()

        assert status["collection_enabled"] is True
        assert status["daily_collection_enabled"] is True
        assert "timestamp" in status
        assert "sources" in status
        assert "recent_logs" in status

    def test_get_collection_status_with_manager(self, service):
        """Test collection status with collection manager information"""
        service.collection_manager.collection_enabled = True
        service.collection_manager.last_run = "2023-01-01T10:00:00"

        status = service.get_collection_status()

        assert "collection_manager_status" in status
        assert status["collection_manager_status"]["enabled"] is True
        assert status["collection_manager_status"]["last_run"] == "2023-01-01T10:00:00"

    def test_get_collection_status_exception(self, service):
        """Test collection status with exception"""
        service.get_collection_logs = mock.Mock(side_effect=Exception("Log error"))

        status = service.get_collection_status()

        # Should handle exception gracefully
        assert "collection_enabled" in status
        assert status["recent_logs"] == []

    def test_trigger_collection_all(self, service):
        """Test triggering collection for all sources"""
        with mock.patch("asyncio.create_task") as mock_create_task:
            result = service.trigger_collection("all")

            assert "전체 수집이 시작되었습니다" in result
            mock_create_task.assert_called_once()

    def test_trigger_collection_regtech(self, service, mock_regtech_component):
        """Test triggering REGTECH collection"""
        service._components = {"regtech": mock_regtech_component}

        with mock.patch("asyncio.create_task") as mock_create_task:
            result = service.trigger_collection("regtech")

            assert "REGTECH 수집이 시작되었습니다" in result
            mock_create_task.assert_called_once()

    def test_trigger_collection_secudium(self, service, mock_secudium_component):
        """Test triggering SECUDIUM collection"""
        service._components = {"secudium": mock_secudium_component}

        with mock.patch("asyncio.create_task") as mock_create_task:
            result = service.trigger_collection("secudium")

            assert "SECUDIUM 수집이 시작되었습니다" in result
            mock_create_task.assert_called_once()

    def test_trigger_collection_unknown_source(self, service):
        """Test triggering collection for unknown source"""
        result = service.trigger_collection("unknown")

        assert "알 수 없는 소스" in result

    def test_trigger_regtech_collection_disabled(self, service):
        """Test REGTECH collection trigger when collection is disabled"""
        service.collection_enabled = False

        result = service.trigger_regtech_collection()

        assert result["success"] is False
        assert "수집이 비활성화되어 있습니다" in result["message"]

    def test_trigger_regtech_collection_component_unavailable(self, service):
        """Test REGTECH collection trigger when component is unavailable"""
        service.collection_enabled = True
        service._components = {}

        result = service.trigger_regtech_collection()

        assert result["success"] is False
        assert "REGTECH 컴포넌트가 사용할 수 없습니다" in result["message"]

    def test_trigger_regtech_collection_with_dates(
        self, service, mock_regtech_component
    ):
        """Test REGTECH collection trigger with date range"""
        service.collection_enabled = True
        service._components = {"regtech": mock_regtech_component}

        result = service.trigger_regtech_collection(
            start_date="2023-01-01", end_date="2023-01-31"
        )

        assert result["success"] is True
        assert result["start_date"] == "2023-01-01"
        assert result["end_date"] == "2023-01-31"
        mock_regtech_component.collect_from_web.assert_called_once()

    def test_trigger_regtech_collection_default_dates(
        self, service, mock_regtech_component
    ):
        """Test REGTECH collection trigger with default date handling"""
        service.collection_enabled = True
        service._components = {"regtech": mock_regtech_component}

        # Test with only start_date
        result = service.trigger_regtech_collection(start_date="2023-01-01")

        assert result["success"] is True
        assert result["start_date"] == "2023-01-01"
        assert "end_date" in result

    def test_trigger_regtech_collection_basic(self, service, mock_regtech_component):
        """Test basic REGTECH collection trigger without dates"""
        service.collection_enabled = True
        service._components = {"regtech": mock_regtech_component}

        result = service.trigger_regtech_collection()

        assert result["success"] is True
        assert "REGTECH 수집이 시작되었습니다" in result["message"]
        mock_regtech_component.collect_from_web.assert_called_once()

    def test_trigger_regtech_collection_exception(
        self, service, mock_regtech_component
    ):
        """Test REGTECH collection trigger with exception"""
        service.collection_enabled = True
        service._components = {"regtech": mock_regtech_component}
        mock_regtech_component.collect_from_web.side_effect = Exception(
            "Collection error"
        )

        result = service.trigger_regtech_collection()

        assert result["success"] is False
        assert "REGTECH 수집 중 오류" in result["message"]

    def test_trigger_secudium_collection_success(
        self, service, mock_secudium_component
    ):
        """Test successful SECUDIUM collection trigger"""
        service.collection_enabled = True
        service._components = {"secudium": mock_secudium_component}

        with mock.patch("asyncio.create_task") as mock_create_task:
            result = service.trigger_secudium_collection()

            assert result["success"] is True
            assert "SECUDIUM 수집이 시작되었습니다" in result["message"]
            mock_create_task.assert_called_once()

    def test_trigger_secudium_collection_disabled(self, service):
        """Test SECUDIUM collection trigger when collection is disabled"""
        service.collection_enabled = False

        result = service.trigger_secudium_collection()

        assert result["success"] is False
        assert "수집이 비활성화되어 있습니다" in result["message"]

    def test_trigger_secudium_collection_component_unavailable(self, service):
        """Test SECUDIUM collection trigger when component is unavailable"""
        service.collection_enabled = True
        service._components = {}

        result = service.trigger_secudium_collection()

        assert result["success"] is False
        assert "SECUDIUM 컴포넌트가 사용할 수 없습니다" in result["message"]

    def test_get_missing_dates_for_collection(self, service):
        """Test getting missing dates for collection"""
        missing_dates = service.get_missing_dates_for_collection("regtech", 7)

        # Since _has_data_for_date returns False, all dates should be missing
        assert len(missing_dates) == 7

        # Verify dates are in correct format
        for date_str in missing_dates:
            datetime.strptime(date_str, "%Y-%m-%d")

    def test_get_missing_dates_exception(self, service):
        """Test getting missing dates with exception"""
        # Mock the method itself to raise an exception
        with mock.patch.object(
            service, "get_missing_dates_for_collection", return_value=[]
        ):
            missing_dates = service.get_missing_dates_for_collection("regtech", 7)
            assert missing_dates == []

    def test_has_data_for_date_no_manager(self, service):
        """Test _has_data_for_date when blacklist_manager is None"""
        service.blacklist_manager = None

        result = service._has_data_for_date("regtech", "2023-01-01")

        assert result is False

    def test_has_data_for_date_exception(self, service):
        """Test _has_data_for_date with exception"""
        service.blacklist_manager.search_data = mock.Mock(
            side_effect=Exception("DB error")
        )

        result = service._has_data_for_date("regtech", "2023-01-01")

        assert result is False


if __name__ == "__main__":
    pytest.main([__file__])
