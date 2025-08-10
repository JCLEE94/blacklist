"""
Shared test fixtures for integration tests
"""

import os
import sqlite3
import tempfile
from unittest.mock import Mock

import pytest

from src.core.container import BlacklistContainer


class IntegrationTestFixtures:
    """Shared fixtures for all integration tests"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database for testing"""
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        db_path = temp_file.name
        temp_file.close()

        # Initialize database schema using shared function
        from tests.conftest import _create_additional_test_tables

        conn = sqlite3.connect(db_path)
        _create_additional_test_tables(conn)
        conn.commit()
        conn.close()

        yield db_path

        # Cleanup
        try:
            os.unlink(db_path)
        except:
            pass

    @pytest.fixture
    def mock_container(self, temp_db):
        """Create mock container with test dependencies"""
        container = Mock(spec=BlacklistContainer)

        # Create simple mock services
        blacklist_manager = Mock()
        blacklist_manager.get_active_ips.return_value = (["192.168.1.1", "10.0.0.1"], 2)
        blacklist_manager.get_all_ips.return_value = ["192.168.1.1", "10.0.0.1"]
        blacklist_manager.get_ip_count.return_value = 2
        blacklist_manager.add_ip.return_value = True
        blacklist_manager.remove_ip.return_value = True

        cache_manager = Mock()
        cache_manager.get.return_value = None
        cache_manager.set.return_value = True
        cache_manager.delete.return_value = True

        collection_manager = Mock()
        collection_manager.collection_enabled = True
        collection_manager.is_collection_enabled.return_value = True
        collection_manager.enable_collection.return_value = {
            "success": True,
            "enabled": True,
        }
        collection_manager.disable_collection.return_value = {
            "success": True,
            "enabled": False,
        }
        collection_manager.get_status.return_value = {
            "enabled": True,
            "last_collection": "2024-01-01 00:00:00",
            "protection_active": True,
        }

        regtech_collector = Mock()
        regtech_collector.collect_data.return_value = {
            "success": True,
            "data": ["192.168.1.1", "192.168.1.2"],
            "count": 2,
            "collected": 2,
            "message": "Collection successful",
        }
        regtech_collector.collect_from_web.return_value = []
        regtech_collector.auto_collect.return_value = {
            "success": True,
            "collected": 2,
            "data": ["192.168.1.1", "192.168.1.2"],
            "message": "Mock REGTECH collection successful",
        }

        # Configure container to return mocks
        container.get.side_effect = lambda key: {
            "blacklist_manager": blacklist_manager,
            "cache_manager": cache_manager,
            "collection_manager": collection_manager,
            "regtech_collector": regtech_collector,
            "db_path": temp_db,
        }.get(key)

        # Mock resolve method to delegate to get method
        container.resolve = container.get

        return container
