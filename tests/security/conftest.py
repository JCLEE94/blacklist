#!/usr/bin/env python3
"""
Security Test Configuration and Fixtures

Common test fixtures and setup for security test modules.
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


@pytest.fixture
def secret_key():
    """Test secret key fixture"""
    return "test_secret_key_123"


@pytest.fixture
def jwt_secret():
    """Test JWT secret fixture"""
    return "test_jwt_secret_456"


@pytest.fixture
def security_manager(secret_key, jwt_secret):
    """SecurityManager instance fixture"""
    return SecurityManager(secret_key, jwt_secret)


@pytest.fixture
def mock_flask_app():
    """Mock Flask app for testing"""
    app = Mock()
    app.config = {}
    return app


@pytest.fixture
def mock_request():
    """Mock Flask request for testing"""
    request = Mock()
    request.headers = {}
    request.remote_addr = "127.0.0.1"
    request.method = "GET"
    request.path = "/test"
    return request
