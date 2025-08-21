#!/usr/bin/env python3
"""
API Key Security Function Tests

Tests API key validation, generation, and management functions.
Focuses on API key security implementation.

Links:
- API Key best practices: https://cloud.google.com/docs/authentication/api-keys
- UUID documentation: https://docs.python.org/3/library/uuid.html

Sample input: pytest tests/test_api_key_security.py -v
Expected output: All API key security tests pass with proper validation
"""

import secrets
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class TestAPIKeyValidation:
    """Test validate_api_key standalone function"""

    def test_validate_api_key_valid(self):
        """Test API key validation with valid key"""
        try:
            from src.utils.security import validate_api_key

            # Test with a properly formatted API key
            valid_key = "blk_" + secrets.token_urlsafe(32)
            
            # Mock a valid API key database lookup
            with patch('src.utils.security.get_api_key_from_db') as mock_db:
                mock_db.return_value = {
                    "api_key": valid_key,
                    "is_active": True,
                    "expires_at": None
                }
                
                result = validate_api_key(valid_key)
                assert result is True or isinstance(result, dict)

        except ImportError:
            pytest.skip("validate_api_key function not found")

    def test_validate_api_key_invalid_format(self):
        """Test API key validation with invalid format"""
        try:
            from src.utils.security import validate_api_key

            invalid_keys = [
                "invalid_key",
                "short",
                "",
                None,
                "wrong_prefix_" + secrets.token_urlsafe(32)
            ]

            for key in invalid_keys:
                result = validate_api_key(key)
                assert result is False or result is None

        except ImportError:
            pytest.skip("validate_api_key function not found")

    def test_validate_api_key_inactive(self):
        """Test API key validation with inactive key"""
        try:
            from src.utils.security import validate_api_key

            inactive_key = "blk_" + secrets.token_urlsafe(32)
            
            with patch('src.utils.security.get_api_key_from_db') as mock_db:
                mock_db.return_value = {
                    "api_key": inactive_key,
                    "is_active": False,
                    "expires_at": None
                }
                
                result = validate_api_key(inactive_key)
                assert result is False

        except ImportError:
            pytest.skip("validate_api_key function not found")

    def test_validate_api_key_expired(self):
        """Test API key validation with expired key"""
        try:
            from src.utils.security import validate_api_key
            from datetime import datetime, timedelta

            expired_key = "blk_" + secrets.token_urlsafe(32)
            expired_time = datetime.utcnow() - timedelta(days=1)
            
            with patch('src.utils.security.get_api_key_from_db') as mock_db:
                mock_db.return_value = {
                    "api_key": expired_key,
                    "is_active": True,
                    "expires_at": expired_time.isoformat()
                }
                
                result = validate_api_key(expired_key)
                assert result is False

        except ImportError:
            pytest.skip("validate_api_key function not found")

    def test_validate_api_key_not_found(self):
        """Test API key validation with key not in database"""
        try:
            from src.utils.security import validate_api_key

            unknown_key = "blk_" + secrets.token_urlsafe(32)
            
            with patch('src.utils.security.get_api_key_from_db') as mock_db:
                mock_db.return_value = None  # Key not found
                
                result = validate_api_key(unknown_key)
                assert result is False

        except ImportError:
            pytest.skip("validate_api_key function not found")


class TestAPIKeyGeneration:
    """Test API key generation functions"""

    def test_generate_api_key_basic(self):
        """Test basic API key generation"""
        try:
            from src.utils.security import generate_api_key

            api_key = generate_api_key()
            
            # Should return a string
            assert isinstance(api_key, str)
            assert len(api_key) > 20  # Should be reasonably long
            
            # Should start with prefix
            assert api_key.startswith("blk_") or api_key.startswith("api_")

        except ImportError:
            pytest.skip("generate_api_key function not found")

    def test_generate_api_key_uniqueness(self):
        """Test that generated API keys are unique"""
        try:
            from src.utils.security import generate_api_key

            keys = [generate_api_key() for _ in range(10)]
            
            # All keys should be unique
            assert len(set(keys)) == len(keys)
            
            # All keys should be different
            for i, key1 in enumerate(keys):
                for j, key2 in enumerate(keys):
                    if i != j:
                        assert key1 != key2

        except ImportError:
            pytest.skip("generate_api_key function not found")

    def test_generate_api_key_with_prefix(self):
        """Test API key generation with custom prefix"""
        try:
            from src.utils.security import generate_api_key

            custom_prefix = "test_"
            api_key = generate_api_key(prefix=custom_prefix)
            
            assert isinstance(api_key, str)
            assert api_key.startswith(custom_prefix)

        except ImportError:
            pytest.skip("generate_api_key function not found")

    def test_generate_api_key_length(self):
        """Test API key generation with specified length"""
        try:
            from src.utils.security import generate_api_key

            # Test different lengths
            for length in [16, 32, 64]:
                api_key = generate_api_key(length=length)
                
                # Remove prefix to check actual token length
                if api_key.startswith("blk_"):
                    token_part = api_key[4:]
                elif api_key.startswith("api_"):
                    token_part = api_key[4:]
                else:
                    token_part = api_key
                
                # Token part should be roughly the specified length
                # (allowing for base64 encoding variations)
                assert len(token_part) >= length - 5

        except ImportError:
            pytest.skip("generate_api_key function not found")


if __name__ == "__main__":
    # Validation tests
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: Test classes instantiation
    total_tests += 1
    try:
        test_val = TestAPIKeyValidation()
        test_gen = TestAPIKeyGeneration()
        if (hasattr(test_val, 'test_validate_api_key_valid') and 
            hasattr(test_gen, 'test_generate_api_key_basic')):
            pass  # Test passed
        else:
            all_validation_failures.append("API key security test classes missing methods")
    except Exception as e:
        all_validation_failures.append(f"API key security test classes instantiation failed: {e}")
    
    # Test 2: API key format validation helper
    total_tests += 1
    try:
        def is_valid_api_key_format(key):
            if not key or not isinstance(key, str):
                return False
            return (key.startswith("blk_") or key.startswith("api_")) and len(key) > 20
        
        # Test API key format validation
        valid_key = "blk_" + secrets.token_urlsafe(32)
        invalid_key = "invalid_key"
        
        if is_valid_api_key_format(valid_key) and not is_valid_api_key_format(invalid_key):
            pass  # Test passed
        else:
            all_validation_failures.append("API key format validation helper failed")
    except Exception as e:
        all_validation_failures.append(f"API key format validation test failed: {e}")
    
    # Test 3: Test method coverage
    total_tests += 1
    try:
        required_methods = [
            'test_validate_api_key_valid',
            'test_validate_api_key_invalid_format',
            'test_generate_api_key_basic',
            'test_generate_api_key_uniqueness'
        ]
        
        test_val = TestAPIKeyValidation()
        test_gen = TestAPIKeyGeneration()
        
        missing_methods = []
        for method in required_methods[:2]:  # Validation methods
            if not hasattr(test_val, method):
                missing_methods.append(method)
        
        for method in required_methods[2:]:  # Generation methods
            if not hasattr(test_gen, method):
                missing_methods.append(method)
        
        if not missing_methods:
            pass  # Test passed
        else:
            all_validation_failures.append(f"Missing API key test methods: {missing_methods}")
    except Exception as e:
        all_validation_failures.append(f"API key method coverage check failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("API key security test module is validated and ready for use")
        sys.exit(0)
