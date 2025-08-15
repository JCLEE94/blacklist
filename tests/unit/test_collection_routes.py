#!/usr/bin/env python3
"""
Unit tests for collection route endpoints
Tests collection status, triggering, and logging endpoints.
"""

import json
import unittest.mock as mock
from datetime import datetime

import pytest
from flask import Flask

from src.core.routes.collection_logs_routes import collection_logs_bp
from src.core.routes.collection_status_routes import collection_status_bp
from src.core.routes.collection_trigger_routes import collection_trigger_bp


class TestCollectionRoutes:
    """Test cases for collection route endpoints"""

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

    def test_get_collection_status_success(self, client, mock_service):
        """Test successful collection status retrieval"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/status")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["enabled"] is True
            assert data["collection_enabled"] is True
            assert data["status"] == "active"
            assert "stats" in data
            assert "daily_collection" in data

    def test_get_collection_status_disabled(self, client, mock_service):
        """Test collection status when collection is disabled"""
        mock_service.collection_enabled = False
        mock_service.get_collection_status.return_value["collection_enabled"] = False

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/status")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["enabled"] is False
            assert data["status"] == "inactive"

    def test_get_collection_status_exception(self, client, mock_service):
        """Test collection status with exception"""
        mock_service.get_collection_status.side_effect = Exception("Service error")

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["enabled"] is False
            assert data["status"] == "error"
            assert "error" in data

    def test_enable_collection_success(self, client, mock_service, mock_container):
        """Test successful collection enablement"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/enable", json={"clear_data": True}
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["collection_enabled"] is True
                mock_service.add_collection_log.assert_called()

    def test_enable_collection_no_manager(self, client, mock_service):
        """Test collection enablement when manager is unavailable"""
        mock_container = mock.Mock()
        mock_container.get.return_value = None

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/enable")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False
                assert "Collection manager not available" in data["error"]

    def test_enable_collection_exception(self, client, mock_service, mock_container):
        """Test collection enablement with exception"""
        collection_manager = mock_container.get("collection_manager")
        collection_manager.enable_collection.side_effect = Exception("Enable failed")

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/enable")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_disable_collection_success(self, client, mock_service, mock_container):
        """Test successful collection disablement"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/disable")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                mock_service.add_collection_log.assert_called()

    def test_disable_collection_no_manager(self, client, mock_service):
        """Test collection disablement when manager is unavailable"""
        mock_container = mock.Mock()
        mock_container.get.return_value = None

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/disable")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_collection_statistics_success(self, client, mock_service):
        """Test successful collection statistics retrieval"""
        mock_service.get_source_statistics.return_value = {
            "regtech": {"total": 50, "active": 45},
            "secudium": {"total": 30, "active": 25},
        }

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/statistics")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "daily_stats" in data
            assert "source_stats" in data
            assert "summary" in data

    def test_collection_statistics_exception(self, client, mock_service):
        """Test collection statistics with exception"""
        mock_service.get_daily_collection_stats.side_effect = Exception("Stats error")

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_status_routes.create_error_response",
                return_value={"error": "Stats error"},
            ):
                response = client.get("/api/collection/statistics")

                assert response.status_code == 500

    def test_get_collection_intervals_success(self, client, mock_service):
        """Test successful collection intervals retrieval"""
        mock_service.get_collection_intervals.return_value = {
            "regtech_days": 90,
            "secudium_days": 3,
        }

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.get("/api/collection/intervals")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["regtech_days"] == 90
            assert data["secudium_days"] == 3

    def test_update_collection_intervals_success(self, client, mock_service):
        """Test successful collection intervals update"""
        mock_service.update_collection_intervals = mock.Mock()

        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.post(
                "/api/collection/intervals",
                json={"regtech_days": 120, "secudium_days": 5},
            )

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            mock_service.update_collection_intervals.assert_called_with(120, 5)

    def test_update_collection_intervals_invalid_regtech(self, client, mock_service):
        """Test collection intervals update with invalid REGTECH days"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.post(
                "/api/collection/intervals",
                json={"regtech_days": 400, "secudium_days": 5},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "REGTECH 수집 간격" in data["error"]

    def test_update_collection_intervals_invalid_secudium(self, client, mock_service):
        """Test collection intervals update with invalid SECUDIUM days"""
        with mock.patch(
            "src.core.routes.collection_status_routes.service", mock_service
        ):
            response = client.post(
                "/api/collection/intervals",
                json={"regtech_days": 90, "secudium_days": 50},
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "SECUDIUM 수집 간격" in data["error"]

    def test_trigger_regtech_collection_success(
        self, client, mock_service, mock_container
    ):
        """Test successful REGTECH collection trigger"""
        mock_service.trigger_regtech_collection.return_value = {
            "success": True,
            "message": "Collection started",
        }

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/regtech/trigger",
                    json={"start_date": "2023-01-01", "end_date": "2023-01-31"},
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["source"] == "regtech"
                mock_service.add_collection_log.assert_called()

    def test_trigger_regtech_collection_failure(
        self, client, mock_service, mock_container
    ):
        """Test REGTECH collection trigger failure"""
        mock_service.trigger_regtech_collection.return_value = {
            "success": False,
            "message": "Collection failed",
            "error": "Network error",
        }

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/regtech/trigger")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_trigger_regtech_collection_exception(
        self, client, mock_service, mock_container
    ):
        """Test REGTECH collection trigger with exception"""
        mock_service.trigger_regtech_collection.side_effect = Exception("Trigger error")

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/regtech/trigger")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False
                assert "error" in data

    def test_trigger_secudium_collection_disabled(
        self, client, mock_service, mock_container
    ):
        """Test SECUDIUM collection trigger (disabled)"""
        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/secudium/trigger")

                assert response.status_code == 503
                data = json.loads(response.data)
                assert data["success"] is False
                assert data["disabled"] is True
                assert "SECUDIUM 수집은 현재 비활성화" in data["message"]

    def test_trigger_secudium_collection_exception(
        self, client, mock_service, mock_container
    ):
        """Test SECUDIUM collection trigger with exception"""
        mock_container.get.side_effect = Exception("Container error")

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/secudium/trigger")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_get_collection_progress_success(
        self, client, mock_service, mock_container
    ):
        """Test successful collection progress retrieval"""
        progress_tracker = mock_container.get("progress_tracker")
        progress_tracker.get_progress.return_value = {
            "status": "running",
            "current_item": 25,
            "total_items": 100,
            "percentage": 25.0,
            "message": "Processing data",
            "started_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.get("/api/collection/progress/regtech")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["source"] == "regtech"
                assert data["progress"]["status"] == "running"
                assert data["progress"]["percentage"] == 25.0

    def test_get_collection_progress_no_tracker(self, client, mock_service):
        """Test collection progress when tracker is unavailable"""
        mock_container = mock.Mock()
        mock_container.get.return_value = None

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.get("/api/collection/progress/regtech")

                assert response.status_code == 503
                data = json.loads(response.data)
                assert data["success"] is False

    def test_get_collection_progress_no_progress(
        self, client, mock_service, mock_container
    ):
        """Test collection progress when no progress is available"""
        progress_tracker = mock_container.get("progress_tracker")
        progress_tracker.get_progress.return_value = None

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.get("/api/collection/progress/regtech")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert data["progress"] is None

    def test_api_collection_logs_success(self, client, mock_service):
        """Test successful collection logs retrieval"""
        with mock.patch("os.path.exists", return_value=False):  # No log files
            with mock.patch(
                "src.core.routes.collection_logs_routes.service", mock_service
            ):
                response = client.get("/api/collection/logs")

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["success"] is True
                assert "logs" in data
                assert "count" in data

    def test_api_collection_logs_with_file(self, client, mock_service):
        """Test collection logs retrieval with log files"""
        log_content = [
            "2023-01-01 10:00:00 - REGTECH collection started\n",
            "2023-01-01 10:05:00 - Collection completed\n",
        ]

        with mock.patch("os.path.exists", return_value=True):
            with mock.patch(
                "builtins.open", mock.mock_open(read_data="".join(log_content))
            ):
                with mock.patch(
                    "src.core.routes.collection_logs_routes.service", mock_service
                ):
                    response = client.get("/api/collection/logs")

                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data["success"] is True
                    assert len(data["logs"]) > 0

    def test_api_collection_logs_exception(self, client, mock_service):
        """Test collection logs retrieval with exception"""
        mock_service.get_collection_logs.side_effect = Exception("Log error")

        with mock.patch("os.path.exists", return_value=False):
            with mock.patch(
                "src.core.routes.collection_logs_routes.service", mock_service
            ):
                response = client.get("/api/collection/logs")

                assert response.status_code == 500
                data = json.loads(response.data)
                assert data["success"] is False

    def test_get_realtime_logs_success(self, client, mock_service):
        """Test successful realtime logs retrieval"""
        with mock.patch("src.core.routes.collection_logs_routes.service", mock_service):
            response = client.get("/api/collection/logs/realtime")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert "logs" in data
            assert "count" in data

    def test_get_realtime_logs_exception(self, client, mock_service):
        """Test realtime logs retrieval with exception"""
        mock_service.get_collection_logs.side_effect = Exception("Realtime error")

        with mock.patch("src.core.routes.collection_logs_routes.service", mock_service):
            response = client.get("/api/collection/logs/realtime")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False

    def test_get_collection_logs_with_limit(self, client, mock_service):
        """Test collection logs retrieval with limit parameter"""
        with mock.patch("src.core.routes.collection_logs_routes.service", mock_service):
            response = client.get("/api/collection/logs?limit=10")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            # Verify that the service was called with the correct limit
            mock_service.get_collection_logs.assert_called()

    def test_request_data_handling_json(self, client, mock_service, mock_container):
        """Test request data handling for JSON content"""
        mock_service.trigger_regtech_collection.return_value = {"success": True}

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/regtech/trigger",
                    json={"start_date": "2023-01-01"},
                    content_type="application/json",
                )

                assert response.status_code == 200
                # Verify the service was called with the extracted date
                mock_service.trigger_regtech_collection.assert_called_with(
                    start_date="2023-01-01", end_date=None
                )

    def test_request_data_handling_form(self, client, mock_service, mock_container):
        """Test request data handling for form content"""
        mock_service.trigger_regtech_collection.return_value = {"success": True}

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post(
                    "/api/collection/regtech/trigger",
                    data={"start_date": "2023-01-01"},
                    content_type="application/x-www-form-urlencoded",
                )

                assert response.status_code == 200
                # Verify the service was called with the extracted date
                mock_service.trigger_regtech_collection.assert_called_with(
                    start_date="2023-01-01", end_date=None
                )

    def test_progress_tracker_integration(self, client, mock_service, mock_container):
        """Test progress tracker integration in collection trigger"""
        progress_tracker = mock_container.get("progress_tracker")
        mock_service.trigger_regtech_collection.return_value = {"success": True}

        with mock.patch(
            "src.core.routes.collection_trigger_routes.service", mock_service
        ):
            with mock.patch(
                "src.core.routes.collection_trigger_routes.get_container",
                return_value=mock_container,
            ):
                response = client.post("/api/collection/regtech/trigger")

                assert response.status_code == 200
                # Verify progress tracker methods were called
                progress_tracker.start_collection.assert_called_with("regtech")
                progress_tracker.get_progress.assert_called_with("regtech")


if __name__ == "__main__":
    pytest.main([__file__])
