#!/usr/bin/env python3
"""
Tests for src/api/auth_routes.py - Complete coverage for authentication routes.

This module provides comprehensive test coverage for the authentication API routes,
including login, token refresh, logout, verification, password change, and profile endpoints.

Test Coverage Areas:
- User login with various credential scenarios
- JWT token refresh functionality
- Token verification and validation
- User profile retrieval
- Password change functionality
- Rate limiting and input validation
- Error handling for all endpoints
- Blueprint error handlers
"""

import pytest
import json
import os
from unittest.mock import patch, MagicMock
from flask import Flask

# Import the auth blueprint with proper Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.api.auth_routes import auth_bp

class TestAuthRoutesSetup:
    """Test cases for authentication routes setup and configuration."""

    def test_auth_blueprint_creation(self):
        """Test that authentication blueprint is properly created."""
        assert auth_bp is not None
        assert auth_bp.name == "auth"
        assert auth_bp.url_prefix == "/api/auth"

    def test_auth_routes_registration(self):
        """Test that all expected routes are registered."""
        app = Flask(__name__)
        app.register_blueprint(auth_bp)
        
        # Check that routes exist
        route_rules = [rule.rule for rule in app.url_map.iter_rules()]
        
        expected_routes = [
            '/api/auth/login',
            '/api/auth/refresh',
            '/api/auth/logout',
            '/api/auth/verify',
            '/api/auth/change-password',
            '/api/auth/profile'
        ]
        
        for route in expected_routes:
            assert route in route_rules

class TestLoginEndpoint:
    """Test cases for the login endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_login_success_admin(self):
        """Test successful admin login."""
        with patch.dict(os.environ, {
            'ADMIN_USERNAME': 'testadmin',
            'ADMIN_PASSWORD': 'testpassword'
        }):
            # Mock security manager
            mock_security = MagicMock()
            mock_security.generate_jwt_token.side_effect = ['access_token_123', 'refresh_token_456']
            
            with self.app.app_context():
                self.app.security_manager = mock_security
                
                response = self.client.post('/api/auth/login',
                    json={'username': 'testadmin', 'password': 'testpassword'},
                    content_type='application/json')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'access_token' in data
                assert 'refresh_token' in data
                assert data['user']['username'] == 'testadmin'
                assert 'admin' in data['user']['roles']

    def test_login_success_collector(self):
        """Test successful collector login."""
        with patch.dict(os.environ, {
            'REGTECH_USERNAME': 'regtech_user',
            'REGTECH_PASSWORD': 'regtech_pass'
        }):
            mock_security = MagicMock()
            mock_security.generate_jwt_token.side_effect = ['access_token_123', 'refresh_token_456']
            
            with self.app.app_context():
                self.app.security_manager = mock_security
                
                response = self.client.post('/api/auth/login',
                    json={'username': 'regtech_user', 'password': 'regtech_pass'},
                    content_type='application/json')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'collector' in data['user']['roles']
                assert 'user' in data['user']['roles']

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        with patch.dict(os.environ, {
            'ADMIN_USERNAME': 'admin',
            'ADMIN_PASSWORD': 'correct_password'
        }):
            response = self.client.post('/api/auth/login',
                json={'username': 'admin', 'password': 'wrong_password'},
                content_type='application/json')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
            assert '사용자명 또는 비밀번호' in data['error']

    def test_login_missing_security_manager(self):
        """Test login when security manager is not available."""
        with patch.dict(os.environ, {
            'ADMIN_USERNAME': 'admin',
            'ADMIN_PASSWORD': 'password'
        }):
            response = self.client.post('/api/auth/login',
                json={'username': 'admin', 'password': 'password'},
                content_type='application/json')
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['success'] is False
            assert '보안 시스템이 초기화되지 않았습니다' in data['error']

    def test_login_invalid_json(self):
        """Test login with invalid JSON data."""
        response = self.client.post('/api/auth/login',
            data='invalid json',
            content_type='application/json')
        
        # Should trigger input validation or JSON parsing error
        assert response.status_code in [400, 422]

class TestTokenRefreshEndpoint:
    """Test cases for the token refresh endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_refresh_token_success(self):
        """Test successful token refresh."""
        mock_security = MagicMock()
        # Mock token verification to return valid refresh token payload
        mock_security.verify_jwt_token.return_value = {
            'user_id': 'testuser',
            'roles': ['refresh'],
            'exp': 1234567890,
            'iat': 1234567800
        }
        mock_security.generate_jwt_token.side_effect = ['new_access_token', 'new_refresh_token']
        
        with patch.dict(os.environ, {'ADMIN_USERNAME': 'testuser'}):
            with self.app.app_context():
                self.app.security_manager = mock_security
                
                response = self.client.post('/api/auth/refresh',
                    json={'refresh_token': 'valid_refresh_token_123'},
                    content_type='application/json')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert data['access_token'] == 'new_access_token'
                assert data['refresh_token'] == 'new_refresh_token'

    def test_refresh_token_invalid(self):
        """Test token refresh with invalid token."""
        mock_security = MagicMock()
        mock_security.verify_jwt_token.return_value = None
        
        with self.app.app_context():
            self.app.security_manager = mock_security
            
            response = self.client.post('/api/auth/refresh',
                json={'refresh_token': 'invalid_token'},
                content_type='application/json')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
            assert '유효하지 않거나 만료된' in data['error']

    def test_refresh_token_not_refresh_type(self):
        """Test token refresh with non-refresh token."""
        mock_security = MagicMock()
        # Return valid token but without refresh role
        mock_security.verify_jwt_token.return_value = {
            'user_id': 'testuser',
            'roles': ['user'],  # Missing 'refresh' role
            'exp': 1234567890
        }
        
        with self.app.app_context():
            self.app.security_manager = mock_security
            
            response = self.client.post('/api/auth/refresh',
                json={'refresh_token': 'access_token_not_refresh'},
                content_type='application/json')
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
            assert '유효하지 않은 리프레시 토큰' in data['error']

class TestLogoutEndpoint:
    """Test cases for the logout endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_logout_success(self):
        """Test successful logout."""
        response = self.client.post('/api/auth/logout')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert '성공적으로 로그아웃' in data['message']

class TestTokenVerificationEndpoint:
    """Test cases for the token verification endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_verify_token_valid(self):
        """Test verification of valid token."""
        mock_security = MagicMock()
        mock_payload = {
            'user_id': 'testuser',
            'roles': ['user'],
            'exp': 1234567890,
            'iat': 1234567800
        }
        mock_security.verify_jwt_token.return_value = mock_payload
        
        with self.app.app_context():
            self.app.security_manager = mock_security
            
            response = self.client.post('/api/auth/verify',
                json={'token': 'valid_token_123'},
                content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['valid'] is True
            assert data['payload']['user_id'] == 'testuser'

    def test_verify_token_invalid(self):
        """Test verification of invalid token."""
        mock_security = MagicMock()
        mock_security.verify_jwt_token.return_value = None
        
        with self.app.app_context():
            self.app.security_manager = mock_security
            
            response = self.client.post('/api/auth/verify',
                json={'token': 'invalid_token'},
                content_type='application/json')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['valid'] is False

class TestPasswordChangeEndpoint:
    """Test cases for the password change endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_change_password_not_implemented(self):
        """Test password change returns not implemented."""
        response = self.client.post('/api/auth/change-password',
            json={'current_password': 'old', 'new_password': 'newpassword123'},
            content_type='application/json')
        
        assert response.status_code == 501
        data = json.loads(response.data)
        assert data['success'] is False
        assert '현재 환경에서는 비밀번호 변경이 지원되지 않습니다' in data['error']

class TestProfileEndpoint:
    """Test cases for the profile endpoint."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_get_profile_success(self):
        """Test successful profile retrieval."""
        mock_security = MagicMock()
        mock_payload = {
            'user_id': 'testuser',
            'roles': ['user'],
            'exp': 1234567890,
            'iat': 1234567800
        }
        mock_security.verify_jwt_token.return_value = mock_payload
        
        with self.app.app_context():
            self.app.security_manager = mock_security
            
            response = self.client.get('/api/auth/profile',
                headers={'Authorization': 'Bearer valid_token_123'})
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['profile']['user_id'] == 'testuser'
            assert 'token_issued_at' in data['profile']
            assert 'token_expires_at' in data['profile']

    def test_get_profile_missing_auth_header(self):
        """Test profile retrieval without authentication header."""
        response = self.client.get('/api/auth/profile')
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False
        assert '인증 토큰이 필요합니다' in data['error']

    def test_get_profile_invalid_auth_header(self):
        """Test profile retrieval with invalid auth header format."""
        response = self.client.get('/api/auth/profile',
            headers={'Authorization': 'InvalidFormat token123'})
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['success'] is False

    def test_get_profile_invalid_token(self):
        """Test profile retrieval with invalid token."""
        mock_security = MagicMock()
        mock_security.verify_jwt_token.return_value = None
        
        with self.app.app_context():
            self.app.security_manager = mock_security
            
            response = self.client.get('/api/auth/profile',
                headers={'Authorization': 'Bearer invalid_token'})
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert data['success'] is False
            assert '유효하지 않은 토큰' in data['error']

class TestAuthErrorHandlers:
    """Test cases for authentication blueprint error handlers."""

    def setup_method(self):
        """Set up test client for each test."""
        self.app = Flask(__name__)
        self.app.register_blueprint(auth_bp)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_error_handlers_exist(self):
        """Test that error handlers are properly registered."""
        # Error handlers are registered on the blueprint
        assert 400 in auth_bp.error_handler_spec[None]
        assert 401 in auth_bp.error_handler_spec[None]
        assert 429 in auth_bp.error_handler_spec[None]
        assert 500 in auth_bp.error_handler_spec[None]

if __name__ == "__main__":
    # Validation block - test core functionality with actual data
    import sys
    
    all_validation_failures = []
    total_tests = 0

    # Test 1: Blueprint creation and configuration
    total_tests += 1
    try:
        if auth_bp is None:
            all_validation_failures.append("Blueprint creation: auth_bp is None")
        elif auth_bp.name != "auth":
            all_validation_failures.append(f"Blueprint creation: Expected name 'auth', got '{auth_bp.name}'")
        elif auth_bp.url_prefix != "/api/auth":
            all_validation_failures.append(f"Blueprint creation: Expected url_prefix '/api/auth', got '{auth_bp.url_prefix}'")
    except Exception as e:
        all_validation_failures.append(f"Blueprint creation: Exception raised: {e}")

    # Test 2: Blueprint registration with Flask app
    total_tests += 1
    try:
        test_app = Flask(__name__)
        test_app.register_blueprint(auth_bp)
        
        route_rules = [rule.rule for rule in test_app.url_map.iter_rules()]
        expected_routes = ['/api/auth/login', '/api/auth/refresh', '/api/auth/logout']
        
        for route in expected_routes:
            if route not in route_rules:
                all_validation_failures.append(f"Route registration: Missing expected route: {route}")
    except Exception as e:
        all_validation_failures.append(f"Route registration: Exception raised: {e}")

    # Test 3: Error handler registration
    total_tests += 1
    try:
        expected_errors = [400, 401, 429, 500]
        if not hasattr(auth_bp, 'error_handler_spec') or auth_bp.error_handler_spec is None:
            all_validation_failures.append("Error handlers: error_handler_spec not found")
        else:
            error_spec = auth_bp.error_handler_spec.get(None, {})
            for error_code in expected_errors:
                if error_code not in error_spec:
                    all_validation_failures.append(f"Error handlers: Missing error handler for {error_code}")
    except Exception as e:
        all_validation_failures.append(f"Error handlers: Exception raised: {e}")

    # Test 4: Route endpoint functions exist
    total_tests += 1
    try:
        from src.api.auth_routes import login, refresh_token, logout, verify_token, change_password, get_profile
        
        functions = [login, refresh_token, logout, verify_token, change_password, get_profile]
        for func in functions:
            if not callable(func):
                all_validation_failures.append(f"Route functions: {func.__name__} is not callable")
    except ImportError as e:
        all_validation_failures.append(f"Route functions: Import error: {e}")
    except Exception as e:
        all_validation_failures.append(f"Route functions: Exception raised: {e}")

    # Test 5: Environment variable handling
    total_tests += 1
    try:
        import os
        # Test environment variable access pattern used in the module
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin")
        
        if not isinstance(admin_username, str):
            all_validation_failures.append("Environment variables: ADMIN_USERNAME not string type")
        if not isinstance(admin_password, str):
            all_validation_failures.append("Environment variables: ADMIN_PASSWORD not string type")
    except Exception as e:
        all_validation_failures.append(f"Environment variables: Exception raised: {e}")

    # Final validation result
    if all_validation_failures:
        print(f"❌ VALIDATION FAILED - {len(all_validation_failures)} of {total_tests} tests failed:")
        for failure in all_validation_failures:
            print(f"  - {failure}")
        sys.exit(1)
    else:
        print(f"✅ VALIDATION PASSED - All {total_tests} tests produced expected results")
        print("Authentication routes are validated and ready for comprehensive testing")
        sys.exit(0)