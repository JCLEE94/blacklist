#!/usr/bin/env python3
"""
Security Utilities Test Module

Tests for security utility functions including:
- Input sanitization
- CSRF token generation and validation
- Security manager singleton
- Security setup functionality
"""

from unittest.mock import Mock, patch

import pytest

from src.utils.security import (
    SecurityManager,
    generate_csrf_token,
    get_security_manager,
    sanitize_input,
    setup_security,
    validate_csrf_token,
)


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
        # URL-safe base64 token should be reasonably long
        assert len(token) > 30

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

    def test_setup_security_success(self):
        """Test security setup for Flask application"""
        mock_app = Mock()
        mock_app.after_request = Mock()

        result = setup_security(mock_app, "secret_key", "jwt_secret")

        assert result is True
        assert hasattr(mock_app, "security_manager")
        assert isinstance(mock_app.security_manager, SecurityManager)
        mock_app.after_request.assert_called_once()

    @patch("src.utils.security.logger")
    def test_setup_security_failure(self, mock_logger):
        """Test security setup failure"""
        mock_app = Mock()
        mock_app.after_request = Mock(side_effect=Exception("Setup error"))

        result = setup_security(mock_app, "secret_key", "jwt_secret")

        assert result is False
        mock_logger.error.assert_called_once()
