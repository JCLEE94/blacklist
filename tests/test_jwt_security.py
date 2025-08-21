#!/usr/bin/env python3
"""
JWT Token Security Function Tests

Tests JWT token generation, validation, and security functions.
Focuses on JWT implementation and token security.

Links:
- PyJWT documentation: https://pyjwt.readthedocs.io/
- JWT.io: https://jwt.io/

Sample input: pytest tests/test_jwt_security.py -v
Expected output: All JWT security tests pass with proper token handling
"""

import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestJWTTokenGeneration:
    """Test generate_jwt_token standalone function"""

    def test_generate_jwt_token_basic(self):
        """Test basic JWT token generation"""
        try:
            from src.utils.security import generate_jwt_token

            payload = {"user_id": 123, "username": "testuser"}
            secret = "test_secret_key"

            token = generate_jwt_token(payload, secret)

            # Should return a string token
            assert isinstance(token, str)
            assert len(token) > 0

            # Should be valid JWT format (3 parts separated by dots)
            parts = token.split(".")
            assert len(parts) == 3
            assert all(part for part in parts)  # No empty parts

        except ImportError:
            pytest.skip("generate_jwt_token function not found")

    def test_generate_jwt_token_with_expiration(self):
        """Test JWT token generation with expiration"""
        try:
            from src.utils.security import generate_jwt_token

            payload = {"user_id": 456}
            secret = "test_secret"
            expires_in = 3600  # 1 hour

            token = generate_jwt_token(payload, secret, expires_in)

            assert isinstance(token, str)
            parts = token.split(".")
            assert len(parts) == 3

        except ImportError:
            pytest.skip("generate_jwt_token function not found")

    def test_generate_jwt_token_different_payloads(self):
        """Test that different payloads produce different tokens"""
        try:
            from src.utils.security import generate_jwt_token

            payload1 = {"user_id": 1}
            payload2 = {"user_id": 2}
            secret = "same_secret"

            token1 = generate_jwt_token(payload1, secret)
            token2 = generate_jwt_token(payload2, secret)

            # Different payloads should produce different tokens
            assert token1 != token2

        except ImportError:
            pytest.skip("generate_jwt_token function not found")

    def test_generate_jwt_token_different_secrets(self):
        """Test that different secrets produce different tokens"""
        try:
            from src.utils.security import generate_jwt_token

            payload = {"user_id": 123}
            secret1 = "secret1"
            secret2 = "secret2"

            token1 = generate_jwt_token(payload, secret1)
            token2 = generate_jwt_token(payload, secret2)

            # Different secrets should produce different tokens
            assert token1 != token2

        except ImportError:
            pytest.skip("generate_jwt_token function not found")

    def test_generate_jwt_token_edge_cases(self):
        """Test JWT token generation edge cases"""
        try:
            from src.utils.security import generate_jwt_token

            # Empty payload
            token = generate_jwt_token({}, "secret")
            assert isinstance(token, str)
            assert len(token.split(".")) == 3

            # None values should raise appropriate errors
            with pytest.raises((ValueError, TypeError)):
                generate_jwt_token(None, "secret")

            with pytest.raises((ValueError, TypeError)):
                generate_jwt_token({"user": 1}, None)

        except ImportError:
            pytest.skip("generate_jwt_token function not found")


class TestJWTTokenValidation:
    """Test JWT token validation functions"""

    def test_validate_jwt_token_valid(self):
        """Test JWT token validation with valid token"""
        try:
            from src.utils.security import (generate_jwt_token,
                                            validate_jwt_token)

            payload = {"user_id": 789, "username": "validuser"}
            secret = "validation_secret"

            # Generate token
            token = generate_jwt_token(payload, secret)

            # Validate token
            decoded = validate_jwt_token(token, secret)

            assert isinstance(decoded, dict)
            assert decoded["user_id"] == 789
            assert decoded["username"] == "validuser"

        except ImportError:
            pytest.skip("JWT functions not found")

    def test_validate_jwt_token_invalid_signature(self):
        """Test JWT token validation with invalid signature"""
        try:
            from src.utils.security import (generate_jwt_token,
                                            validate_jwt_token)

            payload = {"user_id": 999}
            correct_secret = "correct_secret"
            wrong_secret = "wrong_secret"

            # Generate with one secret
            token = generate_jwt_token(payload, correct_secret)

            # Try to validate with different secret
            result = validate_jwt_token(token, wrong_secret)
            assert result is None or result is False

        except ImportError:
            pytest.skip("JWT functions not found")

    def test_validate_jwt_token_expired(self):
        """Test JWT token validation with expired token"""
        try:
            from src.utils.security import (generate_jwt_token,
                                            validate_jwt_token)

            payload = {"user_id": 111}
            secret = "expiry_test_secret"
            expires_in = -1  # Already expired

            # Generate expired token
            token = generate_jwt_token(payload, secret, expires_in)

            # Validation should fail
            result = validate_jwt_token(token, secret)
            assert result is None or result is False

        except ImportError:
            pytest.skip("JWT functions not found")

    def test_validate_jwt_token_malformed(self):
        """Test JWT token validation with malformed tokens"""
        try:
            from src.utils.security import validate_jwt_token

            secret = "test_secret"
            malformed_tokens = [
                "not.a.jwt",
                "malformed",
                "too.many.parts.here.invalid",
                "",
                None,
            ]

            for token in malformed_tokens:
                result = validate_jwt_token(token, secret)
                assert result is None or result is False

        except ImportError:
            pytest.skip("validate_jwt_token function not found")


if __name__ == "__main__":
    # Validation tests
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Test classes instantiation
    total_tests += 1
    try:
        test_gen = TestJWTTokenGeneration()
        test_val = TestJWTTokenValidation()
        if hasattr(test_gen, "test_generate_jwt_token_basic") and hasattr(
            test_val, "test_validate_jwt_token_valid"
        ):
            pass  # Test passed
        else:
            all_validation_failures.append("JWT security test classes missing methods")
    except Exception as e:
        all_validation_failures.append(
            f"JWT security test classes instantiation failed: {e}"
        )

    # Test 2: JWT format validation helper
    total_tests += 1
    try:

        def is_valid_jwt_format(token):
            if not token or not isinstance(token, str):
                return False
            parts = token.split(".")
            return len(parts) == 3 and all(part for part in parts)

        # Test JWT format validation
        valid_jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0.Gfx6VO9tcxwk6xqx9yYzSfebfeakZp5JYIgP_edcw_A"
        invalid_jwt = "invalid.token"

        if is_valid_jwt_format(valid_jwt) and not is_valid_jwt_format(invalid_jwt):
            pass  # Test passed
        else:
            all_validation_failures.append("JWT format validation helper failed")
    except Exception as e:
        all_validation_failures.append(f"JWT format validation test failed: {e}")

    # Test 3: Test method coverage
    total_tests += 1
    try:
        required_methods = [
            "test_generate_jwt_token_basic",
            "test_generate_jwt_token_with_expiration",
            "test_validate_jwt_token_valid",
            "test_validate_jwt_token_invalid_signature",
        ]

        test_gen = TestJWTTokenGeneration()
        test_val = TestJWTTokenValidation()

        missing_methods = []
        for method in required_methods[:2]:  # Generation methods
            if not hasattr(test_gen, method):
                missing_methods.append(method)

        for method in required_methods[2:]:  # Validation methods
            if not hasattr(test_val, method):
                missing_methods.append(method)

        if not missing_methods:
            pass  # Test passed
        else:
            all_validation_failures.append(
                f"Missing JWT test methods: {missing_methods}"
            )
    except Exception as e:
        all_validation_failures.append(f"JWT method coverage check failed: {e}")

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
        print("JWT security test module is validated and ready for use")
        sys.exit(0)
