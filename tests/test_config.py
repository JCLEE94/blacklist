"""
Comprehensive test configuration and utilities
Manages test environment setup, configuration, and utilities
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Dict
from unittest.mock import patch


class TestConfigManager:
    """Centralized test configuration management"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_root = Path(__file__).parent
        self.temp_dir = tempfile.mkdtemp(prefix="blacklist_test_")
        self.test_db_path = os.path.join(self.temp_dir, "test.db")

        # Ensure src is in Python path
        src_path = str(self.project_root / "src")
        if src_path not in sys.path:
            sys.path.insert(0, src_path)

        # Ensure project root is in Python path
        if str(self.project_root) not in sys.path:
            sys.path.insert(0, str(self.project_root))

    def get_test_env_vars(self) -> Dict[str, str]:
        """Get comprehensive test environment variables"""
        return {
            # Flask/Application
            "FLASK_ENV": "testing",
            "TESTING": "1",
            "DEBUG": "true",
            # Database
            "DATABASE_URL": "sqlite:///{self.test_db_path}",
            "TEST_DATABASE_URL": "sqlite:///{self.test_db_path}",
            # Cache
            "CACHE_TYPE": "simple",
            "REDIS_URL": "redis://localhost:6380/0",  # Different port for testing
            # Security (disabled for testing)
            "FORCE_DISABLE_COLLECTION": "false",
            "COLLECTION_ENABLED": "true",
            "RESTART_PROTECTION": "false",
            "SAFETY_PROTECTION": "false",
            "SECRET_KEY": "test-secret-key-for-testing-only",
            # Auth limits (higher for tests)
            "MAX_AUTH_ATTEMPTS": "100",
            # Mock credentials
            "REGTECH_USERNAME": "test_regtech",
            "REGTECH_PASSWORD": "test_pass",
            "SECUDIUM_USERNAME": "test_secudium",
            "SECUDIUM_PASSWORD": "test_pass",
            # Paths
            "PYTHONPATH": "{self.project_root}:{self.project_root / 'src'}",
            "DATA_DIR": self.temp_dir,
        }

    def setup_test_environment(self):
        """Setup complete test environment"""
        # Set environment variables
        for key, value in self.get_test_env_vars().items():
            os.environ[key] = value

        # Create test database
        self.create_test_database()

        # Create necessary directories
        os.makedirs(os.path.join(self.temp_dir, "data"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "cache"), exist_ok=True)

    def create_test_database(self):
        """Create and initialize test database"""
        try:
            with sqlite3.connect(self.test_db_path) as conn:
                # Create tables
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS blacklist (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        ip TEXT UNIQUE NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        source TEXT,
                        metadata TEXT,
                        detection_date DATE,
                        is_active BOOLEAN DEFAULT 1
                    );

                    CREATE TABLE IF NOT EXISTS auth_attempts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        username TEXT,
                        success BOOLEAN NOT NULL DEFAULT 0,
                        attempt_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        error_message TEXT,
                        ip_address TEXT
                    );

                    CREATE TABLE IF NOT EXISTS collection_config (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        config_data TEXT NOT NULL,
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE IF NOT EXISTS collection_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source TEXT NOT NULL,
                        status TEXT NOT NULL,
                        message TEXT,
                        data_count INTEGER DEFAULT 0,
                        collection_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        duration_seconds INTEGER DEFAULT 0
                    );

                    CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON blacklist(ip);
                    CREATE INDEX IF NOT EXISTS idx_blacklist_source ON blacklist(source);
                    CREATE INDEX IF NOT EXISTS idx_blacklist_created_at ON blacklist(created_at);
                    CREATE INDEX IF NOT EXISTS idx_auth_attempts_source ON auth_attempts(source);
                    CREATE INDEX IF NOT EXISTS idx_collection_logs_source ON collection_logs(source);
                """
                )

                # Insert test data
                conn.executescript(
                    """
                    INSERT OR IGNORE INTO blacklist (ip, source, metadata, detection_date) VALUES
                        ('192.168.1.100', 'REGTECH', '{"severity": "high", "category": "malware"}', '2024-01-01'),
                        ('10.0.0.100', 'SECUDIUM', '{"severity": "medium", "category": "spam"}', '2024-01-02'),
                        ('172.16.0.100', 'MANUAL', '{"severity": "low", "category": "suspicious"}', '2024-01-03');

                    INSERT OR IGNORE INTO collection_logs (source, status, message, data_count, duration_seconds) VALUES
                        ('REGTECH', 'success', 'Test collection successful', 100, 30),
                        ('SECUDIUM', 'success', 'Test collection successful', 150, 45);
                """
                )

                conn.commit()
        except Exception as e:
            print("Warning: Failed to create test database: {e}")

    def cleanup(self):
        """Clean up test environment"""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class TestEnvironmentManager:
    """Manages test environment context"""

    def __init__(self):
        self.config = TestConfigManager()
        self.original_env = {}
        self.patches = []

    def __enter__(self):
        # Save original environment
        for key in self.config.get_test_env_vars().keys():
            if key in os.environ:
                self.original_env[key] = os.environ[key]

        # Setup test environment
        self.config.setup_test_environment()

        return self.config

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original environment
        for key, value in self.original_env.items():
            os.environ[key] = value

        # Remove test-only environment variables
        for key in self.config.get_test_env_vars().keys():
            if key not in self.original_env and key in os.environ:
                del os.environ[key]

        # Clean up patches
        for patch_obj in self.patches:
            patch_obj.stop()

        # Clean up test files
        self.config.cleanup()


class TestConfig:
    """Test configuration wrapper class"""

    def __init__(self):
        self.config = TestConfigManager()

    def cleanup(self):
        """Clean up test configuration"""
        if hasattr(self.config, "cleanup"):
            self.config.cleanup()


def get_test_config() -> TestConfig:
    """Get test configuration instance"""
    return TestConfig()


def pytest_configure():
    """Configure pytest with test settings"""
    config = TestConfig()
    config.setup_test_environment()


def mock_external_services():
    """Apply comprehensive mocks for external services"""

    patches = []

    # Create simple mock collectors
    class MockREGTECHCollector:
        def collect_data(self, start_date=None, end_date=None):
            return {
                "success": True,
                "data": ["192.168.1.100", "192.168.1.101"],
                "count": 2,
                "message": "Mock collection successful",
            }

    class MockSECUDIUMCollector:
        def collect_data(self, **kwargs):
            return {
                "success": True,
                "data": ["10.0.0.100", "10.0.0.101"],
                "count": 2,
                "message": "Mock collection successful",
            }

    class MockCacheManager:
        def __init__(self):
            self.cache = {}

        def get(self, key):
            return self.cache.get(key)

        def set(self, key, value, ttl=None, timeout=None):
            self.cache[key] = value
            return True

        def delete(self, key):
            return self.cache.pop(key, None) is not None

    # Mock REGTECH collector
    regtech_mock = MockREGTECHCollector()
    patches.append(
        patch(
            "src.core.collectors.regtech_collector.REGTECHCollector",
            return_value=regtech_mock,
        )
    )

    # Mock SECUDIUM collector
    secudium_mock = MockSECUDIUMCollector()
    patches.append(
        patch(
            "src.core.collectors.secudium_collector.SECUDIUMCollector",
            return_value=secudium_mock,
        )
    )

    # Mock cache manager
    cache_mock = MockCacheManager()
    patches.append(patch("src.utils.cache_utils.CacheManager", return_value=cache_mock))

    # Start all patches
    for patch_obj in patches:
        patch_obj.start()

    return patches


def create_test_app(config_name: str = "testing"):
    """Create Flask app for testing with proper configuration"""
    try:
        from src.core.app_compact import create_compact_app

        app = create_compact_app(config_name)
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for testing

        # Override data directory
        test_config = TestConfig()
        app.config["DATA_DIR"] = test_config.temp_dir

        return app

    except ImportError as e:
        print("Warning: Could not import app_compact: {e}")
        # Fallback to minimal app
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True
        return app


def assert_response_format(response, expected_keys: list, status_code: int = 200):
    """Assert response format and content"""
    assert (
        response.status_code == status_code
    ), "Expected {status_code}, got {response.status_code}"

    if response.is_json:
        data = response.get_json()
        for key in expected_keys:
            assert key in data, "Expected key '{key}' not found in response"


def create_test_data(count: int = 10) -> list:
    """Create test IP data"""
    return ["192.168.1.{i}" for i in range(1, count + 1)]


# Type aliases for public interface
# Legacy aliases removed - use TestConfig and TestEnvironmentManager directly

# Global test configuration instance
TEST_CONFIG = get_test_config()
