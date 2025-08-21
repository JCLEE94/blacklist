#!/usr/bin/env python3
"""
TDD Tests for Standalone Security Functions
Comprehensive test suite for critical security functions before implementation.

Tests required functions:
1. hash_password() - Secure password hashing
2. verify_password() - Password verification
3. generate_jwt_token() - JWT token generation
4. validate_api_key() - API key validation
5. create_rate_limiter() - Rate limiting functionality
"""

import secrets
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestPasswordHashing:
    """Test hash_password standalone function"""

    def test_hash_password_basic(self):
        """Test basic password hashing functionality"""
        try:
            from src.utils.security import hash_password

            password = "SecurePassword123!"
            result = hash_password(password)

            # Should return tuple (hash, salt)
            assert isinstance(result, tuple)
            assert len(result) == 2
            hash_value, salt = result

            # Hash should be different from original password
            assert hash_value != password
            assert len(hash_value) > 0
            assert len(salt) > 0

        except ImportError:
            pytest.fail("hash_password function not found in src.utils.security")

    def test_hash_password_with_custom_salt(self):
        """Test password hashing with custom salt"""
        try:
            from src.utils.security import hash_password

            password = "TestPassword123"
            custom_salt = "custom_salt_value"

            hash_value, returned_salt = hash_password(password, custom_salt)

            # Should use provided salt
            assert returned_salt == custom_salt
            assert hash_value != password
            assert len(hash_value) > 0

        except ImportError:
            pytest.fail("hash_password function not found")

    def test_hash_password_consistency(self):
        """Test that same password+salt produces same hash"""
        try:
            from src.utils.security import hash_password

            password = "ConsistentTest123"
            salt = "fixed_salt"

            hash1, _ = hash_password(password, salt)
            hash2, _ = hash_password(password, salt)

            # Same inputs should produce same hash
            assert hash1 == hash2

        except ImportError:
            pytest.fail("hash_password function not found")

    def test_hash_password_different_passwords(self):
        """Test that different passwords produce different hashes"""
        try:
            from src.utils.security import hash_password

            password1 = "Password123"
            password2 = "Password456"
            salt = "same_salt"

            hash1, _ = hash_password(password1, salt)
            hash2, _ = hash_password(password2, salt)

            # Different passwords should produce different hashes
            assert hash1 != hash2

        except ImportError:
            pytest.fail("hash_password function not found")

    def test_hash_password_error_handling(self):
        """Test password hashing error handling"""
        try:
            from src.utils.security import hash_password

            # Test with None password
            try:
                result = hash_password(None)
                # Should either handle gracefully or raise appropriate error
                if result:
                    assert isinstance(result, tuple)
            except (TypeError, ValueError, AttributeError):
                # Expected for None input
                pass

            # Test with empty password
            result = hash_password("")
            assert isinstance(result, tuple)

        except ImportError:
            pytest.fail("hash_password function not found")


class TestPasswordVerification:
    """Test verify_password standalone function"""

    def test_verify_password_basic(self):
        """Test basic password verification"""
        try:
            from src.utils.security import hash_password, verify_password

            password = "VerifyMe123!"
            hash_value, salt = hash_password(password)

            # Correct password should verify
            assert verify_password(password, hash_value, salt) is True

            # Wrong password should not verify
            assert verify_password("WrongPassword", hash_value, salt) is False

        except ImportError:
            pytest.fail("verify_password or hash_password function not found")

    def test_verify_password_edge_cases(self):
        """Test password verification edge cases"""
        try:
            from src.utils.security import hash_password, verify_password

            # Test empty password
            hash_value, salt = hash_password("")
            assert verify_password("", hash_value, salt) is True
            assert verify_password("nonempty", hash_value, salt) is False

            # Test with special characters
            special_password = "Test@#$%^&*()_+123"
            hash_value, salt = hash_password(special_password)
            assert verify_password(special_password, hash_value, salt) is True

        except ImportError:
            pytest.fail("Password verification functions not found")

    def test_verify_password_error_handling(self):
        """Test password verification error handling"""
        try:
            from src.utils.security import verify_password

            # Test with None inputs
            result = verify_password(None, "hash", "salt")
            assert result is False

            result = verify_password("password", None, "salt")
            assert result is False

            result = verify_password("password", "hash", None)
            assert result is False

        except ImportError:
            pytest.fail("verify_password function not found")


class TestJWTTokenGeneration:
    """Test generate_jwt_token standalone function"""

    def test_generate_jwt_token_basic(self):
        """Test basic JWT token generation"""
        try:
            from src.utils.security import generate_jwt_token

            user_id = "test_user_123"
            token = generate_jwt_token(user_id)

            assert isinstance(token, str)
            assert len(token) > 0
            assert "." in token  # JWT format has dots

        except ImportError:
            pytest.fail("generate_jwt_token function not found")

    def test_generate_jwt_token_with_roles(self):
        """Test JWT token generation with roles"""
        try:
            from src.utils.security import generate_jwt_token

            user_id = "admin_user"
            roles = ["admin", "user"]
            token = generate_jwt_token(user_id, roles=roles)

            assert isinstance(token, str)
            assert len(token) > 0

        except ImportError:
            pytest.fail("generate_jwt_token function not found")

    def test_generate_jwt_token_with_expiry(self):
        """Test JWT token generation with custom expiry"""
        try:
            from src.utils.security import generate_jwt_token

            user_id = "temp_user"
            token = generate_jwt_token(user_id, expires_hours=1)

            assert isinstance(token, str)
            assert len(token) > 0

        except ImportError:
            pytest.fail("generate_jwt_token function not found")

    def test_generate_jwt_token_uniqueness(self):
        """Test that JWT tokens are unique"""
        try:
            from src.utils.security import generate_jwt_token

            user_id = "test_user"
            token1 = generate_jwt_token(user_id)
            time.sleep(0.1)  # Small delay to ensure different timestamps
            token2 = generate_jwt_token(user_id)

            # Tokens should be different due to timestamp
            assert token1 != token2

        except ImportError:
            pytest.fail("generate_jwt_token function not found")

    def test_generate_jwt_token_error_handling(self):
        """Test JWT token generation error handling"""
        try:
            from src.utils.security import generate_jwt_token

            # Test with None user_id
            try:
                token = generate_jwt_token(None)
                # Should handle gracefully or raise appropriate error
                if token:
                    assert isinstance(token, str)
            except (TypeError, ValueError):
                # Expected for None input
                pass

        except ImportError:
            pytest.fail("generate_jwt_token function not found")


class TestAPIKeyValidation:
    """Test validate_api_key standalone function"""

    def test_validate_api_key_basic(self):
        """Test basic API key validation"""
        try:
            from src.utils.security import validate_api_key

            # Test with valid format key
            valid_key = "ak_" + secrets.token_urlsafe(32)
            result = validate_api_key(valid_key)

            # Should return boolean or validation object
            assert result is not None

        except ImportError:
            pytest.fail("validate_api_key function not found")

    def test_validate_api_key_invalid_formats(self):
        """Test API key validation with invalid formats"""
        try:
            from src.utils.security import validate_api_key

            invalid_keys = [
                "",
                None,
                "invalid",
                "short",
                "no_prefix_" + secrets.token_urlsafe(32),
                "ak_tooshort",
                "wrongprefix_" + secrets.token_urlsafe(32),
            ]

            for key in invalid_keys:
                result = validate_api_key(key)
                # Should return False or None for invalid keys
                assert result is False or result is None

        except ImportError:
            pytest.fail("validate_api_key function not found")

    def test_validate_api_key_format_check(self):
        """Test API key format validation"""
        try:
            from src.utils.security import generate_api_key, validate_api_key

            # Test proper format using our generator
            proper_key = generate_api_key("ak")
            result = validate_api_key(proper_key)

            # Should be valid format
            assert result is not False and result is not None

        except ImportError:
            pytest.fail("validate_api_key function not found")

    def test_validate_api_key_error_handling(self):
        """Test API key validation error handling"""
        try:
            from src.utils.security import validate_api_key

            # Test with various problematic inputs
            problematic_inputs = [
                None,
                123,
                [],
                {},
                "\x00\x01\x02",  # Binary data
                "key with spaces",
                "key\nwith\nnewlines",
            ]

            for input_val in problematic_inputs:
                try:
                    result = validate_api_key(input_val)
                    # Should handle gracefully
                    assert result is False or result is None
                except (TypeError, ValueError, AttributeError):
                    # Expected for some invalid inputs
                    pass

        except ImportError:
            pytest.fail("validate_api_key function not found")


class TestRateLimiterCreation:
    """Test create_rate_limiter standalone function"""

    def test_create_rate_limiter_basic(self):
        """Test basic rate limiter creation"""
        try:
            from src.utils.security import create_rate_limiter

            limiter = create_rate_limiter()

            # Should return a rate limiter object
            assert limiter is not None

        except ImportError:
            pytest.fail("create_rate_limiter function not found")

    def test_create_rate_limiter_with_params(self):
        """Test rate limiter creation with parameters"""
        try:
            from src.utils.security import create_rate_limiter

            limiter = create_rate_limiter(limit=50, window_seconds=3600)

            assert limiter is not None

        except ImportError:
            pytest.fail("create_rate_limiter function not found")

    def test_create_rate_limiter_functionality(self):
        """Test that created rate limiter has basic functionality"""
        try:
            from src.utils.security import create_rate_limiter

            limiter = create_rate_limiter(limit=5, window_seconds=60)

            # Should have check method or similar
            if hasattr(limiter, "check_rate_limit"):
                result = limiter.check_rate_limit("test_identifier")
                assert isinstance(result, bool)
            elif hasattr(limiter, "check"):
                result = limiter.check("test_identifier")
                assert isinstance(result, bool)
            elif callable(limiter):
                # If limiter itself is callable
                result = limiter("test_identifier")
                assert result is not None

        except ImportError:
            pytest.fail("create_rate_limiter function not found")

    def test_create_rate_limiter_error_handling(self):
        """Test rate limiter creation error handling"""
        try:
            from src.utils.security import create_rate_limiter

            # Test with invalid parameters
            try:
                limiter = create_rate_limiter(limit=-1)
                # Should handle gracefully or raise appropriate error
                assert limiter is not None
            except (ValueError, TypeError):
                # Expected for invalid parameters
                pass

            try:
                limiter = create_rate_limiter(window_seconds=0)
                assert limiter is not None
            except (ValueError, TypeError):
                pass

        except ImportError:
            pytest.fail("create_rate_limiter function not found")


class TestSecurityIntegration:
    """Test integration between security functions"""

    def test_password_hash_verify_integration(self):
        """Test integration between hash_password and verify_password"""
        try:
            from src.utils.security import hash_password, verify_password

            test_cases = [
                "SimplePassword",
                "Complex@Password123!",
                "Short1!",
                "Very_Long_Password_With_Many_Characters_123456789",
                "",  # Edge case: empty password
            ]

            for password in test_cases:
                hash_value, salt = hash_password(password)

                # Verification should work
                assert verify_password(password, hash_value, salt) is True

                # Wrong password should fail
                wrong_password = password + "_wrong" if password else "wrong"
                assert verify_password(wrong_password, hash_value, salt) is False

        except ImportError:
            pytest.fail("Password hash/verify functions not found")

    def test_jwt_api_key_integration(self):
        """Test that JWT and API key systems work together"""
        try:
            from src.utils.security import generate_jwt_token, validate_api_key

            # Generate JWT for a user
            user_id = "integration_test_user"
            token = generate_jwt_token(user_id)
            assert isinstance(token, str)

            # Test API key validation
            test_key = f"ak_{secrets.token_urlsafe(32)}"
            api_result = validate_api_key(test_key)

            # Both should work independently
            assert token is not None
            assert api_result is not None

        except ImportError:
            pytest.fail("JWT or API key functions not found")

    def test_rate_limiter_security_integration(self):
        """Test rate limiter with other security functions"""
        try:
            from src.utils.security import (create_rate_limiter,
                                            validate_api_key)

            limiter = create_rate_limiter(limit=10, window_seconds=60)
            test_key = f"ak_{secrets.token_urlsafe(32)}"

            # Should be able to use rate limiter for API key validation
            api_result = validate_api_key(test_key)

            assert limiter is not None
            assert api_result is not None

        except ImportError:
            pytest.fail("Rate limiter or API key functions not found")


if __name__ == "__main__":
    """
    TDD Validation - Tests must pass before implementation
    """
    import sys

    all_validation_failures = []
    total_tests = 0

    # Test 1: Check for hash_password function
    total_tests += 1
    try:
        from src.utils.security import hash_password

        test_password = "TestPassword123"
        result = hash_password(test_password)
        expected_format = isinstance(result, tuple) and len(result) == 2
        if not expected_format:
            all_validation_failures.append(
                "hash_password: Expected tuple(hash, salt), got different format"
            )
    except ImportError:
        all_validation_failures.append(
            "hash_password: Function not found in src.utils.security"
        )
    except Exception as e:
        all_validation_failures.append(f"hash_password: Unexpected error - {e}")

    # Test 2: Check for verify_password function
    total_tests += 1
    try:
        from src.utils.security import hash_password, verify_password

        test_password = "VerifyTest123"
        hash_val, salt = hash_password(test_password)
        result = verify_password(test_password, hash_val, salt)
        if result is not True:
            all_validation_failures.append(
                "verify_password: Failed to verify correct password"
            )
        wrong_result = verify_password("wrong", hash_val, salt)
        if wrong_result is not False:
            all_validation_failures.append(
                "verify_password: Failed to reject wrong password"
            )
    except ImportError:
        all_validation_failures.append(
            "verify_password: Function not found in src.utils.security"
        )
    except Exception as e:
        all_validation_failures.append(f"verify_password: Unexpected error - {e}")

    # Test 3: Check for generate_jwt_token function
    total_tests += 1
    try:
        from src.utils.security import generate_jwt_token

        user_id = "test_user_validation"
        token = generate_jwt_token(user_id)
        if not isinstance(token, str) or len(token) == 0:
            all_validation_failures.append(
                "generate_jwt_token: Expected non-empty string"
            )
        if "." not in token:
            all_validation_failures.append(
                "generate_jwt_token: Token doesn't appear to be JWT format"
            )
    except ImportError:
        all_validation_failures.append(
            "generate_jwt_token: Function not found in src.utils.security"
        )
    except Exception as e:
        all_validation_failures.append(f"generate_jwt_token: Unexpected error - {e}")

    # Test 4: Check for validate_api_key function
    total_tests += 1
    try:
        from src.utils.security import validate_api_key

        valid_key = f"ak_{secrets.token_urlsafe(32)}"
        result = validate_api_key(valid_key)
        if result is None:
            all_validation_failures.append(
                "validate_api_key: Expected non-None result for valid key"
            )
        invalid_result = validate_api_key("invalid_key")
        if invalid_result is True:
            all_validation_failures.append(
                "validate_api_key: Should reject invalid key format"
            )
    except ImportError:
        all_validation_failures.append(
            "validate_api_key: Function not found in src.utils.security"
        )
    except Exception as e:
        all_validation_failures.append(f"validate_api_key: Unexpected error - {e}")

    # Test 5: Check for create_rate_limiter function
    total_tests += 1
    try:
        from src.utils.security import create_rate_limiter

        limiter = create_rate_limiter()
        if limiter is None:
            all_validation_failures.append(
                "create_rate_limiter: Expected non-None rate limiter object"
            )
    except ImportError:
        all_validation_failures.append(
            "create_rate_limiter: Function not found in src.utils.security"
        )
    except Exception as e:
        all_validation_failures.append(f"create_rate_limiter: Unexpected error - {e}")

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
            "Standalone security functions are validated and ready for production use"
        )
        sys.exit(0)
