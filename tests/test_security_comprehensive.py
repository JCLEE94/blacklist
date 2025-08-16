#!/usr/bin/env python3
"""
Comprehensive Security Module Test Suite

Tests all critical security features including:
- JWT token management and validation
- API key generation and verification
- Password hashing and security utilities
- Rate limiting and security middleware
- Authentication decorators and middleware
- Security headers and CSRF protection
"""

import hashlib
import json
import secrets
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import jwt
import pytest

# Test imports
from src.utils.security import (
    SecurityHeaders,
    SecurityManager,
    generate_csrf_token,
    get_security_manager,
    input_validation,
    rate_limit,
    require_api_key,
    require_auth,
    require_permission,
    sanitize_input,
    security_check,
    setup_security,
    validate_csrf_token,
)


class TestSecurityManager:
    """Test SecurityManager class functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.secret_key = "test_secret_key_123"
        self.jwt_secret = "test_jwt_secret_456"
        self.security_manager = SecurityManager(self.secret_key, self.jwt_secret)

    def test_initialization(self):
        """Test SecurityManager initialization"""
        assert self.security_manager.secret_key == self.secret_key
        assert self.security_manager.jwt_secret == self.jwt_secret
        assert isinstance(self.security_manager.rate_limits, dict)
        assert isinstance(self.security_manager.blocked_ips, set)
        assert isinstance(self.security_manager.failed_attempts, dict)

    def test_initialization_with_default_jwt_secret(self):
        """Test SecurityManager initialization with default JWT secret"""
        manager = SecurityManager("test_secret")
        assert manager.secret_key == "test_secret"
        assert manager.jwt_secret == "test_secret"

    def test_hash_password_with_salt(self):
        """Test password hashing with provided salt"""
        password = "test_password_123"
        salt = "test_salt"
        
        password_hash, returned_salt = self.security_manager.hash_password(password, salt)
        
        assert returned_salt == salt
        assert len(password_hash) > 0
        assert isinstance(password_hash, str)

    def test_hash_password_without_salt(self):
        """Test password hashing with auto-generated salt"""
        password = "test_password_123"
        
        password_hash, salt = self.security_manager.hash_password(password)
        
        assert len(salt) == 64  # 32 bytes hex = 64 chars
        assert len(password_hash) > 0
        assert isinstance(password_hash, str)

    def test_hash_password_consistency(self):
        """Test password hashing consistency"""
        password = "test_password_123"
        salt = "consistent_salt"
        
        hash1, _ = self.security_manager.hash_password(password, salt)
        hash2, _ = self.security_manager.hash_password(password, salt)
        
        assert hash1 == hash2

    def test_hash_password_different_salts(self):
        """Test password hashing with different salts produces different hashes"""
        password = "test_password_123"
        salt1 = "salt_one"
        salt2 = "salt_two"
        
        hash1, _ = self.security_manager.hash_password(password, salt1)
        hash2, _ = self.security_manager.hash_password(password, salt2)
        
        assert hash1 != hash2

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "test_password_123"
        password_hash, salt = self.security_manager.hash_password(password)
        
        result = self.security_manager.verify_password(password, password_hash, salt)
        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "test_password_123"
        wrong_password = "wrong_password"
        password_hash, salt = self.security_manager.hash_password(password)
        
        result = self.security_manager.verify_password(wrong_password, password_hash, salt)
        assert result is False

    def test_verify_password_with_exception(self):
        """Test password verification error handling"""
        with patch.object(self.security_manager, 'hash_password', side_effect=Exception("Hash error")):
            result = self.security_manager.verify_password("password", "hash", "salt")
            assert result is False

    def test_generate_jwt_token_basic(self):
        """Test basic JWT token generation"""
        user_id = "test_user_123"
        token = self.security_manager.generate_jwt_token(user_id)
        
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode to verify content
        payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        assert payload["user_id"] == user_id
        assert payload["roles"] == []

    def test_generate_jwt_token_with_roles(self):
        """Test JWT token generation with roles"""
        user_id = "test_user_123"
        roles = ["admin", "user"]
        token = self.security_manager.generate_jwt_token(user_id, roles)
        
        payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        assert payload["user_id"] == user_id
        assert payload["roles"] == roles

    def test_generate_jwt_token_with_custom_expiry(self):
        """Test JWT token generation with custom expiry"""
        user_id = "test_user_123"
        expires_hours = 1
        token = self.security_manager.generate_jwt_token(user_id, expires_hours=expires_hours)
        
        payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
        
        # Check expiry time is approximately 1 hour from now
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = datetime.utcnow() + timedelta(hours=expires_hours)
        time_diff = abs((exp_time - expected_exp).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_verify_jwt_token_valid(self):
        """Test JWT token verification with valid token"""
        user_id = "test_user_123"
        roles = ["admin"]
        token = self.security_manager.generate_jwt_token(user_id, roles)
        
        payload = self.security_manager.verify_jwt_token(token)
        
        assert payload is not None
        assert payload["user_id"] == user_id
        assert payload["roles"] == roles

    def test_verify_jwt_token_invalid(self):
        """Test JWT token verification with invalid token"""
        invalid_token = "invalid.jwt.token"
        
        payload = self.security_manager.verify_jwt_token(invalid_token)
        assert payload is None

    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token"""
        # Create expired token
        expired_payload = {
            "user_id": "test_user",
            "exp": datetime.utcnow() - timedelta(hours=1)  # 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, self.jwt_secret, algorithm="HS256")
        
        payload = self.security_manager.verify_jwt_token(expired_token)
        assert payload is None

    def test_verify_jwt_token_wrong_secret(self):
        """Test JWT token verification with wrong secret"""
        # Create token with different secret
        payload = {"user_id": "test_user", "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        result = self.security_manager.verify_jwt_token(token)
        assert result is None

    def test_check_rate_limit_under_limit(self):
        """Test rate limiting under the limit"""
        identifier = "test_ip_123"
        limit = 5
        
        # Make requests under the limit
        for i in range(limit):
            result = self.security_manager.check_rate_limit(identifier, limit)
            assert result is True

    def test_check_rate_limit_over_limit(self):
        """Test rate limiting over the limit"""
        identifier = "test_ip_456"
        limit = 3
        
        # Make requests up to the limit
        for i in range(limit):
            self.security_manager.check_rate_limit(identifier, limit)
        
        # Next request should be rejected
        result = self.security_manager.check_rate_limit(identifier, limit)
        assert result is False

    def test_check_rate_limit_window_reset(self):
        """Test rate limiting window reset"""
        identifier = "test_ip_789"
        limit = 2
        window_seconds = 1
        
        # Make requests up to limit
        for i in range(limit):
            self.security_manager.check_rate_limit(identifier, limit, window_seconds)
        
        # Should be rejected
        assert self.security_manager.check_rate_limit(identifier, limit, window_seconds) is False
        
        # Wait for window to reset
        time.sleep(1.1)
        
        # Should be allowed again
        result = self.security_manager.check_rate_limit(identifier, limit, window_seconds)
        assert result is True

    def test_record_failed_attempt_under_limit(self):
        """Test recording failed attempts under limit"""
        identifier = "test_user_123"
        max_attempts = 3
        
        # Record attempts under limit
        for i in range(max_attempts - 1):
            result = self.security_manager.record_failed_attempt(identifier, max_attempts)
            assert result is True
            assert identifier not in self.security_manager.blocked_ips

    def test_record_failed_attempt_over_limit(self):
        """Test recording failed attempts over limit"""
        identifier = "test_user_456"
        max_attempts = 3
        
        # Record attempts up to limit
        for i in range(max_attempts):
            self.security_manager.record_failed_attempt(identifier, max_attempts)
        
        # Should be blocked
        assert identifier in self.security_manager.blocked_ips
        assert self.security_manager.is_blocked(identifier) is True

    def test_record_failed_attempt_reset_after_timeout(self):
        """Test failed attempt counter reset after timeout"""
        identifier = "test_user_789"
        max_attempts = 2
        lockout_minutes = 0.01  # Very short lockout for testing
        
        # Record attempts up to limit
        for i in range(max_attempts):
            self.security_manager.record_failed_attempt(identifier, max_attempts, lockout_minutes)
        
        # Should be blocked
        assert identifier in self.security_manager.blocked_ips
        
        # Wait for lockout to expire
        time.sleep(0.6)  # 0.01 minutes = 0.6 seconds
        
        # Next attempt should reset counter
        result = self.security_manager.record_failed_attempt(identifier, max_attempts, lockout_minutes)
        assert result is True

    def test_is_blocked(self):
        """Test blocked status checking"""
        identifier = "test_blocked_ip"
        
        # Initially not blocked
        assert self.security_manager.is_blocked(identifier) is False
        
        # Add to blocked list
        self.security_manager.blocked_ips.add(identifier)
        
        # Should be blocked
        assert self.security_manager.is_blocked(identifier) is True

    def test_unblock(self):
        """Test unblocking functionality"""
        identifier = "test_blocked_ip"
        
        # Block the identifier
        self.security_manager.blocked_ips.add(identifier)
        self.security_manager.failed_attempts[identifier] = {"count": 5, "last_attempt": time.time()}
        
        assert self.security_manager.is_blocked(identifier) is True
        
        # Unblock
        self.security_manager.unblock(identifier)
        
        assert self.security_manager.is_blocked(identifier) is False
        assert identifier not in self.security_manager.failed_attempts

    def test_generate_api_key_default_prefix(self):
        """Test API key generation with default prefix"""
        api_key = self.security_manager.generate_api_key()
        
        assert api_key.startswith("ak_")
        assert len(api_key) > 35  # ak_ + 32+ chars
        
        # Should be different each time
        api_key2 = self.security_manager.generate_api_key()
        assert api_key != api_key2

    def test_generate_api_key_custom_prefix(self):
        """Test API key generation with custom prefix"""
        custom_prefix = "custom"
        api_key = self.security_manager.generate_api_key(custom_prefix)
        
        assert api_key.startswith(f"{custom_prefix}_")
        assert len(api_key) > len(custom_prefix) + 35

    def test_validate_api_key_format_valid(self):
        """Test API key format validation with valid keys"""
        valid_keys = [
            "ak_" + secrets.token_urlsafe(32),
            "custom_" + secrets.token_urlsafe(40),
            "test_1234567890123456789012345678901234567890"
        ]
        
        for key in valid_keys:
            assert self.security_manager.validate_api_key_format(key) is True

    def test_validate_api_key_format_invalid(self):
        """Test API key format validation with invalid keys"""
        invalid_keys = [
            "no_underscore",
            "short_key",
            "ak_",
            "ak_short",
            "",
            None,
            123
        ]
        
        for key in invalid_keys:
            assert self.security_manager.validate_api_key_format(key) is False


class TestSecurityHeaders:
    """Test SecurityHeaders class"""

    def test_get_security_headers(self):
        """Test security headers generation"""
        headers = SecurityHeaders.get_security_headers()
        
        assert isinstance(headers, dict)
        assert "X-Content-Type-Options" in headers
        assert "X-Frame-Options" in headers
        assert "X-XSS-Protection" in headers
        assert "Strict-Transport-Security" in headers
        assert "Content-Security-Policy" in headers
        assert "Referrer-Policy" in headers
        assert "Permissions-Policy" in headers

    def test_security_headers_values(self):
        """Test security headers have correct values"""
        headers = SecurityHeaders.get_security_headers()
        
        assert headers["X-Content-Type-Options"] == "nosnif"
        assert headers["X-Frame-Options"] == "DENY"
        assert headers["X-XSS-Protection"] == "1; mode=block"
        assert "max-age=31536000" in headers["Strict-Transport-Security"]

    @patch('src.utils.security.logger')
    def test_apply_security_headers_success(self, mock_logger):
        """Test applying security headers to response"""
        # Mock Flask response
        mock_response = Mock()
        mock_response.headers = {}
        
        result = SecurityHeaders.apply_security_headers(mock_response)
        
        assert result == mock_response
        assert len(mock_response.headers) > 0
        assert "X-Content-Type-Options" in mock_response.headers

    @patch('src.utils.security.logger')
    def test_apply_security_headers_with_exception(self, mock_logger):
        """Test applying security headers with exception"""
        # Mock response that raises exception
        mock_response = Mock()
        mock_response.headers = Mock(side_effect=Exception("Header error"))
        
        result = SecurityHeaders.apply_security_headers(mock_response)
        
        assert result == mock_response
        mock_logger.error.assert_called_once()


class TestSecurityDecorators:
    """Test security decorators"""

    def setup_method(self):
        """Setup test environment"""
        self.app = Mock()
        self.security_manager = SecurityManager("test_secret", "test_jwt_secret")

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    @patch('src.utils.security.g')
    def test_require_auth_decorator_valid_jwt(self, mock_g, mock_request, mock_current_app):
        """Test require_auth decorator with valid JWT token"""
        # Setup mocks
        mock_current_app.security_manager = self.security_manager
        mock_request.headers.get.return_value = "Bearer valid_token"
        
        # Mock JWT verification
        with patch.object(self.security_manager, 'verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "roles": ["admin"]}
            
            @require_auth()
            def test_function():
                return "success"
            
            result = test_function()
            assert result == "success"
            assert hasattr(mock_g, 'current_user')

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    def test_require_auth_decorator_no_security_manager(self, mock_request, mock_current_app):
        """Test require_auth decorator without security manager"""
        mock_current_app.security_manager = None
        
        @require_auth()
        def test_function():
            return "success"
        
        result, status_code = test_function()
        assert status_code == 500
        assert result["error"] == "Security not configured"

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    def test_require_auth_decorator_invalid_token(self, mock_request, mock_current_app):
        """Test require_auth decorator with invalid token"""
        mock_current_app.security_manager = self.security_manager
        mock_request.headers.get.return_value = "Bearer invalid_token"
        
        with patch.object(self.security_manager, 'verify_jwt_token') as mock_verify:
            mock_verify.return_value = None
            
            @require_auth()
            def test_function():
                return "success"
            
            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "Authentication required"

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    def test_require_auth_decorator_insufficient_roles(self, mock_request, mock_current_app):
        """Test require_auth decorator with insufficient roles"""
        mock_current_app.security_manager = self.security_manager
        mock_request.headers.get.return_value = "Bearer valid_token"
        
        with patch.object(self.security_manager, 'verify_jwt_token') as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "roles": ["user"]}
            
            @require_auth(roles=["admin"])
            def test_function():
                return "success"
            
            result, status_code = test_function()
            assert status_code == 403
            assert result["error"] == "Insufficient permissions"

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    def test_rate_limit_decorator_under_limit(self, mock_request, mock_current_app):
        """Test rate_limit decorator under limit"""
        mock_current_app.security_manager = self.security_manager
        mock_request.remote_addr = "192.168.1.1"
        
        @rate_limit(limit=10, window_seconds=3600)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    def test_rate_limit_decorator_over_limit(self, mock_request, mock_current_app):
        """Test rate_limit decorator over limit"""
        mock_current_app.security_manager = self.security_manager
        mock_request.remote_addr = "192.168.1.1"
        
        # Fill up rate limit
        for _ in range(10):
            self.security_manager.check_rate_limit("192.168.1.1", 2, 3600)
        
        @rate_limit(limit=2, window_seconds=3600)
        def test_function():
            return "success"
        
        result, status_code = test_function()
        assert status_code == 429
        assert result["error"] == "Rate limit exceeded"

    @patch('src.utils.security.current_app')
    @patch('src.utils.security.request')
    def test_rate_limit_decorator_blocked_ip(self, mock_request, mock_current_app):
        """Test rate_limit decorator with blocked IP"""
        mock_current_app.security_manager = self.security_manager
        mock_request.remote_addr = "192.168.1.1"
        
        # Block the IP
        self.security_manager.blocked_ips.add("192.168.1.1")
        
        @rate_limit(limit=10, window_seconds=3600)
        def test_function():
            return "success"
        
        result, status_code = test_function()
        assert status_code == 429
        assert result["error"] == "IP blocked due to abuse"

    @patch('src.utils.security.request')
    def test_input_validation_decorator_valid_data(self, mock_request):
        """Test input_validation decorator with valid data"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "name": "test_user",
            "age": 25
        }
        
        schema = {
            "name": {"required": True, "type": str, "min_length": 3, "max_length": 50},
            "age": {"required": True, "type": int}
        }
        
        @input_validation(schema)
        def test_function():
            return "success"
        
        result = test_function()
        assert result == "success"

    @patch('src.utils.security.request')
    def test_input_validation_decorator_missing_field(self, mock_request):
        """Test input_validation decorator with missing required field"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "age": 25
        }
        
        schema = {
            "name": {"required": True, "type": str},
            "age": {"required": True, "type": int}
        }
        
        @input_validation(schema)
        def test_function():
            return "success"
        
        result, status_code = test_function()
        assert status_code == 400
        assert "Missing required field: name" in result["error"]

    @patch('src.utils.security.request')
    def test_input_validation_decorator_invalid_type(self, mock_request):
        """Test input_validation decorator with invalid type"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "name": 123,  # Should be string
            "age": 25
        }
        
        schema = {
            "name": {"required": True, "type": str},
            "age": {"required": True, "type": int}
        }
        
        @input_validation(schema)
        def test_function():
            return "success"
        
        result, status_code = test_function()
        assert status_code == 400
        assert "Invalid type for name" in result["error"]

    @patch('src.utils.security.request')
    def test_input_validation_decorator_invalid_length(self, mock_request):
        """Test input_validation decorator with invalid length"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "name": "ab",  # Too short
            "age": 25
        }
        
        schema = {
            "name": {"required": True, "type": str, "min_length": 3},
            "age": {"required": True, "type": int}
        }
        
        @input_validation(schema)
        def test_function():
            return "success"
        
        result, status_code = test_function()
        assert status_code == 400
        assert "Invalid length for name" in result["error"]


class TestSecurityUtilities:
    """Test security utility functions"""

    def test_sanitize_input_normal_string(self):
        """Test input sanitization with normal string"""
        input_str = "Hello World 123"
        result = sanitize_input(input_str)
        assert result == "Hello World 123"

    def test_sanitize_input_dangerous_characters(self):
        """Test input sanitization with dangerous characters"""
        input_str = "<script>alert('xss')</script>"
        result = sanitize_input(input_str)
        assert "<" not in result
        assert ">" not in result
        assert result == "scriptalert('xss')/script"

    def test_sanitize_input_length_limit(self):
        """Test input sanitization with length limit"""
        input_str = "a" * 2000
        result = sanitize_input(input_str, max_length=100)
        assert len(result) == 100

    def test_sanitize_input_non_string(self):
        """Test input sanitization with non-string input"""
        result = sanitize_input(123)
        assert result == ""
        
        result = sanitize_input(None)
        assert result == ""

    def test_generate_csrf_token(self):
        """Test CSRF token generation"""
        token = generate_csrf_token()
        
        assert isinstance(token, str)
        assert len(token) > 30  # URL-safe base64 token should be reasonably long
        
        # Should be different each time
        token2 = generate_csrf_token()
        assert token != token2

    def test_validate_csrf_token_valid(self):
        """Test CSRF token validation with valid tokens"""
        token = generate_csrf_token()
        result = validate_csrf_token(token, token)
        assert result is True

    def test_validate_csrf_token_invalid(self):
        """Test CSRF token validation with invalid tokens"""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()
        
        result = validate_csrf_token(token1, token2)
        assert result is False

    def test_validate_csrf_token_with_exception(self):
        """Test CSRF token validation with exception"""
        # Passing non-strings to cause comparison error
        result = validate_csrf_token(None, "token")
        assert result is False

    def test_get_security_manager_singleton(self):
        """Test security manager singleton pattern"""
        manager1 = get_security_manager("secret1", "jwt_secret1")
        manager2 = get_security_manager("secret2", "jwt_secret2")
        
        # Should return the same instance
        assert manager1 is manager2
        assert manager1.secret_key == "secret1"  # First call's values

    def test_get_security_manager_none_when_no_secret(self):
        """Test security manager returns None when no secret provided"""
        global _security_manager
        original = _security_manager
        _security_manager = None
        
        try:
            manager = get_security_manager()
            assert manager is None
        finally:
            _security_manager = original

    def test_require_api_key_decorator_valid_key(self):
        """Test require_api_key decorator with valid key"""
        with patch('src.utils.security.request') as mock_request:
            mock_request.headers.get.return_value = "ak_1234567890123456789012345678901234567890"
            
            @require_api_key
            def test_function():
                return "success"
            
            result = test_function()
            assert result == "success"

    def test_require_api_key_decorator_missing_key(self):
        """Test require_api_key decorator with missing key"""
        with patch('src.utils.security.request') as mock_request:
            mock_request.headers.get.return_value = None
            
            @require_api_key
            def test_function():
                return "success"
            
            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "API key required"

    def test_require_api_key_decorator_invalid_key(self):
        """Test require_api_key decorator with invalid key"""
        with patch('src.utils.security.request') as mock_request:
            mock_request.headers.get.return_value = "invalid_key"
            
            @require_api_key
            def test_function():
                return "success"
            
            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "Invalid API key"

    def test_require_permission_decorator_with_permission(self):
        """Test require_permission decorator with required permission"""
        with patch('src.utils.security.g') as mock_g:
            mock_g.current_user = {"roles": ["admin", "read"]}
            
            @require_permission("read")
            def test_function():
                return "success"
            
            result = test_function()
            assert result == "success"

    def test_require_permission_decorator_admin_override(self):
        """Test require_permission decorator with admin role override"""
        with patch('src.utils.security.g') as mock_g:
            mock_g.current_user = {"roles": ["admin"]}
            
            @require_permission("special_permission")
            def test_function():
                return "success"
            
            result = test_function()
            assert result == "success"

    def test_require_permission_decorator_insufficient_permission(self):
        """Test require_permission decorator without required permission"""
        with patch('src.utils.security.g') as mock_g:
            mock_g.current_user = {"roles": ["user"]}
            
            @require_permission("admin")
            def test_function():
                return "success"
            
            result, status_code = test_function()
            assert status_code == 403
            assert result["error"] == "Insufficient permissions"

    def test_require_permission_decorator_no_user(self):
        """Test require_permission decorator without authenticated user"""
        with patch('src.utils.security.g') as mock_g:
            mock_g.current_user = None
            
            @require_permission("read")
            def test_function():
                return "success"
            
            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "Authentication required"

    def test_security_check_decorator_normal_request(self):
        """Test security_check decorator with normal request"""
        with patch('src.utils.security.request') as mock_request:
            mock_request.headers.get.return_value = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            
            @security_check
            def test_function():
                return "success"
            
            result = test_function()
            assert result == "success"

    def test_security_check_decorator_malicious_user_agent(self):
        """Test security_check decorator with malicious user agent"""
        malicious_agents = ["sqlmap/1.0", "nmap scanner", "nikto/2.1"]
        
        for agent in malicious_agents:
            with patch('src.utils.security.request') as mock_request:
                mock_request.headers.get.return_value = agent
                
                @security_check
                def test_function():
                    return "success"
                
                result, status_code = test_function()
                assert status_code == 403
                assert result["error"] == "Request blocked"

    def test_setup_security_success(self):
        """Test security setup for Flask application"""
        mock_app = Mock()
        mock_app.after_request = Mock()
        
        result = setup_security(mock_app, "secret_key", "jwt_secret")
        
        assert result is True
        assert hasattr(mock_app, 'security_manager')
        assert isinstance(mock_app.security_manager, SecurityManager)
        mock_app.after_request.assert_called_once()

    @patch('src.utils.security.logger')
    def test_setup_security_failure(self, mock_logger):
        """Test security setup failure"""
        mock_app = Mock()
        mock_app.after_request = Mock(side_effect=Exception("Setup error"))
        
        result = setup_security(mock_app, "secret_key", "jwt_secret")
        
        assert result is False
        mock_logger.error.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])