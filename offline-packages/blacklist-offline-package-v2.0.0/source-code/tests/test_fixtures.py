"""테스트용 픽스쳐 모듈"""

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


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

    class SimpleMockCache:
        def __init__(self):
            self.cache = {}
            self.call_log = []

        def get(self, key):
            self.call_log.append(("get", key))
            return self.cache.get(key)

        def set(self, key, value, ex=None):
            self.call_log.append(("set", key, value))
            self.cache[key] = value
            return True

        def delete(self, key):
            self.call_log.append(("delete", key))
            return self.cache.pop(key, None) is not None

        def exists(self, key):
            return key in self.cache

        def flushdb(self):
            self.cache.clear()
            return True

    mock = SimpleMockCache()
    monkeypatch.setattr("redis.Redis", lambda **kwargs: mock)
    return mock


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory for tests"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def enhanced_mock_container():
    """Enhanced mock container with comprehensive service mocking"""
    container = Mock()

    # Basic mock services
    services = {
        "unified_service": Mock(),
        "blacklist_manager": Mock(),
        "collection_manager": Mock(),
        "cache_manager": Mock(),
        "cache": Mock(),
    }

    def mock_get(service_name):
        return services.get(service_name, Mock())

    container.get.side_effect = mock_get
    return container


@pytest.fixture
def sample_test_data():
    """Comprehensive sample test data"""
    return {
        "sample_ips": [
            "192.168.1.100",
            "192.168.1.101",
            "192.168.1.102",
            "10.0.0.100",
            "10.0.0.101",
            "172.16.1.100",
            "203.0.113.100",
            "198.51.100.100",
        ],
        "blacklist_data": [
            {
                "ip": "192.168.1.100",
                "source": "REGTECH",
                "detection_date": "2024-01-01",
                "metadata": {"severity": "high", "category": "malware"},
            },
            {
                "ip": "10.0.0.100",
                "source": "SECUDIUM",
                "detection_date": "2024-01-02",
                "metadata": {"severity": "medium", "category": "spam"},
            },
        ],
    }


@pytest.fixture
def mock_cache():
    """Mock cache for testing with call tracking"""

    class SimpleMockCache:
        def __init__(self):
            self.cache = {}
            self.call_log = []

        def get(self, key):
            self.call_log.append(("get", key))
            return self.cache.get(key)

        def set(self, key, value, ttl=None, timeout=None):
            self.call_log.append(("set", key, value))
            self.cache[key] = value
            return True

        def delete(self, key):
            self.call_log.append(("delete", key))
            return self.cache.pop(key, None) is not None

        def clear(self):
            self.call_log.append(("clear",))
            self.cache.clear()
            return True

        def exists(self, key):
            return key in self.cache

    return SimpleMockCache()


@pytest.fixture
def sample_ips():
    """Sample IP data for testing"""
    return ["192.168.1.1", "10.0.0.1", "172.16.0.1", "203.0.113.1"]


@pytest.fixture
def blacklist_manager(temp_data_dir):
    """Create blacklist manager for testing"""
    from src.core.blacklist_unified import UnifiedBlacklistManager

    return UnifiedBlacklistManager(temp_data_dir)
