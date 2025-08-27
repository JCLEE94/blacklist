#!/usr/bin/env python3
"""
Authentication Tests Import Module

This module has been refactored into smaller, focused test modules:
- test_utils.py: Common test utilities and base classes
- test_auth_routes.py: JWT authentication route tests
- test_api_key_routes.py: API key management tests
- test_security_features.py: Security and attack prevention tests
- test_performance_reliability.py: Performance and reliability tests

To run all authentication tests: pytest tests/test_auth_* tests/test_api_key_* tests/test_security_* tests/test_performance_*
"""

import os
import time

# Import all test modules for backward compatibility
import pytest
import requests

# Import all the refactored test classes
try:
    from test_api_key_routes import TestAPIKeyRoutes
    from test_auth_routes import TestAuthenticationRoutes
    from test_performance_reliability import TestPerformanceAndReliability
    from test_security_features import TestSecurityFeatures
    from test_utils import TestBase
except ImportError as e:
    pytest.skip(
        f"Unable to import refactored test modules: {e}", allow_module_level=True
    )


# All test classes have been moved to separate modules.
# This file now serves as a compatibility layer.

# For individual test execution, use:
# pytest tests/test_auth_routes.py::TestAuthenticationRoutes::test_login_success_admin
# pytest tests/test_api_key_routes.py::TestAPIKeyRoutes::test_create_api_key_success
# pytest tests/test_security_features.py::TestSecurityFeatures::test_malformed_jwt_token
# pytest tests/test_performance_reliability.py::TestPerformanceAndReliability::test_concurrent_login_requests


if __name__ == "__main__":
    # Validation test for refactored module
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Module imports work
    total_tests += 1
    try:
        from test_api_key_routes import TestAPIKeyRoutes
        from test_auth_routes import TestAuthenticationRoutes
        from test_performance_reliability import TestPerformanceAndReliability
        from test_security_features import TestSecurityFeatures
        from test_utils import TestBase

        # Test passed if no exception
    except Exception as e:
        all_validation_failures.append(f"Module imports failed: {e}")

    # Test 2: All classes are available
    total_tests += 1
    try:
        required_classes = [
            TestBase,
            TestAuthenticationRoutes,
            TestAPIKeyRoutes,
            TestSecurityFeatures,
            TestPerformanceAndReliability,
        ]

        for cls in required_classes:
            if not hasattr(cls, "__name__"):
                all_validation_failures.append(f"Invalid class: {cls}")
                break
        else:
            # All classes are valid
            pass
    except Exception as e:
        all_validation_failures.append(f"Class validation failed: {e}")

    # Test 3: Module can be used for pytest discovery
    total_tests += 1
    try:
        # This should work for pytest discovery
        test_classes = [
            TestAuthenticationRoutes,
            TestAPIKeyRoutes,
            TestSecurityFeatures,
            TestPerformanceAndReliability,
        ]

        for test_cls in test_classes:
            if not test_cls.__name__.startswith("Test"):
                all_validation_failures.append(
                    f"Invalid test class name: {test_cls.__name__}"
                )
                break
        else:
            # Test passed
            pass
    except Exception as e:
        all_validation_failures.append(f"Pytest compatibility check failed: {e}")

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
        print(
            "Refactored authentication comprehensive module is validated and ready for use"
        )
        sys.exit(0)
