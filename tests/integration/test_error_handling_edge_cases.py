"""
Integration tests for error handling and edge cases

These tests verify the system handles errors gracefully and
behaves correctly in edge case scenarios.

Extensive test cases have been moved to specialized modules:
- error_scenarios.py: Network, auth, database errors
- edge_case_tests.py: Data, date, resource exhaustion cases
"""

import pytest

from .edge_case_tests import (
    TestDataEdgeCases,
    TestDateEdgeCases,
    TestResourceExhaustionCases,
    TestSpecialInputCases,
)
from .error_scenarios import (
    TestAuthenticationErrors,
    TestConcurrencyErrors,
    TestDatabaseErrors,
    TestNetworkErrors,
)
from .test_helpers import BaseIntegrationTest


class TestErrorHandlingIntegration(BaseIntegrationTest):
    """Core error handling integration tests"""

    # Fixtures inherited from BaseIntegrationTest

    # Test methods moved to specialized modules for better organization

    def test_basic_error_response_format(self, client):
        """Test that error responses follow consistent format"""
        from unittest.mock import Mock, patch

        mock_service = Mock()
        mock_service.get_collection_status.side_effect = Exception("Test error")

        with patch("src.core.unified_routes.service", mock_service):
            response = client.get("/api/collection/status")

            assert response.status_code == 500
            data = response.get_json()
            assert "error" in data
            assert isinstance(data["error"], str)


# Import test classes from specialized modules
# This ensures all tests are discoverable by pytest while keeping code
# organized
__all__ = [
    "TestErrorHandlingIntegration",
    "TestNetworkErrors",
    "TestAuthenticationErrors",
    "TestDatabaseErrors",
    "TestConcurrencyErrors",
    "TestDataEdgeCases",
    "TestDateEdgeCases",
    "TestResourceExhaustionCases",
    "TestSpecialInputCases",
]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
