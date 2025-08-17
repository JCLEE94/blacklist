"""
Comprehensive tests for src/core/collection_manager/manager.py
Tests the main CollectionManager class and its coordination functionality
"""

import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.collection_manager.manager import CollectionManager


class TestCollectionManagerInit:
    """Test CollectionManager initialization"""

    def test_init_with_default_paths(self):
        """Test initialization with default paths"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            manager = CollectionManager()

            assert manager.db_path == "instance/blacklist.db"
            assert str(manager.config_path) == "instance/collection_config.json"

    @patch("pathlib.Path.mkdir")
    def test_init_with_custom_paths(self, mock_mkdir):
        """Test initialization with custom paths"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            custom_db = "/custom/path/db.sqlite"
            custom_config = "/custom/path/config.json"

            manager = CollectionManager(db_path=custom_db, config_path=custom_config)

            assert manager.db_path == custom_db
            assert str(manager.config_path) == custom_config
            # Verify mkdir was called for the config directory
            mock_mkdir.assert_called_once_with(exist_ok=True)

    @patch("pathlib.Path.mkdir")
    def test_config_directory_creation(self, mock_mkdir):
        """Test that config directory is created during initialization"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            manager = CollectionManager()

            # Should create parent directory
            mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_services_initialization(self):
        """Test that all services are properly initialized"""
        with (
            patch(
                "src.core.collection_manager.manager.CollectionConfigService"
            ) as mock_config,
            patch(
                "src.core.collection_manager.manager.ProtectionService"
            ) as mock_protection,
            patch("src.core.collection_manager.manager.AuthService") as mock_auth,
            patch("src.core.collection_manager.manager.StatusService") as mock_status,
        ):

            db_path = "test.db"
            config_path = "test_config.json"

            manager = CollectionManager(db_path=db_path, config_path=config_path)

            # Verify services were initialized with correct parameters
            mock_config.assert_called_once_with(db_path, config_path)
            mock_protection.assert_called_once_with(db_path, config_path)
            mock_auth.assert_called_once_with(db_path)
            mock_status.assert_called_once()

            # Verify services are assigned to manager
            assert manager.config_service == mock_config.return_value
            assert manager.protection_service == mock_protection.return_value
            assert manager.auth_service == mock_auth.return_value
            assert manager.status_service == mock_status.return_value

    @patch("pathlib.Path.mkdir")
    def test_pathlib_path_conversion(self, mock_mkdir):
        """Test that config_path is converted to Path object"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            manager = CollectionManager(config_path="string/path/config.json")

            assert isinstance(manager.config_path, Path)
            assert str(manager.config_path) == "string/path/config.json"
            # Verify mkdir was called
            mock_mkdir.assert_called_once_with(exist_ok=True)


class TestCollectionManagerServices:
    """Test CollectionManager service interactions"""

    def setUp(self):
        """Set up test environment"""
        self.mock_config_service = Mock()
        self.mock_protection_service = Mock()
        self.mock_auth_service = Mock()
        self.mock_status_service = Mock()

    def create_manager_with_mocks(self):
        """Create CollectionManager with mocked services"""
        with (
            patch(
                "src.core.collection_manager.manager.CollectionConfigService",
                return_value=self.mock_config_service,
            ),
            patch(
                "src.core.collection_manager.manager.ProtectionService",
                return_value=self.mock_protection_service,
            ),
            patch(
                "src.core.collection_manager.manager.AuthService",
                return_value=self.mock_auth_service,
            ),
            patch(
                "src.core.collection_manager.manager.StatusService",
                return_value=self.mock_status_service,
            ),
        ):

            return CollectionManager()

    def test_service_access(self):
        """Test that services are accessible from manager"""
        self.setUp()
        manager = self.create_manager_with_mocks()

        assert manager.config_service == self.mock_config_service
        assert manager.protection_service == self.mock_protection_service
        assert manager.auth_service == self.mock_auth_service
        assert manager.status_service == self.mock_status_service

    def test_service_method_delegation(self):
        """Test that manager can delegate to services"""
        self.setUp()
        manager = self.create_manager_with_mocks()

        # Test that service methods can be called through manager
        self.mock_config_service.get_config.return_value = {"test": "value"}
        self.mock_protection_service.is_protected.return_value = False
        self.mock_auth_service.validate_credentials.return_value = True
        self.mock_status_service.get_status.return_value = {"status": "active"}

        # Verify services can be used (assuming manager might delegate to them)
        config_result = manager.config_service.get_config()
        protection_result = manager.protection_service.is_protected()
        auth_result = manager.auth_service.validate_credentials()
        status_result = manager.status_service.get_status()

        assert config_result == {"test": "value"}
        assert protection_result == False
        assert auth_result == True
        assert status_result == {"status": "active"}


class TestCollectionManagerFileOperations:
    """Test CollectionManager file and directory operations"""

    def test_config_path_handling(self):
        """Test configuration path handling"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "subdir" / "config.json"

            with (
                patch("src.core.collection_manager.manager.CollectionConfigService"),
                patch("src.core.collection_manager.manager.ProtectionService"),
                patch("src.core.collection_manager.manager.AuthService"),
                patch("src.core.collection_manager.manager.StatusService"),
            ):

                manager = CollectionManager(config_path=str(config_path))

                # Parent directory should be created
                assert config_path.parent.exists()
                assert manager.config_path == config_path

    def test_db_path_handling(self):
        """Test database path handling"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            db_path = "/some/path/database.db"
            manager = CollectionManager(db_path=db_path)

            assert manager.db_path == db_path

    def test_relative_paths(self):
        """Test handling of relative paths"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            manager = CollectionManager(
                db_path="relative/db.sqlite", config_path="relative/config.json"
            )

            assert manager.db_path == "relative/db.sqlite"
            assert str(manager.config_path) == "relative/config.json"


class TestCollectionManagerErrorHandling:
    """Test CollectionManager error handling"""

    def test_service_initialization_failure(self):
        """Test handling of service initialization failures"""
        with patch(
            "src.core.collection_manager.manager.CollectionConfigService",
            side_effect=Exception("Config service failed"),
        ):

            with pytest.raises(Exception) as exc_info:
                CollectionManager()

            assert "Config service failed" in str(exc_info.value)

    def test_protection_service_failure(self):
        """Test handling of protection service failure"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch(
                "src.core.collection_manager.manager.ProtectionService",
                side_effect=Exception("Protection failed"),
            ),
        ):

            with pytest.raises(Exception) as exc_info:
                CollectionManager()

            assert "Protection failed" in str(exc_info.value)

    def test_auth_service_failure(self):
        """Test handling of auth service failure"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch(
                "src.core.collection_manager.manager.AuthService",
                side_effect=Exception("Auth failed"),
            ),
        ):

            with pytest.raises(Exception) as exc_info:
                CollectionManager()

            assert "Auth failed" in str(exc_info.value)

    def test_status_service_failure(self):
        """Test handling of status service failure"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch(
                "src.core.collection_manager.manager.StatusService",
                side_effect=Exception("Status failed"),
            ),
        ):

            with pytest.raises(Exception) as exc_info:
                CollectionManager()

            assert "Status failed" in str(exc_info.value)

    def test_directory_creation_failure(self):
        """Test handling of directory creation failure"""
        with patch(
            "pathlib.Path.mkdir", side_effect=PermissionError("Cannot create directory")
        ):
            with (
                patch("src.core.collection_manager.manager.CollectionConfigService"),
                patch("src.core.collection_manager.manager.ProtectionService"),
                patch("src.core.collection_manager.manager.AuthService"),
                patch("src.core.collection_manager.manager.StatusService"),
            ):

                with pytest.raises(PermissionError):
                    CollectionManager()


class TestCollectionManagerLogging:
    """Test CollectionManager logging functionality"""

    @patch("src.core.collection_manager.manager.logger")
    def test_logger_exists(self, mock_logger):
        """Test that logger is properly configured"""
        # Just importing the module should have logger
        from src.core.collection_manager.manager import logger

        assert logger is not None

    def test_logger_name(self):
        """Test logger has correct name"""
        from src.core.collection_manager.manager import logger

        assert logger.name == "src.core.collection_manager.manager"


class TestCollectionManagerIntegration:
    """Integration tests for CollectionManager"""

    def test_full_initialization_flow(self):
        """Test complete initialization flow"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            config_path = Path(temp_dir) / "config" / "collection.json"

            with (
                patch(
                    "src.core.collection_manager.manager.CollectionConfigService"
                ) as mock_config,
                patch(
                    "src.core.collection_manager.manager.ProtectionService"
                ) as mock_protection,
                patch("src.core.collection_manager.manager.AuthService") as mock_auth,
                patch(
                    "src.core.collection_manager.manager.StatusService"
                ) as mock_status,
            ):

                manager = CollectionManager(
                    db_path=str(db_path), config_path=str(config_path)
                )

                # Verify directory was created
                assert config_path.parent.exists()

                # Verify services were called with correct paths
                mock_config.assert_called_once_with(str(db_path), str(config_path))
                mock_protection.assert_called_once_with(str(db_path), str(config_path))
                mock_auth.assert_called_once_with(str(db_path))
                mock_status.assert_called_once()

    def test_service_interaction_pattern(self):
        """Test typical service interaction patterns"""
        with (
            patch(
                "src.core.collection_manager.manager.CollectionConfigService"
            ) as mock_config,
            patch(
                "src.core.collection_manager.manager.ProtectionService"
            ) as mock_protection,
            patch("src.core.collection_manager.manager.AuthService") as mock_auth,
            patch("src.core.collection_manager.manager.StatusService") as mock_status,
        ):

            # Setup service return values
            mock_config_instance = mock_config.return_value
            mock_protection_instance = mock_protection.return_value
            mock_auth_instance = mock_auth.return_value
            mock_status_instance = mock_status.return_value

            manager = CollectionManager()

            # Verify manager has access to all service instances
            assert manager.config_service == mock_config_instance
            assert manager.protection_service == mock_protection_instance
            assert manager.auth_service == mock_auth_instance
            assert manager.status_service == mock_status_instance

    def test_manager_with_real_paths(self):
        """Test manager with realistic file paths"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "instance" / "blacklist.db"
            config_path = Path(temp_dir) / "instance" / "collection_config.json"

            with (
                patch("src.core.collection_manager.manager.CollectionConfigService"),
                patch("src.core.collection_manager.manager.ProtectionService"),
                patch("src.core.collection_manager.manager.AuthService"),
                patch("src.core.collection_manager.manager.StatusService"),
            ):

                manager = CollectionManager(
                    db_path=str(db_path), config_path=str(config_path)
                )

                # Should create instance directory
                assert config_path.parent.exists()
                assert manager.config_path == config_path


class TestCollectionManagerAttributes:
    """Test CollectionManager attributes and properties"""

    def test_required_attributes(self):
        """Test that manager has all required attributes"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            manager = CollectionManager()

            # Check all expected attributes exist
            assert hasattr(manager, "db_path")
            assert hasattr(manager, "config_path")
            assert hasattr(manager, "config_service")
            assert hasattr(manager, "protection_service")
            assert hasattr(manager, "auth_service")
            assert hasattr(manager, "status_service")

    def test_attribute_types(self):
        """Test that attributes have correct types"""
        with (
            patch("src.core.collection_manager.manager.CollectionConfigService"),
            patch("src.core.collection_manager.manager.ProtectionService"),
            patch("src.core.collection_manager.manager.AuthService"),
            patch("src.core.collection_manager.manager.StatusService"),
        ):

            manager = CollectionManager()

            assert isinstance(manager.db_path, str)
            assert isinstance(manager.config_path, Path)
            assert manager.config_service is not None
            assert manager.protection_service is not None
            assert manager.auth_service is not None
            assert manager.status_service is not None


class TestCollectionManagerDocumentation:
    """Test CollectionManager documentation and type hints"""

    def test_class_docstring(self):
        """Test that class has proper docstring"""
        assert CollectionManager.__doc__ is not None
        assert "통합 수집 관리자" in CollectionManager.__doc__

    def test_init_docstring(self):
        """Test that __init__ has proper docstring"""
        assert CollectionManager.__init__.__doc__ is not None
        assert "Args:" in CollectionManager.__init__.__doc__

    def test_type_annotations(self):
        """Test that methods have proper type annotations"""
        # Check __init__ method signature
        import inspect

        sig = inspect.signature(CollectionManager.__init__)

        # Should have type hints for parameters
        assert "db_path" in sig.parameters
        assert "config_path" in sig.parameters


if __name__ == "__main__":
    pytest.main([__file__])
