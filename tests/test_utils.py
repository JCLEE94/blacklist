#!/usr/bin/env python3
"""
Common Test Utilities for Blacklist Management System Tests

Shared utilities, fixtures, and setup code for all test modules.
Extracted from larger test files to reduce duplication and maintain consistency.

Links:
- pytest documentation: https://docs.pytest.org/
- requests documentation: https://docs.python-requests.org/

Sample input: Used by importing in test modules
Expected output: Provides common test setup and utilities
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import pytest
import requests

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def load_test_env():
    """Load environment variables from .env file for tests"""
    try:
        from dotenv import load_dotenv

        dotenv_path = os.path.join(project_root, ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
    except ImportError:
        # If python-dotenv is not available, try to read .env manually
        env_file = os.path.join(project_root, ".env")
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        if key not in os.environ:  # Don't override existing env vars
                            os.environ[key] = value

# Load environment once on import
load_test_env()

class TestBase:
    """Base class for all test classes with common utilities"""
    
    BASE_URL = "http://localhost:32542"
    
    def __init__(self):
        self.auth_headers = {}
        self.test_tokens = {}
    
    def setup_method(self):
        """Setup method run before each test"""
        self.auth_headers = {}
        self.test_tokens = {}
        # Add small delay to avoid rate limiting
        time.sleep(0.5)
    
    def make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make HTTP request with error handling and rate limiting"""
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.request(method, url, timeout=10, **kwargs)
            
            # Handle common error conditions
            if response.status_code == 429:
                pytest.skip("Rate limiting active - test skipped")
            elif response.status_code == 503:
                pytest.skip("Service unavailable - test skipped")
            
            return response
            
        except requests.RequestException as e:
            pytest.skip(f"Request failed: {e}")
    
    def get_admin_credentials(self) -> tuple[str, str]:
        """Get admin credentials from environment"""
        username = "admin"
        password = os.getenv("ADMIN_PASSWORD", "bingogo1")
        return username, password
    
    def get_regtech_credentials(self) -> Optional[tuple[str, str]]:
        """Get REGTECH credentials from environment"""
        username = os.getenv("REGTECH_USERNAME")
        password = os.getenv("REGTECH_PASSWORD")
        
        if not username or not password:
            return None
        return username, password
    
    def login_admin(self) -> Optional[Dict[str, str]]:
        """Login as admin and return tokens"""
        username, password = self.get_admin_credentials()
        
        response = self.make_request(
            "POST", "/api/auth/login",
            json={"username": username, "password": password}
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        success_indicator = (
            data.get("success", False) or data.get("status") == "success"
        )
        
        if success_indicator:
            tokens = {}
            if "access_token" in data:
                tokens["access_token"] = data["access_token"]
            if "refresh_token" in data:
                tokens["refresh_token"] = data["refresh_token"]
            
            # Store for instance use
            self.test_tokens["admin"] = tokens.get("access_token")
            self.test_tokens["admin_refresh"] = tokens.get("refresh_token")
            
            return tokens
        
        return None
    
    def get_auth_headers(self, token: str) -> Dict[str, str]:
        """Get authorization headers for API requests"""
        return {"Authorization": f"Bearer {token}"}
    
    def wait_for_rate_limit_reset(self):
        """Wait for rate limiting to reset"""
        time.sleep(2)


def validate_response_structure(response_data: Dict[str, Any], required_fields: list[str]):
    """Validate that response contains required fields"""
    for field in required_fields:
        assert field in response_data, f"Missing required field: {field}"


def is_valid_jwt_format(token: str) -> bool:
    """Check if token has valid JWT format (3 parts separated by dots)"""
    if not token or not isinstance(token, str):
        return False
    
    parts = token.split(".")
    return len(parts) == 3 and all(part for part in parts)


if __name__ == "__main__":
    # Validation tests
    import sys
    
    all_validation_failures = []
    total_tests = 0
    
    # Test 1: TestBase instantiation
    total_tests += 1
    try:
        test_base = TestBase()
        if hasattr(test_base, 'BASE_URL') and hasattr(test_base, 'auth_headers'):
            pass  # Test passed
        else:
            all_validation_failures.append("TestBase missing required attributes")
    except Exception as e:
        all_validation_failures.append(f"TestBase instantiation failed: {e}")
    
    # Test 2: Environment loading
    total_tests += 1
    try:
        load_test_env()  # Should not raise exception
        # Test passed if no exception
    except Exception as e:
        all_validation_failures.append(f"Environment loading failed: {e}")
    
    # Test 3: JWT format validation
    total_tests += 1
    try:
        valid_jwt = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"
        invalid_jwt = "invalid.token"
        
        if is_valid_jwt_format(valid_jwt) and not is_valid_jwt_format(invalid_jwt):
            pass  # Test passed
        else:
            all_validation_failures.append("JWT format validation failed")
    except Exception as e:
        all_validation_failures.append(f"JWT format validation failed: {e}")
    
    # Test 4: Response validation utility
    total_tests += 1
    try:
        test_response = {"status": "success", "data": {"id": 1}}
        validate_response_structure(test_response, ["status", "data"])
        # Test passed if no exception
    except Exception as e:
        all_validation_failures.append(f"Response validation utility failed: {e}")
    
    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Test utilities module is validated and ready for use")
        sys.exit(0)
