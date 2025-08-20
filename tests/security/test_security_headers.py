#!/usr/bin/env python3
"""
Security Headers Test Module

Tests for SecurityHeaders class functionality including:
- Security headers generation
- Security headers application to responses
- Error handling in header application
"""

from unittest.mock import Mock
from unittest.mock import patch

import pytest

from src.utils.security import SecurityHeaders


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

    @patch("src.utils.security.logger")
    def test_apply_security_headers_success(self, mock_logger):
        """Test applying security headers to response"""
        # Mock Flask response
        mock_response = Mock()
        mock_response.headers = {}

        result = SecurityHeaders.apply_security_headers(mock_response)

        assert result == mock_response
        assert len(mock_response.headers) > 0
        assert "X-Content-Type-Options" in mock_response.headers

    @patch("src.utils.security.logger")
    def test_apply_security_headers_with_exception(self, mock_logger):
        """Test applying security headers with exception"""
        # Mock response that raises exception
        mock_response = Mock()
        mock_response.headers = Mock(side_effect=Exception("Header error"))

        result = SecurityHeaders.apply_security_headers(mock_response)

        assert result == mock_response
        mock_logger.error.assert_called_once()
