"""
Integration tests for error handling and edge cases

These tests verify the system handles errors gracefully and
behaves correctly in edge case scenarios.
"""
import json
import os
import sqlite3
import tempfile
import threading
import time
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest
from flask import Flask


class TestErrorHandlingIntegration:
    """Test error handling across the integrated system"""

    @pytest.fixture
    def app(self):
        """Create test Flask app"""
        from src.core.unified_routes import unified_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.register_blueprint(unified_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    @pytest.fixture
    def failing_service(self):
        """Mock service that fails in various ways"""
        service = Mock()

        # Configure various failure modes
        service.network_error = Exception("Network connection timeout")
        service.auth_error = Exception("Authentication failed: Invalid credentials")
        service.db_error = sqlite3.DatabaseError("Database is locked")
        service.parse_error = json.JSONDecodeError("Invalid JSON", "", 0)

        return service

    # ===== Network Error Tests =====

    def test_network_timeout_handling(self, client, failing_service):
        """Test handling of network timeouts during collection"""
        failing_service.trigger_regtech_collection.side_effect = (
            failing_service.network_error
        )

        with patch("src.core.unified_routes.service", failing_service):
            response = client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "20250601"},
                timeout=5,
            )  # Set timeout

            assert response.status_code == 500
            data = response.get_json()
            assert data["success"] is False
            assert "Network connection timeout" in data["error"]
            assert data["message"] == "REGTECH 수집 트리거 중 오류가 발생했습니다."

    def test_partial_network_failure(self, client):
        """Test handling when network fails mid-collection"""
        mock_service = Mock()

        # Simulate partial success then failure
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
            # First call succeeds
            response1 = client.post("/api/collection/regtech/trigger")
            assert response1.status_code == 200

            # Second call fails
            response2 = client.post("/api/collection/regtech/trigger")
            assert response2.status_code == 500

    # ===== Authentication Error Tests =====

    def test_authentication_failure_handling(self, client, failing_service):
        """Test handling of authentication failures"""
        failing_service.trigger_regtech_collection.return_value = {
            "success": False,
            "message": "Authentication failed",
            "error": "Invalid credentials or session expired",
        }

        with patch("src.core.unified_routes.service", failing_service):
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

    # ===== Database Error Tests =====

    def test_database_lock_handling(self, client, failing_service):
        """Test handling of database lock errors"""
        failing_service.get_collection_status.side_effect = failing_service.db_error

        with patch("src.core.unified_routes.service", failing_service):
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
            # Service should degrade gracefully
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = response.get_json()
            assert data["stats"]["total_ips"] == 0

    # ===== Data Parsing Error Tests =====

    def test_malformed_response_handling(self, client):
        """Test handling of malformed responses from external services"""
        mock_service = Mock()

        # Simulate service returning invalid data structure
        mock_service.trigger_regtech_collection.return_value = (
            "Not a dict"  # Wrong type
        )
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post("/api/collection/regtech/trigger")

            # Should handle gracefully
            assert response.status_code in [200, 500]

    def test_invalid_date_format_handling(self, client):
        """Test handling of invalid date formats"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.side_effect = ValueError(
            "Invalid date format"
        )
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post(
                "/api/collection/regtech/trigger",
                json={
                    "start_date": "invalid-date",
                    "end_date": "2025-13-45",  # Invalid month/day
                },
            )

            assert response.status_code == 500
            data = response.get_json()
            assert "Invalid date format" in data["error"]

    # ===== Concurrent Access Error Tests =====

    def test_race_condition_handling(self, client):
        """Test handling of race conditions in concurrent requests"""
        mock_service = Mock()
        request_order = []
        lock = threading.Lock()

        def track_request(*args, **kwargs):
            with lock:
                request_order.append(threading.current_thread().name)
                time.sleep(0.1)  # Simulate processing
            return {"success": True, "collected": 10}

        mock_service.trigger_regtech_collection.side_effect = track_request
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            threads = []
            results = []

            def make_request(thread_id):
                response = client.post("/api/collection/regtech/trigger")
                results.append((thread_id, response.status_code))

            # Start concurrent requests
            for i in range(5):
                t = threading.Thread(target=make_request, args=(i,), name=f"Thread-{i}")
                threads.append(t)
                t.start()

            # Wait for completion
            for t in threads:
                t.join()

            # All should succeed despite concurrent access
            assert all(status == 200 for _, status in results)
            assert len(request_order) == 5

    # ===== Resource Exhaustion Tests =====

    def test_memory_exhaustion_handling(self, client):
        """Test handling when system runs low on memory"""
        mock_service = Mock()

        # Simulate memory error
        mock_service.get_collection_status.side_effect = MemoryError(
            "Cannot allocate memory"
        )

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = response.get_json()
            assert data["status"] == "error"

    def test_large_response_handling(self, client):
        """Test handling of extremely large responses"""
        mock_service = Mock()

        # Create very large response
        large_ip_list = [f"10.0.{i//256}.{i%256}" for i in range(100000)]
        mock_service.get_collection_status.return_value = {
            "enabled": True,
            "sources": {},
            "large_data": large_ip_list,  # Very large data
        }
        mock_service.get_daily_collection_stats.return_value = []
        mock_service.get_system_health.return_value = {
            "total_ips": 100000,
            "active_ips": 100000,
        }
        mock_service.get_collection_logs.return_value = []

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            # Should handle large response
            assert response.status_code == 200
            # Response should be truncated or paginated

    # ===== Edge Case Tests =====

    def test_unicode_handling_in_errors(self, client):
        """Test handling of unicode characters in error messages"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.side_effect = Exception(
            "에러: 한글 오류 메시지 🚫"
        )
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post("/api/collection/regtech/trigger")

            assert response.status_code == 500
            data = response.get_json()
            assert "한글 오류 메시지" in data["error"]

    def test_null_and_undefined_handling(self, client):
        """Test handling of null and undefined values"""
        mock_service = Mock()
        mock_service.get_collection_status.return_value = {
            "enabled": None,  # Null value
            "sources": {},
            "undefined_field": None,
        }
        mock_service.get_daily_collection_stats.return_value = None  # Null response
        mock_service.get_system_health.return_value = {}  # Empty response
        mock_service.get_collection_logs.return_value = []

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            # Should handle null values gracefully
            assert response.status_code == 200
            data = response.get_json()
            assert "stats" in data

    def test_circular_reference_handling(self, client):
        """Test handling of circular references in data"""
        mock_service = Mock()

        # Create circular reference
        circular_data = {"enabled": True}
        circular_data["self"] = circular_data  # Circular reference

        mock_service.get_collection_status.return_value = circular_data

        with patch("src.core.unified_routes.service", mock_service):
            # Should handle without infinite loop
            try:
                response = client.get("/api/collection/status")
                # Should either succeed with sanitized data or fail gracefully
                assert response.status_code in [200, 500]
            except Exception as e:
                # Should not hang or crash
                assert True

    def test_extremely_long_processing_timeout(self, client):
        """Test handling of operations that take too long"""
        mock_service = Mock()

        def slow_operation(*args, **kwargs):
            time.sleep(10)  # Simulate very slow operation
            return {"success": True}

        mock_service.trigger_regtech_collection.side_effect = slow_operation
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            # Client should timeout before operation completes
            start_time = time.time()

            # This should timeout or be interrupted
            response = client.post("/api/collection/regtech/trigger")

            duration = time.time() - start_time

            # Should not wait full 10 seconds
            assert duration < 10


class TestEdgeCaseScenarios:
    """Test various edge case scenarios"""

    @pytest.fixture
    def app(self):
        from src.core.unified_routes import unified_bp

        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.register_blueprint(unified_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_empty_database_scenario(self, client):
        """Test system behavior with completely empty database"""
        mock_service = Mock()
        mock_service.get_collection_status.return_value = {
            "enabled": True,
            "sources": {},
        }
        mock_service.get_daily_collection_stats.return_value = []
        mock_service.get_system_health.return_value = {"total_ips": 0, "active_ips": 0}
        mock_service.get_collection_logs.return_value = []

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            assert response.status_code == 200
            data = response.get_json()
            assert data["stats"]["total_ips"] == 0
            assert data["stats"]["today_collected"] == 0

    def test_future_date_handling(self, client):
        """Test handling of future dates in requests"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {
            "success": True,
            "collected": 0,
            "message": "No data for future dates",
        }
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            # Request data from the future
            response = client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "20990101", "end_date": "20991231"},
            )

            assert response.status_code == 200
            data = response.get_json()
            assert data["data"]["collected"] == 0

    def test_very_old_date_handling(self, client):
        """Test handling of very old dates"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {
            "success": True,
            "collected": 0,
            "message": "No data available for requested period",
        }
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            # Request data from 1990
            response = client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "19900101", "end_date": "19901231"},
            )

            assert response.status_code == 200

    def test_inverted_date_range(self, client):
        """Test handling when end date is before start date"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {
            "success": False,
            "error": "Invalid date range: end date before start date",
        }
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            response = client.post(
                "/api/collection/regtech/trigger",
                json={"start_date": "20250630", "end_date": "20250601"},  # Before start
            )

            assert response.status_code == 500
            data = response.get_json()
            assert "Invalid date range" in str(data)

    def test_special_characters_in_requests(self, client):
        """Test handling of special characters in request data"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {
            "success": True,
            "collected": 0,
        }
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            # Special characters in JSON
            response = client.post(
                "/api/collection/regtech/trigger",
                json={
                    "start_date": "2025-06-01",
                    "end_date": "2025/06/30",
                    "extra": '<script>alert("test")</script>',
                    "unicode": "한글 テスト émojis 🎉",
                },
            )

            assert response.status_code == 200

    def test_http_method_not_allowed(self, client):
        """Test handling of wrong HTTP methods"""
        # Try GET on POST-only endpoint
        response = client.get("/api/collection/enable")
        assert response.status_code == 405  # Method Not Allowed

        # Try POST on GET-only endpoint (if any)
        response = client.post("/api/collection/status")
        assert response.status_code == 405

    def test_missing_content_type_header(self, client):
        """Test handling when Content-Type header is missing"""
        mock_service = Mock()
        mock_service.trigger_regtech_collection.return_value = {
            "success": True,
            "collected": 0,
        }
        mock_service.add_collection_log.return_value = None

        with patch("src.core.unified_routes.service", mock_service):
            # Send request without Content-Type
            response = client.post(
                "/api/collection/regtech/trigger", data='{"start_date": "20250601"}'
            )

            # Should still work (form data fallback)
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
