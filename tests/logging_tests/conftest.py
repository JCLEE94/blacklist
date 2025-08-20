#!/usr/bin/env python3
"""
Logging Test Configuration and Fixtures

Common test fixtures and setup for logging test modules.
"""

import json
import logging
import os
import sqlite3
import tempfile
import threading
import time
import unittest
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from src.utils.structured_logging import BufferHandler
from src.utils.structured_logging import LogManager
from src.utils.structured_logging import StructuredLogger
from src.utils.structured_logging import get_logger
from src.utils.structured_logging import log_manager
from src.utils.structured_logging import setup_request_logging


@pytest.fixture
def temp_log_dir():
    """Temporary log directory fixture"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup handled by system temp cleanup


@pytest.fixture
def logger_name():
    """Test logger name fixture"""
    return "test_logger"


@pytest.fixture
def structured_logger(temp_log_dir, logger_name):
    """StructuredLogger instance fixture"""
    return StructuredLogger(logger_name, temp_log_dir)


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
    request.method = "GET"
    request.path = "/test"
    request.remote_addr = "127.0.0.1"
    request.user_agent = Mock()
    request.user_agent.string = "test-agent"
    return request


@pytest.fixture
def mock_response():
    """Mock Flask response for testing"""
    response = Mock()
    response.status_code = 200
    response.content_length = 1024
    return response
