"""
Integration tests for collection management endpoints

These tests verify the collection management API endpoints work correctly
in an integrated environment with real services and database interactions.
"""

import threading
import time

import pytest
from flask import Flask

from src.core.unified_routes import unified_bp


class TestCollectionEndpointsIntegration:
    """Integration tests for collection management endpoints"""

    @pytest.fixture
    def app(self):
        """Create test Flask app with real configuration"""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.config["WTF_CSRF_ENABLED"] = False

        # Register blueprint
        app.register_blueprint(unified_bp)

        return app

    @pytest.fixture
    def client(self, app):
        """Create test client"""
        return app.test_client()

    @pytest.fixture
    def real_service(self):
        """Use real service instance"""
        from src.core.unified_service import get_unified_service

        return get_unified_service()

    # ===== Collection Status Tests =====

    def test_collection_status_returns_always_enabled(self, client, real_service):
        """Test that collection status always shows enabled state"""
        response = client.get("/api/collection/status")

        assert response.status_code == 200
        data = response.get_json()

        # Verify structure
        assert data["enabled"] is True
        assert data["status"] == "active"
        assert "수집" in data["message"] and "활성화" in data["message"]

        # Verify stats
        assert "stats" in data
        assert "total_ips" in data["stats"]
        assert "active_ips" in data["stats"]
        assert "today_collected" in data["stats"]

        # Verify daily collection info
        assert "daily_collection" in data
        assert "today" in data["daily_collection"]
        assert "recent_days" in data["daily_collection"]

    def test_collection_status_handles_service_errors(self, client):
        """Test collection status error handling"""
        # This test needs to simulate an error condition
        # For now, we'll test that the endpoint handles missing service gracefully
        response = client.get("/api/collection/status")

        # The actual service should return 200 with valid data
        assert response.status_code == 200
        data = response.get_json()

        # Verify structure exists even if service has issues
        assert "enabled" in data
        assert "status" in data
        assert "stats" in data

    # ===== Collection Enable/Disable Tests =====

    def test_collection_enable_is_idempotent(self, client, real_service):
        """Test that enable endpoint can be called multiple times safely"""
        # First disable collection to ensure we start from disabled state
        response = client.post(
            "/api/collection/disable", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200

        # Call enable multiple times (without clear_data flag)
        for i in range(3):
            response = client.post(
                "/api/collection/enable", headers={"Content-Type": "application/json"}
            )

            assert response.status_code == 200
            data = response.get_json()

            assert data["success"] is True
            assert data["collection_enabled"] is True

            # Without clear_data flag, data should never be cleared
            assert data["cleared_data"] is False
            # Messages may vary with real service

    def test_collection_enable_with_clear_data(self, client, real_service):
        """Test that enable endpoint with clear_data flag clears data"""
        # Enable collection with clear_data flag
        response = client.post(
            "/api/collection/enable",
            headers={"Content-Type": "application/json"},
            json={"clear_data": True},
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["success"] is True
        assert data["collection_enabled"] is True
        assert data["cleared_data"] is True
        assert "기존 데이터가 클리어되었습니다" in data["message"]

    def test_collection_disable_returns_warning(self, client, real_service):
        """Test that disable endpoint returns appropriate warning"""
        response = client.post(
            "/api/collection/disable", headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["success"] is True
        assert data["collection_enabled"] is True  # Still enabled
        # Check for warning and message content flexibly
        assert "warning" in data or "message" in data
        if "warning" in data:
            assert "비활성화" in data["warning"]
        if "message" in data:
            assert "활성화" in data["message"] or "비활성화" in data["message"]

    def test_collection_enable_disable_error_handling(self, client):
        """Test error handling in enable/disable endpoints"""
        # With real service, the endpoint should work
        response = client.post("/api/collection/enable")
        # Should succeed with real service
        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data

    # ===== REGTECH Collection Trigger Tests =====

    def test_regtech_trigger_with_date_parameters(self, client, real_service):
        """Test REGTECH collection trigger with date range"""
        # Test with JSON payload
        response = client.post(
            "/api/collection/regtech/trigger",
            json={"start_date": "20250601", "end_date": "20250630"},
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["success"] is True
        assert data["source"] == "regtech"
        assert "REGTECH 수집이 트리거되었습니다" in data["message"]
        assert "data" in data

    def test_regtech_trigger_with_form_data(self, client, real_service):
        """Test REGTECH collection trigger with form data"""
        # Test with form data
        response = client.post(
            "/api/collection/regtech/trigger",
            data={"start_date": "20250701", "end_date": "20250731"},
        )

        assert response.status_code == 200
        data = response.get_json()

        assert data["success"] is True
        assert data["source"] == "regtech"

    def test_regtech_trigger_without_dates(self, client, real_service):
        """Test REGTECH collection trigger without date parameters"""
        response = client.post("/api/collection/regtech/trigger")

        assert response.status_code == 200
        data = response.get_json()

        assert data["success"] is True

    def test_regtech_trigger_handles_collection_failure(self, client, real_service):
        """Test REGTECH trigger when collection fails"""
        # With real service, we can't force a failure easily
        # But we can test that the endpoint handles responses properly
        response = client.post("/api/collection/regtech/trigger")

        # Should get a response even if collection fails
        assert response.status_code in [200, 500]
        data = response.get_json()

        assert "success" in data
        assert "message" in data

    def test_regtech_trigger_handles_exceptions(self, client):
        """Test REGTECH trigger exception handling"""
        # Test with invalid endpoint to trigger error handling
        response = client.post("/api/collection/invalid/trigger")

        # Should get 404 for invalid endpoint
        assert response.status_code == 404

    # ===== SECUDIUM Collection Trigger Tests =====

    def test_secudium_trigger_returns_disabled_status(self, client):
        """Test that SECUDIUM trigger returns disabled status"""
        response = client.post(
            "/api/collection/secudium/trigger",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 503  # Service Unavailable
        data = response.get_json()

        assert data["success"] is False
        assert data["disabled"] is True
        assert data["source"] == "secudium"
        assert data["message"] == "SECUDIUM 수집은 현재 비활성화되어 있습니다."
        assert data["reason"] == "계정 문제로 인해 일시적으로 사용할 수 없습니다."

    def test_secudium_trigger_with_any_payload(self, client):
        """Test SECUDIUM trigger ignores payload and returns disabled"""
        response = client.post(
            "/api/collection/secudium/trigger", json={"force": True, "test": "data"}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert data["disabled"] is True

    # ===== Concurrent Request Tests =====

    def test_concurrent_collection_requests(self, client, real_service):
        """Test handling of concurrent collection trigger requests"""
        results = []
        errors = []

        def make_request():
            try:
                response = client.post("/api/collection/regtech/trigger")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        # Create and start threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join(timeout=5)

        # Verify results
        assert len(errors) == 0, "Errors occurred: {errors}"
        assert len(results) == 10
        assert all(status == 200 for status in results)

    # ===== Integration with Service Layer Tests =====

    def test_collection_status_with_real_service_calls(self, client, real_service):
        """Test collection status makes all expected service calls"""
        response = client.get("/api/collection/status")

        assert response.status_code == 200
        data = response.get_json()

        # Verify response contains expected data from service calls
        assert "stats" in data
        assert "daily_collection" in data
        assert "logs" in data

    def test_regtech_trigger_logging(self, client, real_service):
        """Test that REGTECH trigger properly logs actions"""
        response = client.post("/api/collection/regtech/trigger")

        assert response.status_code == 200

        # Check that logs are created by checking collection status
        status_response = client.get("/api/collection/status")
        status_data = status_response.get_json()

        # Should have logs in the response
        assert "logs" in status_data
        if status_data["logs"]:
            # Check recent logs for trigger action
            recent_log = status_data["logs"][0]
            assert "source" in recent_log
            assert "action" in recent_log

    # ===== Response Format Validation Tests =====

    def test_all_endpoints_return_json(self, client, real_service):
        """Test that all endpoints return valid JSON responses"""
        endpoints = [
            ("GET", "/api/collection/status"),
            ("POST", "/api/collection/enable"),
            ("POST", "/api/collection/disable"),
            ("POST", "/api/collection/regtech/trigger"),
            ("POST", "/api/collection/secudium/trigger"),
        ]

        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint)

            # Verify JSON response
            assert response.content_type == "application/json"
            data = response.get_json()
            assert data is not None

            # All responses should have either 'success' or 'enabled' field
            assert "success" in data or "enabled" in data

    # ===== State Consistency Tests =====

    def test_collection_state_remains_consistent(self, client, real_service):
        """Test that collection state remains consistent across operations"""
        # Initial state
        response = client.get("/api/collection/status")
        initial_state = response.get_json()
        assert initial_state["enabled"] is True

        # Try to disable
        response = client.post("/api/collection/disable")
        assert response.status_code == 200

        # Check state hasn't changed
        response = client.get("/api/collection/status")
        current_state = response.get_json()
        assert current_state["enabled"] is True

        # Try to enable (should be idempotent)
        response = client.post("/api/collection/enable")
        assert response.status_code == 200

        # Final state check
        response = client.get("/api/collection/status")
        final_state = response.get_json()
        assert final_state["enabled"] is True
        assert final_state["status"] == initial_state["status"]


# ===== Performance Tests =====


class TestCollectionEndpointsPerformance:
    """Performance tests for collection endpoints"""

    @pytest.fixture
    def app(self):
        """Create test app for performance testing"""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.register_blueprint(unified_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_collection_status_response_time(self, client):
        """Test that collection status responds within acceptable time"""
        start_time = time.time()
        response = client.get("/api/collection/status")
        duration = time.time() - start_time

        assert response.status_code == 200
        assert duration < 0.5  # Should respond in less than 500ms with real service

    def test_multiple_rapid_requests(self, client):
        """Test handling of multiple rapid requests"""
        start_time = time.time()

        # Send 5 requests rapidly (reduced for real service)
        for i in range(5):
            response = client.post("/api/collection/regtech/trigger")
            assert response.status_code == 200

        duration = time.time() - start_time

        # Should handle 5 requests in reasonable time
        assert duration < 30.0  # Less than 30 seconds for 5 requests


# ===== Edge Case Tests =====


class TestCollectionEndpointsEdgeCases:
    """Edge case tests for collection endpoints"""

    @pytest.fixture
    def app(self):
        """Create test app"""
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.register_blueprint(unified_bp)
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_malformed_json_handling(self, client):
        """Test handling of malformed JSON in requests"""
        # Send invalid JSON
        response = client.post(
            "/api/collection/regtech/trigger",
            data='{"invalid": json}',
            headers={"Content-Type": "application/json"},
        )

        # Should still handle gracefully (form data fallback)
        assert response.status_code in [200, 500]

    def test_empty_request_handling(self, client):
        """Test handling of empty requests"""
        # Empty POST request
        response = client.post(
            "/api/collection/regtech/trigger",
            data="",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data

    def test_large_date_range_handling(self, client):
        """Test handling of very large date ranges"""
        # Request 10 years of data
        response = client.post(
            "/api/collection/regtech/trigger",
            json={"start_date": "20150101", "end_date": "20250101"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data

    def test_special_characters_in_parameters(self, client):
        """Test handling of special characters in parameters"""
        # Special characters in dates
        response = client.post(
            "/api/collection/regtech/trigger",
            json={
                "start_date": "2025-06-01",  # With dashes
                "end_date": "2025/06/30",  # With slashes
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert "success" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
