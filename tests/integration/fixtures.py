"""
Shared test fixtures for integration tests
"""
import os
import sqlite3
import tempfile
from unittest.mock import Mock
from datetime import datetime

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

        # Initialize database schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_ip (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ip_address VARCHAR(45) NOT NULL,
                source VARCHAR(50) NOT NULL,
                detection_date TIMESTAMP,
                reason TEXT,
                threat_level VARCHAR(20),
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP
            )
        """
        )
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

        # Mock blacklist manager
        blacklist_manager = Mock()
        blacklist_manager.get_active_ips.return_value = (["1.1.1.1", "2.2.2.2"], 2)
        blacklist_manager.add_ip.return_value = True
        blacklist_manager.get_all_ips.return_value = [
            {
                "ip": "1.1.1.1",
                "source": "regtech",
                "detection_date": datetime.now().isoformat(),
                "is_active": True,
            }
        ]

        # Mock cache manager
        cache_manager = Mock()
        cache_manager.get.return_value = None
        cache_manager.set.return_value = True
        cache_manager.delete.return_value = True
        cache_manager.clear.return_value = True

        # Mock collection manager
        collection_manager = Mock()
        collection_manager.is_collection_enabled.return_value = True
        collection_manager.get_status.return_value = {
            "enabled": True,
            "sources": {"regtech": {"enabled": True}},
        }

        # Mock REGTECH collector
        regtech_collector = Mock()
        regtech_collector.collect_from_web.return_value = [
            {
                "ip": "3.3.3.3",
                "source": "regtech",
                "detection_date": datetime.now(),
                "reason": "Malicious activity",
            }
        ]

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