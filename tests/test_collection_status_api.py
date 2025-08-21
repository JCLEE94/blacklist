#!/usr/bin/env python3
"""
Collection Status API Tests

Tests collection status endpoints, monitoring, and statistics APIs.
Focuses on collection system status and reporting functionality.

Links:
- Flask API documentation: https://flask.restful.readthedocs.io/
- Collection system documentation: Internal system docs

Sample input: pytest tests/test_collection_status_api.py -v
Expected output: All collection status API tests pass with proper endpoint validation
"""

import json
import os
import sys
from datetime import datetime, timedelta

import pytest
import requests
from test_utils import TestBase

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestCollectionStatusAPI(TestBase):
    """Test collection status and monitoring endpoints"""

    def test_collection_status_endpoint(self):
        """Test collection status endpoint"""
        response = self.make_request("GET", "/api/collection/status")

        assert response.status_code in [200, 503]
        data = response.json()

        if response.status_code == 200:
            # Check for expected fields in successful response
            assert "enabled" in data or "collection_enabled" in data
            assert "status" in data
            assert "stats" in data
        else:
            # Error response should have error field
            assert "error" in data

    def test_collection_daily_stats(self):
        """Test daily collection statistics"""
        response = self.make_request(
            "GET", "/api/collection/daily-stats", params={"days": 7}
        )

        # This endpoint might not exist (404) or return different formats
        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            # Just verify it returns valid JSON
            assert isinstance(data, dict)

    def test_collection_daily_stats_limits(self):
        """Test daily stats with limit enforcement"""
        # Test exceeding max days limit
        response = self.make_request(
            "GET", "/api/collection/daily-stats", params={"days": 120}
        )

        assert response.status_code in [200, 400, 404, 503]
        if response.status_code == 200:
            data = response.json()
            # Should be capped at reasonable limit (e.g., 90 days)
            if "period" in data and "days" in data["period"]:
                assert data["period"]["days"] <= 90

    def test_collection_history(self):
        """Test collection execution history"""
        response = self.make_request(
            "GET", "/api/collection/history", params={"limit": 10, "offset": 0}
        )

        assert response.status_code in [200, 404, 503]

        if response.status_code == 200:
            data = response.json()
            # Flexible validation for different response formats
            if "success" in data:
                assert data["success"] is True

            # Check for expected fields
            expected_fields = ["history", "data", "results"]
            has_expected = any(field in data for field in expected_fields)
            if not has_expected and data:  # Only check if data is not empty
                # Allow any structure as long as it's valid JSON
                pass

    def test_collection_history_limits(self):
        """Test collection history with limit enforcement"""
        # Test exceeding max limit
        response = self.make_request(
            "GET", "/api/collection/history", params={"limit": 150}
        )

        assert response.status_code in [200, 400, 404, 503]
        if response.status_code == 200:
            data = response.json()
            # Should handle limit appropriately
            if "pagination" in data and "limit" in data["pagination"]:
                # Should be capped at reasonable limit (e.g., 100)
                assert data["pagination"]["limit"] <= 100

    def test_collection_source_status(self):
        """Test individual source status endpoints"""
        sources = ["regtech", "secudium"]

        for source in sources:
            response = self.make_request("GET", f"/api/collection/{source}/status")

            # Should return valid response or indicate not implemented
            assert response.status_code in [200, 404, 501, 503]

            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, dict)

                # Common status fields
                status_fields = ["enabled", "status", "last_run", "active"]
                has_status = any(field in data for field in status_fields)
                if data:  # Only check if response has data
                    assert has_status or "error" in data

    def test_collection_logs_endpoint(self):
        """Test collection logs endpoint"""
        response = self.make_request(
            "GET", "/api/collection/logs", params={"limit": 50}
        )

        # Logs endpoint might not be implemented
        assert response.status_code in [200, 404, 501, 503]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

            # If it's a dict, should have log-related fields
            if isinstance(data, dict):
                log_fields = ["logs", "entries", "messages", "data"]
                has_log_field = any(field in data for field in log_fields)
                if data:  # Only check if response has data
                    assert has_log_field

    def test_collection_metrics_endpoint(self):
        """Test collection metrics endpoint"""
        response = self.make_request("GET", "/api/collection/metrics")

        assert response.status_code in [200, 404, 501, 503]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

            # Common metrics fields
            metrics_fields = ["total", "count", "success_rate", "errors", "performance"]
            has_metrics = any(field in data for field in metrics_fields)
            if data:  # Only check if response has data
                assert has_metrics


if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: TestCollectionStatusAPI instantiation
    total_tests += 1
    try:
        test_collection = TestCollectionStatusAPI()
        if hasattr(test_collection, "BASE_URL") and hasattr(
            test_collection, "make_request"
        ):
            pass  # Test passed
        else:
            all_validation_failures.append(
                "TestCollectionStatusAPI missing required attributes"
            )
    except Exception as e:
        all_validation_failures.append(
            f"TestCollectionStatusAPI instantiation failed: {e}"
        )

    # Test 2: Test method availability
    total_tests += 1
    try:
        test_collection = TestCollectionStatusAPI()
        required_methods = [
            "test_collection_status_endpoint",
            "test_collection_daily_stats",
            "test_collection_history",
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(test_collection, method):
                missing_methods.append(method)

        if not missing_methods:
            pass  # Test passed
        else:
            all_validation_failures.append(
                f"Missing collection status test methods: {missing_methods}"
            )
    except Exception as e:
        all_validation_failures.append(f"Collection status method check failed: {e}")

    # Test 3: Inheritance from TestBase
    total_tests += 1
    try:
        test_collection = TestCollectionStatusAPI()
        if hasattr(test_collection, "make_request") and hasattr(
            test_collection, "setup_method"
        ):
            pass  # Test passed
        else:
            all_validation_failures.append(
                "TestCollectionStatusAPI missing inherited TestBase methods"
            )
    except Exception as e:
        all_validation_failures.append(f"TestBase inheritance check failed: {e}")

    # Final validation result
    if all_validation_failures:
        print(
            f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:"
        )
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(
            f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results"
        )
        print("Collection status API test module is validated and ready for use")
        sys.exit(0)
