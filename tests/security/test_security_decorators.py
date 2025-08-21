#!/usr/bin/env python3
"""
Security Decorators Test Module

Tests for security decorators including:
- require_auth decorator functionality
- rate_limit decorator functionality
- input_validation decorator functionality
- API key and permission decorators
"""

from unittest.mock import Mock, patch

import pytest

from src.utils.security import (
    SecurityManager,
    input_validation,
    rate_limit,
    require_api_key,
    require_auth,
    require_permission,
    security_check,
)


class TestSecurityDecorators:
    """Test security decorators"""

    def setup_method(self):
        """Setup test environment"""
        self.app = Mock()
        self.security_manager = SecurityManager("test_secret", "test_jwt_secret")

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
    @patch("src.utils.security.g")
    def test_require_auth_decorator_valid_jwt(
        self, mock_g, mock_request, mock_current_app
    ):
        """Test require_auth decorator with valid JWT token"""
        # Setup mocks
        mock_current_app.security_manager = self.security_manager
        mock_request.headers.get.return_value = "Bearer valid_token"

        # Mock JWT verification
        with patch.object(self.security_manager, "verify_jwt_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "roles": ["admin"]}

            @require_auth()
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"
            assert hasattr(mock_g, "current_user")

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
    def test_require_auth_decorator_no_security_manager(
        self, mock_request, mock_current_app
    ):
        """Test require_auth decorator without security manager"""
        mock_current_app.security_manager = None

        @require_auth()
        def test_function():
            return "success"

        result, status_code = test_function()
        assert status_code == 500
        assert result["error"] == "Security not configured"

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
    def test_require_auth_decorator_invalid_token(self, mock_request, mock_current_app):
        """Test require_auth decorator with invalid token"""
        mock_current_app.security_manager = self.security_manager
        mock_request.headers.get.return_value = "Bearer invalid_token"

        with patch.object(self.security_manager, "verify_jwt_token") as mock_verify:
            mock_verify.return_value = None

            @require_auth()
            def test_function():
                return "success"

            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "Authentication required"

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
    def test_require_auth_decorator_insufficient_roles(
        self, mock_request, mock_current_app
    ):
        """Test require_auth decorator with insufficient roles"""
        mock_current_app.security_manager = self.security_manager
        mock_request.headers.get.return_value = "Bearer valid_token"

        with patch.object(self.security_manager, "verify_jwt_token") as mock_verify:
            mock_verify.return_value = {"user_id": "test_user", "roles": ["user"]}

            @require_auth(roles=["admin"])
            def test_function():
                return "success"

            result, status_code = test_function()
            assert status_code == 403
            assert result["error"] == "Insufficient permissions"

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
    def test_rate_limit_decorator_under_limit(self, mock_request, mock_current_app):
        """Test rate_limit decorator under limit"""
        mock_current_app.security_manager = self.security_manager
        mock_request.remote_addr = "192.168.1.1"

        @rate_limit(limit=10, window_seconds=3600)
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
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

    @patch("src.utils.security.current_app")
    @patch("src.utils.security.request")
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

    @patch("src.utils.security.request")
    def test_input_validation_decorator_valid_data(self, mock_request):
        """Test input_validation decorator with valid data"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {"name": "test_user", "age": 25}

        schema = {
            "name": {"required": True, "type": str, "min_length": 3, "max_length": 50},
            "age": {"required": True, "type": int},
        }

        @input_validation(schema)
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    @patch("src.utils.security.request")
    def test_input_validation_decorator_missing_field(self, mock_request):
        """Test input_validation decorator with missing required field"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {"age": 25}

        schema = {
            "name": {"required": True, "type": str},
            "age": {"required": True, "type": int},
        }

        @input_validation(schema)
        def test_function():
            return "success"

        result, status_code = test_function()
        assert status_code == 400
        assert "Missing required field: name" in result["error"]

    @patch("src.utils.security.request")
    def test_input_validation_decorator_invalid_type(self, mock_request):
        """Test input_validation decorator with invalid type"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "name": 123,  # Should be string
            "age": 25,
        }

        schema = {
            "name": {"required": True, "type": str},
            "age": {"required": True, "type": int},
        }

        @input_validation(schema)
        def test_function():
            return "success"

        result, status_code = test_function()
        assert status_code == 400
        assert "Invalid type for name" in result["error"]

    @patch("src.utils.security.request")
    def test_input_validation_decorator_invalid_length(self, mock_request):
        """Test input_validation decorator with invalid length"""
        mock_request.is_json = True
        mock_request.get_json.return_value = {"name": "ab", "age": 25}  # Too short

        schema = {
            "name": {"required": True, "type": str, "min_length": 3},
            "age": {"required": True, "type": int},
        }

        @input_validation(schema)
        def test_function():
            return "success"

        result, status_code = test_function()
        assert status_code == 400
        assert "Invalid length for name" in result["error"]

    def test_require_api_key_decorator_valid_key(self):
        """Test require_api_key decorator with valid key"""
        with patch("src.utils.security.request") as mock_request:
            mock_request.headers.get.return_value = (
                "ak_1234567890123456789012345678901234567890"
            )

            @require_api_key
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"

    def test_require_api_key_decorator_missing_key(self):
        """Test require_api_key decorator with missing key"""
        with patch("src.utils.security.request") as mock_request:
            mock_request.headers.get.return_value = None

            @require_api_key
            def test_function():
                return "success"

            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "API key required"

    def test_require_api_key_decorator_invalid_key(self):
        """Test require_api_key decorator with invalid key"""
        with patch("src.utils.security.request") as mock_request:
            mock_request.headers.get.return_value = "invalid_key"

            @require_api_key
            def test_function():
                return "success"

            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "Invalid API key"

    def test_require_permission_decorator_with_permission(self):
        """Test require_permission decorator with required permission"""
        with patch("src.utils.security.g") as mock_g:
            mock_g.current_user = {"roles": ["admin", "read"]}

            @require_permission("read")
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"

    def test_require_permission_decorator_admin_override(self):
        """Test require_permission decorator with admin role override"""
        with patch("src.utils.security.g") as mock_g:
            mock_g.current_user = {"roles": ["admin"]}

            @require_permission("special_permission")
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"

    def test_require_permission_decorator_insufficient_permission(self):
        """Test require_permission decorator without required permission"""
        with patch("src.utils.security.g") as mock_g:
            mock_g.current_user = {"roles": ["user"]}

            @require_permission("admin")
            def test_function():
                return "success"

            result, status_code = test_function()
            assert status_code == 403
            assert result["error"] == "Insufficient permissions"

    def test_require_permission_decorator_no_user(self):
        """Test require_permission decorator without authenticated user"""
        with patch("src.utils.security.g") as mock_g:
            mock_g.current_user = None

            @require_permission("read")
            def test_function():
                return "success"

            result, status_code = test_function()
            assert status_code == 401
            assert result["error"] == "Authentication required"

    def test_security_check_decorator_normal_request(self):
        """Test security_check decorator with normal request"""
        with patch("src.utils.security.request") as mock_request:
            mock_request.headers.get.return_value = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )

            @security_check
            def test_function():
                return "success"

            result = test_function()
            assert result == "success"

    def test_security_check_decorator_malicious_user_agent(self):
        """Test security_check decorator with malicious user agent"""
        malicious_agents = ["sqlmap/1.0", "nmap scanner", "nikto/2.1"]

        for agent in malicious_agents:
            with patch("src.utils.security.request") as mock_request:
                mock_request.headers.get.return_value = agent

                @security_check
                def test_function():
                    return "success"

                result, status_code = test_function()
                assert status_code == 403
                assert result["error"] == "Request blocked"
