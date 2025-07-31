"""
Shared test fixtures and configuration
"""
import pytest
import sys
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "1"

# Disable Redis in tests (use memory cache)
os.environ["CACHE_TYPE"] = "simple"


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment after each test"""
    yield
    # Clean up any test-specific environment variables
    for key in list(os.environ.keys()):
        if key.startswith("TEST_"):
            os.environ.pop(key)


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis for testing"""

    class MockRedis:
        def __init__(self):
            self.data = {}

        def get(self, key):
            return self.data.get(key)

        def set(self, key, value, ex=None):
            self.data[key] = value
            return True

        def delete(self, key):
            return self.data.pop(key, None) is not None

        def exists(self, key):
            return key in self.data

        def flushdb(self):
            self.data.clear()

    mock = MockRedis()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: mock)
    return mock


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def app():
    """Create Flask app for testing"""
    from core.app_compact import create_compact_app

    app = create_compact_app("testing")
    app.config["TESTING"] = True
    app.config["DATA_DIR"] = tempfile.mkdtemp()

    yield app

    # Cleanup
    if "DATA_DIR" in app.config:
        shutil.rmtree(app.config["DATA_DIR"], ignore_errors=True)


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def blacklist_manager(temp_data_dir):
    """Create blacklist manager for testing"""
    from core.blacklist_unified import UnifiedBlacklistManager

    return UnifiedBlacklistManager(temp_data_dir)


@pytest.fixture
def mock_cache():
    """Mock cache for testing"""
    mock = Mock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    return mock


@pytest.fixture
def sample_ips():
    """Sample IP data for testing"""
    return ["192.168.1.1", "10.0.0.1", "172.16.0.1", "203.0.113.1"]
