#!/usr/bin/env python3
"""
Security Manager Test Module

Tests for SecurityManager class functionality including:
- Password hashing and verification
- JWT token generation and validation
- Rate limiting functionality
- API key generation and validation
"""

import secrets
import time
from datetime import datetime, timedelta
from unittest.mock import patch

import jwt
import pytest

from src.utils.security import SecurityManager


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
