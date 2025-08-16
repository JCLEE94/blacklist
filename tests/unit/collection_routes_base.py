#!/usr/bin/env python3
"""
Base test fixtures for collection route tests
Common fixtures and mock objects used across collection route test modules.
"""

import json
import unittest.mock as mock
from datetime import datetime

import pytest
from flask import Flask

from src.core.routes.collection_logs_routes import collection_logs_bp
from src.core.routes.collection_status_routes import collection_status_bp
from src.core.routes.collection_trigger_routes import collection_trigger_bp


class CollectionRoutesTestBase:
    """Base class for collection route tests with common fixtures"""

    @pytest.fixture
    def app(self):
        """Create Flask test application"""
        app = Flask(__name__)
        app.config["TESTING"] = True

        # Register blueprints
        app.register_blueprint(collection_status_bp)
        app.register_blueprint(collection_trigger_bp)
        app.register_blueprint(collection_logs_bp)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def mock_service(self):
        """Mock unified service"""
        service = mock.Mock()
        service.collection_enabled = True
        service.get_collection_status.return_value = {
            "collection_enabled": True,
            "sources": {
                "regtech": {"available": True},
                "secudium": {"available": False},
            },
            "last_updated": datetime.now().isoformat(),
        }
        service.get_daily_collection_stats.return_value = [
            {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "count": 10,
                "sources": {"regtech": 10},
            }
        ]
        service.get_system_health.return_value = {"total_ips": 100, "active_ips": 90}
        service.get_collection_logs.return_value = [
            {
                "timestamp": datetime.now().isoformat(),
                "source": "regtech",
                "action": "collection",
                "details": {"ips_collected": 10},
            }
        ]
        service.add_collection_log = mock.Mock()
        return service

    @pytest.fixture
    def mock_container(self, mock_service):
        """Mock container"""
        container = mock.Mock()
        collection_manager = mock.Mock()
        collection_manager.enable_collection.return_value = {
            "message": "Collection enabled",
            "cleared_data": False,
            "sources": {},
        }
        collection_manager.disable_collection.return_value = {
            "message": "Collection disabled",
            "enabled": False,
            "sources": {},
        }
        container.get.side_effect = lambda key: {
            "collection_manager": collection_manager,
            "progress_tracker": mock.Mock(),
        }.get(key, mock.Mock())
        
        return container

    def assert_json_response(self, response, expected_status=200):
        """Helper to assert JSON response structure"""
        assert response.status_code == expected_status
        assert response.content_type == "application/json"
        return json.loads(response.data)