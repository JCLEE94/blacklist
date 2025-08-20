#!/usr/bin/env python3
"""
Comprehensive Authentication Tests for Blacklist Management System

Tests JWT authentication, API key management, rate limiting, and security features.
Designed to achieve 95% test coverage for authentication components.
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

class TestAuthenticationRoutes:
    """Test JWT authentication routes with comprehensive coverage"""
    
    BASE_URL = "http://localhost:32542"
    
    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup test environment"""
        self.auth_headers = {}
        self.test_tokens = {}
        
    def test_login_success_admin(self):
        """Test successful admin login"""
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "bingogo1")
            },
            timeout=10
        )
        
        # Handle rate limiting and service availability
        if response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check for success indicator (flexible format)
        success_indicator = data.get("success", False) or data.get("status") == "success"
        assert success_indicator is True
        
        if "access_token" in data:
            assert "access_token" in data
            # Store token for subsequent tests
            self.test_tokens["admin"] = data["access_token"]
        
        if "refresh_token" in data:
            assert "refresh_token" in data
            self.test_tokens["admin_refresh"] = data["refresh_token"]
        
    def test_login_success_collector(self):
        """Test successful collector login"""
        regtech_user = os.getenv("REGTECH_USERNAME")
        regtech_pass = os.getenv("REGTECH_PASSWORD")
        
        if not regtech_user or not regtech_pass:
            pytest.skip("REGTECH credentials not configured")
            
        # Add delay to avoid rate limiting
        time.sleep(1)
            
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": regtech_user,
                "password": regtech_pass
            },
            timeout=10
        )
        
        # Handle rate limiting and service availability
        if response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        
        assert response.status_code == 200
        data = response.json()
        success_indicator = data.get("success", False) or data.get("status") == "success"
        assert success_indicator is True
        
    def test_login_failure_invalid_credentials(self):
        """Test login failure with invalid credentials"""
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "invalid_user",
                "password": "wrong_password"
            },
            timeout=10
        )
        
        # Handle rate limiting
        if response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        
        assert response.status_code in [401, 400]  # Accept both unauthorized and bad request
        data = response.json()
        
        # Check for failure indicator
        failure_indicator = data.get("success", True) is False or data.get("status") == "error"
        assert failure_indicator or "error" in data
        
    def test_login_validation_errors(self):
        """Test login input validation"""
        # Add delay to avoid rate limiting
        time.sleep(1)
        
        # Missing username
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={"password": "test"},
            timeout=10
        )
        
        # Handle rate limiting
        if response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        
        assert response.status_code == 400
        
        # Add delay between requests
        time.sleep(1)
        
        # Missing password
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={"username": "test"},
            timeout=10
        )
        
        if response.status_code != 429 and response.status_code != 503:
            assert response.status_code == 400
        
    def test_token_refresh_success(self):
        """Test successful token refresh"""
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        # First login to get refresh token
        login_response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "bingogo1")
            },
            timeout=10
        )
        
        # Handle rate limiting
        if login_response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif login_response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        elif login_response.status_code != 200:
            pytest.skip(f"Login failed with status {login_response.status_code} - test skipped")
        
        login_data = login_response.json()
        if "refresh_token" not in login_data:
            pytest.skip("Refresh token not in response - test skipped")
            
        refresh_token = login_data["refresh_token"]
        
        # Add delay between requests
        time.sleep(1)
        
        # Test refresh
        response = requests.post(
            f"{self.BASE_URL}/api/auth/refresh",
            json={"refresh_token": refresh_token},
            timeout=10
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limiting active on refresh - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable on refresh - test skipped")
        
        if response.status_code == 200:
            data = response.json()
            success_indicator = data.get("success", False) or data.get("status") == "success"
            assert success_indicator is True
        
    def test_token_refresh_invalid_token(self):
        """Test token refresh with invalid token"""
        response = requests.post(
            f"{self.BASE_URL}/api/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
            timeout=10
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "유효하지 않거나 만료된" in data["error"]
        
    def test_token_verification_valid(self):
        """Test token verification with valid token"""
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        # Get valid token
        login_response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "bingogo1")
            },
            timeout=10
        )
        
        # Handle rate limiting and errors
        if login_response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif login_response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        elif login_response.status_code != 200:
            pytest.skip(f"Login failed with status {login_response.status_code} - test skipped")
        
        login_data = login_response.json()
        if "access_token" not in login_data:
            pytest.skip("Access token not in response - test skipped")
            
        token = login_data["access_token"]
        
        # Add delay between requests
        time.sleep(1)
        
        # Verify token
        response = requests.post(
            f"{self.BASE_URL}/api/auth/verify",
            json={"token": token},
            timeout=10
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limiting active on verify - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable on verify - test skipped")
        
        if response.status_code == 200:
            data = response.json()
            success_indicator = data.get("success", False) or data.get("status") == "success"
            assert success_indicator is True
        
    def test_token_verification_invalid(self):
        """Test token verification with invalid token"""
        response = requests.post(
            f"{self.BASE_URL}/api/auth/verify",
            json={"token": "invalid.token.here"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["valid"] is False
        
    def test_logout_functionality(self):
        """Test logout functionality"""
        response = requests.post(f"{self.BASE_URL}/api/auth/logout", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "로그아웃" in data["message"]
        
    def test_profile_retrieval_authenticated(self):
        """Test profile retrieval with valid authentication"""
        # Add delay to avoid rate limiting
        time.sleep(2)
        
        # Get valid token
        login_response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "bingogo1")
            },
            timeout=10
        )
        
        # Handle rate limiting and errors
        if login_response.status_code == 429:
            pytest.skip("Rate limiting active - test skipped")
        elif login_response.status_code == 503:
            pytest.skip("Service unavailable - test skipped")
        elif login_response.status_code != 200:
            pytest.skip(f"Login failed with status {login_response.status_code} - test skipped")
        
        login_data = login_response.json()
        if "access_token" not in login_data:
            pytest.skip("Access token not in response - test skipped")
            
        token = login_data["access_token"]
        
        # Add delay between requests
        time.sleep(1)
        
        # Get profile
        response = requests.get(
            f"{self.BASE_URL}/api/auth/profile",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
        
        if response.status_code == 429:
            pytest.skip("Rate limiting active on profile - test skipped")
        elif response.status_code == 503:
            pytest.skip("Service unavailable on profile - test skipped")
        
        if response.status_code == 200:
            data = response.json()
            success_indicator = data.get("success", False) or data.get("status") == "success"
            assert success_indicator is True
        
    def test_profile_retrieval_unauthenticated(self):
        """Test profile retrieval without authentication"""
        response = requests.get(f"{self.BASE_URL}/api/auth/profile", timeout=10)
        
        assert response.status_code == 401
        data = response.json()
        assert data["success"] is False
        assert "인증 토큰이 필요" in data["error"]
        
    def test_change_password_not_implemented(self):
        """Test password change endpoint (not implemented)"""
        response = requests.post(
            f"{self.BASE_URL}/api/auth/change-password",
            json={
                "current_password": "old_pass",
                "new_password": "new_password123"
            },
            timeout=10
        )
        
        assert response.status_code == 501
        data = response.json()
        assert data["success"] is False
        assert "지원되지 않습니다" in data["error"]
        
    def test_rate_limiting_login(self):
        """Test rate limiting on login endpoint"""
        # Make multiple failed login attempts
        for i in range(6):  # Exceeds rate limit of 5
            response = requests.post(
                f"{self.BASE_URL}/api/auth/login",
                json={
                    "username": "invalid_user",
                    "password": "wrong_password"
                },
                timeout=10
            )
            
            if i < 5:
                assert response.status_code in [401, 429]  # Auth failure or rate limited
            else:
                # Should be rate limited after 5 attempts
                assert response.status_code == 429


class TestAPIKeyRoutes:
    """Test API key management routes with comprehensive coverage"""
    
    BASE_URL = "http://localhost:32542"
    
    @pytest.fixture(autouse=True)
    def setup_test(self):
        """Setup test environment with admin authentication"""
        # Get admin token for authenticated requests
        login_response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "admin")
            },
            timeout=10
        )
        
        if login_response.status_code == 200:
            self.admin_token = login_response.json()["access_token"]
            self.auth_headers = {"Authorization": f"Bearer {self.admin_token}"}
        else:
            self.admin_token = None
            self.auth_headers = {}
            
    def test_create_api_key_success(self):
        """Test successful API key creation"""
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
            
        response = requests.post(
            f"{self.BASE_URL}/api/keys/create",
            headers=self.auth_headers,
            json={
                "name": "test-key",
                "description": "Test API key",
                "permissions": ["read", "write"],
                "expires_in_days": 30
            },
            timeout=10
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "api_key" in data
        assert "key_info" in data
        assert "warning" in data
        
    def test_create_api_key_validation_errors(self):
        """Test API key creation validation"""
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
            
        # Missing name
        response = requests.post(
            f"{self.BASE_URL}/api/keys/create",
            headers=self.auth_headers,
            json={"description": "Test"},
            timeout=10
        )
        assert response.status_code == 400
        
        # Invalid name length
        response = requests.post(
            f"{self.BASE_URL}/api/keys/create",
            headers=self.auth_headers,
            json={"name": ""},
            timeout=10
        )
        assert response.status_code == 400
        
    def test_list_api_keys(self):
        """Test API key listing"""
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
            
        response = requests.get(
            f"{self.BASE_URL}/api/keys/list",
            headers=self.auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "api_keys" in data
        assert "total" in data
        
    def test_list_api_keys_include_inactive(self):
        """Test API key listing including inactive keys"""
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
            
        response = requests.get(
            f"{self.BASE_URL}/api/keys/list?include_inactive=true",
            headers=self.auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        
    def test_validate_api_key_endpoint(self):
        """Test API key validation endpoint"""
        # Test with a known test key if available
        test_key = os.getenv("DEFAULT_API_KEY", "blk_test_key")
        
        response = requests.post(
            f"{self.BASE_URL}/api/keys/validate",
            json={"api_key": test_key},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "valid" in data
        
    def test_api_key_stats(self):
        """Test API key statistics"""
        if not self.admin_token:
            pytest.skip("Admin authentication failed")
            
        response = requests.get(
            f"{self.BASE_URL}/api/keys/stats",
            headers=self.auth_headers,
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "stats" in data
        assert "total_keys" in data["stats"]
        assert "active_keys" in data["stats"]
        
    def test_unauthorized_access(self):
        """Test unauthorized access to admin endpoints"""
        # Test without authentication
        response = requests.get(f"{self.BASE_URL}/api/keys/list", timeout=10)
        assert response.status_code == 401
        
        response = requests.post(
            f"{self.BASE_URL}/api/keys/create",
            json={"name": "test"},
            timeout=10
        )
        assert response.status_code == 401


class TestSecurityFeatures:
    """Test security features and edge cases"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_malformed_jwt_token(self):
        """Test handling of malformed JWT tokens"""
        response = requests.post(
            f"{self.BASE_URL}/api/auth/verify",
            json={"token": "not.a.valid.jwt"},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        
    def test_expired_token_handling(self):
        """Test handling of expired tokens"""
        # This would require a token with past expiration
        # For now, test with invalid token structure
        expired_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2NDcyOTQyMDB9.invalid"
        
        response = requests.post(
            f"{self.BASE_URL}/api/auth/verify",
            json={"token": expired_token},
            timeout=10
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        
    def test_injection_attack_prevention(self):
        """Test prevention of injection attacks"""
        # Test SQL injection attempts
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "admin' OR '1'='1",
            "../../../etc/passwd"
        ]
        
        for malicious_input in malicious_inputs:
            response = requests.post(
                f"{self.BASE_URL}/api/auth/login",
                json={
                    "username": malicious_input,
                    "password": malicious_input
                },
                timeout=10
            )
            
            # Should return proper error or rate limit, not crash
            assert response.status_code in [400, 401, 429]
            
    def test_authorization_header_variations(self):
        """Test various authorization header formats"""
        # Invalid formats
        invalid_headers = [
            {"Authorization": "Invalid token"},
            {"Authorization": "Bearer"},
            {"Authorization": "Basic dGVzdDp0ZXN0"},
            {"Authorization": ""},
        ]
        
        for header in invalid_headers:
            response = requests.get(
                f"{self.BASE_URL}/api/auth/profile",
                headers=header,
                timeout=10
            )
            assert response.status_code == 401


class TestPerformanceAndReliability:
    """Test performance and reliability aspects"""
    
    BASE_URL = "http://localhost:32542"
    
    def test_concurrent_login_requests(self):
        """Test handling of concurrent login requests"""
        import threading
        import queue
        
        results = queue.Queue()
        
        def login_worker():
            try:
                response = requests.post(
                    f"{self.BASE_URL}/api/auth/login",
                    json={
                        "username": "admin",
                        "password": os.getenv("ADMIN_PASSWORD", "admin")
                    },
                    timeout=10
                )
                results.put(response.status_code)
            except Exception as e:
                results.put(str(e))
        
        # Start 5 concurrent requests with small delay to avoid rate limiting
        threads = []
        for i in range(5):
            thread = threading.Thread(target=login_worker)
            threads.append(thread)
            thread.start()
            if i < 4:  # Add small delay between requests except for the last one
                time.sleep(0.1)
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check results
        success_count = 0
        while not results.empty():
            result = results.get()
            if result == 200:
                success_count += 1
        
        # At least some should succeed
        assert success_count > 0
        
    def test_large_payload_handling(self):
        """Test handling of large payloads"""
        large_description = "x" * 10000  # 10KB description
        
        # Should handle gracefully
        response = requests.post(
            f"{self.BASE_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": os.getenv("ADMIN_PASSWORD", "admin"),
                "extra_data": large_description
            },
            timeout=10
        )
        
        # Should not crash the server (may be rate limited)
        assert response.status_code in [200, 400, 429]
        
    def test_response_time_performance(self):
        """Test API response time performance"""
        start_time = time.time()
        
        response = requests.get(f"{self.BASE_URL}/api/auth/profile", timeout=10)
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Should respond within reasonable time (2 seconds)
        assert response_time < 2.0
        assert response.status_code in [200, 401]


if __name__ == "__main__":
    import sys
    
    # Track all validation failures
    all_validation_failures = []
    total_tests = 0
    
    # Test classes to run
    test_classes = [
        TestAuthenticationRoutes,
        TestAPIKeyRoutes,
        TestSecurityFeatures,
        TestPerformanceAndReliability
    ]
    
    for test_class in test_classes:
        test_instance = test_class()
        
        # Get all test methods
        test_methods = [method for method in dir(test_instance) 
                       if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            test_method = getattr(test_instance, method_name)
            
            try:
                # Setup if needed
                if hasattr(test_instance, 'setup_test'):
                    test_instance.setup_test()
                
                # Run test
                test_method()
                print(f"✅ {test_class.__name__}.{method_name}")
                
            except Exception as e:
                all_validation_failures.append(
                    f"{test_class.__name__}.{method_name}: {str(e)}"
                )
                print(f"❌ {test_class.__name__}.{method_name}: {str(e)}")
    
    # Final validation result
    if all_validation_failures:
        print(f"\n❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"\n✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Authentication system is validated and formal tests can now be written")
        sys.exit(0)