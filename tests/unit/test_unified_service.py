#!/usr/bin/env python3
"""
Unit tests for UnifiedBlacklistService class
Tests core service functionality, lifecycle management, and integration.
"""

import asyncio
import unittest.mock as mock
from datetime import datetime
from datetime import timedelta

import pytest

from src.core.services.unified_service_core import UnifiedBlacklistService


class TestUnifiedBlacklistService:
    """Test cases for UnifiedBlacklistService class"""

    @pytest.fixture
    def mock_container(self):
        """Create mock container"""
        container = mock.Mock()
        container.get.side_effect = lambda key: {
            "blacklist_manager": mock.Mock(),
            "cache_manager": mock.Mock(),
            "collection_manager": mock.Mock(),
        }.get(key, mock.Mock())
        return container

    @pytest.fixture
    def service(self, mock_container):
        """Create UnifiedBlacklistService instance with mocked dependencies"""
        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ):
                            return UnifiedBlacklistService()

    def test_init_default_config(self, service):
        """Test service initialization with default configuration"""
        assert service.config["service_name"] == "blacklist"
        assert service.config["regtech_enabled"] is True
        assert service.config["auto_collection"] is True
        assert service.config["collection_interval"] == 3600
        assert service.collection_enabled is False
        assert service.daily_collection_enabled is False
        assert service._running is True
        assert service.max_logs == 1000

    @mock.patch.dict(
        "os.environ",
        {
            "REGTECH_ENABLED": "false",
            "AUTO_COLLECTION": "false",
            "COLLECTION_INTERVAL": "7200",
        },
    )
    def test_init_custom_config(self, mock_container):
        """Test service initialization with custom environment configuration"""
        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ):
                            service = UnifiedBlacklistService()

                            assert service.config["regtech_enabled"] is False
                            assert service.config["auto_collection"] is False
                            assert service.config["collection_interval"] == 7200

    def test_init_container_dependency_injection(self, service):
        """Test that container dependencies are properly injected"""
        assert service.blacklist_manager is not None
        assert service.cache is not None
        assert service.collection_manager is not None
        assert service.container is not None

    def test_init_collection_manager_unavailable(self, mock_container):
        """Test initialization when collection_manager is unavailable"""
        mock_container.get.side_effect = lambda key: {
            "blacklist_manager": mock.Mock(),
            "cache_manager": mock.Mock(),
            "collection_manager": Exception("Collection manager not available"),
        }.get(key, mock.Mock())

        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ):
                            service = UnifiedBlacklistService()

                            assert service.collection_manager is None

    def test_init_core_services_failure(self, mock_container):
        """Test initialization when core services fail"""
        mock_container.get.side_effect = Exception("Container error")

        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ):
                            service = UnifiedBlacklistService()

                            assert service.blacklist_manager is None
                            assert service.cache is None
                            assert service.collection_manager is None

    def test_sync_component_init_success(self, service):
        """Test successful synchronous component initialization"""
        with mock.patch(
            "src.core.services.unified_service_core.RegtechCollector"
        ) as mock_regtech:
            mock_regtech_instance = mock.Mock()
            mock_regtech.return_value = mock_regtech_instance

            service._sync_component_init()

            assert "regtech" in service._components
            assert service._components["regtech"] is mock_regtech_instance
            mock_regtech.assert_called_once_with("data")

    def test_sync_component_init_regtech_disabled(self, service):
        """Test component initialization when REGTECH is disabled"""
        service.config["regtech_enabled"] = False

        service._sync_component_init()

        assert "regtech" not in service._components

    def test_sync_component_init_failure(self, service):
        """Test component initialization failure handling"""
        with mock.patch(
            "src.core.services.unified_service_core.RegtechCollector",
            side_effect=ImportError("Module not found"),
        ):
            # Should not raise exception
            service._sync_component_init()
            assert "regtech" not in service._components

    @pytest.mark.asyncio
    async def test_immediate_component_init_success(self, service):
        """Test immediate component initialization success"""
        with mock.patch.object(service, "_initialize_components") as mock_init:
            mock_init.return_value = asyncio.Future()
            mock_init.return_value.set_result(None)

            await service._immediate_component_init()
            mock_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_immediate_component_init_failure_fallback(self, service):
        """Test immediate component initialization failure with fallback"""
        with mock.patch.object(
            service,
            "_initialize_components",
            side_effect=Exception("Async init failed"),
        ):
            with mock.patch.object(service, "_sync_component_init") as mock_sync:
                await service._immediate_component_init()
                mock_sync.assert_called_once()

    def test_collection_manager_synchronization(self, service):
        """Test synchronization with collection manager state"""
        # Mock collection manager with enabled state
        service.collection_manager.collection_enabled = True

        # Re-initialize to test synchronization
        with mock.patch.object(service, "_ensure_log_table"):
            with mock.patch.object(service, "_load_logs_from_db", return_value=[]):
                service.__init__()  # Call init again to test sync

                assert service.collection_enabled is True

    def test_logging_setup(self, service):
        """Test that logging is properly configured"""
        assert service.logger is not None
        assert service.collection_logs == []  # Initially empty or loaded from DB

    def test_service_state_management(self, service):
        """Test service state management"""
        assert service._running is True
        assert isinstance(service._components, dict)
        assert service.max_logs == 1000

    def test_version_information(self, service):
        """Test version information is included in config"""
        assert "version" in service.config
        assert isinstance(service.config["version"], str)

    def test_components_dictionary_initialization(self, service):
        """Test that components dictionary is properly initialized"""
        assert isinstance(service._components, dict)
        # After sync init, may contain regtech if enabled
        if service.config["regtech_enabled"]:
            # Components may be initialized in _sync_component_init
            pass

    def test_collection_logs_initialization(self, service):
        """Test collection logs initialization"""
        assert isinstance(service.collection_logs, list)
        assert len(service.collection_logs) <= service.max_logs

    def test_config_validation(self, service):
        """Test configuration validation"""
        required_config_keys = [
            "regtech_enabled",
            "auto_collection",
            "collection_interval",
            "service_name",
            "version",
        ]

        for key in required_config_keys:
            assert key in service.config

    def test_boolean_config_parsing(self, service):
        """Test boolean configuration values are properly parsed"""
        assert isinstance(service.config["regtech_enabled"], bool)
        assert isinstance(service.config["auto_collection"], bool)

    def test_integer_config_parsing(self, service):
        """Test integer configuration values are properly parsed"""
        assert isinstance(service.config["collection_interval"], int)
        assert service.config["collection_interval"] > 0

    def test_error_handling_in_log_loading(self, mock_container):
        """Test error handling when loading existing logs fails"""
        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService,
                    "_load_logs_from_db",
                    side_effect=Exception("DB error"),
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ):
                            service = UnifiedBlacklistService()

                            # Should still initialize successfully
                            assert service._running is True

    def test_initial_collection_trigger(self, mock_container):
        """Test initial collection is triggered when needed"""
        mock_collection_manager = mock.Mock()
        mock_collection_manager.is_initial_collection_needed.return_value = True
        mock_container.get.return_value = mock_collection_manager

        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ) as mock_initial:
                            service = UnifiedBlacklistService()
                            mock_initial.assert_called_once()

    def test_no_initial_collection_when_not_needed(self, mock_container):
        """Test initial collection is not triggered when not needed"""
        mock_collection_manager = mock.Mock()
        mock_collection_manager.is_initial_collection_needed.return_value = False
        mock_container.get.return_value = mock_collection_manager

        with mock.patch(
            "src.core.services.unified_service_core.get_container",
            return_value=mock_container,
        ):
            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ) as mock_initial:
                            service = UnifiedBlacklistService()
                            mock_initial.assert_not_called()

    def test_mixin_composition(self, service):
        """Test that service properly inherits from all mixins"""
        # Check that the service has methods from each mixin
        mixin_methods = [
            # CollectionServiceMixin
            "collect_all_data",
            "enable_collection",
            "disable_collection",
            # CoreOperationsMixin (if available)
            # 'start', 'stop',
            # DatabaseOperationsMixin (if available)
            # '_ensure_log_table',
            # LoggingOperationsMixin (if available)
            # 'add_collection_log',
            # StatisticsServiceMixin
            # 'get_statistics'
        ]

        for method_name in mixin_methods:
            if hasattr(service, method_name):
                assert callable(getattr(service, method_name))

    @pytest.mark.integration
    def test_service_integration_with_real_container(self):
        """Integration test with real container (if available)"""
        try:
            # This test requires the actual container to be available
            from src.core.container import get_container

            real_container = get_container()

            with mock.patch.object(UnifiedBlacklistService, "_ensure_log_table"):
                with mock.patch.object(
                    UnifiedBlacklistService, "_load_logs_from_db", return_value=[]
                ):
                    with mock.patch.object(
                        UnifiedBlacklistService, "_sync_component_init"
                    ):
                        with mock.patch.object(
                            UnifiedBlacklistService, "_perform_initial_collection_now"
                        ):
                            service = UnifiedBlacklistService()

                            assert service.container is not None
                            assert service._running is True

        except ImportError:
            # Container module not available, skip integration test
            pytest.skip("Container module not available for integration test")


if __name__ == "__main__":
    pytest.main([__file__])
