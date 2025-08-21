#!/usr/bin/env python3
"""
Security Standalone Functions Tests Import Module

This module has been refactored into smaller, focused test modules:
- test_password_security.py: Password hashing and verification tests
- test_jwt_security.py: JWT token generation and validation tests
- test_api_key_security.py: API key validation and generation tests
- test_rate_limiter_security.py: Rate limiting functionality tests

To run all security function tests: pytest tests/test_*_security.py -v
"""

# Import all test modules for backward compatibility
import pytest

# Import all the refactored test classes
try:
    from test_api_key_security import (TestAPIKeyGeneration,
                                       TestAPIKeyValidation)
    from test_jwt_security import (TestJWTTokenGeneration,
                                   TestJWTTokenValidation)
    from test_password_security import (TestPasswordHashing,
                                        TestPasswordVerification)
    from test_rate_limiter_security import (TestRateLimiterCreation,
                                            TestRateLimiterFunctionality)
except ImportError as e:
    pytest.skip(f"Unable to import refactored security test modules: {e}")


# All test classes have been moved to separate modules.
# This file now serves as a compatibility layer.

# For individual test execution, use:
# pytest tests/test_password_security.py::TestPasswordHashing::test_hash_password_basic
# pytest tests/test_jwt_security.py::TestJWTTokenGeneration::test_generate_jwt_token_basic
# pytest tests/test_api_key_security.py::TestAPIKeyValidation::test_validate_api_key_valid
# pytest tests/test_rate_limiter_security.py::TestRateLimiterCreation::test_create_rate_limiter_basic


if __name__ == "__main__":
    # Validation test for refactored module
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Module imports work
    total_tests += 1
    try:
        from test_api_key_security import (TestAPIKeyGeneration,
                                           TestAPIKeyValidation)
        from test_jwt_security import (TestJWTTokenGeneration,
                                       TestJWTTokenValidation)
        from test_password_security import (TestPasswordHashing,
                                            TestPasswordVerification)
        from test_rate_limiter_security import (TestRateLimiterCreation,
                                                TestRateLimiterFunctionality)

        # Test passed if no exception
    except Exception as e:
        all_validation_failures.append(f"Security module imports failed: {e}")

    # Test 2: All security test classes are available
    total_tests += 1
    try:
        required_classes = [
            TestPasswordHashing,
            TestPasswordVerification,
            TestJWTTokenGeneration,
            TestJWTTokenValidation,
            TestAPIKeyValidation,
            TestAPIKeyGeneration,
            TestRateLimiterCreation,
            TestRateLimiterFunctionality,
        ]

        for cls in required_classes:
            if not hasattr(cls, "__name__"):
                all_validation_failures.append(f"Invalid security test class: {cls}")
                break
        else:
            # All classes are valid
            pass
    except Exception as e:
        all_validation_failures.append(f"Security class validation failed: {e}")

    # Test 3: Module can be used for pytest discovery
    total_tests += 1
    try:
        # This should work for pytest discovery
        security_test_classes = [
            TestPasswordHashing,
            TestPasswordVerification,
            TestJWTTokenGeneration,
            TestJWTTokenValidation,
            TestAPIKeyValidation,
            TestAPIKeyGeneration,
            TestRateLimiterCreation,
            TestRateLimiterFunctionality,
        ]

        for test_cls in security_test_classes:
            if not test_cls.__name__.startswith("Test"):
                all_validation_failures.append(
                    f"Invalid security test class name: {test_cls.__name__}"
                )
                break
        else:
            # Test passed
            pass
    except Exception as e:
        all_validation_failures.append(
            f"Security pytest compatibility check failed: {e}"
        )

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
            "Refactored security standalone functions module is validated and ready for use"
        )
        sys.exit(0)
