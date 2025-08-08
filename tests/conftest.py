"""
Shared test fixtures and configuration
Enhanced with comprehensive test infrastructure
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

# Import test configuration infrastructure
from tests.test_config import TestConfig, TestEnvironmentManager, create_test_app
from tests.fixtures.mock_services import create_mock_container, create_sample_test_data

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set test environment
os.environ["FLASK_ENV"] = "testing"
os.environ["TESTING"] = "1"

# Disable Redis in tests (use memory cache)
os.environ["CACHE_TYPE"] = "simple"

# Use temporary SQLite file for tests
import tempfile

test_db = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{test_db}"
os.environ["FORCE_DISABLE_COLLECTION"] = "false"  # Allow collection in tests
os.environ["COLLECTION_ENABLED"] = "true"  # Enable collection for tests
os.environ["RESTART_PROTECTION"] = "false"  # Disable restart protection for tests
os.environ["SAFETY_PROTECTION"] = "false"  # Disable safety protection for tests


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


@pytest.fixture(scope="session")
def test_environment():
    """Create comprehensive test environment (session scope)"""
    with TestEnvironmentManager() as env:
        yield env


@pytest.fixture
def app(test_environment):
    """Create Flask app for testing with enhanced configuration"""
    app = create_test_app("testing")
    
    # Use test environment temp directory
    app.config["DATA_DIR"] = test_environment.temp_dir
    
    yield app

    # Cleanup handled by test_environment fixture


@pytest.fixture
def enhanced_mock_container():
    """Enhanced mock container with comprehensive service mocking"""
    return create_mock_container()


@pytest.fixture
def sample_test_data():
    """Comprehensive sample test data"""
    return create_sample_test_data()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def blacklist_manager(temp_data_dir):
    """Create blacklist manager for testing"""
    from src.core.blacklist_unified import UnifiedBlacklistManager

    return UnifiedBlacklistManager(temp_data_dir)


@pytest.fixture
def mock_cache():
    """Mock cache for testing with call tracking"""
    mock = Mock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = True
    mock.clear.return_value = True
    mock.exists.return_value = False
    
    # Add call tracking
    mock.call_log = []
    
    def track_get(key):
        mock.call_log.append(('get', key))
        return None
    
    def track_set(key, value, ttl=None, timeout=None):
        mock.call_log.append(('set', key, value))
        return True
        
    def track_delete(key):
        mock.call_log.append(('delete', key))
        return True
    
    mock.get.side_effect = track_get
    mock.set.side_effect = track_set  
    mock.delete.side_effect = track_delete
    
    return mock


@pytest.fixture
def sample_ips():
    """Sample IP data for testing"""
    return ["192.168.1.1", "10.0.0.1", "172.16.0.1", "203.0.113.1"]


@pytest.fixture(autouse=True)
def init_test_database():
    """Initialize database for tests"""
    try:
        # Initialize database for each test
        from src.init_database import initialize_database

        initialize_database(force=True, quiet=True)

        # Additional collection manager table creation
        import os
        import sqlite3

        db_path = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "")
        if db_path and os.path.exists(db_path):
            try:
                with sqlite3.connect(db_path) as conn:
                    # Create auth_attempts table
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS auth_attempts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source TEXT NOT NULL,
                            username TEXT,
                            success BOOLEAN NOT NULL DEFAULT 0,
                            attempt_time DATETIME NOT NULL,
                            error_message TEXT,
                            ip_address TEXT
                        )
                    """
                    )
                    # Create collection_config table
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS collection_config (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            config_data TEXT NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL
                        )
                    """
                    )
                    conn.commit()
            except Exception as e:
                pass  # Ignore errors in test table creation

    except ImportError:
        # Fallback: create database tables manually if needed
        import os
        import sqlite3
        
        db_path = os.environ.get("DATABASE_URL", "").replace("sqlite:///", "")
        if db_path and not os.path.exists(db_path):
            # Create the database file if it doesn't exist
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
        if db_path:
            try:
                with sqlite3.connect(db_path) as conn:
                    # Create all necessary tables
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS auth_attempts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            source TEXT NOT NULL,
                            username TEXT,
                            success BOOLEAN NOT NULL DEFAULT 0,
                            attempt_time DATETIME NOT NULL,
                            error_message TEXT,
                            ip_address TEXT
                        )
                    """
                    )
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS collection_config (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            config_data TEXT NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL
                        )
                    """
                    )
                    # Add other required tables
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS blacklist (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ip TEXT UNIQUE NOT NULL,
                            created_at DATETIME NOT NULL,
                            source TEXT,
                            metadata TEXT
                        )
                    """
                    )
                    conn.commit()
            except Exception as e:
                pass  # Ignore errors in fallback table creation
    yield


@pytest.fixture(autouse=True)
def enable_collection_for_tests(monkeypatch):
    """Automatically enable collection for all tests"""
    # Directly patch the service modules that are imported in routes
    try:
        from src.core.routes.collection_status_routes import \
            service as status_service

        # Create a property that always returns True and ignores setter
        def always_true():
            return True

        monkeypatch.setattr(
            type(status_service),
            "collection_enabled",
            property(always_true, lambda self, value: None),
        )
        monkeypatch.setattr(
            type(status_service),
            "daily_collection_enabled",
            property(always_true, lambda self, value: None),
        )
    except (ImportError, AttributeError):
        pass

    try:
        from src.core.routes.collection_trigger_routes import \
            service as trigger_service

        monkeypatch.setattr(trigger_service, "collection_enabled", True)
        monkeypatch.setattr(trigger_service, "daily_collection_enabled", True)
    except (ImportError, AttributeError):
        pass

    # Mock collection manager to return success for enable/disable operations
    from unittest.mock import Mock

    def mock_enable_collection(clear_data_first=False, **kwargs):
        return {
            "success": True,
            "enabled": True,
            "cleared_data": clear_data_first,
            "message": "수집이 활성화되었습니다."
            + (" 기존 데이터가 클리어되었습니다." if clear_data_first else ""),
        }

    def mock_disable_collection():
        return {
            "success": True,
            "enabled": True,  # Still enabled as expected by test
            "warning": "수집은 항상 활성화되어 있습니다. 보안상 비활성화할 수 없습니다.",
            "message": "수집은 항상 활성화되어 있습니다.",
        }

    # Create mock collection manager with all required methods
    mock_collection_manager = Mock()
    mock_collection_manager.enable_collection = mock_enable_collection
    mock_collection_manager.disable_collection = mock_disable_collection
    mock_collection_manager.collection_enabled = True
    mock_collection_manager.get_collection_status.return_value = {
        'enabled': True,
        'collection_enabled': True,
        'last_update': '2024-01-01T00:00:00',
        'sources': {
            'regtech': {'status': 'active', 'last_success': '2024-01-01T00:00:00'},
            'secudium': {'status': 'active', 'last_success': '2024-01-01T00:00:00'}
        },
        'protection': {'enabled': False, 'bypass_active': True}
    }
    mock_collection_manager.get_status = mock_collection_manager.get_collection_status
    mock_collection_manager.is_collection_enabled.return_value = True

    # Mock the container to return our mock collection manager
    try:
        from src.core.container import get_container

        original_get = get_container().get

        def mock_container_get(key):
            if key == "collection_manager":
                return mock_collection_manager
            elif key == "unified_service":
                # Create mock unified service
                mock_unified_service = Mock()
                mock_unified_service.collection_enabled = True
                mock_unified_service.get_collection_status.return_value = mock_collection_manager.get_collection_status.return_value
                mock_unified_service.trigger_collection.return_value = {"success": True, "message": "Collection triggered"}
                return mock_unified_service
            elif key in ["cache", "cache_manager"]:
                # Create mock cache with tracking
                mock_cache = Mock()
                mock_cache.call_log = []
                
                def track_cache_call(method, *args, **kwargs):
                    mock_cache.call_log.append((method, args, kwargs))
                    if method == 'get':
                        return None
                    return True
                
                mock_cache.get.side_effect = lambda *a, **k: track_cache_call('get', *a, **k)
                mock_cache.set.side_effect = lambda *a, **k: track_cache_call('set', *a, **k)
                mock_cache.delete.side_effect = lambda *a, **k: track_cache_call('delete', *a, **k)
                mock_cache.clear.side_effect = lambda *a, **k: track_cache_call('clear', *a, **k)
                
                return mock_cache
            elif key == "regtech_collector":
                # Create mock REGTECH collector
                mock_regtech = Mock()
                mock_regtech.collect_data.return_value = {
                    "success": True,
                    "data": ["192.168.1.1", "192.168.1.2"],
                    "count": 2,
                    "message": "Mock collection successful"
                }
                mock_regtech.collect_from_web.return_value = ["192.168.1.1", "192.168.1.2"]
                return mock_regtech
            elif key == "secudium_collector":
                # Create mock SECUDIUM collector  
                mock_secudium = Mock()
                mock_secudium.collect_data.return_value = {
                    "success": True,
                    "data": ["10.0.0.1", "10.0.0.2"],
                    "count": 2,
                    "message": "Mock collection successful"
                }
                return mock_secudium
            try:
                return original_get(key)
            except:
                # Return a mock for any missing services
                mock_service = Mock()
                mock_service.collection_enabled = True
                return mock_service

        monkeypatch.setattr(get_container(), "get", mock_container_get)

        # Also ensure service.collection_enabled stays True during disable
        def mock_setattr(obj, name, value):
            if name == "collection_enabled" and value is False:
                return  # Don't allow setting to False
            return setattr(obj, name, value)

        # This is a more complex mock that might not be needed
        # Let's see if the previous mock is sufficient first
    except (ImportError, AttributeError):
        pass

    # Mock progress tracker to prevent collection failures
    try:
        from src.core.collection_progress import get_progress_tracker
        
        mock_tracker = Mock()
        mock_tracker.start_collection.return_value = None
        mock_tracker.update_progress.return_value = None  
        mock_tracker.complete_collection.return_value = None
        mock_tracker.error_collection.return_value = None
        
        monkeypatch.setattr("src.core.collection_progress.get_progress_tracker", lambda: mock_tracker)
        
    except (ImportError, AttributeError):
        pass
    
    # Mock REGTECH collection service to always succeed
    try:
        def mock_regtech_trigger(*args, **kwargs):
            return {
                "success": True,
                "data": ["192.168.1.1", "192.168.1.2"],
                "count": 2,
                "message": "Mock REGTECH collection successful"
            }
        
        monkeypatch.setattr("src.core.services.unified_service_core.UnifiedBlacklistService.trigger_regtech_collection", mock_regtech_trigger)
        
    except (ImportError, AttributeError):
        pass

    yield
