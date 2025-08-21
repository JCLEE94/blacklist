#!/usr/bin/env python3
"""
Unit tests for web API routes

Tests core API endpoint functionality and response handling.
"""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest
from flask import Blueprint, Flask

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.web.api_routes import (api_bp, api_search, api_stats_simple,
                                get_daily_ips, get_month_details, get_stats,
                                refresh_data)


class TestApiBlueprint:
    """Test the API blueprint creation and structure"""

    def test_blueprint_creation(self):
        """Test that api_bp is properly created"""
        assert isinstance(api_bp, Blueprint)
        assert api_bp.name == "api"
        assert api_bp.url_prefix == "/api"

    def test_blueprint_routes_registered(self):
        """Test that all expected routes are registered"""
        # Get all registered routes for the blueprint
        routes = []
        for rule in api_bp.url_map.iter_rules():
            routes.append(rule.rule)

        # Should have routes registered (though URL map might be empty until app registration)
        assert api_bp.deferred_functions  # Should have deferred route registrations


class TestGetStats:
    """Test the get_stats function"""

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_stats_file_exists(self, mock_file, mock_exists):
        """Test get_stats when stats file exists"""
        mock_exists.return_value = True
        mock_stats_data = {
            "total_ips": 1000,
            "active_ips": 500,
            "sources": {"REGTECH": 600, "SECUDIUM": 400},
            "last_updated": "2024-01-01T12:00:00",
        }
        mock_file.return_value.read.return_value = json.dumps(mock_stats_data)

        with patch("json.load", return_value=mock_stats_data):
            result = get_stats()

            assert result == mock_stats_data
            assert result["total_ips"] == 1000
            assert result["active_ips"] == 500

    @patch("pathlib.Path.exists")
    def test_get_stats_file_not_exists(self, mock_exists):
        """Test get_stats when stats file doesn't exist"""
        mock_exists.return_value = False

        result = get_stats()

        assert result["total_ips"] == 0
        assert result["active_ips"] == 0
        assert result["sources"] == {}
        assert "last_updated" in result

    @patch("pathlib.Path.exists")
    @patch("builtins.open", side_effect=IOError("File read error"))
    def test_get_stats_file_read_error(self, mock_file, mock_exists):
        """Test get_stats when file read fails"""
        mock_exists.return_value = True

        result = get_stats()

        # Should return default stats on error
        assert result["total_ips"] == 0
        assert result["active_ips"] == 0
        assert result["sources"] == {}

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.load", side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
    def test_get_stats_json_decode_error(self, mock_json, mock_file, mock_exists):
        """Test get_stats when JSON parsing fails"""
        mock_exists.return_value = True

        result = get_stats()

        # Should return default stats on JSON error
        assert result["total_ips"] == 0
        assert result["active_ips"] == 0


class TestApiSearch:
    """Test the api_search endpoint"""

    def test_api_search_with_app(self):
        """Test api_search endpoint with Flask app context"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            # Test valid search
            response = client.post(
                "/api/search", json={"ip": "192.168.1.1", "type": "exact"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["results"]) > 0
            assert data["results"][0]["ip"] == "192.168.1.1"

    def test_api_search_localhost(self):
        """Test api_search with localhost IP"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post(
                "/api/search", json={"ip": "127.0.0.1", "type": "exact"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["results"]) > 0

    def test_api_search_no_results(self):
        """Test api_search with IP that returns no results"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post(
                "/api/search", json={"ip": "10.0.0.1", "type": "exact"}
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert len(data["results"]) == 0

    def test_api_search_missing_ip(self):
        """Test api_search without IP parameter"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post("/api/search", json={})

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False
            assert "required" in data["error"]

    def test_api_search_empty_ip(self):
        """Test api_search with empty IP"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post("/api/search", json={"ip": "   "})

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False

    def test_api_search_no_json(self):
        """Test api_search without JSON data"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post("/api/search")

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False

    def test_api_search_form_data(self):
        """Test api_search with form data instead of JSON"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            # When no JSON is provided, get_json() returns None
            response = client.post("/api/search", data={"ip": "192.168.1.1"})

            assert response.status_code == 400
            data = response.get_json()
            assert data["success"] is False


class TestRefreshData:
    """Test the refresh_data endpoint"""

    def test_refresh_data_success(self):
        """Test successful data refresh"""
        app = Flask(__name__)
        app.register_blueprint(api_bp)

        with app.test_client() as client:
            response = client.post("/api/refresh-data")

            assert response.status_code == 200
            data = response.get_json()
            assert data["success"] is True
            assert "refresh completed" in data["message"]
            assert "timestamp" in data


if __name__ == "__main__":
    pytest.main([__file__])
