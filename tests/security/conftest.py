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
from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import jwt
import pytest

# Test imports
from src.utils.security import SecurityHeaders
from src.utils.security import SecurityManager
from src.utils.security import generate_csrf_token
from src.utils.security import get_security_manager
from src.utils.security import input_validation
from src.utils.security import rate_limit
from src.utils.security import require_api_key
from src.utils.security import require_auth
from src.utils.security import require_permission
from src.utils.security import sanitize_input
from src.utils.security import security_check
from src.utils.security import setup_security
from src.utils.security import validate_csrf_token


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
