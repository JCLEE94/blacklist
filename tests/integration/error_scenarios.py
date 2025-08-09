"""Error scenario test cases

Extracted from test_error_handling_edge_cases.py for better organization.
"""

import sqlite3
import threading
import time
from unittest.mock import Mock, patch

from .test_helpers import BaseIntegrationTest, create_mock_service


class TestNetworkErrors(BaseIntegrationTest):
    """Test network-related error handling"""

    def test_network_timeout_handling(self, client):
        """Test handling of network timeouts during collection"""
        mock_service = create_mock_service(failing=True)
        mock_service.trigger_regtech_collection.side_effect = mock_service.network_error

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "20250601"},
                timeout=5,
            )

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "Network connection timeout" in data["error"]

    def test_partial_network_failure(self, client):
        """Test handling when network fails mid-collection"""
        mock_service = Mock()
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"success": True, "collected": 50}
            else:
                raise Exception("Network error after partial success")

        mock_service.trigger_regtech_collection.side_effect = side_effect
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            response1 = client.post("/api/collection/regtech/trigger")
            assert response1.status_code == 200

            response2 = client.post("/api/collection/regtech/trigger")
            assert response2.status_code == 500


class TestAuthenticationErrors(BaseIntegrationTest):
    """Test authentication-related errors"""

    def test_authentication_failure_handling(self, client):
        """Test handling of authentication failures"""
        mock_service = create_mock_service(failing=True)
        mock_service.trigger_regtech_collection.return_value = {
            "success": False,
            "message": "Authentication failed",
            "error": "Invalid credentials or session expired",
        }

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post("/api/collection/regtech/trigger")

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "Authentication failed" in data["message"]

    def test_expired_session_handling(self, client):
        """Test handling of expired session during collection"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {
            "success": False,
            "message": "Session expired",
            "error": "Please re-authenticate",
            "error_code": "SESSION_EXPIRED",
        }
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post("/api/collection/regtech/trigger")

            assert response.status_code == 500
            data = response.get_json()
            assert "Session expired" in data["message"]


class TestDatabaseErrors(BaseIntegrationTest):
    """Test database-related errors"""

    def test_database_lock_handling(self, client):
        """Test handling of database lock errors"""
        mock_service = create_mock_service(failing=True)
        mock_service.get_collection_status.side_effect = mock_service.db_error

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = response.get_json()
            assert data["enabled"] is False
            assert data["status"] == "error"
            assert "Database is locked" in data["error"]

    def test_database_corruption_handling(self, client):
        """Test handling of database corruption"""
        mock_service = Mock()
        mock_service.get_system_health.side_effect = sqlite3.DatabaseError(
            "Database disk image is malformed"
        )

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = response.get_json()
            assert data["stats"]["total_ips"] == 0


class TestConcurrencyErrors(BaseIntegrationTest):
    """Test concurrency-related errors"""

    def test_race_condition_handling(self, client):
        """Test handling of race conditions in concurrent requests"""
        mock_service = Mock()
        request_order = []
        lock = threading.Lock()

        def track_request(*args, **kwargs):
            with lock:
                request_order.append(threading.current_thread().name)
                time.sleep(0.1)
            return {"success": True, "collected": 10}

        mock_service.trigger_regtech_collection.side_effect = track_request
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            threads = []
            results = []

            def make_request(thread_id):
                response = client.post("/api/collection/regtech/trigger")
                results.append((thread_id, response.status_code))

            for i in range(5):
                t = threading.Thread(target=make_request, args=(i,), name=f"Thread-{i}")
                threads.append(t)
                t.start()

            for t in threads:
                t.join()

            assert all(status == 200 for _, status in results)
            assert len(request_order) == 5
